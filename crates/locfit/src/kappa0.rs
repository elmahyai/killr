//! Tube constants for `kappa0`: locfit's `geth = 2` output (`dc = TRUE`), ported
//! from locfit 1.5-9.12 (GPL, version 2 or later).
//!
//! Ported from:
//! - `S_enter.c` `slocfit` (case `GKAP`) and `scb_iface.c` `constants`: the
//!   tube constants of the grid fit, with the bounding box of `set_flim`
//!   (`startlf.c`: the data range when `ll = ur = 0`) and `set_scales`
//!   (`scale = FALSE` gives `sca = 1`);
//! - `scb_cons.c`: `tube_constants` (grid `ISIMPSON`), `k0x`, `l1x`, `m0x`,
//!   `d1x`, `d2x`, `k2x`, `rproject`;
//! - `m_isimp.c`: `simpson4`, `simp1`, `simp2`;
//! - `lf_wdiag.c`: `wdiag` and `nnresproj`, the weight diagrams of the local
//!   fit at a point, with degree-1 and degree-2 derivative weights;
//! - `weight.c`: `WdW`, `Wd`, `Wdd`, `weightd`, for the tricube kernel;
//! - `m_qr.c`: `qr`, `qrsolv`.
//!
//! Original copyright notices:
//!   Copyright (c) 1996-2004 Catherine Loader (`scb_cons.c`, `scb.c`).
//!   Copyright (c) 1996-2001 Lucent Technologies (`lf_wdiag.c`, `m_isimp.c`,
//!   `weight.c`, `m_qr.c`).
//! The locfit package is licensed GPL (>= 2), as is this crate.
//!
//! Scope: the spherical kernel with the tricube weight, local degree 2,
//! Gaussian identity family with unit prior weights, no parametric component,
//! and dimension `d = 1` or `d = 2`. `d >= 3` needs `n0x` and `simp3`, which are
//! not ported.

use std::f64::consts::PI;

use crate::eig::Jac;
use crate::fit::compbandwid;
use crate::kernel::{calcp, fitfun, w_fn, Kernel, Kt};

/// Locfit's `EPS` in `WdW` (weight.c).
const EPS: f64 = 1.0e-10;

/// Options for the `geth = 2` grid fit.
#[derive(Clone, Copy, Debug)]
pub struct Geth2Opts {
    /// Nearest-neighbour fraction (`alpha`).
    pub nn: f64,
    /// Fixed bandwidth floor (`fixh`).
    pub fixh: f64,
    /// Local polynomial degree.
    pub deg: usize,
    pub kern: Kernel,
    pub kt: Kt,
    /// Grid points per dimension (`lfgrid(mg)`).
    pub mg: usize,
}

/// Weight function (locfit `W`, tricube).
fn tcub_w(u: f64) -> f64 {
    w_fn(u, Kernel::Tcub)
}

/// locfit `WdW`: `W'(u) / W(u)` for the tricube kernel.
fn wdw_tcub(u: f64) -> f64 {
    if u.abs() >= 1.0 {
        return 0.0;
    }
    let sgn = if u > 0.0 {
        1.0
    } else if u < 0.0 {
        -1.0
    } else {
        0.0
    };
    -9.0 * sgn * u * u / (1.0 - u * u * u.abs() + EPS)
}

/// locfit `Wd`: `W'(u) / u` for the tricube kernel.
fn wd_tcub(u: f64) -> f64 {
    if u.abs() > 1.0 {
        return 0.0;
    }
    let v = 1.0 - u * u * u;
    -9.0 * v * v * u
}

/// locfit `Wdd` for the tricube kernel.
fn wdd_tcub(u: f64) -> f64 {
    if u > 1.0 {
        return 0.0;
    }
    let v = 1.0 - u * u * u;
    -9.0 * u * v * v + 54.0 * u * u * u * u * v
}

/// locfit `weightd` for the spherical kernel, `sca = 1`, no angular variable:
/// the derivative of `log W(|x - xev| / h)` in the coordinate with offset `u`.
fn weightd_sph(u: f64, h: f64, di: f64) -> f64 {
    if di == 0.0 {
        return 0.0;
    }
    -wdw_tcub(di / h) * u / (h * di)
}

