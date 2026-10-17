//! Cox partial likelihood (survival `coxfit6.c` / `coxmart.c`).

use std::f64;

#[cfg(feature = "python")]
use numpy::{PyArray1, PyArray2, PyReadonlyArray1, PyReadonlyArray2};
#[cfg(feature = "python")]
use pyo3::prelude::*;

fn cholesky2(matrix: &mut [f64], n: usize, toler: f64) -> i32 {
    let mut eps = 0.0;
    for i in 0..n {
        if matrix[i * n + i] > eps {
            eps = matrix[i * n + i];
        }
        for j in (i + 1)..n {
            matrix[j * n + i] = matrix[i * n + j];
        }
    }
    if eps == 0.0 {
        eps = toler;
    } else {
        eps *= toler;
    }
    let mut rank = 0;
    for i in 0..n {
        let pivot = matrix[i * n + i];
        if !pivot.is_finite() || pivot < eps {
            matrix[i * n + i] = 0.0;
        } else {
            rank += 1;
            for j in (i + 1)..n {
                let temp = matrix[j * n + i] / pivot;
                matrix[j * n + i] = temp;
                matrix[j * n + j] -= temp * temp * pivot;
                for k in (j + 1)..n {
                    matrix[k * n + j] -= temp * matrix[k * n + i];
                }
            }
        }
    }
    rank
}

fn chsolve2(matrix: &[f64], n: usize, y: &mut [f64]) {
    for i in 0..n {
        let mut temp = y[i];
        for j in 0..i {
            temp -= y[j] * matrix[i * n + j];
        }
        y[i] = temp;
    }
    for i in (0..n).rev() {
        if matrix[i * n + i] == 0.0 {
            y[i] = 0.0;
        } else {
            let mut temp = y[i] / matrix[i * n + i];
            for j in (i + 1)..n {
                temp -= y[j] * matrix[j * n + i];
            }
            y[i] = temp;
        }
    }
}

fn chinv2(matrix: &mut [f64], n: usize) {
    for i in 0..n {
        if matrix[i * n + i] > 0.0 {
            matrix[i * n + i] = 1.0 / matrix[i * n + i];
            for j in (i + 1)..n {
                matrix[j * n + i] = -matrix[j * n + i];
                for k in 0..i {
                    matrix[j * n + k] += matrix[j * n + i] * matrix[i * n + k];
                }
            }
        }
    }
    for i in 0..n {
        if matrix[i * n + i] == 0.0 {
            for j in 0..i {
                matrix[j * n + i] = 0.0;
            }
            for j in i..n {
                matrix[i * n + j] = 0.0;
            }
        } else {
            for j in (i + 1)..n {
                let temp = matrix[j * n + i] * matrix[j * n + j];
                if j != i {
                    matrix[i * n + j] = temp;
                }
                for k in i..j {
                    matrix[i * n + k] += temp * matrix[j * n + k];
                }
            }
        }
    }
}

