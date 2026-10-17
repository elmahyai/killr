//! Mixed-model decomposition, likelihood, EM, and the Newton step.
//!
//! Ported from the `mixed_*` routines in nlme `src/nlmefit.c`. Matrices are
//! column-major. `optif9` is R's Dennis–Schnabel minimizer; both call sites
//! force a finite-difference gradient (`iagflg = 0`).

use std::os::raw::{c_int, c_void};

use crate::dims::Dims;
use crate::linalg::{
    chol_factor, comp_symm_pd, copy_mat, copy_trans, d_axpy, d_dot, d_sum_sqr, dtrsl_upper,
    dtrsl_upper_sep, log_chol_pd, matrix_log_pd, mult_into, plus_equals_mat, qr_factor,
    qr_log_abs_det, qr_qty_inplace, qr_solve_into, qr_store_r, scale_mat, zero_mat,
};
use crate::optif::{dummy_grad, optif9};

#[derive(Debug)]
pub struct KernelError(pub String);

struct Store<'a> {
    dc: &'a mut [f64],
    at: usize,
    ld: usize,
}

fn qr_and_rotate(
    mat: &mut [f64],
    mat0: usize,
    ldmat: usize,
    nrow: usize,
    ncol: usize,
    dm_half: &[f64],
    dm0: usize,
    qi: usize,
    ndecomp: usize,
    logdet: Option<&mut f64>,
    store: Option<Store<'_>>,
) -> usize {
    let arow = nrow + qi;
    if arow == 0 || ncol == 0 || ndecomp == 0 {
        return 0;
    }
    let ndrow = arow.min(ndecomp);
    let mut aug = vec![0.0; arow * ncol];
    if nrow > 0 {
        copy_mat(&mut aug, arow, 0, mat, ldmat, mat0, nrow, ncol);
    }
    if qi > 0 {
        copy_mat(&mut aug, arow, nrow, dm_half, qi, dm0, qi, qi.min(ncol));
    }
    let qr = qr_factor(&mut aug, arow, arow, ndecomp);
    if let Some(slot) = logdet {
        *slot += qr_log_abs_det(&aug, &qr);
    }
    for col in ndecomp..ncol {
        let mut y = vec![0.0; arow];
        for r in 0..arow {
            y[r] = aug[r + col * arow];
        }
        qr_qty_inplace(&mut aug, &qr, &mut y);
        for r in 0..arow {
            aug[r + col * arow] = y[r];
        }
    }
    if let Some(store) = store {
        if store.ld > 0 {
            qr_store_r(&aug, &qr, store.dc, store.ld, store.at);
            let cols = ncol - ndecomp;
            if ndrow > 0 && cols > 0 {
                copy_mat(
                    store.dc,
                    store.ld,
                    store.at + ndecomp * store.ld,
                    &aug,
                    arow,
                    ndecomp * arow,
                    ndrow,
                    cols,
                );
            }
        }
    }
    if qi < ndecomp {
        zero_mat(mat, ldmat, mat0, nrow, ncol);
    }
    let rows = arow - ndrow;
    let cols = ncol.saturating_sub(ndecomp);
    if rows > 0 && cols > 0 {
        copy_mat(
            mat,
            ldmat,
            mat0 + ndecomp * ldmat,
            &aug,
            arow,
            ndecomp * (arow + 1),
            rows,
            cols,
        );
    }
    qr.rank
}

pub fn count_dm_half_pars(dims: &Dims, pd_class: &[i32]) -> usize {
    let mut result = 0usize;
    for i in 0..dims.q as usize {
        let q = dims.qvec[i];
        match pd_class[i] {
            0 | 4 => result += (q * (q + 1) / 2) as usize,
            1 => result += q as usize,
            2 => result += 1,
            3 => result += 2,
            _ => {}
        }
    }
    result
}

pub fn generate_dm_half(dm: &mut [f64], dims: &Dims, pd_class: &[i32], pars: &[f64]) {
    let mut p = 0usize;
    for i in 0..dims.q as usize {
        let q = dims.qvec[i] as usize;
        let off = dims.dm_off[i] as usize;
        match pd_class[i] {
            0 => {
                let m = matrix_log_pd(&pars[p..], q);
                dm[off..off + q * q].copy_from_slice(&m);
                p += q * (q + 1) / 2;
            }
            1 => {
                dm[off..off + q * q].fill(0.0);
                for j in 0..q {
                    dm[off + j * (q + 1)] = pars[p].exp();
                    p += 1;
                }
            }
            2 => {
                dm[off..off + q * q].fill(0.0);
                let diag = pars[p].exp();
                p += 1;
                for j in 0..q {
                    dm[off + j * (q + 1)] = diag;
                }
            }
            3 => {
                let m = comp_symm_pd(&pars[p..], q);
                dm[off..off + q * q].copy_from_slice(&m);
                p += 2;
            }
            4 => {
                let m = log_chol_pd(&pars[p..], q);
                dm[off..off + q * q].copy_from_slice(&m);
                p += q * (q + 1) / 2;
            }
            _ => {}
        }
    }
}

