//! Penalized parametric survival fit: survival `survpenal.fit` (R front end) with
//! `Csurvreg7` (src/survreg7.c), `survpenal` (src/survpenal.c), `survregc1`
//! (src/survregc1.c), and the dense branch of `coxpenal.df` (R/coxpenal.df.R).
//!
//! Matrices use the survival C layout `at(col, row, n) = col * n + row`. That flat
//! order is also R's column-major order, so flat index `c * n + r` is R element
//! `[r, c]` of an `n x n` matrix.
//!
//! Scope of this crate:
//! - built-in distributions only (dnum 1 to 3: extreme value, logistic, Gaussian);
//!   dnum 4 needs R's density callback and is not included;
//! - dense penalties with a diagonal penalty matrix (`diag = TRUE`), evaluated through
//!   Python callbacks `pfun` and `cfun`;
//! - no sparse frailty term and no full (non-diagonal) penalty matrix.

use numpy::{PyArray1, PyReadonlyArray1};
use pyo3::exceptions::{PyNotImplementedError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyFloat, PyTuple};

const SMALL: f64 = -200.0;
const SPI: f64 = 2.506628274631001;
const ROOT_2: f64 = 1.414213562373095;
const COXPH_WTEST_TOLER: f64 = 1e-9;

// Same libm `erf` / `erfc` the survival C code calls.
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

/// survival's `matrix[col][row]` for an `n x n` block.
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