fn coxfit6_iter(
    nvar: usize,
    nused: usize,
    method: i32,
    beta: &[f64],
    xtime: &[f64],
    status: &[i32],
    strata: &[i32],
    offset: &[f64],
    weights: &[f64],
    covar: &[f64],
    u: &mut [f64],
    imat: &mut [f64],
) -> f64 {
    u.fill(0.0);
    imat.fill(0.0);
    let mut a = vec![0.0; nvar];
    let mut a2 = vec![0.0; nvar];
    let mut cmat = vec![0.0; nvar * nvar];
    let mut cmat2 = vec![0.0; nvar * nvar];
    let mut loglik = 0.0;
    let mut person = nused as i32 - 1;
    let mut denom = 0.0;
    while person >= 0 {
        let pi = person as usize;
        if strata[pi] == 1 {
            denom = 0.0;
            for i in 0..nvar {
                a[i] = 0.0;
                for j in 0..nvar {
                    cmat[i * nvar + j] = 0.0;
                }
            }
        }
        let dtime = xtime[pi];
        let mut ndead = 0;
        let mut deadwt = 0.0;
        let mut denom2 = 0.0;
        while person >= 0 && xtime[person as usize] == dtime {
            let p = person as usize;
            let mut zbeta = offset[p];
            for i in 0..nvar {
                zbeta += beta[i] * covar[i * nused + p];
            }
            let risk = zbeta.exp() * weights[p];
            if status[p] == 0 {
                denom += risk;
                for i in 0..nvar {
                    a[i] += risk * covar[i * nused + p];
                    for j in 0..=i {
                        cmat[i * nvar + j] += risk * covar[i * nused + p] * covar[j * nused + p];
                    }
                }
            } else {
                ndead += 1;
                deadwt += weights[p];
                denom2 += risk;
                loglik += weights[p] * zbeta;
                for i in 0..nvar {
                    u[i] += weights[p] * covar[i * nused + p];
                    a2[i] += risk * covar[i * nused + p];
                    for j in 0..=i {
                        cmat2[i * nvar + j] += risk * covar[i * nused + p] * covar[j * nused + p];
                    }
                }
            }
            person -= 1;
            if person >= 0 && strata[person as usize] == 1 {
                break;
            }
        }
        if ndead > 0 {
            if method == 0 || ndead == 1 {
                denom += denom2;
                loglik -= deadwt * denom.ln();
                for i in 0..nvar {
                    a[i] += a2[i];
                    let temp2 = a[i] / denom;
                    u[i] -= deadwt * temp2;
                    for j in 0..=i {
                        cmat[i * nvar + j] += cmat2[i * nvar + j];
                        imat[j * nvar + i] += deadwt * (cmat[i * nvar + j] - temp2 * a[j]) / denom;
                    }
                }
            } else {
                let wtave = deadwt / ndead as f64;
                for _ in 0..ndead {
                    denom += denom2 / ndead as f64;
                    loglik -= wtave * denom.ln();
                    for i in 0..nvar {
                        a[i] += a2[i] / ndead as f64;
                        let temp2 = a[i] / denom;
                        u[i] -= wtave * temp2;
                        for j in 0..=i {
                            cmat[i * nvar + j] += cmat2[i * nvar + j] / ndead as f64;
                            imat[j * nvar + i] += wtave * (cmat[i * nvar + j] - temp2 * a[j]) / denom;
                        }
                    }
                }
            }
            a2.fill(0.0);
            cmat2.fill(0.0);
        }
    }
    for i in 0..nvar {
        for j in (i + 1)..nvar {
            imat[j * nvar + i] = imat[i * nvar + j];
        }
    }
    loglik
}