fn crossprod(y: &mut [f64], ldy: usize, x: &[f64], ldx: usize, nrow: usize, ncol: usize) {
    for i in 0..ncol {
        y[i + i * ldy] = d_dot(x, i * ldx, 1, x, i * ldx, 1, nrow);
        for j in 0..i {
            let v = d_dot(x, i * ldx, 1, x, j * ldx, 1, nrow);
            y[j + i * ldy] = v;
            y[i + j * ldy] = v;
        }
    }
}

pub fn generate_theta(theta: &mut [f64], dims: &Dims, pd_class: &[i32], dm_half: &mut [f64]) -> Result<(), KernelError> {
    let mut t = 0usize;
    for i in 0..dims.q as usize {
        let q = dims.qvec[i] as usize;
        let off = dims.dm_off[i] as usize;
        match pd_class[i] {
            0 => {
                delta_to_matrix_log(&mut theta[t..], q, &dm_half[off..off + q * q])?;
                t += q * (q + 1) / 2;
            }
            1 => {
                for j in 0..q {
                    theta[t] = dm_half[off + j * (q + 1)].ln();
                    t += 1;
                }
            }
            2 => {
                theta[t] = dm_half[off].ln();
                t += 1;
            }
            3 => {
                return Err(KernelError(
                    "compound symmetry has no parameter map in generate_theta".to_string(),
                ));
            }
            4 => {
                delta_to_log_chol(&mut theta[t..], q, &mut dm_half[off..off + q * q])?;
                t += q * (q + 1) / 2;
            }
            _ => {}
        }
    }
    Ok(())
}

fn delta_to_matrix_log(theta: &mut [f64], q: usize, delta: &[f64]) -> Result<(), KernelError> {
    if q == 1 {
        theta[0] = (delta[0] * delta[0]).ln() / 2.0;
        return Ok(());
    }
    let mut dtd = vec![0.0; q * q];
    crossprod(&mut dtd, q, delta, q, q, q);
    let (values, vectors) = crate::linalg::jacobi_sym(&mut dtd, q);
    let mut work = vec![0.0; q * q];
    copy_mat(&mut work, q, 0, &vectors, q, 0, q, q);
    for i in 0..q {
        let lv = values[i].ln() / 2.0;
        for j in 0..q {
            work[j + i * q] *= lv;
        }
    }
    let mut trans = vec![0.0; q * q];
    copy_trans(&mut trans, q, 0, &work, q, 0, q, q);
    let mut prod = vec![0.0; q * q];
    mult_into(&mut prod, q, 0, &vectors, q, 0, q, q, &trans, q, 0, q);
    let mut pt = 0usize;
    for i in 0..q {
        for j in 0..=i {
            theta[pt] = prod[j + i * q];
            pt += 1;
        }
    }
    Ok(())
}

fn delta_to_log_chol(theta: &mut [f64], q: usize, delta: &mut [f64]) -> Result<(), KernelError> {
    if q == 1 {
        theta[0] = (delta[0] * delta[0]).ln() / 2.0;
        return Ok(());
    }
    let mut dtd = vec![0.0; q * q];
    crossprod(&mut dtd, q, delta, q, q, q);
    let factor = chol_factor(&dtd, q, q).map_err(|info| {
        KernelError(format!("Cholesky failed for log-Cholesky map, info {info}"))
    })?;
    delta[..q * q].copy_from_slice(&factor);
    theta[0] = delta[0].ln();
    let mut ll = q;
    for i in 1..q {
        theta[i] = delta[i * (q + 1)].ln();
        theta[ll..ll + i].copy_from_slice(&delta[i * q..i * q + i]);
        ll += i;
    }
    Ok(())
}

