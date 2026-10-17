//! Parametric survival regression (survival `survreg6.c` / `survregc1.c`).
//!
//! Newton–Raphson on the log-likelihood for the three built-in distributions:
//! extreme value, logistic, and Gaussian. Matrices are stored the way `dmatrix`
//! addresses them: `flat[col * n + row]` is C `matrix[col][row]`.
//! Distribution 4, the R density callback, is not part of this crate.

use std::time::Instant;

#[cfg(feature = "python")]
use numpy::{PyArray1, PyReadonlyArray1};
#[cfg(feature = "python")]
use pyo3::exceptions::PyValueError;
#[cfg(feature = "python")]
use pyo3::prelude::*;

const SMALL: f64 = -200.0;
const SPI: f64 = 2.506628274631001;
const ROOT_2: f64 = 1.414213562373095;

// Same libm `erf` / `erfc` the survival C code calls. Rust's `f64::erf` is still unstable here.
#[link(name = "m")]
unsafe extern "C" {
    fn erf(x: f64) -> f64;
    fn erfc(x: f64) -> f64;
}

fn libm_erf(x: f64) -> f64 {
    unsafe { erf(x) }
}

fn libm_erfc(x: f64) -> f64 {
    unsafe { erfc(x) }
}

#[derive(Clone, Copy)]
enum Dist {
    Extreme,
    Logistic,
    Gauss,
}

/// Column-major address used by survival's `dmatrix`: `matrix[col][row]`.
#[inline]
fn at(col: usize, row: usize, n: usize) -> usize {
    col * n + row
}

fn logistic_d(z: f64, ans: &mut [f64; 4], j: i32) {
    let (w, sign, ii) = if z > 0.0 {
        ((-z).exp(), -1.0, 0usize)
    } else {
        (z.exp(), 1.0, 1usize)
    };
    let temp = 1.0 + w;
    match j {
        1 => {
            ans[1] = w / (temp * temp);
            ans[2] = sign * (1.0 - w) / temp;
            ans[3] = (w * w - 4.0 * w + 1.0) / (temp * temp);
        }
        2 => {
            ans[1 - ii] = w / temp;
            ans[ii] = 1.0 / temp;
            ans[2] = w / (temp * temp);
            ans[3] = sign * ans[2] * (1.0 - w) / temp;
        }
        _ => {}
    }
}

fn gauss_d(z: f64, ans: &mut [f64; 4], j: i32) {
    let f = (-z * z / 2.0).exp() / SPI;
    match j {
        1 => {
            ans[1] = f;
            ans[2] = -z;
            ans[3] = z * z - 1.0;
        }
        2 => {
            if z > 0.0 {
                ans[0] = (1.0 + libm_erf(z / ROOT_2)) / 2.0;
                ans[1] = libm_erfc(z / ROOT_2) / 2.0;
            } else {
                ans[1] = (1.0 + libm_erf(-z / ROOT_2)) / 2.0;
                ans[0] = libm_erfc(-z / ROOT_2) / 2.0;
            }
            ans[2] = f;
            ans[3] = -z * f;
        }
        _ => {}
    }
}

fn exvalue_d(z: f64, ans: &mut [f64; 4], j: i32) {
    let w = if z < SMALL {
        SMALL.exp()
    } else if -z < SMALL {
        (-SMALL).exp()
    } else {
        z.exp()
    };
    let temp = (-w).exp();
    match j {
        1 => {
            ans[1] = w * temp;
            ans[2] = 1.0 - w;
            ans[3] = w * (w - 3.0) + 1.0;
        }
        2 => {
            ans[0] = 1.0 - temp;
            ans[1] = temp;
            ans[2] = w * temp;
            ans[3] = w * temp * (1.0 - w);
        }
        _ => {}
    }
}

fn sreg_gg(dist: Dist, z: f64, ans: &mut [f64; 4], j: i32) {
    match dist {
        Dist::Extreme => exvalue_d(z, ans, j),
        Dist::Logistic => logistic_d(z, ans, j),
        Dist::Gauss => gauss_d(z, ans, j),
    }
}