pub fn fit_coxfit6(
    maxiter: i32,
    time: &[f64],
    status: &[i32],
    x: &[f64],
    nused: usize,
    nvar: usize,
    offset: &[f64],
    weights: &[f64],
    strata: &mut [i32],
    method: i32,
    eps: f64,
    toler_chol: f64,
    doscale: &[i32],
) -> (Vec<f64>, Vec<f64>, Vec<f64>, Vec<f64>, [f64; 2], f64, i32, i32) {
    let mut covar = x.to_vec();
    let mut beta = vec![0.0; nvar];
    let mut means = vec![0.0; nvar];
    let mut scale = vec![1.0; nvar];
    let wt_sum: f64 = weights.iter().sum();
    for i in 0..nvar {
        if doscale[i] == 0 {
            scale[i] = 1.0;
            means[i] = 0.0;
        } else {
            let mut temp = 0.0;
            for person in 0..nused {
                temp += weights[person] * covar[i * nused + person];
            }
            temp /= wt_sum;
            means[i] = temp;
            for person in 0..nused {
                covar[i * nused + person] -= temp;
            }
            temp = 0.0;
            for person in 0..nused {
                temp += weights[person] * covar[i * nused + person].abs();
            }
            if temp > 0.0 {
                temp = wt_sum / temp;
            } else {
                temp = 1.0;
            }
            scale[i] = temp;
            for person in 0..nused {
                covar[i * nused + person] *= temp;
            }
        }
    }
    let mut u = vec![0.0; nvar];
    let mut imat = vec![0.0; nvar * nvar];
    strata[nused - 1] = 1;
    let mut loglik = [0.0; 2];
    loglik[0] = coxfit6_iter(
        nvar, nused, method, &beta, time, status, strata, offset, weights, &covar, &mut u, &mut imat,
    );
    loglik[1] = loglik[0];
    let u0 = u.clone();
    let mut a_score = u0.clone();
    let mut chol = imat.clone();
    cholesky2(&mut chol, nvar, toler_chol);
    chsolve2(&chol, nvar, &mut a_score);
    let sctest: f64 = u0.iter().zip(a_score.iter()).map(|(a, b)| a * b).sum();
    if maxiter == 0 || !loglik[0].is_finite() {
        cholesky2(&mut imat, nvar, toler_chol);
        chinv2(&mut imat, nvar);
        rescale(&mut beta, &mut u, &mut imat, &scale, nvar);
        return (beta, means, u, imat, loglik, sctest, 0, 0);
    }
    let mut newbeta: Vec<f64> = beta.iter().zip(a_score.iter()).map(|(b, a)| b + a).collect();
    let mut halving = 0;
    let mut it = 0;
    let mut best_lk = loglik[0];
    let mut best_beta = beta.clone();
    for iter in 1..=maxiter {
        it = iter;
        let newlk = coxfit6_iter(
            nvar, nused, method, &newbeta, time, status, strata, offset, weights, &covar, &mut u, &mut imat,
        );
        let mut notfinite = 0;
        if u.iter().any(|v| !v.is_finite()) {
            notfinite = 2;
        }
        if imat.iter().any(|v| !v.is_finite()) {
            notfinite = 3;
        }
        if !newlk.is_finite() {
            notfinite = 4;
        }
        if notfinite == 0 && (1.0 - (best_lk / newlk)).abs() <= eps {
            loglik[1] = newlk;
            beta.copy_from_slice(&newbeta);
            cholesky2(&mut imat, nvar, toler_chol);
            chinv2(&mut imat, nvar);
            rescale(&mut beta, &mut u, &mut imat, &scale, nvar);
            let flag = if halving != 0 { -2 } else { 0 };
            return (beta, means, u, imat, loglik, sctest, it, flag);
        }
        if notfinite > 0 || newlk < best_lk {
            halving += 1;
            for i in 0..nvar {
                newbeta[i] = (newbeta[i] + halving as f64 * beta[i]) / (halving as f64 + 1.0);
            }
        } else {
            halving = 0;
            if newlk > best_lk {
                best_lk = newlk;
                best_beta.copy_from_slice(&newbeta);
            }
            beta.copy_from_slice(&newbeta);
            let mut step = u.clone();
            let mut chol = imat.clone();
            cholesky2(&mut chol, nvar, toler_chol);
            chsolve2(&chol, nvar, &mut step);
            for i in 0..nvar {
                newbeta[i] += step[i];
            }
        }
    }
    beta.copy_from_slice(&best_beta);
    if maxiter > 1 {
        loglik[1] = coxfit6_iter(
            nvar, nused, method, &beta, time, status, strata, offset, weights, &covar, &mut u, &mut imat,
        );
    } else {
        loglik[1] = best_lk;
    }
    chinv2(&mut imat, nvar);
    rescale(&mut beta, &mut u, &mut imat, &scale, nvar);
    (beta, means, u, imat, loglik, sctest, it, 1000)
}

fn rescale(beta: &mut [f64], u: &mut [f64], imat: &mut [f64], scale: &[f64], nvar: usize) {
    for i in 0..nvar {
        beta[i] *= scale[i];
        u[i] /= scale[i];
        imat[i * nvar + i] *= scale[i] * scale[i];
        for j in 0..i {
            imat[j * nvar + i] *= scale[i] * scale[j];
            imat[i * nvar + j] = imat[j * nvar + i];
        }
    }
}