pub(crate) fn internal_decomp(dims: &mut Dims, zxy: &mut [f64]) {
    if dims.s_rows >= dims.zx_rows {
        return;
    }
    let srows = dims.s_rows as usize;
    let zxcols = dims.zx_cols as usize;
    let mut dc = vec![0.0; srows * zxcols];
    let qp2 = dims.qp2();
    for i in 0..qp2 {
        let ngrp = dims.ngrp[i] as usize;
        for j in 0..ngrp {
            let off = dims.grp(&dims.zx_off.clone(), i, j) as usize;
            let len = dims.grp(&dims.zx_len.clone(), i, j) as usize;
            let sto = dims.grp(&dims.st_off.clone(), i, j) as usize;
            let ncol = dims.ncol[i] as usize;
            let nrot = dims.nrot[i] as usize;
            let zx_rows = dims.zx_rows as usize;
            qr_and_rotate(
                zxy,
                off,
                zx_rows,
                len,
                ncol + nrot,
                &[],
                0,
                0,
                ncol,
                None,
                Some(Store {
                    dc: &mut dc,
                    at: sto,
                    ld: srows,
                }),
            );
        }
    }
    let ncopy = srows * zxcols;
    zxy[..ncopy].copy_from_slice(&dc[..ncopy]);
    for i in 0..qp2 {
        let ngrp = dims.ngrp[i] as usize;
        for j in 0..ngrp {
            let pos = dims.pos[i] + j;
            let dec_off = dims.dec_off[pos];
            let dec_len = dims.dec_len[pos];
            dims.zx_off[pos] = dec_off;
            dims.zx_len[pos] = dec_len;
        }
    }
    dims.zx_rows = dims.s_rows;
}

fn level_loglik(
    dims: &Dims,
    zxy: &mut [f64],
    dm_half: &[f64],
    mut store: Option<&mut [f64]>,
) -> Result<Vec<f64>, KernelError> {
    let qp2 = dims.qp2();
    let mut lglk = vec![0.0; qp2];
    let zx_rows = dims.zx_rows as usize;
    let srows = dims.s_rows as usize;
    for i in 0..qp2 {
        let qi = dims.qvec[i] as usize;
        let ngrp = dims.ngrp[i] as usize;
        let ncol = dims.ncol[i] as usize;
        let nrot = dims.nrot[i] as usize;
        let dm_off = dims.dm_off[i] as usize;
        for j in 0..ngrp {
            let off = dims.grp(&dims.zx_off, i, j) as usize;
            let len = dims.grp(&dims.zx_len, i, j) as usize;
            let sto = dims.grp(&dims.st_off, i, j) as usize;
            let store_arg = store.as_deref_mut().map(|dc| Store {
                dc,
                at: sto,
                ld: srows,
            });
            let rank = qr_and_rotate(
                zxy,
                off,
                zx_rows,
                len,
                ncol + nrot,
                dm_half,
                dm_off,
                qi,
                ncol,
                Some(&mut lglk[i]),
                store_arg,
            );
            if qi > rank {
                return Err(KernelError("singular precision".to_string()));
            }
        }
    }
    Ok(lglk)
}

pub(crate) fn internal_loglik(
    dims: &Dims,
    zxy: &mut [f64],
    dm_half: &[f64],
    rml: i32,
    mut store: Option<&mut [f64]>,
    sigma: f64,
) -> f64 {
    let lglk = match level_loglik(dims, zxy, dm_half, store.as_deref_mut()) {
        Ok(v) => v,
        Err(_) => return -f64::MAX,
    };
    let q = dims.q as usize;
    let mut accum = 0.0;
    for i in 0..q {
        let qi = dims.qvec[i] as usize;
        if qi == 0 {
            continue;
        }
        let off = dims.dm_off[i] as usize;
        let mut block = vec![0.0; qi * qi];
        copy_mat(&mut block, qi, 0, dm_half, qi, off, qi, qi);
        let qr = qr_factor(&mut block, qi, qi, qi);
        accum += dims.ngrp[i] as f64 * qr_log_abs_det(&block, &qr) - lglk[i];
    }
    let ncol_q = dims.ncol[q] as f64;
    if sigma > 0.0 {
        let mut h = 0.0;
        if rml == 1 {
            h += (lglk[q] - ncol_q * lglk[q + 1]) - 1.0;
        }
        accum -= lglk[q + 1].exp().powi(2) / (2.0 * sigma * sigma);
        accum -= (dims.n - dims.ncol[q]) as f64 * sigma.ln();
        accum -= h;
    } else {
        accum -= rml as f64 * lglk[q] + (dims.n - rml * dims.ncol[q]) as f64 * lglk[q + 1];
    }
    let _ = store;
    accum
}