/// Cholesky `C = FDF'` for the dense triangle `survregc1` fills.
/// `m` is the sparse diagonal block; `survreg6` always passes `m = 0`.
fn cholesky3(matrix: &mut [f64], n: usize, m: usize, diag: Option<&[f64]>, toler: f64) -> i32 {
    let n2 = n - m;
    let mut nonneg = 1i32;
    let mut eps = 0.0;
    if m > 0 {
        let diag = diag.expect("diag");
        for i in 0..m {
            if diag[i] < eps {
                eps = diag[i];
            }
        }
    }
    for i in 0..n2 {
        let v = matrix[at(i, i + m, n)];
        if v < eps {
            eps = v;
        }
    }
    if eps == 0.0 {
        eps = toler;
    } else {
        eps *= toler;
    }
    let mut rank = 0i32;
    if m > 0 {
        let diag = diag.expect("diag");
        for i in 0..m {
            let pivot = diag[i];
            if !pivot.is_finite() || pivot < eps {
                for j in 0..n2 {
                    matrix[at(j, i, n)] = 0.0;
                }
                if pivot < -8.0 * eps {
                    nonneg = -1;
                }
            } else {
                rank += 1;
                for j in 0..n2 {
                    let temp = matrix[at(j, i, n)] / pivot;
                    matrix[at(j, i, n)] = temp;
                    matrix[at(j, j + m, n)] -= temp * temp * pivot;
                    for k in (j + 1)..n2 {
                        let mk = matrix[at(k, i, n)];
                        matrix[at(k, j + m, n)] -= temp * mk;
                    }
                }
            }
        }
    }
    for i in 0..n2 {
        let pivot = matrix[at(i, i + m, n)];
        if !pivot.is_finite() || pivot < eps {
            for j in i..n2 {
                matrix[at(j, i + m, n)] = 0.0;
            }
            if pivot < -8.0 * eps {
                nonneg = -1;
            }
        } else {
            rank += 1;
            for j in (i + 1)..n2 {
                let temp = matrix[at(j, i + m, n)] / pivot;
                matrix[at(j, i + m, n)] = temp;
                matrix[at(j, j + m, n)] -= temp * temp * pivot;
                for k in (j + 1)..n2 {
                    let mk = matrix[at(k, i + m, n)];
                    matrix[at(k, j + m, n)] -= temp * mk;
                }
            }
        }
    }
    rank * nonneg
}

fn chsolve2(matrix: &[f64], n: usize, y: &mut [f64]) {
    for i in 0..n {
        let mut temp = y[i];
        for j in 0..i {
            temp -= y[j] * matrix[at(i, j, n)];
        }
        y[i] = temp;
    }
    for i in (0..n).rev() {
        if matrix[at(i, i, n)] == 0.0 {
            y[i] = 0.0;
        } else {
            let mut temp = y[i] / matrix[at(i, i, n)];
            for j in (i + 1)..n {
                temp -= y[j] * matrix[at(j, i, n)];
            }
            y[i] = temp;
        }
    }
}

fn chinv2(matrix: &mut [f64], n: usize) {
    for i in 0..n {
        if matrix[at(i, i, n)] > 0.0 {
            matrix[at(i, i, n)] = 1.0 / matrix[at(i, i, n)];
            for j in (i + 1)..n {
                matrix[at(j, i, n)] = -matrix[at(j, i, n)];
                for k in 0..i {
                    matrix[at(j, k, n)] += matrix[at(j, i, n)] * matrix[at(i, k, n)];
                }
            }
        }
    }
    for i in 0..n {
        if matrix[at(i, i, n)] == 0.0 {
            for j in 0..i {
                matrix[at(j, i, n)] = 0.0;
            }
            for j in i..n {
                matrix[at(i, j, n)] = 0.0;
            }
        } else {
            for j in (i + 1)..n {
                let temp = matrix[at(j, i, n)] * matrix[at(j, j, n)];
                if j != i {
                    matrix[at(i, j, n)] = temp;
                }
                for k in i..j {
                    matrix[at(i, k, n)] += temp * matrix[at(j, k, n)];
                }
            }
        }
    }
}

fn symmetrize(imat: &mut [f64], n: usize) {
    for i in 1..n {
        for j in 0..i {
            imat[at(i, j, n)] = imat[at(j, i, n)];
        }
    }
}