pub fn martingale(
    n: usize,
    method_efron: bool,
    time: &[f64],
    status: &[i32],
    strata: &mut [i32],
    score: &[f64],
    weights: &[f64],
) -> Vec<f64> {
    let mut expect = vec![0.0; n];
    strata[n - 1] = 1;
    let mut denom = 0.0;
    for i in (0..n).rev() {
        if strata[i] == 1 {
            denom = 0.0;
        }
        denom += score[i] * weights[i];
        if i == 0 || strata[i - 1] == 1 || time[i - 1] != time[i] {
            expect[i] = denom;
        }
    }
    let mut deaths = 0.0;
    let mut wtsum = 0.0;
    let mut e_denom = 0.0;
    let mut hazard = 0.0;
    let mut lastone = 0;
    let method = if method_efron { 1 } else { 0 };
    for i in 0..n {
        if expect[i] != 0.0 {
            denom = expect[i];
        }
        expect[i] = status[i] as f64;
        deaths += status[i] as f64;
        wtsum += status[i] as f64 * weights[i];
        e_denom += score[i] * status[i] as f64 * weights[i];
        if strata[i] == 1 || (i + 1 < n && time[i + 1] != time[i]) {
            if deaths < 2.0 || method == 0 {
                hazard += wtsum / denom;
                for j in lastone..=i {
                    expect[j] -= score[j] * hazard;
                }
            } else {
                let mut temp = hazard;
                let wts = wtsum / deaths;
                let nd = deaths as i32;
                for j in 0..nd {
                    let downwt = j as f64 / deaths;
                    hazard += wts / (denom - e_denom * downwt);
                    temp += wts * (1.0 - downwt) / (denom - e_denom * downwt);
                }
                for j in lastone..=i {
                    if status[j] == 0 {
                        expect[j] = -score[j] * hazard;
                    } else {
                        expect[j] -= score[j] * temp;
                    }
                }
            }
            lastone = i + 1;
            deaths = 0.0;
            wtsum = 0.0;
            e_denom = 0.0;
        }
        if strata[i] == 1 {
            hazard = 0.0;
        }
    }
    for j in lastone..n {
        expect[j] -= score[j] * hazard;
    }
    expect
}

#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(signature = (time, status, x, offset, weights, strata, method, beta, doscale=None))]
fn coxfit6_eval_py(
    time: PyReadonlyArray1<'_, f64>,
    status: PyReadonlyArray1<'_, i32>,
    x: PyReadonlyArray2<'_, f64>,
    offset: PyReadonlyArray1<'_, f64>,
    weights: PyReadonlyArray1<'_, f64>,
    mut strata: PyReadonlyArray1<'_, i32>,
    method: &str,
    beta: PyReadonlyArray1<'_, f64>,
    doscale: Option<PyReadonlyArray1<'_, i32>>,
) -> PyResult<(f64, Py<PyArray1<f64>>, Py<PyArray2<f64>>, Py<PyArray1<f64>>, Py<PyArray1<f64>>)> {
    let time = time.as_slice()?;
    let status = status.as_slice()?;
    let xview = x.as_array();
    let nused = xview.nrows();
    let nvar = xview.ncols();
    let mut xflat = vec![0.0; nused * nvar];
    for i in 0..nused {
        for j in 0..nvar {
            xflat[j * nused + i] = xview[[i, j]];
        }
    }
    let offset = offset.as_slice()?;
    let weights = weights.as_slice()?;
    let mut strata_vec = strata.as_slice()?.to_vec();
    let meth = if method == "efron" { 1 } else { 0 };
    let doscale_vec = if let Some(d) = doscale {
        d.as_slice()?.to_vec()
    } else {
        vec![1; nvar]
    };
    let beta_vec = beta.as_slice()?.to_vec();
    let mut means = vec![0.0; nvar];
    let mut scales = vec![1.0; nvar];
    let wt_sum: f64 = weights.iter().sum();
    for i in 0..nvar {
        if doscale_vec[i] == 0 {
            continue;
        }
        let mut temp = 0.0;
        for person in 0..nused {
            temp += weights[person] * xflat[i * nused + person];
        }
        temp /= wt_sum;
        means[i] = temp;
        for person in 0..nused {
            xflat[i * nused + person] -= temp;
        }
        temp = 0.0;
        for person in 0..nused {
            temp += weights[person] * xflat[i * nused + person].abs();
        }
        let scale = if temp > 0.0 { wt_sum / temp } else { 1.0 };
        scales[i] = scale;
        for person in 0..nused {
            xflat[i * nused + person] *= scale;
        }
    }
    strata_vec[nused - 1] = 1;
    let mut u = vec![0.0; nvar];
    let mut imat = vec![0.0; nvar * nvar];
    let loglik = coxfit6_iter(
        nvar,
        nused,
        meth,
        &beta_vec,
        time,
        status,
        &mut strata_vec,
        offset,
        weights,
        &xflat,
        &mut u,
        &mut imat,
    );
    Python::attach(|py| {
        let mut mat = vec![0.0; nvar * nvar];
        for i in 0..nvar {
            for j in 0..nvar {
                mat[i * nvar + j] = imat[j * nvar + i];
            }
        }
        Ok((
            loglik,
            PyArray1::from_vec(py, u).into(),
            PyArray2::from_vec2(py, &chunk(nvar, &mat))?.into(),
            PyArray1::from_vec(py, means).into(),
            PyArray1::from_vec(py, scales).into(),
        ))
    })
}