pub(crate) fn internal_loglik_rss(
    dims: &Dims,
    zxy: &mut [f64],
    dm_half: &[f64],
    rml: i32,
    store: Option<&mut [f64]>,
    sigma: f64,
) -> (f64, f64) {
    let lglk_holder = level_loglik(dims, zxy, dm_half, store);
    let lglk = match lglk_holder {
        Ok(v) => v,
        Err(_) => return (-f64::MAX, 0.0),
    };
    let q = dims.q as usize;
    let lrss = lglk[q + 1];
    let mut accum = 0.0;
    for i in 0..q {
        let qi = dims.qvec[i] as usize;
        if qi == 0 {
            continue;
        }
        let off = dims.dm_off[i] as usize;
        let mut block = vec![0.0; qi * qi];
        copy_mat(&mut block, qi, 0, dm_half, qi, off, qi, qi);
        let qr = qr_factor(&mut block, qi, qi, qi);
        accum += dims.ngrp[i] as f64 * qr_log_abs_det(&block, &qr) - lglk[i];
    }
    let ncol_q = dims.ncol[q] as f64;
    if sigma > 0.0 {
        let mut h = 0.0;
        if rml == 1 {
            h += (lglk[q] - ncol_q * lglk[q + 1]) - 1.0;
        }
        accum -= lglk[q + 1].exp().powi(2) / (2.0 * sigma * sigma);
        accum -= (dims.n - dims.ncol[q]) as f64 * sigma.ln();
        accum -= h;
    } else {
        accum -= rml as f64 * lglk[q] + (dims.n - rml * dims.ncol[q]) as f64 * lglk[q + 1];
    }
    (accum, lrss)
}

fn backsolve(dc: &mut [f64], base: isize, ld: isize, nupdate: isize, ncol: isize, nrot: isize, ny: isize) -> i32 {
    let mut info = 0;
    let mut y = base + (ncol + nrot - ny) * ld;
    let mat0 = base - nupdate;
    for _ in 0..ny {
        info = dtrsl_upper(dc, (mat0 + nupdate) as usize, ld as usize, ncol as usize, y as usize);
        if info != 0 {
            return info;
        }
        for j in 0..ncol {
            let yj = dc[(y as usize) + (j as usize)];
            let dest = (y - nupdate) as usize;
            let src = (mat0 + j * ld) as usize;
            let nup = nupdate as usize;
            for i in 0..nup {
                dc[dest + i] += -yj * dc[src + i];
            }
        }
        y += ld;
    }
    info
}

pub(crate) fn internal_estimate(dims: &Dims, dc: &mut [f64]) -> Result<(), KernelError> {
    let q = dims.q as usize;
    let ld = dims.s_rows as isize;
    for i in (0..=q).rev() {
        let ngrp = dims.ngrp[i] as usize;
        for j in 0..ngrp {
            let sto = dims.grp(&dims.st_off, i, j) as isize;
            let dec = dims.grp(&dims.dec_off, i, j) as isize;
            let info = backsolve(
                dc,
                sto,
                ld,
                sto - dec,
                dims.ncol[i] as isize,
                dims.nrot[i] as isize,
                dims.ncol[q + 1] as isize,
            );
            if info != 0 {
                return Err(KernelError(format!(
                    "singularity in backsolve at level {}, block {}",
                    i as i32 - dims.q,
                    j + 1
                )));
            }
        }
    }
    Ok(())
}

fn invert_upper(mat: &mut [f64], mat0: usize, ld: usize, ncol: usize) -> i32 {
    if ncol == 0 {
        return 0;
    }
    let mut b = vec![0.0; ncol];
    for i in (2..=ncol).rev() {
        for j in 0..(i - 1) {
            b[j] = 0.0;
        }
        b[i - 1] = 1.0;
        let info = dtrsl_upper_sep(mat, mat0, ld, i, &mut b[..i]);
        if info != 0 {
            return info;
        }
        for r in 0..i {
            mat[mat0 + r + (i - 1) * ld] = b[r];
        }
    }
    if mat[mat0] == 0.0 {
        return 1;
    }
    mat[mat0] = 1.0 / mat[mat0];
    0
}

fn invert_block(dc: &mut [f64], mat: usize, ld: usize, nabove: usize, ncol: usize, nright: isize) -> i32 {
    let info = invert_upper(dc, mat, ld, ncol);
    if info != 0 {
        return info;
    }
    if nright > 0 {
        let nright = nright as usize;
        let mut ntri = vec![0.0; ncol * ncol];
        scale_mat(&mut ntri, ncol, 0, -1.0, dc, ld, mat, ncol, ncol);
        let rtblk = mat + ncol * ld;
        let saved = dc.to_vec();
        mult_into(dc, ld, rtblk, &ntri, ncol, 0, ncol, ncol, &saved, ld, rtblk, nright);
        if nabove > 0 {
            let tpblk = mat - nabove;
            let mut tmp = vec![0.0; nabove * nright];
            mult_into(&mut tmp, nabove, 0, dc, ld, tpblk, nabove, ncol, dc, ld, rtblk, nright);
            plus_equals_mat(dc, ld, rtblk - nabove, &tmp, nabove, 0, nabove, nright);
        }
    }
    if nabove > 0 {
        let tpblk = mat - nabove;
        let saved = dc.to_vec();
        mult_into(dc, ld, tpblk, &saved, ld, tpblk, nabove, ncol, &saved, ld, mat, ncol);
    }
    0
}