/// Log-likelihood and derivatives for one Newton step (`survregc1`, no frailty).
fn survregc1(
    n: usize,
    nvar: usize,
    nstrat: usize,
    whichcase: i32,
    beta: &[f64],
    dist: Dist,
    strat: &[i32],
    offset: &[f64],
    time1: &[f64],
    time2: Option<&[f64]>,
    status: &[f64],
    wt: &[f64],
    covar: &[f64],
    imat: &mut [f64],
    jj: &mut [f64],
    u: &mut [f64],
) -> f64 {
    let nvar2 = nvar + nstrat;
    let mut loglik = 0.0;
    if whichcase == 0 {
        for i in 0..nvar2 {
            u[i] = 0.0;
            for j in 0..nvar2 {
                imat[at(j, i, nvar2)] = 0.0;
                jj[at(j, i, nvar2)] = 0.0;
            }
        }
    }

    let mut strata = 0usize;
    let mut sigma = beta[nvar].exp();
    let mut sig2 = 1.0 / (sigma * sigma);
    let mut funs = [0.0; 4];
    let mut ufun = [0.0; 4];

    for person in 0..n {
        if nstrat > 1 {
            strata = (strat[person] - 1) as usize;
            sigma = beta[strata + nvar].exp();
            sig2 = 1.0 / (sigma * sigma);
        }
        let mut eta = 0.0;
        for i in 0..nvar {
            eta += beta[i] * covar[i * n + person];
        }
        eta += offset[person];
        let sz = time1[person] - eta;
        let z = sz / sigma;
        let jstat = status[person] as i32;

        let mut g = 0.0;
        let mut dg = 0.0;
        let mut ddg = 0.0;
        let mut dsig = 0.0;
        let mut ddsig = 0.0;
        let mut dsg = 0.0;

        match jstat {
            1 => {
                sreg_gg(dist, z, &mut funs, 1);
                if funs[1] <= 0.0 {
                    g = SMALL;
                    dg = -z / sigma;
                    ddg = -1.0 / sigma;
                    dsig = 0.0;
                    ddsig = 0.0;
                    dsg = 0.0;
                } else {
                    g = funs[1].ln() - sigma.ln();
                    let temp = funs[2] / sigma;
                    let temp2 = funs[3] * sig2;
                    dg = -temp;
                    dsig = -temp * sz;
                    ddg = temp2 - dg * dg;
                    dsg = sz * temp2 - dg * (dsig + 1.0);
                    ddsig = sz * sz * temp2 - dsig * (1.0 + dsig);
                    dsig -= 1.0;
                }
            }
            0 => {
                sreg_gg(dist, z, &mut funs, 2);
                if funs[1] <= 0.0 {
                    g = SMALL;
                    dg = z / sigma;
                    ddg = 0.0;
                    dsig = 0.0;
                    ddsig = 0.0;
                    dsg = 0.0;
                } else {
                    g = funs[1].ln();
                    let temp = -funs[2] / (funs[1] * sigma);
                    let temp2 = -funs[3] * sig2 / funs[1];
                    dg = -temp;
                    dsig = -temp * sz;
                    ddg = temp2 - dg * dg;
                    dsg = sz * temp2 - dg * (dsig + 1.0);
                    ddsig = sz * sz * temp2 - dsig * (1.0 + dsig);
                }
            }
            2 => {
                sreg_gg(dist, z, &mut funs, 2);
                if funs[0] <= 0.0 {
                    g = SMALL;
                    dg = -z / sigma;
                    dsig = 0.0;
                    ddsig = 0.0;
                    dsg = 0.0;
                    ddg = 0.0;
                } else {
                    g = funs[0].ln();
                    let temp = funs[2] / (funs[0] * sigma);
                    let temp2 = funs[3] * sig2 / funs[0];
                    dg = -temp;
                    dsig = -temp * sz;
                    ddg = temp2 - dg * dg;
                    dsg = sz * temp2 - dg * (dsig + 1.0);
                    ddsig = sz * sz * temp2 - dsig * (1.0 + dsig);
                }
            }
            3 => {
                let zu = (time2.expect("time2")[person] - eta) / sigma;
                sreg_gg(dist, z, &mut funs, 2);
                sreg_gg(dist, zu, &mut ufun, 2);
                let temp = if z > 0.0 {
                    funs[1] - ufun[1]
                } else {
                    ufun[0] - funs[0]
                };
                if temp <= 0.0 {
                    g = SMALL;
                    dg = 1.0;
                    ddg = 0.0;
                    dsig = 0.0;
                    ddsig = 0.0;
                    dsg = 0.0;
                } else {
                    g = temp.ln();
                    dg = -(ufun[2] - funs[2]) / (temp * sigma);
                    ddg = (ufun[3] - funs[3]) * sig2 / temp - dg * dg;
                    dsig = (z * funs[2] - zu * ufun[2]) / temp;
                    ddsig = (zu * zu * ufun[3] - z * z * funs[3]) / temp - dsig * (1.0 + dsig);
                    dsg = (zu * ufun[3] - z * funs[3]) / (temp * sigma) - dg * (dsig + 1.0);
                }
            }
            _ => {}
        }
        loglik += g * wt[person];
        if whichcase == 1 {
            continue;
        }
        let w = wt[person];
        for i in 0..nvar {
            let temp = dg * covar[i * n + person] * w;
            u[i] += temp;
            for j in 0..=i {
                imat[at(i, j, nvar2)] -= covar[i * n + person] * covar[j * n + person] * ddg * w;
                jj[at(i, j, nvar2)] += temp * covar[j * n + person] * dg;
            }
        }
        if nstrat != 0 {
            let k = strata + nvar;
            u[k] += w * dsig;
            for i in 0..nvar {
                imat[at(k, i, nvar2)] -= dsg * covar[i * n + person] * w;
                jj[at(k, i, nvar2)] += dsig * covar[i * n + person] * dg * w;
            }
            imat[at(k, k, nvar2)] -= ddsig * w;
            jj[at(k, k, nvar2)] += dsig * dsig * w;
        }
    }
    loglik
}