/// Neighbourhood of one evaluation point, with the local design and the
/// information matrix `A = X^T W X` (locfit `nbhd`, `design`, `des->xtwx`).
struct Nbhd {
    m: usize,
    p: usize,
    h: f64,
    /// Data indices of the neighbours.
    idx: Vec<usize>,
    /// Distances from the evaluation point.
    di: Vec<f64>,
    /// Kernel weights.
    w: Vec<f64>,
    /// Local design, `m x p`, row-major.
    xm: Vec<f64>,
    jac: Jac,
}

fn nbhd(x: &[f64], n: usize, d: usize, xev: &[f64], o: &Geth2Opts) -> Nbhd {
    let p = calcp(Kt::Sph, d, o.deg);
    let mut di = vec![0.0; n];
    for i in 0..n {
        let mut s = 0.0;
        for j in 0..d {
            let r = x[i * d + j] - xev[j];
            s += r * r;
        }
        di[i] = s.sqrt();
    }
    // The 1e-12 avoids problems with roundoff (locfit `locfit.c`).
    let nn = (n as f64 * o.nn + 1e-12) as usize;
    let h = compbandwid(&di, nn, n, d, o.fixh);

    let mut idx = Vec::new();
    let mut w = Vec::new();
    let mut dist = Vec::new();
    for i in 0..n {
        let wi = if h == 0.0 {
            if di[i] == 0.0 {
                1.0
            } else {
                0.0
            }
        } else {
            tcub_w(di[i] / h)
        };
        if wi > 0.0 {
            idx.push(i);
            w.push(wi);
            dist.push(di[i]);
        }
    }
    let m = idx.len();
    let mut xm = vec![0.0; m * p];
    for (k, &i) in idx.iter().enumerate() {
        fitfun(
            &x[i * d..(i + 1) * d],
            Some(xev),
            d,
            Kt::Sph,
            o.deg,
            &[],
            &mut xm[k * p..(k + 1) * p],
        );
    }
    let mut a = vec![0.0; p * p];
    for k in 0..m {
        for r in 0..p {
            for c in 0..p {
                a[r * p + c] += w[k] * xm[k * p + r] * xm[k * p + c];
            }
        }
    }
    Nbhd {
        m,
        p,
        h,
        idx,
        di: dist,
        w,
        xm,
        jac: Jac::new(&a, p),
    }
}

fn dot(a: &[f64], b: &[f64]) -> f64 {
    a.iter().zip(b).map(|(x, y)| x * y).sum()
}

/// locfit `nnresproj`: project a weight column onto the complement of the
/// local fit, `u <- (I - W X A^{-1} X^T) u` (the link weight is 1 here).
fn nnresproj(u: &mut [f64], nb: &Nbhd) {
    let (m, p) = (nb.m, nb.p);
    let mut f1 = vec![0.0; p];
    for j in 0..m {
        for i in 0..p {
            f1[i] += nb.xm[j * p + i] * u[j];
        }
    }
    nb.jac.solve(&mut f1);
    for i in 0..m {
        u[i] -= dot(&f1, &nb.xm[i * p..(i + 1) * p]) * nb.w[i];
    }
}