pub(crate) fn internal_r_invert(dims: &Dims, dc: &mut [f64]) -> Result<(), KernelError> {
    let q = dims.q as usize;
    let ld = dims.s_rows as usize;
    for i in (0..=q).rev() {
        let ngrp = dims.ngrp[i] as usize;
        for j in 0..ngrp {
            let sto = dims.grp(&dims.st_off, i, j) as usize;
            let dec = dims.grp(&dims.dec_off, i, j) as usize;
            let nabove = sto - dec;
            let nright = dims.nrot[i] as isize - 1;
            let info = invert_block(dc, sto, ld, nabove, dims.ncol[i] as usize, nright);
            if info != 0 {
                return Err(KernelError("singular block inverse".to_string()));
            }
        }
    }
    Ok(())
}

fn finite_diff_hess(mut func: impl FnMut(&[f64]) -> f64, pars: &[f64], npar: usize) -> Vec<f64> {
    let n_tot = 1 + npar + npar * (npar + 1) / 2;
    let out_len = 1 + npar * (npar + 1);
    let mut vals = vec![0.0; out_len.max(n_tot)];
    let mut incr = vec![0.0; npar];
    let mut parray = vec![0.0; n_tot * npar.max(1)];
    let mut div = vec![0.0; n_tot.max(1)];
    let mut xmat = vec![0.0; n_tot * n_tot];
    let cube = (f64::EPSILON.ln() / 3.0).exp();
    div[0] = 1.0;
    let mut ppt = npar * (2 * npar + 1);
    let mut xpt = n_tot * (2 * npar + 1);
    let mut dpt = 2 * npar + 1;
    for i in 0..npar {
        incr[i] = if pars[i] != 0.0 { cube * pars[i] } else { cube };
        div[i + 1] = 1.0 / incr[i];
        div[npar + i + 1] = 2.0 / (incr[i] * incr[i]);
        let np1 = npar + 1;
        parray[npar + i * np1] = 1.0;
        parray[(npar + i) * np1] = -1.0;
        for j in (i + 1)..npar {
            parray[ppt + i] = 1.0;
            parray[ppt + j] = 1.0;
            ppt += npar;
        }
        for j in 0..n_tot {
            xmat[j + (i + 1) * n_tot] = parray[i + j * npar];
        }
        for j in 0..n_tot {
            let v = xmat[j + (i + 1) * n_tot];
            xmat[j + (npar + i + 1) * n_tot] = v * v;
        }
        for _j in 0..i {
            for k in 0..n_tot {
                xmat[xpt + k] = xmat[k + (i + 1) * n_tot] * xmat[k + (_j + 1) * n_tot];
            }
            xpt += n_tot;
            div[dpt] = 1.0 / (incr[i] * incr[_j]);
            dpt += 1;
        }
    }
    vals[0] = func(pars);
    xmat[0] = 1.0;
    for i in 1..n_tot {
        xmat[i] = 1.0;
        let mut trial = pars.to_vec();
        for j in 0..npar {
            trial[j] += parray[j + i * npar] * incr[j];
        }
        vals[i] = func(&trial);
    }
    let qr = qr_factor(&mut xmat, n_tot, n_tot, n_tot);
    let y = vals[..n_tot].to_vec();
    qr_solve_into(&mut xmat, &qr, &y, &mut vals[..n_tot]);
    for i in 0..n_tot {
        vals[i] *= div[i];
    }
    let saved: Vec<f64> = vals[npar + 1..n_tot].to_vec();
    let mut cursor = npar;
    for i in 0..npar {
        vals[npar + 1 + i * (npar + 1)] = saved[i];
        for j in 0..i {
            let v = saved[cursor];
            cursor += 1;
            vals[npar + 1 + i + j * npar] = v;
            vals[npar + 1 + j + i * npar] = v;
        }
    }
    vals.truncate(out_len);
    vals
}