/// Coefficients, iteration count, inverse information, log-likelihood, flag, and score.
#[derive(Clone, Debug)]
pub struct SurvregResult {
    pub coef: Vec<f64>,
    pub iter: i32,
    pub var: Vec<f64>,
    pub loglik: f64,
    pub flag: i32,
    pub u: Vec<f64>,
}

fn split_y(y: &[f64], n: usize, ny: i32) -> (&[f64], Option<&[f64]>, &[f64]) {
    if ny == 2 {
        (&y[..n], None, &y[n..2 * n])
    } else {
        (&y[..n], Some(&y[n..2 * n]), &y[2 * n..3 * n])
    }
}

fn validate(
    maxiter: i32,
    nvar: usize,
    y: &[f64],
    ny: i32,
    covar: &[f64],
    wt: &[f64],
    offset: &[f64],
    beta: &[f64],
    nstrat: i32,
    strata: &[i32],
    dist: i32,
) -> Result<(usize, Dist), String> {
    if maxiter < 0 {
        return Err("maxiter must be >= 0".to_string());
    }
    if ny != 2 && ny != 3 {
        return Err("ny must be 2 or 3".to_string());
    }
    if nstrat < 0 {
        return Err("nstrat must be >= 0".to_string());
    }
    let dist = match dist {
        1 => Dist::Extreme,
        2 => Dist::Logistic,
        3 => Dist::Gauss,
        _ => return Err("dist must be 1, 2, or 3".to_string()),
    };
    let n = wt.len();
    if offset.len() != n || strata.len() != n {
        return Err("wt, offset, and strata must have the same length".to_string());
    }
    if y.len() != n * ny as usize {
        return Err("y must have length n * ny in column-major order".to_string());
    }
    if covar.len() != n * nvar {
        return Err("covar must have length n * nvar in column-major order".to_string());
    }
    let nstrat_u = nstrat as usize;
    let need = if nstrat_u == 0 {
        nvar + 1
    } else {
        nvar + nstrat_u
    };
    if beta.len() < need {
        return Err("beta is shorter than nvar + scales".to_string());
    }
    Ok((n, dist))
}