/// Log-likelihood and its derivatives for the built-in distributions (`survregc1`).
/// With no sparse term, `beta` holds `nvar` coefficients then `nstrat` log-scales.
#[allow(clippy::too_many_arguments)]
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

        let mut g = 0.0;
        let mut dg = 0.0;
        let mut ddg = 0.0;
        let mut dsig = 0.0;
        let mut ddsig = 0.0;
        let mut dsg = 0.0;

        match status[person] as i32 {
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

/// Cholesky `C = FDF'` with no sparse block (`cholesky3` with `m = 0`).
fn cholesky3(matrix: &mut [f64], n: usize, toler: f64) -> i32 {
    let mut nonneg = 1i32;
    let mut eps = 0.0;
    for i in 0..n {
        let v = matrix[at(i, i, n)];
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
    for i in 0..n {
        let pivot = matrix[at(i, i, n)];
        if !pivot.is_finite() || pivot < eps {
            for j in i..n {
                matrix[at(j, i, n)] = 0.0;
            }
            if pivot < -8.0 * eps {
                nonneg = -1;
            }
        } else {
            rank += 1;
            for j in (i + 1)..n {
                let temp = matrix[at(j, i, n)] / pivot;
                matrix[at(j, i, n)] = temp;
                matrix[at(j, j, n)] -= temp * temp * pivot;
                for k in (j + 1)..n {
                    let mk = matrix[at(k, i, n)];
                    matrix[at(k, j, n)] -= temp * mk;
                }
            }
        }
    }
    rank * nonneg
}

/// Solve with the factor from `cholesky3` (`chsolve3` with `m = 0`).
fn chsolve3(matrix: &[f64], n: usize, y: &mut [f64]) {
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

/// Invert the Cholesky factor in place (`chinv3` with `m = 0`). Only the first loop
/// of survival's `chinv3` is ported: the lower triangle then holds the inverse factor.
fn chinv3(matrix: &mut [f64], n: usize) {
    for i in 0..n {
        let ii = i;
        if matrix[at(i, ii, n)] > 0.0 {
            matrix[at(i, ii, n)] = 1.0 / matrix[at(i, ii, n)];
            for j in (i + 1)..n {
                matrix[at(j, ii, n)] = -matrix[at(j, ii, n)];
                for k in 0..ii {
                    let add = matrix[at(j, ii, n)] * matrix[at(i, k, n)];
                    matrix[at(j, k, n)] += add;
                }
            }
        }
    }
}

/// `cholesky2` from survival: `C = FDF'` for a plain dense matrix, copying the upper
/// triangle into the lower one first. Used by the Wald test in `coxph.wtest`.
fn cholesky2(matrix: &mut [f64], n: usize, toler: f64) -> i32 {
    let mut nonneg = 1i32;
    let mut eps = 0.0;
    for i in 0..n {
        if matrix[at(i, i, n)] > eps {
            eps = matrix[at(i, i, n)];
        }
        for j in (i + 1)..n {
            matrix[at(j, i, n)] = matrix[at(i, j, n)];
        }
    }
    if eps == 0.0 {
        eps = toler;
    } else {
        eps *= toler;
    }
    let mut rank = 0i32;
    for i in 0..n {
        let pivot = matrix[at(i, i, n)];
        if !pivot.is_finite() || pivot < eps {
            matrix[at(i, i, n)] = 0.0;
            if pivot < -8.0 * eps {
                nonneg = -1;
            }
        } else {
            rank += 1;
            for j in (i + 1)..n {
                let temp = matrix[at(j, i, n)] / pivot;
                matrix[at(j, i, n)] = temp;
                matrix[at(j, j, n)] -= temp * temp * pivot;
                for k in (j + 1)..n {
                    let mk = matrix[at(k, i, n)];
                    matrix[at(k, j, n)] -= temp * mk;
                }
            }
        }
    }
    rank * nonneg
}

/// `chsolve2` from survival: solve with a `cholesky2` factor.
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

/// Solution `var^{-1} b` for each of the `ntest` columns of `b` (`Ccoxph_wtest`).
/// `var` is `k x k` and `b` is `k x ntest`, both in R column-major order.
fn coxph_wtest_solve(var: &[f64], k: usize, b: &[f64], ntest: usize) -> Vec<f64> {
    let mut factor = var.to_vec();
    cholesky2(&mut factor, k, COXPH_WTEST_TOLER);
    let mut solve = vec![0.0; k * ntest];
    for j in 0..ntest {
        let mut col = b[j * k..(j + 1) * k].to_vec();
        chsolve2(&factor, k, &mut col);
        solve[j * k..(j + 1) * k].copy_from_slice(&col);
    }
    solve
}

/// Output of the dense branch of `coxpenal.df`.
struct DfOut {
    var2: Vec<f64>,
    df: Vec<f64>,
    trh: Vec<f64>,
    var: Vec<f64>,
}

/// Dense branch of `coxpenal.df` (the `ptype == 2` case).
///
/// `hmat` and `hinv` are the R matrices `matrix(fit$hmat, ncol = n)` and
/// `matrix(fit$hinv, ncol = n)`, `fdiag` is `hdiag`, `pen2` is the diagonal of the
/// penalty second-derivative matrix, and `assign` holds 0-based column groups
/// (with the scale columns appended when there are strata).
fn coxpenal_df_dense(
    hmat: &[f64],
    hinv: &[f64],
    fdiag: &[f64],
    assign: &[Vec<usize>],
    pen2: &[f64],
    n: usize,
) -> DfOut {
    // R element [r, c] of an n x n matrix stored column-major.
    let rm = |m: &[f64], r: usize, c: usize| m[c * n + r];

    let w: Vec<f64> = fdiag
        .iter()
        .map(|&d| if d == 0.0 { 0.0 } else { 1.0 / d })
        .collect();

    // hmat.full = t(hmat) %*% (w * hmat)
    let mut hmat_full = vec![0.0; n * n];
    for a in 0..n {
        for b in 0..n {
            let mut s = 0.0;
            for r in 0..n {
                s += rm(hmat, r, a) * w[r] * rm(hmat, r, b);
            }
            hmat_full[b * n + a] = s;
        }
    }
    // hinv.full = hinv %*% (fdiag * t(hinv))
    let mut hinv_full = vec![0.0; n * n];
    for a in 0..n {
        for b in 0..n {
            let mut s = 0.0;
            for r in 0..n {
                s += rm(hinv, a, r) * fdiag[r] * rm(hinv, b, r);
            }
            hinv_full[b * n + a] = s;
        }
    }
    // imat = hmat.full - diag(pen2)
    let mut imat = hmat_full;
    for a in 0..n {
        imat[a * n + a] -= pen2[a];
    }
    // var = hinv.full %*% imat %*% hinv.full
    let mut tmp = vec![0.0; n * n];
    for a in 0..n {
        for b in 0..n {
            let mut s = 0.0;
            for c in 0..n {
                s += rm(&hinv_full, a, c) * rm(&imat, c, b);
            }
            tmp[b * n + a] = s;
        }
    }
    let mut var = vec![0.0; n * n];
    for a in 0..n {
        for b in 0..n {
            let mut s = 0.0;
            for c in 0..n {
                s += rm(&tmp, a, c) * rm(&hinv_full, c, b);
            }
            var[b * n + a] = s;
        }
    }

    if assign.len() == 1 {
        let mut df = 0.0;
        for a in 0..n {
            for b in 0..n {
                df += rm(&imat, a, b) * rm(&hinv_full, a, b);
            }
        }
        let mut trh = 0.0;
        for a in 0..n {
            trh += rm(&hinv_full, a, a);
        }
        return DfOut {
            var2: var,
            df: vec![df],
            trh: vec![trh],
            var: hinv_full,
        };
    }

    let d2: Vec<f64> = (0..n).map(|a| rm(&hinv_full, a, a)).collect();
    let mut df = Vec::with_capacity(assign.len());
    let mut trh = Vec::with_capacity(assign.len());
    for group in assign {
        let k = group.len();
        if k == 1 {
            let a = group[0];
            // coxph.wtest on a scalar: solve = b / var
            let b = rm(&var, a, a);
            let v = rm(&hinv_full, a, a);
            df.push(b / v);
        } else {
            // sub-blocks in R column-major order
            let mut sub_var = vec![0.0; k * k];
            let mut sub_b = vec![0.0; k * k];
            for c in 0..k {
                for r in 0..k {
                    sub_var[c * k + r] = rm(&hinv_full, group[r], group[c]);
                    sub_b[c * k + r] = rm(&var, group[r], group[c]);
                }
            }
            let solve = coxph_wtest_solve(&sub_var, k, &sub_b, k);
            let mut trace = 0.0;
            for j in 0..k {
                trace += solve[j * k + j];
            }
            df.push(trace);
        }
        let mut t = 0.0;
        for &a in group {
            t += d2[a];
        }
        trh.push(t);
    }
    DfOut {
        var2: var,
        df,
        trh,
        var: hinv_full,
    }
}

/// One penalized term as the R list `pattr[[i]]` gives it, with its callbacks.
struct Penalty {
    pcols: Vec<usize>,
    pfun: Py<PyAny>,
    cfun: Py<PyAny>,
    parms: Py<PyAny>,
    cargs: Vec<String>,
    extra: Option<Py<PyAny>>,
}

/// The list `pfun` returns: penalty, first, second, flag, and optional recenter.
struct PenValue {
    penalty: f64,
    first: Vec<f64>,
    second: Vec<f64>,
    flag: bool,
    recenter: Option<Vec<f64>>,
}

/// Result of one `Csurvreg7` call (`survreg7` in survreg7.c).
struct FitOut {
    coef: Vec<f64>,
    iter: i32,
    hmat: Vec<f64>,
    hinv: Vec<f64>,
    hdiag: Vec<f64>,
    loglik: f64,
    flag: i32,
    penalty: f64,
    u: Vec<f64>,
}

/// Result of the whole `survpenal.fit` iteration.
struct RunOut {
    fit: FitOut,
    df: Vec<f64>,
    var: Vec<f64>,
    var2: Vec<f64>,
    hdiag: Vec<f64>,
    iter_outer: i32,
    iter_total: i32,
    iterfail: Vec<i32>,
    iterlist: Vec<Py<PyAny>>,
    flags: Vec<bool>,
}

struct Fitter<'py> {
    py: Python<'py>,
    n: usize,
    nvar: usize,
    nstrat: usize,
    dist: Dist,
    ny: usize,
    time1: Vec<f64>,
    time2: Option<Vec<f64>>,
    status: Vec<f64>,
    covar: Vec<f64>,
    wt: Vec<f64>,
    offset: Vec<f64>,
    strat: Vec<i32>,
    eps: f64,
    tol: f64,
    n_eff: f64,
    pens: Vec<Penalty>,
    thetas: Vec<Vec<f64>>,
    // coxlist2 state: persists across calls, as the R closure's environment does.
    first: Vec<f64>,
    second: Vec<f64>,
    flag: Vec<bool>,
}

fn theta_of(res: &Bound<'_, PyAny>) -> PyResult<Vec<f64>> {
    let d = res.cast::<PyDict>()?;
    let v = d
        .get_item("theta")?
        .ok_or_else(|| PyValueError::new_err("cfun result has no theta"))?;
    if let Ok(vec) = v.extract::<Vec<f64>>() {
        return Ok(vec);
    }
    Ok(vec![v.extract::<f64>()?])
}

fn done_of(res: &Bound<'_, PyAny>) -> PyResult<bool> {
    let d = res.cast::<PyDict>()?;
    let v = d
        .get_item("done")?
        .ok_or_else(|| PyValueError::new_err("cfun result has no done"))?;
    v.is_truthy()
}

fn vec_or_scalar(v: &Bound<'_, PyAny>) -> PyResult<Vec<f64>> {
    if let Ok(vec) = v.extract::<Vec<f64>>() {
        return Ok(vec);
    }
    Ok(vec![v.extract::<f64>()?])
}

fn parse_pen(res: &Bound<'_, PyAny>) -> PyResult<PenValue> {
    let d = res.cast::<PyDict>()?;
    let get = |key: &str| -> PyResult<Bound<'_, PyAny>> {
        d.get_item(key)?
            .ok_or_else(|| PyValueError::new_err(format!("pfun result has no {key}")))
    };
    let penalty = get("penalty")?.extract::<f64>()?;
    let first = vec_or_scalar(&get("first")?)?;
    let second = vec_or_scalar(&get("second")?)?;
    let flag = get("flag")?.is_truthy()?;
    let recenter = match d.get_item("recenter")? {
        Some(v) if !v.is_none() => Some(vec_or_scalar(&v)?),
        _ => None,
    };
    Ok(PenValue {
        penalty,
        first,
        second,
        flag,
        recenter,
    })
}

impl<'py> Fitter<'py> {
    fn dolik(
        &self,
        whichcase: i32,
        beta: &[f64],
        imat: &mut [f64],
        jj: &mut [f64],
        u: &mut [f64],
    ) -> f64 {
        survregc1(
            self.n,
            self.nvar,
            self.nstrat,
            whichcase,
            beta,
            self.dist,
            &self.strat,
            &self.offset,
            &self.time1,
            self.time2.as_deref(),
            &self.status,
            &self.wt,
            &self.covar,
            imat,
            jj,
            u,
        )
    }

    /// Call the Python `pfun` of penalty `i` (`(cfun[[i]])`'s partner in `f.expr2`).
    fn call_pfun(&self, i: usize, tcoef: &[f64]) -> PyResult<PenValue> {
        let py = self.py;
        let pen = &self.pens[i];
        let coef_arr = PyArray1::from_slice(py, tcoef);
        let theta_obj: Bound<'_, PyAny> = if self.thetas[i].len() == 1 {
            PyFloat::new(py, self.thetas[i][0]).into_any()
        } else {
            PyArray1::from_slice(py, &self.thetas[i]).into_any()
        };
        let neff = PyFloat::new(py, self.n_eff);
        let res = match &pen.extra {
            None => pen
                .pfun
                .bind(py)
                .call1((coef_arr, theta_obj, neff))?,
            Some(e) => pen
                .pfun
                .bind(py)
                .call1((coef_arr, theta_obj, neff, e.bind(py)))?,
        };
        parse_pen(&res)
    }

    /// `survpenal` for the dense penalty (`ptype == 2`, `pdiag == 0`). It evaluates
    /// `f.expr2`, which updates `first`, `second`, and `flag`, and returns the penalty.
    fn survpenal(
        &mut self,
        whichcase: i32,
        beta: &mut [f64],
        hmat: &mut [f64],
        jj: &mut [f64],
        u: &mut [f64],
    ) -> PyResult<f64> {
        let nvar = self.nvar;
        let coef2: Vec<f64> = beta[..nvar].to_vec();
        let mut newcoef = coef2.clone();
        let mut pentot = 0.0;
        for i in 0..self.pens.len() {
            let cols = self.pens[i].pcols.clone();
            let tcoef: Vec<f64> = cols.iter().map(|&c| coef2[c]).collect();
            let temp = self.call_pfun(i, &tcoef)?;
            if let Some(rec) = &temp.recenter {
                for (k, &c) in cols.iter().enumerate() {
                    newcoef[c] = tcoef[k] - rec[k];
                }
            }
            if temp.flag {
                for &c in &cols {
                    self.flag[c] = true;
                }
            } else {
                for &c in &cols {
                    self.flag[c] = false;
                }
                for (k, &c) in cols.iter().enumerate() {
                    self.first[c] = -temp.first[k];
                    self.second[c] = temp.second[k];
                }
            }
            pentot -= temp.penalty;
        }
        let penalty = pentot;

        if whichcase == 0 {
            // hmat and JJ are n2 x n2 (n2 = nvar + nstrat), so the column stride is n2.
            let n2 = nvar + self.nstrat;
            for i in 0..nvar {
                beta[i] = newcoef[i];
            }
            for i in 0..nvar {
                u[i] += self.first[i];
            }
            for i in 0..nvar {
                jj[at(i, i, n2)] += self.second[i];
                hmat[at(i, i, n2)] += self.second[i];
            }
            for i in 0..nvar {
                if self.flag[i] {
                    // An infinite penalty: no update for this column, identity on H.
                    u[i] = 0.0;
                    hmat[at(i, i, n2)] = 1.0;
                    for j in 0..i {
                        hmat[at(i, j, n2)] = 0.0;
                    }
                }
            }
        }
        Ok(penalty)
    }

    /// `Csurvreg7`: Newton-Raphson with step halving, for one `survpenal.fit` pass.
    fn csurvreg7(&mut self, maxiter: i32, beta_in: &[f64]) -> PyResult<FitOut> {
        let nvar = self.nvar;
        let nstrat = self.nstrat;
        let n2 = nvar + nstrat;
        let mut beta = beta_in.to_vec();
        let mut newbeta = beta.clone();
        let mut hmat = vec![0.0; n2 * n2];
        let mut hinv = vec![0.0; n2 * n2];
        let mut jj = vec![0.0; n2 * n2];
        let mut u = vec![0.0; n2];
        let mut hdiag = vec![0.0; n2];

        let mut loglik = self.dolik(0, &beta, &mut hmat, &mut jj, &mut u);
        let mut penalty = self.survpenal(0, &mut beta, &mut hmat, &mut jj, &mut u)?;
        loglik += penalty;
        let mut usave = u.clone();

        let mut iter: i32 = 1;
        loop {
            if iter > maxiter {
                break;
            }
            // Newton or Fisher step
            let step_flag = cholesky3(&mut hmat, n2, self.tol);
            if step_flag < 0 {
                cholesky3(&mut jj, n2, self.tol);
                chsolve3(&jj, n2, &mut u);
            } else {
                chsolve3(&hmat, n2, &mut u);
            }
            for i in 0..n2 {
                newbeta[i] = beta[i] + u[i];
            }
            let mut newlk = self.dolik(0, &newbeta, &mut hmat, &mut jj, &mut u);
            let mut newpen = self.survpenal(0, &mut newbeta, &mut hmat, &mut jj, &mut u)?;
            newlk += newpen;

            if (1.0 - loglik / newlk).abs() <= self.eps {
                loglik = newlk;
                penalty = newpen;
                for i in 0..n2 {
                    beta[i] = newbeta[i];
                    usave[i] = u[i];
                }
                break;
            }

            if newlk < loglik {
                // Golden section search along the step, with the sigma shrinkage cap.
                for i in 0..n2 {
                    u[i] = newbeta[i] - beta[i];
                }
                for i in 0..nstrat {
                    if u[i + nvar] < -0.7 {
                        u[i + nvar] = -1.1;
                    }
                }
                let mut x4 = 1.0;
                let mut x1 = 0.0;
                let mut x3 = 1.0;
                let mut y1 = loglik;
                let mut y3 = newlk;
                while y1 > y3 {
                    x4 = x3;
                    x3 = x1;
                    x1 = x3 - (x4 - x3) / 0.618;
                    y3 = y1;
                    for i in 0..n2 {
                        newbeta[i] = beta[i] + u[i] * x1;
                    }
                    y1 = self.dolik(1, &newbeta, &mut hmat, &mut jj, &mut u);
                    newpen = self.survpenal(1, &mut newbeta, &mut hmat, &mut jj, &mut u)?;
                    y1 += newpen;
                }

                let mut x2 = 0.618 * x3 + 0.382 * x1;
                for i in 0..n2 {
                    newbeta[i] = beta[i] + u[i] * x2;
                }
                let mut y2 = self.dolik(1, &newbeta, &mut hmat, &mut jj, &mut u);
                newpen = self.survpenal(1, &mut newbeta, &mut hmat, &mut jj, &mut u)?;
                y2 += newpen;

                for _golden in 0..8 {
                    let goright;
                    if y3 > y2 {
                        x1 = x2;
                        x2 = x3;
                        x3 = 0.618 * x4 + 0.382 * x1;
                        y2 = y3;
                        for i in 0..n2 {
                            newbeta[i] = beta[i] + u[i] * x3;
                        }
                        goright = true;
                    } else {
                        x4 = x3;
                        x3 = x2;
                        x2 = 0.618 * x1 + 0.382 * x4;
                        y3 = y2;
                        for i in 0..n2 {
                            newbeta[i] = beta[i] + u[i] * x2;
                        }
                        goright = false;
                    }
                    newlk = self.dolik(1, &newbeta, &mut hmat, &mut jj, &mut u);
                    newpen = self.survpenal(1, &mut newbeta, &mut hmat, &mut jj, &mut u)?;
                    if goright {
                        y3 = newlk + newpen;
                    } else {
                        y2 = newlk + newpen;
                    }
                }

                if y2 > loglik || y3 > loglik {
                    if y2 > y3 {
                        for i in 0..n2 {
                            newbeta[i] = beta[i] + u[i] * x2;
                        }
                    } else {
                        for i in 0..n2 {
                            newbeta[i] = beta[i] + u[i] * x3;
                        }
                    }
                    newlk = self.dolik(0, &newbeta, &mut hmat, &mut jj, &mut u);
                    newpen = self.survpenal(0, &mut newbeta, &mut hmat, &mut jj, &mut u)?;
                    newlk += newpen;
                } else {
                    // abject failure: leave the iteration loop
                    break;
                }
            }

            // Accept newbeta
            for i in 0..n2 {
                beta[i] = newbeta[i];
                usave[i] = u[i];
            }
            loglik = newlk;
            penalty = newpen;
            iter += 1;
        }

        // Normal exit leaves iter at maxiter + 1, and a failed step leaves it at the
        // failing iteration; both are reported as the iteration count.
        // survreg7.c sets flag = 1000 here, but its `alldone` label overwrites it with
        // the Cholesky rank, so the returned flag is always the rank.
        let iter2 = iter;

        // alldone
        let flag = cholesky3(&mut hmat, n2, self.tol);
        hinv.copy_from_slice(&hmat);
        chinv3(&mut hinv, n2);
        for i in 0..n2 {
            hdiag[i] = hinv[at(i, i, n2)];
            hmat[at(i, i, n2)] = 1.0;
            hinv[at(i, i, n2)] = 1.0;
            for j in (i + 1)..n2 {
                hmat[at(i, j, n2)] = 0.0;
                hinv[at(i, j, n2)] = 0.0;
            }
        }
        Ok(FitOut {
            coef: beta,
            iter: iter2,
            hmat,
            hinv,
            hdiag,
            loglik,
            flag,
            penalty,
            u: usave,
        })
    }

    /// The outer loop of `survpenal.fit`: refit, then update every penalty through its
    /// `cfun` (for example the df search for `ridge(df = )`), until all report done.
    #[allow(clippy::too_many_arguments)]
    fn run(
        &mut self,
        init_in: &[f64],
        iter_max: i32,
        outer_max: i32,
        assign: &[Vec<usize>],
        pindex: &[usize],
        need_df: bool,
    ) -> PyResult<RunOut> {
        let py = self.py;
        let nvar = self.nvar;
        let nstrat = self.nstrat;
        let n2 = nvar + nstrat;
        let npen = self.pens.len();

        // Initial control call for each penalty (iter = 0).
        let mut iterlist: Vec<Py<PyAny>> = Vec::with_capacity(npen);
        for i in 0..npen {
            let temp = self.call_cfun(i, 0, None, &[])?;
            let temp_b = temp.bind(py);
            self.thetas[i] = theta_of(temp_b)?;
            iterlist.push(temp);
        }

        let flatten = |thetas: &Vec<Vec<f64>>| -> Vec<f64> { thetas.iter().flatten().copied().collect() };
        // thetasave and coefsave, kept as column lists, as in survpenal.fit
        let mut thetasave: Vec<Vec<f64>> = vec![flatten(&self.thetas)];
        let mut coefsave: Vec<Vec<f64>> = Vec::new();
        let mut init = init_in.to_vec();
        let mut iter_total = 0i32;
        let mut iterfail: Vec<i32> = Vec::new();
        let mut iter_outer = 0i32;

        let mut last_fit: Option<FitOut> = None;
        let mut last_df: Option<DfOut> = None;
        let mut last_hdiag: Vec<f64> = vec![0.0; n2];

        for iterx in 1..=outer_max {
            iter_outer = iterx;
            let fit = self.csurvreg7(iter_max, &init)?;
            iter_total += fit.iter;
            if fit.flag == 1000 {
                iterfail.push(iterx);
            }
            let hdiag = self.masked_hdiag(&fit.hdiag);
            let df_now = if need_df {
                Some(self.df_step(&fit, &hdiag, assign, n2))
            } else {
                None
            };

            let pdf: Vec<f64> = match &df_now {
                Some(d) => pindex.iter().map(|&k| d.df[k]).collect(),
                None => Vec::new(),
            };
            let ptrh: Vec<f64> = match &df_now {
                Some(d) => pindex.iter().map(|&k| d.trh[k]).collect(),
                None => Vec::new(),
            };

            let mut done = true;
            for i in 0..npen {
                let mut values: Vec<f64> = Vec::new();
                for name in &self.pens[i].cargs {
                    match name.as_str() {
                        "df" => values.push(pdf[i]),
                        "trH" => values.push(ptrh[i]),
                        other => {
                            return Err(PyNotImplementedError::new_err(format!(
                                "cfun argument {other:?} is not supported"
                            )))
                        }
                    }
                }
                let old = iterlist[i].clone_ref(py);
                let temp = self.call_cfun(i, iterx, Some(&old), &values)?;
                let temp_b = temp.bind(py);
                self.thetas[i] = theta_of(temp_b)?;
                done = done && done_of(temp_b)?;
                iterlist[i] = temp;
            }

            let coef_fit: Vec<f64> = fit.coef[..n2].to_vec();
            if done {
                last_fit = Some(fit);
                last_df = df_now;
                last_hdiag = hdiag;
                break;
            }

            if iterx == 1 {
                init = fit.coef.clone();
                coefsave = vec![fit.coef.clone()];
                thetasave.push(flatten(&self.thetas));
            } else {
                coefsave.push(fit.coef.clone());
                let temp = flatten(&self.thetas);
                let mut best = f64::INFINITY;
                let mut indx = 0usize;
                let howclose: Vec<f64> = thetasave
                    .iter()
                    .map(|col| {
                        col.iter()
                            .zip(temp.iter())
                            .map(|(a, b)| (a - b) * (a - b))
                            .sum::<f64>()
                    })
                    .collect();
                for (j, &h) in howclose.iter().enumerate() {
                    if h < best {
                        best = h;
                        indx = j;
                    }
                }
                init = coefsave[indx].clone();
                thetasave.push(temp);
            }
            let _ = coef_fit;

            last_fit = Some(fit);
            last_df = df_now;
            last_hdiag = hdiag;
        }

        let fit = last_fit.expect("at least one outer iteration");
        let dfo = match last_df {
            Some(d) => d,
            None => self.df_step(&fit, &last_hdiag, assign, n2),
        };
        let flags = self.flag[..nvar].to_vec();
        Ok(RunOut {
            fit,
            df: dfo.df,
            var: dfo.var,
            var2: dfo.var2,
            hdiag: last_hdiag,
            iter_outer,
            iter_total,
            iterfail,
            iterlist,
            flags,
        })
    }

    /// `hdiag <- ifelse(temp, 0, fit$hdiag)`: flagged penalized coefficients get 0.
    fn masked_hdiag(&self, hdiag: &[f64]) -> Vec<f64> {
        let mut out = hdiag.to_vec();
        for i in 0..self.nvar {
            if self.flag[i] {
                out[i] = 0.0;
            }
        }
        out
    }

    /// The `coxpenal.df` call in `survpenal.fit`, with `pen2 = diag(c(second, 0s))`.
    fn df_step(&self, fit: &FitOut, hdiag: &[f64], assign: &[Vec<usize>], n2: usize) -> DfOut {
        let mut pen2 = vec![0.0; n2];
        for i in 0..self.nvar {
            pen2[i] = self.second[i];
        }
        coxpenal_df_dense(&fit.hmat, &fit.hinv, hdiag, assign, &pen2, n2)
    }

    /// Call the Python `cfun` of penalty `i`. Iteration 0 passes no old state.
    fn call_cfun(
        &self,
        i: usize,
        iter: i32,
        old: Option<&Py<PyAny>>,
        values: &[f64],
    ) -> PyResult<Py<PyAny>> {
        let py = self.py;
        let pen = &self.pens[i];
        let mut items: Vec<Bound<'_, PyAny>> = Vec::with_capacity(3 + values.len());
        items.push(pen.parms.bind(py).clone());
        items.push(iter.into_pyobject(py)?.into_any());
        match old {
            Some(o) => items.push(o.bind(py).clone()),
            None => items.push(py.None().into_bound(py)),
        }
        if values.is_empty() {
            // R leaves these arguments missing at iter = 0; pass None so the Python
            // signature still binds.
            for _ in 0..pen.cargs.len() {
                items.push(py.None().into_bound(py));
            }
        } else {
            for &v in values {
                items.push(PyFloat::new(py, v).into_any());
            }
        }
        let args = PyTuple::new(py, items)?;
        Ok(pen.cfun.bind(py).call1(args)?.unbind())
    }
}