/// locfit `wdiag` with `ty = 2` and `exp = 0`. Returns the weight diagram at
/// `xev`: column `c` (length `m`) is the weight of each neighbour for the
/// coefficient `c`. Column 0 is the value, columns `1..=d` the first
/// derivatives, and columns `1 + d + i * d + j` the second derivatives
/// (only when `deg == 2`). The link scale is 1 for the Gaussian family.
fn wdiag(nb: &Nbhd, x: &[f64], xev: &[f64], d: usize, deg: usize) -> Vec<f64> {
    let (m, p, h) = (nb.m, nb.p, nb.h);
    let ncol = 1 + if deg > 0 { d } else { 0 } + if deg == 2 { d * d } else { 0 };
    let mut lx = vec![0.0; ncol * m];
    let col_d = |j: usize| (1 + j) * m;
    let col_dd = |i: usize, j: usize| (1 + d + i * d + j) * m;

    // c(0) (X^T W X)^{-1}, with c(0) the unit vector of the value.
    let mut f1 = vec![0.0; p];
    f1[0] = 1.0;
    nb.jac.solve(&mut f1);

    let mut wd = vec![0.0; m];
    for i in 0..m {
        let ii = nb.idx[i];
        let di_i = nb.di[i];
        let w_i = nb.w[i];
        // c(0) (X^T W X)^{-1} X_i^T, before the kernel weight.
        let lxi = dot(&f1, &nb.xm[i * p..(i + 1) * p]);
        if deg > 0 {
            wd[i] = wd_tcub(di_i / h);
            for j in 0..d {
                let dfx = x[ii * d + j] - xev[j];
                lx[col_d(j) + i] = lxi * w_i * weightd_sph(dfx, h, di_i);
            }
            if deg > 1 {
                let wdd = wdd_tcub(di_i / h);
                let wv0 = if di_i == 0.0 { 0.0 } else { h / di_i };
                for j in 0..d {
                    for k in 0..d {
                        let mut wv = wdd
                            * (xev[k] - x[ii * d + k])
                            * (xev[j] - x[ii * d + j])
                            * wv0
                            * wv0
                            / (h * h * h * h);
                        if j == k {
                            wv += wd[i] / (h * h);
                        }
                        lx[col_dd(j, k) + i] = lxi * wv;
                    }
                }
            }
        }
        lx[i] = lxi * w_i;
    }

    if deg == 2 {
        for i in 0..d {
            // c'_i(0) - sum_k lxd_i[k] X_k, then (X^T W X)^{-1}.
            let mut f = vec![0.0; p];
            fitfun(xev, Some(xev), d, Kt::Sph, deg, &[i], &mut f);
            for k in 0..m {
                for j in 0..p {
                    f[j] -= lx[col_d(i) + k] * nb.xm[k * p + j];
                }
            }
            nb.jac.solve(&mut f);
            let ulx: Vec<f64> = (0..m)
                .map(|k| dot(&f, &nb.xm[k * p..(k + 1) * p]))
                .collect();
            for j in 0..d {
                for k in 0..m {
                    let ii = nb.idx[k];
                    let dfx = x[ii * d + j] - xev[j];
                    let wdw = nb.w[k] * weightd_sph(dfx, h, nb.di[k]);
                    lx[col_dd(i, j) + k] += ulx[k] * wdw;
                    lx[col_dd(j, i) + k] += ulx[k] * wdw;
                }
            }
        }
        for jj in 0..d * d {
            let c = (1 + d + jj) * m;
            nnresproj(&mut lx[c..c + m], nb);
        }
    }

    if deg > 0 {
        for j in 0..d {
            let c = col_d(j);
            nnresproj(&mut lx[c..c + m], nb);
        }
        for i in 0..d {
            let mut f = vec![0.0; p];
            fitfun(xev, Some(xev), d, Kt::Sph, deg, &[i], &mut f);
            nb.jac.solve(&mut f);
            for k in 0..m {
                for l in 0..p {
                    lx[col_d(i) + k] += f[l] * nb.xm[k * p + l] * nb.w[k];
                }
            }
        }
    }

    if deg == 2 {
        for i in 0..d {
            for j in 0..d {
                let mut f = vec![0.0; p];
                fitfun(xev, Some(xev), d, Kt::Sph, deg, &[i, j], &mut f);
                nb.jac.solve(&mut f);
                for k in 0..m {
                    for l in 0..p {
                        lx[col_dd(i, j) + k] += f[l] * nb.xm[k * p + l] * nb.w[k];
                    }
                }
            }
        }
    }
    lx
}

/// locfit `innerprod`.
fn innerprod(a: &[f64], b: &[f64]) -> f64 {
    dot(a, b)
}