fn survreg6_inner(
    maxiter: i32,
    nvar: usize,
    y: &[f64],
    ny: i32,
    covar: &[f64],
    wt: &[f64],
    offset: &[f64],
    beta_in: &[f64],
    nstrat: i32,
    strata: &[i32],
    eps: f64,
    tol_chol: f64,
    dist: Dist,
    n: usize,
) -> SurvregResult {
    let nstrat_u = nstrat as usize;
    let nvar2 = nvar + nstrat_u;
    let mut beta = beta_in.to_vec();
    let mut newbeta = vec![0.0; beta.len()];
    for i in nvar..beta.len() {
        newbeta[i] = beta[i];
    }
    let (time1, time2, status) = split_y(y, n, ny);
    let mut imat = vec![0.0; nvar2 * nvar2];
    let mut jj = vec![0.0; nvar2 * nvar2];
    let mut u = vec![0.0; nvar2];
    let mut usave = vec![0.0; nvar2];

    let mut loglik = survregc1(
        n, nvar, nstrat_u, 0, &beta, dist, strata, offset, time1, time2, status, wt, covar,
        &mut imat, &mut jj, &mut u,
    );
    usave.copy_from_slice(&u);
    let mut flag = cholesky3(&mut imat, nvar2, 0, None, tol_chol);
    if flag < 0 {
        cholesky3(&mut jj, nvar2, 0, None, tol_chol);
        chsolve2(&jj, nvar2, &mut u);
    } else {
        chsolve2(&imat, nvar2, &mut u);
    }
    for i in 0..nvar2 {
        newbeta[i] = beta[i] + u[i];
    }
    if maxiter == 0 {
        chinv2(&mut imat, nvar2);
        symmetrize(&mut imat, nvar2);
        return SurvregResult {
            coef: beta,
            iter: 0,
            var: imat,
            loglik,
            flag,
            u: usave,
        };
    }

    let mut newlk = survregc1(
        n, nvar, nstrat_u, 0, &newbeta, dist, strata, offset, time1, time2, status, wt, covar,
        &mut imat, &mut jj, &mut u,
    );
    usave.copy_from_slice(&u);
    let mut halving = 0i32;
    let mut finished = false;
    let mut iter_done = maxiter;

    for iter in 1..=maxiter {
        let mut bad = if newlk.is_finite() { 0 } else { 1 };
        for j in 0..nvar2 {
            if !imat[at(j, j, nvar2)].is_finite() {
                bad += 1;
            }
            if !u[j].is_finite() {
                bad += 1;
            }
        }
        if bad == 0
            && halving == 0
            && ((1.0 - loglik / newlk).abs() <= eps || (loglik - newlk).abs() <= eps)
        {
            loglik = newlk;
            flag = cholesky3(&mut imat, nvar2, 0, None, tol_chol);
            chinv2(&mut imat, nvar2);
            symmetrize(&mut imat, nvar2);
            for i in 0..nvar2 {
                beta[i] = newbeta[i];
            }
            if halving == 1 {
                flag = 1000;
            }
            iter_done = iter;
            finished = true;
            break;
        }
        if bad > 0 || newlk < loglik {
            halving += 1;
            for i in 0..nvar2 {
                newbeta[i] = (newbeta[i] + 2.0 * beta[i]) / 3.0;
            }
            if halving == 1 {
                for i in 0..nstrat_u {
                    if beta[nvar + i] - newbeta[nvar + i] > 1.1 {
                        newbeta[nvar + i] = beta[nvar + i] - 1.1;
                    }
                }
            }
            let _ = survregc1(
                n, nvar, nstrat_u, 1, &newbeta, dist, strata, offset, time1, time2, status, wt,
                covar, &mut imat, &mut jj, &mut u,
            );
        } else {
            halving = 0;
            loglik = newlk;
            flag = cholesky3(&mut imat, nvar2, 0, None, tol_chol);
            if flag < 0 {
                cholesky3(&mut jj, nvar2, 0, None, tol_chol);
                chsolve2(&jj, nvar2, &mut u);
            } else {
                chsolve2(&imat, nvar2, &mut u);
            }
            for i in 0..nvar2 {
                beta[i] = newbeta[i];
                newbeta[i] += u[i];
            }
        }
        newlk = survregc1(
            n, nvar, nstrat_u, 0, &newbeta, dist, strata, offset, time1, time2, status, wt, covar,
            &mut imat, &mut jj, &mut u,
        );
        usave.copy_from_slice(&u);
    }

    if !finished {
        if halving == 0 && newlk.is_finite() && newlk >= loglik {
            for i in 0..nvar2 {
                beta[i] = newbeta[i];
            }
        } else {
            survregc1(
                n, nvar, nstrat_u, 0, &beta, dist, strata, offset, time1, time2, status, wt, covar,
                &mut imat, &mut jj, &mut u,
            );
        }
        cholesky3(&mut imat, nvar2, 0, None, tol_chol);
        chinv2(&mut imat, nvar2);
        symmetrize(&mut imat, nvar2);
        flag = 1000;
        iter_done = maxiter;
    }

    SurvregResult {
        coef: beta,
        iter: iter_done,
        var: imat,
        loglik,
        flag,
        u: usave,
    }
}