/// Map the `survpenal.fit` argument list to the Rust fitter and back to a dict.
#[allow(clippy::too_many_arguments)]
#[pyfunction]
#[pyo3(name = "survpenal_fit")]
fn survpenal_fit_py<'py>(
    py: Python<'py>,
    x: PyReadonlyArray1<'py, f64>,
    nvar: usize,
    y: PyReadonlyArray1<'py, f64>,
    ny: usize,
    wt: PyReadonlyArray1<'py, f64>,
    offset: PyReadonlyArray1<'py, f64>,
    strata: PyReadonlyArray1<'py, i32>,
    init: PyReadonlyArray1<'py, f64>,
    nstrat: usize,
    dnum: i32,
    n_eff: f64,
    eps: f64,
    tol: f64,
    iter_max: i32,
    outer_max: i32,
    assign: Vec<Vec<usize>>,
    pindex: Vec<usize>,
    penalties: Vec<(
        Vec<usize>,
        Py<PyAny>,
        Py<PyAny>,
        Py<PyAny>,
        Vec<String>,
        Option<Py<PyAny>>,
    )>,
) -> PyResult<Bound<'py, PyDict>> {
    let wt = wt.as_slice()?.to_vec();
    let n = wt.len();
    if nvar == 0 || ny < 2 || ny > 3 {
        return Err(PyValueError::new_err("nvar must be >= 1 and ny must be 2 or 3"));
    }
    let dist = match dnum {
        1 => Dist::Extreme,
        2 => Dist::Logistic,
        3 => Dist::Gauss,
        _ => {
            return Err(PyNotImplementedError::new_err(
                "dnum 4 (a density callback) is not included in the survreg7 crate",
            ))
        }
    };
    let x = x.as_slice()?.to_vec();
    let y = y.as_slice()?.to_vec();
    if x.len() != n * nvar || y.len() != n * ny {
        return Err(PyValueError::new_err("x or y has the wrong length"));
    }
    let offset = offset.as_slice()?.to_vec();
    let strat = strata.as_slice()?.to_vec();
    if offset.len() != n || strat.len() != n {
        return Err(PyValueError::new_err("offset and strata must have length n"));
    }
    let init = init.as_slice()?.to_vec();
    let nvar2 = nvar + nstrat;
    if init.len() < nvar2 {
        return Err(PyValueError::new_err("init is shorter than nvar + nstrat"));
    }
    let (time1, time2, status) = if ny == 2 {
        (y[..n].to_vec(), None, y[n..2 * n].to_vec())
    } else {
        (
            y[..n].to_vec(),
            Some(y[n..2 * n].to_vec()),
            y[2 * n..3 * n].to_vec(),
        )
    };

    let mut pens = Vec::with_capacity(penalties.len());
    let mut need_df = false;
    for (pcols, pfun, cfun, parms, cargs, extra) in penalties {
        if pcols.iter().any(|&c| c >= nvar) {
            return Err(PyValueError::new_err("pcols index is outside the X matrix"));
        }
        if cargs.iter().any(|c| c == "df" || c == "trH") {
            need_df = true;
        }
        pens.push(Penalty {
            pcols,
            pfun,
            cfun,
            parms,
            cargs,
            extra,
        });
    }
    let npen = pens.len();

    let mut fitter = Fitter {
        py,
        n,
        nvar,
        nstrat,
        dist,
        ny,
        time1,
        time2,
        status,
        covar: x,
        wt,
        offset,
        strat,
        eps,
        tol,
        n_eff,
        pens,
        thetas: vec![Vec::new(); npen],
        first: vec![0.0; nvar],
        second: vec![0.0; nvar],
        flag: vec![false; nvar],
    };
    let _ = fitter.ny;

    let out = fitter.run(&init, iter_max, outer_max, &assign, &pindex, need_df)?;

    let d = PyDict::new(py);
    d.set_item("coef", PyArray1::from_vec(py, out.fit.coef[..nvar2].to_vec()))?;
    d.set_item("coef_full", PyArray1::from_vec(py, out.fit.coef.clone()))?;
    d.set_item("iter_outer", out.iter_outer)?;
    d.set_item("iter_total", out.iter_total)?;
    d.set_item("iterfail", out.iterfail.clone())?;
    d.set_item("loglik", out.fit.loglik)?;
    d.set_item("penalty", out.fit.penalty)?;
    d.set_item("flag", out.fit.flag)?;
    d.set_item("fit_iter", out.fit.iter)?;
    d.set_item("var", PyArray1::from_vec(py, out.var.clone()))?;
    d.set_item("var2", PyArray1::from_vec(py, out.var2.clone()))?;
    d.set_item("df", PyArray1::from_vec(py, out.df.clone()))?;
    d.set_item("hdiag", PyArray1::from_vec(py, out.hdiag.clone()))?;
    d.set_item("hmat", PyArray1::from_vec(py, out.fit.hmat.clone()))?;
    d.set_item("hinv", PyArray1::from_vec(py, out.fit.hinv.clone()))?;
    d.set_item("u", PyArray1::from_vec(py, out.fit.u.clone()))?;
    d.set_item("flags", out.flags.clone())?;
    d.set_item("iterlist", out.iterlist.iter().map(|o| o.clone_ref(py)).collect::<Vec<_>>())?;
    Ok(d)
}

#[pymodule(name = "survreg7")]
fn survreg7_module(m: &Bound<'_, pyo3::types::PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(survpenal_fit_py, m)?)?;
    Ok(())
}
