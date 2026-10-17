//! Nonlinear mixed-model PNLS step, ported from `fit_nlme` in `src/nlme.c`.
//!
//! The model callback replaces R's `evaluate()`. A nonzero `cor_opt` is
//! refused: that adjustment is `corStruct_recalc`, which lives in another crate.

use crate::dims::Dims;
use crate::linalg::{d_sum_sqr, mult_into};
use crate::mixed::{
    generate_dm_half, generate_theta, internal_decomp, internal_em, internal_estimate,
    internal_loglik, run_optif9, KernelError,
};

fn make_sequential(dest: &mut [i32]) {
    if dest.is_empty() {
        return;
    }
    let mut val = 0i32;
    let mut sval = dest[0];
    dest[0] = val;
    for slot in dest.iter_mut().skip(1) {
        if *slot != sval {
            sval = *slot;
            val += 1;
        }
        *slot = val;
    }
}

fn objective(dims: &Dims, newtheta: &[f64], dm_half: &[f64], rss: f64, npar: &[usize]) -> f64 {
    let mut total = rss;
    let mut src = 0usize;
    for i in 0..dims.q as usize {
        let ncol = dims.ncol[i] as usize;
        let ngrp = dims.ngrp[i] as usize;
        let off = dims.dm_off[i] as usize;
        let mut work = vec![0.0; npar[i]];
        mult_into(
            &mut work,
            ncol,
            0,
            dm_half,
            ncol,
            off,
            ncol,
            ncol,
            newtheta,
            ncol,
            src,
            ngrp,
        );
        total += d_sum_sqr(&work, 0, npar[i]);
        src += npar[i];
    }
    total
}

fn working_res(dims: &Dims, gradient: &mut [f64], theta: &[f64]) {
    let mut theta_at = 0usize;
    let zx_rows = dims.zx_rows as usize;
    for j in 0..dims.q as usize {
        let nb = dims.ncol[j] as usize;
        let mut res_at = zx_rows * (dims.zx_cols as usize - 1);
        let ngrp = dims.ngrp[j] as usize;
        for k in 0..ngrp {
            let z_at = dims.grp(&dims.zx_off, j, k) as usize;
            let len = dims.grp(&dims.zx_len, j, k) as usize;
            for i in 0..len {
                let mut dot = 0.0;
                for t in 0..nb {
                    dot += gradient[z_at + i + t * zx_rows] * theta[theta_at + t];
                }
                gradient[res_at] += dot;
                res_at += 1;
            }
            theta_at += nb;
        }
    }
}

fn restore_dims(dims: &mut Dims, saved_off: &[i32], saved_len: &[i32]) {
    dims.zx_rows = dims.n;
    let n = saved_off.len();
    dims.zx_off[..n].copy_from_slice(saved_off);
    dims.zx_len[..n].copy_from_slice(saved_len);
}

struct Step {
    criterion: f64,
    incr: Vec<f64>,
    objective: f64,
}

fn increment(
    dims: &mut Dims,
    gradient: &mut [f64],
    theta: &[f64],
    newtheta: &[f64],
    dm_half: &mut [f64],
    pd_class: &[i32],
    sigma: f64,
    rss: f64,
    npar: &[usize],
    npar_tot: usize,
    nrdof: i32,
) -> Result<Step, KernelError> {
    internal_decomp(dims, gradient);
    working_res(dims, gradient, theta);
    let rml = 0i32;
    internal_em(dims, gradient, dm_half, 20, pd_class, rml, sigma)?;
    let ntheta = crate::mixed::count_dm_half_pars(dims, pd_class);
    let mut th = vec![0.0; ntheta];
    generate_theta(&mut th, dims, pd_class, dm_half)?;
    let gradtl = f64::EPSILON.powf(1.0 / 3.0);
    let msg = run_optif9(dims, gradient, pd_class, rml, sigma, &mut th, 20, -1.0, gradtl);
    if msg == 0 {
        generate_dm_half(dm_half, dims, pd_class, &th);
    }
    let objective = objective(dims, newtheta, dm_half, rss, npar);
    let srows = dims.s_rows as usize;
    let zxcols = dims.zx_cols as usize;
    let active = dims.zx_rows as usize * zxcols;
    let mut lik_buf = gradient[..active].to_vec();
    let mut dc = vec![0.0; srows * zxcols];
    internal_loglik(dims, &mut lik_buf, dm_half, rml, Some(&mut dc), sigma);
    internal_estimate(dims, &mut dc)?;
    let mut incr = vec![0.0; npar_tot];
    let mut dest = 0usize;
    let mut start = 0isize;
    let src0 = ((zxcols - 1) * srows) as isize;
    for i in 0..=dims.q as usize {
        let ncol = dims.ncol[i] as usize;
        let ngrp = dims.ngrp[i] as usize;
        for j in 0..ngrp {
            let sto = dims.grp(&dims.st_off, i, j) as isize;
            let from = (src0 + sto - start) as usize;
            incr[dest..dest + ncol].copy_from_slice(&dc[from..from + ncol]);
            dest += ncol;
        }
        start += (ncol * srows) as isize;
    }
    let n_random = npar_tot - npar[dims.q as usize];
    for i in 0..n_random {
        incr[i] -= theta[i];
    }
    let pred = dc[zxcols * dims.zx_rows as usize - 1];
    let pred_obj = pred * pred;
    let criterion = (((nrdof as f64) * (objective - pred_obj)) / ((npar_tot as f64) * pred_obj)).sqrt();
    Ok(Step {
        criterion,
        incr,
        objective,
    })
}