/// One parametric survival fit. `y` and `covar` are column-major, matching R `as.double`.
///
/// `nstrat == 0` keeps `beta[nvar]` as a fixed log-scale. `flag` is the Cholesky rank on
/// convergence and `1000` when the iteration stops short.
pub fn survreg6(
    maxiter: i32,
    nvar: usize,
    y: &[f64],
    ny: i32,
    covar: &[f64],
    wt: &[f64],
    offset: &[f64],
    beta: &[f64],
    nstrat: i32,
    strata: &[i32],
    eps: f64,
    tol_chol: f64,
    dist: i32,
) -> Result<SurvregResult, String> {
    let (n, dist) = validate(
        maxiter, nvar, y, ny, covar, wt, offset, beta, nstrat, strata, dist,
    )?;
    Ok(survreg6_inner(
        maxiter, nvar, y, ny, covar, wt, offset, beta, nstrat, strata, eps, tol_chol, dist, n,
    ))
}

/// Same fit as [`survreg6`]. The second value is milliseconds from [`Instant`] around the iteration.
pub fn survreg6_timed(
    maxiter: i32,
    nvar: usize,
    y: &[f64],
    ny: i32,
    covar: &[f64],
    wt: &[f64],
    offset: &[f64],
    beta: &[f64],
    nstrat: i32,
    strata: &[i32],
    eps: f64,
    tol_chol: f64,
    dist: i32,
) -> Result<(SurvregResult, f64), String> {
    let (n, dist) = validate(
        maxiter, nvar, y, ny, covar, wt, offset, beta, nstrat, strata, dist,
    )?;
    let start = Instant::now();
    let fit = survreg6_inner(
        maxiter, nvar, y, ny, covar, wt, offset, beta, nstrat, strata, eps, tol_chol, dist, n,
    );
    let ms = start.elapsed().as_secs_f64() * 1000.0;
    Ok((fit, ms))
}

#[cfg(feature = "python")]
fn take_slices(
    nvar: i32,
    y: PyReadonlyArray1<'_, f64>,
    ny: i32,
    covar: PyReadonlyArray1<'_, f64>,
    wt: PyReadonlyArray1<'_, f64>,
    offset: PyReadonlyArray1<'_, f64>,
    beta: PyReadonlyArray1<'_, f64>,
    nstrat: i32,
    strata: PyReadonlyArray1<'_, i32>,
    dist: i32,
) -> PyResult<(
    usize,
    Vec<f64>,
    i32,
    Vec<f64>,
    Vec<f64>,
    Vec<f64>,
    Vec<f64>,
    i32,
    Vec<i32>,
    i32,
)> {
    if nvar < 0 {
        return Err(PyValueError::new_err("nvar must be >= 0"));
    }
    Ok((
        nvar as usize,
        y.as_slice()?.to_vec(),
        ny,
        covar.as_slice()?.to_vec(),
        wt.as_slice()?.to_vec(),
        offset.as_slice()?.to_vec(),
        beta.as_slice()?.to_vec(),
        nstrat,
        strata.as_slice()?.to_vec(),
        dist,
    ))
}

#[cfg(feature = "python")]
fn pack(
    py: Python<'_>,
    fit: SurvregResult,
) -> PyResult<(
    Py<PyArray1<f64>>,
    i32,
    Py<PyArray1<f64>>,
    f64,
    i32,
    Py<PyArray1<f64>>,
)> {
    Ok((
        PyArray1::from_vec(py, fit.coef).into(),
        fit.iter,
        PyArray1::from_vec(py, fit.var).into(),
        fit.loglik,
        fit.flag,
        PyArray1::from_vec(py, fit.u).into(),
    ))
}

#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(name = "survreg6")]
fn survreg6_py(
    maxiter: i32,
    nvar: i32,
    y: PyReadonlyArray1<'_, f64>,
    ny: i32,
    covar: PyReadonlyArray1<'_, f64>,
    wt: PyReadonlyArray1<'_, f64>,
    offset: PyReadonlyArray1<'_, f64>,
    beta: PyReadonlyArray1<'_, f64>,
    nstrat: i32,
    strata: PyReadonlyArray1<'_, i32>,
    eps: f64,
    tol_chol: f64,
    dist: i32,
) -> PyResult<(
    Py<PyArray1<f64>>,
    i32,
    Py<PyArray1<f64>>,
    f64,
    i32,
    Py<PyArray1<f64>>,
)> {
    let (nvar, y, ny, covar, wt, offset, beta, nstrat, strata, dist) =
        take_slices(nvar, y, ny, covar, wt, offset, beta, nstrat, strata, dist)?;
    let fit = survreg6(
        maxiter, nvar, &y, ny, &covar, &wt, &offset, &beta, nstrat, &strata, eps, tol_chol, dist,
    )
    .map_err(PyValueError::new_err)?;
    Python::attach(|py| pack(py, fit))
}