/// locfit `qr` (m_qr.c) on the `n x p` matrix `xm` stored by column (stride
/// `n`), without the weight vector. The diagonal of `R` is positive.
fn qr(xm: &mut [f64], n: usize, p: usize) {
    for j in 0..p {
        let mut mi = j;
        let mut mx = xm[(n + 1) * j].abs();
        let mut nx = mx * mx;
        for i in (j + 1)..n {
            nx += xm[j * n + i] * xm[j * n + i];
            if xm[j * n + i].abs() > mx {
                mi = i;
                mx = xm[j * n + i].abs();
            }
        }
        for i in j..p {
            xm.swap(i * n + j, i * n + mi);
        }
        if xm[(n + 1) * j] > 0.0 {
            for i in j..p {
                xm[i * n + j] = -xm[i * n + j];
            }
        }
        nx = nx.sqrt();
        let c = nx * (nx - xm[(n + 1) * j]);
        if c != 0.0 {
            for i in (j + 1)..p {
                let mut s = 0.0;
                for k in j..n {
                    s += xm[i * n + k] * xm[j * n + k];
                }
                s = (s - nx * xm[i * n + j]) / c;
                for k in j..n {
                    xm[i * n + k] -= s * xm[j * n + k];
                }
                xm[i * n + j] += s * nx;
            }
            xm[j * n + j] = nx;
        }
    }
}

/// locfit `qrinvx`.
fn qrinvx(r: &[f64], x: &mut [f64], n: usize, p: usize) {
    for i in (0..p).rev() {
        for j in (i + 1)..p {
            x[i] -= r[j * n + i] * x[j];
        }
        x[i] /= r[i * n + i];
    }
}

/// locfit `qrtinvx`.
fn qrtinvx(r: &[f64], x: &mut [f64], n: usize, p: usize) {
    for i in 0..p {
        for j in 0..i {
            x[i] -= r[i * n + j] * x[j];
        }
        x[i] /= r[i * n + i];
    }
}

/// locfit `qrsolv`: solves `(R^T R) x = x` with the triangular factor `R`.
fn qrsolv(r: &[f64], x: &mut [f64], n: usize, p: usize) {
    qrtinvx(r, x, n, p);
    qrinvx(r, x, n, p);
}

/// locfit `rproject`: `y <- (I - A (R^T R)^{-1} A^T) y` for the first `p`
/// columns of `a` (stride `n`), with `R` from the QR factorisation in `r`.
fn rproject(y: &mut [f64], a: &[f64], r: &[f64], n: usize, p: usize) {
    let mut v = [0.0_f64; 4];
    for i in 0..p {
        v[i] = innerprod(&a[i * n..i * n + n], y);
    }
    qrsolv(r, &mut v[..p], n, p);
    for i in 0..n {
        for j in 0..p {
            y[i] -= a[j * n + i] * v[j];
        }
    }
}

/// locfit `d1x`: the frame of the derivative weights. Copies the value column
/// of `ft` into `fd`, and writes `fd`'s derivative columns as `M` times the
/// gradient columns of `ft`.
fn d1x(ft: &[f64], fd: &mut [f64], m: usize, d: usize, mm: &[f64]) {
    fd[..m].copy_from_slice(&ft[..m]);
    for v in fd[m..m + m * d].iter_mut() {
        *v = 0.0;
    }
    for j in 0..d {
        for k in 0..d {
            if mm[j * d + k] != 0.0 {
                for i in 0..m {
                    fd[m + j * m + i] += mm[j * d + k] * ft[(k + 1) * m + i];
                }
            }
        }
    }
}