fn rss_of(dims: &Dims, result: &[f64]) -> f64 {
    let n = dims.n as usize;
    let start = (dims.zx_cols as usize - 1) * n;
    d_sum_sqr(result, start, n)
}

fn apply_weights(dims: &Dims, result: &mut [f64], var_opt: i32, var_weights: &[f64]) {
    if var_opt == 0 {
        return;
    }
    let n = dims.n as usize;
    for i in 0..n {
        for j in 0..dims.zx_cols as usize {
            result[i + j * n] *= var_weights[i];
        }
    }
}

pub fn fit_nlme<F>(
    theta: &mut [f64],
    dm_half: &mut [f64],
    groups: &mut [i32],
    pdims: &[i32],
    pd_class: &[i32],
    _cor_factor: &[f64],
    var_weights: &[f64],
    _cor_dims: &[i32],
    settings: &mut [f64],
    additional: &mut [f64],
    cor_opt: i32,
    var_opt: i32,
    sigma: f64,
    mut model: F,
) -> Result<(), KernelError>
where
    F: FnMut(&[f64]) -> Vec<f64>,
{
    if cor_opt != 0 {
        return Err(KernelError(
            "fit_nlme correlation adjustment is corStruct_recalc, which is not in this crate".to_string(),
        ));
    }
    let mut dims = Dims::parse(pdims);
    let mut npar = Vec::with_capacity(dims.q as usize + 1);
    let mut npar_tot = 0usize;
    for i in 0..=dims.q as usize {
        let n = dims.ncol[i] as usize * dims.ngrp[i] as usize;
        npar.push(n);
        npar_tot += n;
    }
    let nrdof = dims.n - npar_tot as i32;
    let mut src = 0usize;
    for _ in 0..dims.q as usize {
        let n = dims.n as usize;
        make_sequential(&mut groups[src..src + n]);
        src += n;
    }
    let ngrp_tot: usize = dims.ngrp.iter().map(|v| *v as usize).sum();
    let saved_off = dims.zx_off[..ngrp_tot].to_vec();
    let saved_len = dims.zx_len[..ngrp_tot].to_vec();
    let _ = model(theta);
    let mut result = model(theta);
    apply_weights(&dims, &mut result, var_opt, var_weights);
    let mut rss = rss_of(&dims, &result);
    settings[3] = 0.0;
    let mut newtheta = theta.to_vec();
    let mut factor = 1.0;
    let mut iteration = 1i64;
    let max_iter = settings[0] as i64;
    let min_factor = settings[1];
    let tolerance = settings[2];
    let mut current_objective = 0.0;
    let converged = loop {
        if iteration > max_iter {
            break false;
        }
        let step = increment(
            &mut dims,
            &mut result,
            theta,
            &newtheta,
            dm_half,
            pd_class,
            sigma,
            rss,
            &npar,
            npar_tot,
            nrdof,
        )?;
        current_objective = step.objective;
        if step.criterion < tolerance {
            break true;
        }
        let accepted = loop {
            if factor < min_factor {
                settings[3] = 1.0;
                settings[4] = iteration as f64;
                settings[5] = current_objective;
                let final_eval = model(theta);
                let ncopy = (dims.n as usize) * (dims.zx_cols as usize);
                additional[..ncopy].copy_from_slice(&final_eval[..ncopy]);
                return Ok(());
            }
            newtheta.copy_from_slice(theta);
            for i in 0..npar_tot {
                newtheta[i] += factor * step.incr[i];
            }
            result = model(&newtheta);
            restore_dims(&mut dims, &saved_off, &saved_len);
            apply_weights(&dims, &mut result, var_opt, var_weights);
            rss = rss_of(&dims, &result);
            let new_objective = objective(&dims, &newtheta, dm_half, rss, &npar);
            factor /= 2.0;
            if new_objective < current_objective {
                factor *= 4.0;
                if factor > 1.0 {
                    factor = 1.0;
                }
                current_objective = new_objective;
                theta.copy_from_slice(&newtheta);
                break true;
            }
        };
        if !accepted {
            break false;
        }
        iteration += 1;
    };
    if converged {
        settings[4] = iteration as f64;
    } else {
        settings[3] = 2.0;
        settings[4] = (iteration - 1) as f64;
    }
    let final_eval = model(theta);
    let ncopy = (dims.n as usize) * (dims.zx_cols as usize);
    additional[..ncopy].copy_from_slice(&final_eval[..ncopy]);
    let final_rss = rss_of(&dims, &final_eval);
    settings[5] = objective(&dims, theta, dm_half, final_rss, &npar);
    Ok(())
}