#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(name = "survreg6_timed")]
fn survreg6_timed_py(
    maxiter: i32,
    nvar: i32,
    y: PyReadonlyArray1<'_, f64>,
    ny: i32,
    covar: PyReadonlyArray1<'_, f64>,
    wt: PyReadonlyArray1<'_, f64>,
    offset: PyReadonlyArray1<'_, f64>,
    beta: PyReadonlyArray1<'_, f64>,
    nstrat: i32,
    strata: PyReadonlyArray1<'_, i32>,
    eps: f64,
    tol_chol: f64,
    dist: i32,
) -> PyResult<(
    Py<PyArray1<f64>>,
    i32,
    Py<PyArray1<f64>>,
    f64,
    i32,
    Py<PyArray1<f64>>,
    f64,
)> {
    let (nvar, y, ny, covar, wt, offset, beta, nstrat, strata, dist) =
        take_slices(nvar, y, ny, covar, wt, offset, beta, nstrat, strata, dist)?;
    let (fit, ms) = survreg6_timed(
        maxiter, nvar, &y, ny, &covar, &wt, &offset, &beta, nstrat, &strata, eps, tol_chol, dist,
    )
    .map_err(PyValueError::new_err)?;
    Python::attach(|py| {
        let (coef, iter, var, loglik, flag, u) = pack(py, fit)?;
        Ok((coef, iter, var, loglik, flag, u, ms))
    })
}

#[cfg(feature = "python")]
#[pymodule(name = "survreg6")]
fn survreg6_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(survreg6_py, m)?)?;
    m.add_function(wrap_pyfunction!(survreg6_timed_py, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn small_extreme_value_matches_r() {
        let time = [1.2, 2.5, 0.8, 4.1, 3.3, 1.7];
        let status = [1.0, 1.0, 0.0, 1.0, 0.0, 1.0];
        let mut y = Vec::new();
        y.extend(time.iter().copied().map(f64::ln));
        y.extend_from_slice(&status);
        let x1 = [0.0, 1.0, 0.0, 1.0, 1.0, 0.0];
        let x2 = [-1.0, 0.5, 1.2, -0.2, 2.1, 0.0];
        let mut covar = vec![1.0; 6];
        covar.extend_from_slice(&x1);
        covar.extend_from_slice(&x2);
        let wt = [1.0; 6];
        let offset = [0.0; 6];
        let beta = [0.5, 0.1, -0.2, (0.8f64).ln()];
        let strata = [1; 6];
        let fit = survreg6(
            30, 3, &y, 2, &covar, &wt, &offset, &beta, 1, &strata, 1e-9, 1e-10, 1,
        )
        .unwrap();
        let expect_coef = [
            0.461692677065212,
            0.87675232871618447,
            0.15482791695081588,
            -1.8252663994775418,
        ];
        let expect_var = [
            0.015068884784640668,
            -0.013807165565142335,
            0.0088826104331996714,
            -0.0024146251196261724,
            -0.013807165565142335,
            0.026954655520726917,
            -0.0045121148104123997,
            -0.009527661110143297,
            0.0088826104331996714,
            -0.0045121148104123997,
            0.039507069451696082,
            0.0059510622882940397,
            -0.0024146251196261724,
            -0.009527661110143297,
            0.0059510622882940397,
            0.17033353284175048,
        ];
        assert_eq!(fit.iter, 10);
        assert_eq!(fit.flag, 4);
        assert!((fit.loglik - 0.49871320617128229).abs() < 1e-8);
        for (a, b) in fit.coef.iter().zip(expect_coef.iter()) {
            assert!((a - b).abs() < 1e-8, "{a} vs {b}");
        }
        for (a, b) in fit.var.iter().zip(expect_var.iter()) {
            assert!((a - b).abs() < 1e-8, "{a} vs {b}");
        }
        for u in &fit.u {
            assert!(u.abs() < 1e-8);
        }
    }
}