/// locfit `d2x`: second derivative weights in the frame `M`, written into
/// `fd` at `(d + 1) * m`, from the Hessian columns of `ft`.
fn d2x(ft: &[f64], fd: &mut [f64], m: usize, dd: usize, d: usize, mm: &[f64]) {
    let nij0 = (d + 1) * m;
    for i in 0..dd {
        for j in 0..dd {
            for k in 0..d {
                for l in 0..d {
                    let t = mm[i * d + k] * mm[j * d + l];
                    if t != 0.0 {
                        for z in 0..m {
                            fd[nij0 + (i * d + j) * m + z] +=
                                t * ft[(d + 1) * m + (k * d + l) * m + z];
                        }
                    }
                }
                let t = mm[(k + 1) * d * d + i * d + j];
                if t != 0.0 {
                    for z in 0..m {
                        fd[nij0 + (i * d + j) * m + z] += t * ft[(1 + k) * m + z];
                    }
                }
            }
        }
    }
}

/// locfit `k2x` (the non-covariance branch): the second fundamental form
/// term of the tube formula. `lij` is the Hessian block (overwritten), `r` the
/// QR factor of the first `d + 1` columns of `ft`.
fn k2x(lij: &mut [f64], ft: &[f64], r: &[f64], m: usize, d: usize, dd: usize) -> f64 {
    for i in 0..d {
        for j in i..d {
            let off = (i * dd + j) * m;
            let mut ll = lij[off..off + m].to_vec();
            rproject(&mut ll, ft, r, m, d + 1);
            lij[off..off + m].copy_from_slice(&ll);
            if i != j {
                let off2 = (j * dd + i) * m;
                lij[off2..off2 + m].copy_from_slice(&ll);
            }
        }
    }
    for k in 0..m {
        for j in 0..d {
            let mut v = vec![0.0; d + 1];
            for i in 0..d {
                v[i + 1] = lij[(j * dd + i) * m + k];
            }
            qrsolv(r, &mut v, m, d + 1);
            for i in 0..d {
                lij[(j * dd + i) * m + k] = v[i + 1];
            }
        }
    }
    let mut s = 0.0;
    for j in 0..d {
        for k in 0..j {
            s += innerprod(
                &lij[(j * dd + j) * m..(j * dd + j) * m + m],
                &lij[(k * dd + k) * m..(k * dd + k) * m + m],
            ) - innerprod(
                &lij[(j * dd + k) * m..(j * dd + k) * m + m],
                &lij[(k * dd + j) * m..(k * dd + j) * m + m],
            );
        }
    }
    s * r[0] * r[0]
}

/// locfit `k0x` (non-covariance branch), at one grid point: the determinant
/// term `kap[0]` and, for `d = 2`, the second-fundamental term `kap[2]`.
/// Entries not used by the dimension are zero.
fn k0x(ft: &[f64], m: usize, d: usize) -> [f64; 3] {
    let mut fd = vec![0.0; (d * d + d + 1) * m];
    fd[..(d + 1) * m].copy_from_slice(&ft[..(d + 1) * m]);
    qr(&mut fd, m, d + 1);
    let mut det = 1.0;
    for j in 1..=d {
        det *= fd[j * (m + 1)] / fd[0];
    }
    let mut kap = [det, 0.0, 0.0];
    if d == 1 {
        return kap;
    }
    let base = (d + 1) * m;
    let mut lij = ft[base..base + d * d * m].to_vec();
    let z = k2x(&mut lij, ft, &fd, m, d, d);
    kap[2] = z * det;
    kap
}

/// locfit `l1x` (non-covariance branch) for the edge frame `mm`: the edge
/// contribution, `[lap0, lap1]` for `d = 2` and `[lap0]` for `d = 1`.
fn l1x(ft: &[f64], m: usize, d: usize, mm: &[f64]) -> Vec<f64> {
    let mut fd = vec![0.0; (d * d + d + 1) * m];
    d1x(ft, &mut fd, m, d, mm);
    let ll_off = d * d * m;
    let tmp = fd[..(d + 1) * m].to_vec();
    fd[ll_off..ll_off + (d + 1) * m].copy_from_slice(&tmp);
    qr(&mut fd, m, d + 1);
    let mut det = 1.0;
    for j in 1..d {
        det *= fd[(m + 1) * j] / fd[0];
    }
    let mut lap = vec![det];
    if d <= 1 {
        return lap;
    }
    // d = 2 from here on.
    d2x(ft, &mut fd, m, d - 1, d, mm);
    let nij_off = (d + 1) * m;
    let u_off = ll_off + d * m;
    let mut u = fd[u_off..u_off + m].to_vec();
    let a = fd[ll_off..ll_off + d * m].to_vec();
    rproject(&mut u, &a, &fd, m, d);
    let mut sumcj = 0.0;
    for i in 0..(d - 1) {
        let mut v = vec![0.0; d + 1];
        for j in 0..(d - 1) {
            let off = nij_off + (i * d + j) * m;
            v[j + 1] = innerprod(&fd[off..off + m], &u);
        }
        qrsolv(&fd, &mut v, m, d);
        sumcj -= v[i + 1];
    }
    lap.push(sumcj * det * fd[0] / fd[(m + 1) * d]);
    lap
}