pub struct OptRef {
    pub dims: *const Dims,
    pub zxy: *const f64,
    pub active: usize,
    pub pd_class: *const i32,
    pub pd_len: usize,
    pub rml: i32,
    pub sigma: f64,
}

pub extern "C" fn mixed_fcn_c(_n: c_int, pars: *mut f64, g: *mut f64, state: *mut c_void) {
    unsafe {
        let st = &*(state as *const OptRef);
        let npar = count_dm_half_pars(&*st.dims, std::slice::from_raw_parts(st.pd_class, st.pd_len));
        let pars = std::slice::from_raw_parts(pars, npar);
        let dims = &*st.dims;
        let zxy = std::slice::from_raw_parts(st.zxy, st.active);
        let pd = std::slice::from_raw_parts(st.pd_class, st.pd_len);
        let mut zx = zxy[..st.active].to_vec();
        let dm_len = dims.dm_off[dims.q as usize] as usize;
        let mut delta = vec![0.0; dm_len];
        generate_dm_half(&mut delta, dims, pd, pars);
        let val = internal_loglik(dims, &mut zx, &delta, st.rml, None, st.sigma);
        let mut neg = -val;
        if !neg.is_finite() {
            neg = f64::MAX;
        }
        *g = neg;
    }
}

pub(crate) fn run_optif9(dims: &Dims, zxy: &mut [f64], pd_class: &[i32], rml: i32, sigma: f64, theta: &mut [f64], itnlim: i32, dlt: f64, gradtl: f64) -> i32 {
    let ntheta = theta.len();
    let active = (dims.zx_rows as usize) * (dims.zx_cols as usize);
    let state = OptRef {
        dims: dims as *const Dims,
        zxy: zxy.as_ptr(),
        active,
        pd_class: pd_class.as_ptr(),
        pd_len: pd_class.len(),
        rml,
        sigma,
    };
    let mut typsiz = vec![1.0; ntheta];
    let mut grad = vec![0.0; ntheta];
    let mut newtheta = vec![0.0; ntheta];
    let mut a = vec![0.0; ntheta * ntheta];
    let mut work = vec![0.0; ntheta * 9];
    let mut msg = 9i32;
    let mut log_lik = 0.0;
    let mut itrmcd = 0i32;
    let mut itncnt = 0i32;
    let eps = f64::EPSILON;
    let steptl = eps.sqrt();
    unsafe {
        optif9(
            ntheta as c_int,
            ntheta as c_int,
            theta.as_mut_ptr(),
            mixed_fcn_c,
            dummy_grad,
            None,
            &state as *const OptRef as *mut c_void,
            typsiz.as_mut_ptr(),
            1.0,
            1,
            1,
            &mut msg,
            -1,
            itnlim,
            0,
            0,
            dlt,
            gradtl,
            0.0,
            steptl,
            newtheta.as_mut_ptr(),
            &mut log_lik,
            grad.as_mut_ptr(),
            &mut itrmcd,
            a.as_mut_ptr(),
            work.as_mut_ptr(),
            &mut itncnt,
        );
    }
    msg
}

pub fn mixed_decomp(zxy: &mut [f64], pdims: &[i32]) -> Vec<f64> {
    let mut dims = Dims::parse(pdims);
    internal_decomp(&mut dims, zxy);
    zxy.to_vec()
}

pub fn mixed_loglik(zxy: &mut [f64], pdims: &[i32], pars: &[f64], settings: &[i32], sigma: f64) -> (Vec<f64>, f64) {
    let dims = Dims::parse(pdims);
    if settings[1] != 0 {
        let (lik, lrss) = internal_loglik_rss(&dims, zxy, pars, settings[0], None, sigma);
        (vec![lik], lrss)
    } else {
        let pd_class = &settings[3..];
        let dm_len = dims.dm_off[dims.q as usize] as usize;
        if settings[2] == 0 {
            let mut delta = vec![0.0; dm_len];
            generate_dm_half(&mut delta, &dims, pd_class, pars);
            let (lik, lrss) = internal_loglik_rss(&dims, zxy, &delta, settings[0], None, sigma);
            (vec![lik], lrss)
        } else {
            let npar = count_dm_half_pars(&dims, pd_class);
            let active = (dims.zx_rows as usize) * (dims.zx_cols as usize);
            let saved = zxy[..active].to_vec();
            let vals = finite_diff_hess(
                |p| {
                    let mut work = saved.clone();
                    let mut delta = vec![0.0; dm_len];
                    generate_dm_half(&mut delta, &dims, pd_class, p);
                    internal_loglik(&dims, &mut work, &delta, settings[0], None, sigma)
                },
                pars,
                npar,
            );
            let lrss = 0.0;
            (vals, lrss)
        }
    }
}