#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(signature = (maxiter, time, status, x, offset, weights, strata, method, eps, toler_chol, doscale=None))]
fn coxfit6_py(
    maxiter: i32,
    time: PyReadonlyArray1<'_, f64>,
    status: PyReadonlyArray1<'_, i32>,
    x: PyReadonlyArray2<'_, f64>,
    offset: PyReadonlyArray1<'_, f64>,
    weights: PyReadonlyArray1<'_, f64>,
    mut strata: PyReadonlyArray1<'_, i32>,
    method: &str,
    eps: f64,
    toler_chol: f64,
    doscale: Option<PyReadonlyArray1<'_, i32>>,
) -> PyResult<(
    Py<PyArray1<f64>>,
    Py<PyArray1<f64>>,
    Py<PyArray1<f64>>,
    Py<PyArray2<f64>>,
    Py<PyArray1<f64>>,
    f64,
    i32,
    i32,
)> {
    let time = time.as_slice()?;
    let status = status.as_slice()?;
    let xview = x.as_array();
    let nused = xview.nrows();
    let nvar = xview.ncols();
    let mut xflat = vec![0.0; nused * nvar];
    for i in 0..nused {
        for j in 0..nvar {
            xflat[j * nused + i] = xview[[i, j]];
        }
    }
    let offset = offset.as_slice()?;
    let weights = weights.as_slice()?;
    let mut strata_vec = strata.as_slice()?.to_vec();
    let meth = if method == "efron" { 1 } else { 0 };
    let doscale_vec = if let Some(d) = doscale {
        d.as_slice()?.to_vec()
    } else {
        vec![1; nvar]
    };
    let (beta, means, u, imat, loglik, sctest, it, flag) = fit_coxfit6(
        maxiter,
        time,
        status,
        &xflat,
        nused,
        nvar,
        offset,
        weights,
        &mut strata_vec,
        meth,
        eps,
        toler_chol,
        &doscale_vec,
    );
    Python::attach(|py| {
        let mut imat2 = vec![0.0; nvar * nvar];
        for i in 0..nvar {
            for j in 0..nvar {
                imat2[i * nvar + j] = imat[j * nvar + i];
            }
        }
        Ok((
            PyArray1::from_vec(py, beta).into(),
            PyArray1::from_vec(py, means).into(),
            PyArray1::from_vec(py, u).into(),
            PyArray2::from_vec2(py, &chunk(nvar, &imat2))?.into(),
            PyArray1::from_vec(py, loglik.to_vec()).into(),
            sctest,
            it,
            flag,
        ))
    })
}

fn chunk(n: usize, flat: &[f64]) -> Vec<Vec<f64>> {
    (0..n).map(|i| flat[i * n..(i + 1) * n].to_vec()).collect()
}

#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(signature = (time, status, strata, score, weights, method_efron=false))]
fn coxmart_py(
    time: PyReadonlyArray1<'_, f64>,
    status: PyReadonlyArray1<'_, i32>,
    mut strata: PyReadonlyArray1<'_, i32>,
    score: PyReadonlyArray1<'_, f64>,
    weights: PyReadonlyArray1<'_, f64>,
    method_efron: bool,
) -> PyResult<Py<PyArray1<f64>>> {
    let time = time.as_slice()?;
    let status = status.as_slice()?;
    let mut strata_vec = strata.as_slice()?.to_vec();
    let score = score.as_slice()?;
    let weights = weights.as_slice()?;
    let out = martingale(
        time.len(),
        method_efron,
        time,
        status,
        &mut strata_vec,
        score,
        weights,
    );
    Python::attach(|py| Ok(PyArray1::from_vec(py, out).into()))
}

#[cfg(feature = "python")]
#[pymodule]
fn coxfit6(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(coxfit6_py, m)?)?;
    m.add_function(wrap_pyfunction!(coxfit6_eval_py, m)?)?;
    m.add_function(wrap_pyfunction!(coxmart_py, m)?)?;
    Ok(())
}