/// locfit `m0x` for `d = 2` and the corner frame `mm`: the angle term `m0[0]`.
fn m0x(ft: &[f64], m: usize, d: usize, mm: &[f64]) -> f64 {
    let mut fd = vec![0.0; (d * d + d + 1) * m];
    d1x(ft, &mut fd, m, d, mm);
    let ll_off = d * d * m;
    let tmp = fd[..(d + 1) * m].to_vec();
    fd[ll_off..ll_off + (d + 1) * m].copy_from_slice(&tmp);
    qr(&mut fd, m, d + 1);
    let mut det = 1.0;
    for j in 1..(d - 1) {
        det *= fd[(m + 1) * j] / fd[0];
    }
    let om = fd[d * (m + 1)].atan2(-fd[d * (m + 1) - 1]);
    det * om
}

/// Tube constants of the grid fit (locfit `constants` and `tube_constants`
/// with the grid rule `ISIMPSON`). `x` is row-major `n x d`. Returns the
/// `d + 1` values of `const` that R's `kappa0` passes to `crit`.
pub fn kappa0_const(x: &[f64], n: usize, d: usize, o: &Geth2Opts) -> Result<Vec<f64>, String> {
    if d != 1 && d != 2 {
        return Err(format!(
            "kappa0: d = {d} is not ported (d = 1 and d = 2 only; d >= 3 needs n0x and simp3)"
        ));
    }
    if o.deg != 2 {
        return Err("kappa0: only local degree 2 is ported".to_string());
    }
    if o.kern != Kernel::Tcub {
        return Err("kappa0: only the tricube kernel is ported".to_string());
    }
    if o.kt != Kt::Sph {
        return Err("kappa0: only the spherical kernel type is ported".to_string());
    }
    if n == 0 || x.len() != n * d {
        return Err("kappa0: x must be n x d with n >= 1".to_string());
    }
    if o.mg == 0 {
        return Err("kappa0: mg must be positive".to_string());
    }

    // set_flim: bounding box of the data in each dimension.
    let mut lo = vec![f64::INFINITY; d];
    let mut hi = vec![f64::NEG_INFINITY; d];
    for i in 0..n {
        for j in 0..d {
            lo[j] = lo[j].min(x[i * d + j]);
            hi[j] = hi[j].max(x[i * d + j]);
        }
    }
    // simpson4: an odd grid count is raised to the next even number.
    let mut mg = vec![o.mg; d];
    for g in mg.iter_mut() {
        if *g % 2 == 1 {
            *g += 1;
        }
    }
    let delta: Vec<f64> = (0..d)
        .map(|i| (hi[i] - lo[i]) / (3 * mg[i]) as f64)
        .collect();

    let mut k0 = [0.0_f64; 3];
    let mut l0 = [0.0_f64; 2];
    let mut m0 = 0.0_f64;
    let mut lfi = vec![0usize; d];
    let mut xpt = lo.clone();
    let r_deg = if d >= 2 { 2 } else { 1 };

    loop {
        let mut wt = 1.0_f64;
        for i in 0..d {
            let even = if lfi[i] % 2 == 0 { 1 } else { 0 };
            let f0 = if lfi[i] == 0 { 1 } else { 0 };
            let fm = if lfi[i] == mg[i] { 1 } else { 0 };
            wt *= (4 - 2 * even - f0 - fm) as f64;
        }

        let nb = nbhd(x, n, d, &xpt, o);
        let ft = wdiag(&nb, x, &xpt, d, r_deg);
        let m = nb.m;
        let kv = k0x(&ft, m, d);
        for j in 0..3 {
            k0[j] += wt * kv[j];
        }

        for i in 0..d {
            if lfi[i] == 0 || lfi[i] == mg[i] {
                let mut mm = vec![0.0; (1 + d) * d * d];
                let mut k = 0;
                for j in 0..d {
                    if j != i {
                        mm[k * d + j] = 1.0;
                        k += 1;
                    }
                }
                mm[(d - 1) * d + i] = if lfi[i] == 0 { -1.0 } else { 1.0 };
                let zb: f64 = (0..d).filter(|&j| j != i).map(|j| delta[j]).product();
                let lap = l1x(&ft, m, d, &mm);
                for j in 0..lap.len() {
                    l0[j] += wt * zb * lap[j];
                }

                // simp2: corners of the edge, for d = 2 the pair (0, 1).
                if d == 2 && i == 0 {
                    let j = 1;
                    if lfi[j] == 0 || lfi[j] == mg[j] {
                        let mut mc = vec![0.0; (1 + d) * d * d];
                        mc[(d - 2) * d + i] = if lfi[i] == 0 { -1.0 } else { 1.0 };
                        mc[(d - 1) * d + j] = if lfi[j] == 0 { -1.0 } else { 1.0 };
                        m0 += wt * m0x(&ft, m, d, &mc);
                    }
                }
            }
        }

        // Advance the grid index, as simpson4 does.
        let mut i = 0;
        let mut done = false;
        loop {
            lfi[i] += 1;
            if lfi[i] > mg[i] {
                lfi[i] = 0;
                xpt[i] = lo[i];
                if i == d - 1 {
                    done = true;
                    break;
                }
                i += 1;
            } else {
                xpt[i] = lo[i] + 3.0 * delta[i] * lfi[i] as f64;
                break;
            }
        }
        if done {
            break;
        }
    }

    // simpson4 multiplies the interior sums by the cell volume.
    let mut z = 1.0_f64;
    for j in 0..d {
        z *= delta[j];
    }
    let mut kap = vec![0.0; d + 1];
    kap[0] = k0[0] * z;
    kap[1] = l0[0] / 2.0;
    if d == 2 {
        kap[2] = (k0[2] * z + l0[1] + m0) / (2.0 * PI);
    }
    Ok(kap)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn value_and_slope_weights_reproduce_linear_data() {
        // The local linear part reproduces y = a + b x: sum_i l_i = 1 and
        // sum_i (slope weight)_i x_i = 1 at any point.
        let n = 25;
        let x: Vec<f64> = (0..n).map(|i| i as f64 / (n - 1) as f64).collect();
        let o = Geth2Opts {
            nn: 0.7,
            fixh: 0.0,
            deg: 2,
            kern: Kernel::Tcub,
            kt: Kt::Sph,
            mg: 20,
        };
        let xev = [0.4];
        let nb = nbhd(&x, n, 1, &xev, &o);
        let ft = wdiag(&nb, &x, &xev, 1, 1);
        let m = nb.m;
        let sum_val: f64 = (0..m).map(|k| ft[k]).sum();
        assert!((sum_val - 1.0).abs() < 1e-10, "value weights sum {sum_val}");
        let slope: f64 = (0..m).map(|k| ft[m + k] * x[nb.idx[k]]).sum();
        assert!((slope - 1.0).abs() < 1e-6, "slope reproduction {slope}");
    }

    #[test]
    fn d3_is_refused() {
        let o = Geth2Opts {
            nn: 0.7,
            fixh: 0.0,
            deg: 2,
            kern: Kernel::Tcub,
            kt: Kt::Sph,
            mg: 20,
        };
        assert!(kappa0_const(&[0.0; 12], 4, 3, &o).is_err());
    }
}