pub fn mixed_estimate(zxy: &mut [f64], pdims: &[i32], dm_half: &[f64], rml: i32, invert: i32, sigma: f64) -> Result<(f64, Vec<f64>), KernelError> {
    let dims = Dims::parse(pdims);
    let mut dc = vec![0.0; dims.s_rows as usize * dims.zx_cols as usize];
    let lik = {
        let (lik, _) = internal_loglik_rss(&dims, zxy, dm_half, rml, Some(&mut dc), sigma);
        lik
    };
    internal_estimate(&dims, &mut dc)?;
    if invert != 0 {
        internal_r_invert(&dims, &mut dc)?;
    }
    Ok((lik, dc))
}

pub(crate) fn internal_em(
    dims: &Dims,
    zxy: &[f64],
    dm_half: &mut [f64],
    mut nn: i32,
    pd_class: &[i32],
    rml: i32,
    sigma: f64,
) -> Result<(f64, Vec<f64>, f64), KernelError> {
    let srows = dims.s_rows as usize;
    let zxcols = dims.zx_cols as usize;
    let zxrows = dims.zx_rows as usize;
    let mut dc = vec![0.0; srows * zxcols];
    let mut zxcopy = vec![0.0; zxrows * zxcols];
    let sqrt_df = ((dims.n - rml * dims.ncol[dims.q as usize]) as f64).sqrt();
    let ra_len = dims.dm_off[dims.q as usize] as usize;
    let mut ra = vec![0.0; ra_len];
    let mut log_lik = 0.0;
    while nn > 0 {
        nn -= 1;
        copy_mat(&mut zxcopy, zxrows, 0, zxy, zxrows, 0, zxrows, zxcols);
        log_lik = internal_loglik_rss(dims, &mut zxcopy, dm_half, rml, Some(&mut dc), sigma).0;
        internal_estimate(dims, &mut dc)?;
        internal_r_invert(dims, &mut dc)?;
        let sigmainv = if sigma > 0.0 {
            1.0 / sigma
        } else {
            let last = dc[srows * zxcols - 1] / sqrt_df;
            if last == 0.0 {
                return Err(KernelError("overfitted model".to_string()));
            }
            1.0 / last.abs()
        };
        let mut offset = (zxcols - 1) * srows;
        for i in 0..dims.q as usize {
            let ncol = dims.qvec[i] as usize;
            let nright = dims.nrot[i] - dims.nrot[dims.q as usize - if rml != 0 { 0 } else { 1 }];
            let ngrp = dims.ngrp[i] as usize;
            let nrow = (ncol as i32 + nright + 1) as usize * ngrp;
            let mut res = vec![0.0; ncol * nrow.max(1)];
            let mut row_at = 0usize;
            for j in 0..ngrp {
                let sto = dims.grp(&dims.st_off, i, j) as usize;
                copy_trans(&mut res, nrow, row_at, &dc, srows, sto, ncol, ncol + nright as usize);
                row_at += ncol + nright as usize;
                scale_mat(
                    &mut res,
                    nrow,
                    row_at,
                    sigmainv,
                    &dc,
                    1,
                    offset + sto,
                    1,
                    ncol,
                );
                row_at += 1;
            }
            offset -= srows * ncol;
            let qr = qr_factor(&mut res, nrow, nrow, ncol);
            let off = dims.dm_off[i] as usize;
            qr_store_r(&res, &qr, &mut ra, ncol, off);
            let scale = (1.0 / ngrp as f64).sqrt();
            scale_mat(&mut res, nrow, 0, scale, &ra, ncol, off, ncol, ncol);
            match pd_class[i] {
                0 | 4 => {
                    let info = invert_upper(&mut res, 0, nrow, ncol);
                    if info != 0 {
                        return Err(KernelError("singular EM factor".to_string()));
                    }
                    copy_trans(&mut dm_half[off..], ncol, 0, &res, nrow, 0, ncol, ncol);
                }
                1 => {
                    for j in 0..ncol {
                        dm_half[off + j * (ncol + 1)] = 1.0 / d_sum_sqr(&res, j * nrow, j + 1).sqrt();
                    }
                }
                2 => {
                    let mut aux = 0.0;
                    for j in 0..ncol {
                        aux += d_sum_sqr(&res, j * nrow, j + 1);
                    }
                    aux = (ncol as f64 / aux).sqrt();
                    for j in 0..ncol {
                        dm_half[off + j * (ncol + 1)] = aux;
                    }
                }
                3 => {
                    return Err(KernelError("compound symmetry EM is not used by this proof".to_string()));
                }
                _ => {}
            }
        }
    }
    copy_mat(&mut zxcopy, zxrows, 0, zxy, zxrows, 0, zxrows, zxcols);
    let (lik, lrss) = internal_loglik_rss(dims, &mut zxcopy, dm_half, rml, Some(&mut dc), sigma);
    let _ = log_lik;
    Ok((lik, ra, lrss))
}

pub fn mixed_em(zxy: &[f64], pdims: &[i32], dm_half: &mut [f64], n_iter: i32, pd_class: &[i32], rml: i32, sigma: f64) -> Result<(f64, Vec<f64>, f64), KernelError> {
    let dims = Dims::parse(pdims);
    internal_em(&dims, zxy, dm_half, n_iter, pd_class, rml, sigma)
}

pub fn mixed_combined(zxy: &mut [f64], pdims: &[i32], dm_half: &mut [f64], n_iter: i32, pd_class: &[i32], rml: i32, sigma: f64) -> Result<(f64, Vec<f64>, f64, i32), KernelError> {
    let mut dims = Dims::parse(pdims);
    internal_decomp(&mut dims, zxy);
    let dm_len = dims.dm_off[dims.q as usize] as usize;
    if d_sum_sqr(dm_half, 0, dm_len) == 0.0 {
        let mut delta = 0usize;
        let mut work = 0usize;
        for i in 0..dims.q as usize {
            let q = dims.qvec[i] as usize;
            let ngrp = dims.ngrp[i] as f64;
            for _j in 0..q {
                let scale = 0.375 * (d_sum_sqr(zxy, work, dims.zx_rows as usize) / ngrp).sqrt();
                dm_half[delta] = scale;
                delta += q + 1;
                work += dims.zx_rows as usize;
            }
            delta -= q;
        }
    }
    let mut ra = vec![0.0; dm_len];
    let (mut log_lik, _, mut lrss) = internal_em(&dims, zxy, dm_half, n_iter, pd_class, rml, sigma)?;
    let _ = ra;
    let ntheta = count_dm_half_pars(&dims, pd_class);
    let mut theta = vec![0.0; ntheta];
    generate_theta(&mut theta, &dims, pd_class, dm_half)?;
    let gradtl = f64::EPSILON.powf(0.25);
    let info = run_optif9(&dims, zxy, pd_class, rml, sigma, &mut theta, 50, 1.0, gradtl);
    let p = dims.ncol[dims.q as usize] as usize;
    let mut r0 = vec![0.0; p * (p + 1)];
    if info == 0 {
        let mut dc = vec![0.0; dims.s_rows as usize * dims.zx_cols as usize];
        generate_dm_half(dm_half, &dims, pd_class, &theta);
        let (lik, rss) = internal_loglik_rss(&dims, zxy, dm_half, rml, Some(&mut dc), sigma);
        log_lik = lik;
        lrss = rss;
        let sto = dims.grp(&dims.st_off, dims.q as usize, 0) as usize;
        copy_mat(&mut r0, p, 0, &dc, dims.s_rows as usize, sto, p, p + 1);
    }
    Ok((log_lik, r0, lrss, info))
}

pub fn inner_perc(x: &[f64], grp: &[i32]) -> f64 {
    let n = x.len();
    let mut nn = 0usize;
    let mut n_inner = 0.0;
    let mut n_grp = 0.0;
    while nn < n {
        let curr_grp = grp[nn];
        let curr_val = x[nn];
        n_grp += 1.0;
        let mut is_inner = 0;
        loop {
            if is_inner == 0 && x[nn] != curr_val {
                n_inner += 1.0;
                is_inner = 1;
            }
            nn += 1;
            if nn >= n || curr_grp != grp[nn] {
                break;
            }
        }
    }
    if n_grp == 0.0 {
        0.0
    } else {
        n_inner / n_grp
    }
}

pub fn inner_perc_table(x: &[f64], grps: &[i32], p: usize, q: usize, n: usize) -> Vec<f64> {
    let mut table = vec![0.0; p * q];
    for i in 0..q {
        for j in 0..p {
            let col = &x[j * n..(j + 1) * n];
            let g = &grps[i * n..(i + 1) * n];
            table[j + i * p] = inner_perc(col, g);
        }
    }
    table
}

/// Expose the symmetric eigensolver used by the matrix-log map.
pub fn jacobi_values(a: &[f64], q: usize) -> Vec<f64> {
    let mut m = a.to_vec();
    crate::linalg::jacobi_sym(&mut m, q).0
}
