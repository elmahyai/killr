//! Andersen-Gill exact Cox partial likelihood and martingale residuals.
//!
//! Ports `agexact` and `agmart` from survival 3.8-12 (`src/agexact.c`,
//! `src/agmart.c`), including `cholesky2`, `chsolve2`, `chinv2`, and `doloop`.
//! Covariates are column-major: covariate `j` for person `i` is `covar[i + j * n]`.
//! Information matrices use the same ragged layout as the C code:
//! `matrix[col][row]` lives at `matrix[col * n + row]`.

use std::time::Instant;

#[cfg(feature = "python")]
use numpy::{PyArray1, PyArray2, PyReadonlyArray1, PyReadonlyArray2};
#[cfg(feature = "python")]
use pyo3::exceptions::PyValueError;
#[cfg(feature = "python")]
use pyo3::prelude::*;

/// Coefficients and information from [`agexact`].
#[derive(Clone, Debug)]
pub struct AgexactResult {
    pub beta: Vec<f64>,
    pub u: Vec<f64>,
    pub imat: Vec<f64>,
    pub means: Vec<f64>,
    pub loglik: [f64; 2],
    pub sctest: f64,
    pub flag: i32,
    pub iter: i32,
}

/// Nested combination generator from survival `doloop.c`.
struct DoLoop {
    minval: i32,
    maxval: i32,
    firsttime: bool,
    depth: i32,
}

impl DoLoop {
    fn init(minval: i32, maxval: i32) -> Self {
        Self {
            minval,
            maxval,
            firsttime: true,
            depth: 1,
        }
    }

    fn next(&mut self, nloops: i32, index: &mut [i32]) -> i32 {
        if self.firsttime {
            for i in 0..nloops {
                index[i as usize] = self.minval + i;
            }
            self.firsttime = false;
            if self.maxval >= self.minval + nloops {
                self.minval + nloops - 1
            } else {
                self.minval - 1
            }
        } else {
            self.step(nloops, index)
        }
    }

    fn step(&mut self, mut nloops: i32, index: &mut [i32]) -> i32 {
        nloops -= 1;
        let slot = nloops as usize;
        index[slot] += 1;
        if index[slot] <= self.maxval - self.depth {
            index[slot]
        } else if nloops == 0 {
            self.minval - self.depth
        } else {
            self.depth += 1;
            let inner = self.step(nloops, index);
            index[slot] = inner + 1;
            self.depth -= 1;
            index[slot]
        }
    }
}

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
    let mut nonneg = 1;
    for i in 0..n {
        let pivot = matrix[i * n + i];
        if !pivot.is_finite() || pivot < eps {
            matrix[i * n + i] = 0.0;
            if pivot < -8.0 * eps {
                nonneg = -1;
            }
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
    rank * nonneg
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

fn symmetrize(imat: &mut [f64], n: usize) {
    for i in 1..n {
        for j in 0..i {
            imat[i * n + j] = imat[j * n + i];
        }
    }
}

fn accumulate(
    coef: &[f64],
    start: &[f64],
    stop: &[f64],
    event: &[i32],
    covar: &[f64],
    offset: &[f64],
    strata: &[i32],
    n: usize,
    nvar: usize,
    score: &mut [f64],
    a: &mut [f64],
    cmat: &mut [f64],
    newvar: &mut [f64],
    index: &mut [i32],
    atrisk: &mut [i32],
    u: &mut [f64],
    imat: &mut [f64],
) -> f64 {
    for i in 0..nvar {
        u[i] = 0.0;
        for j in 0..nvar {
            imat[i * nvar + j] = 0.0;
        }
    }
    for person in 0..n {
        let mut zbeta = 0.0;
        for i in 0..nvar {
            zbeta += coef[i] * covar[person + i * n];
        }
        score[person] = (zbeta + offset[person]).exp();
    }

    let mut loglik = 0.0;
    let mut person = 0usize;
    while person < n {
        if event[person] == 0 {
            person += 1;
            continue;
        }
        let mut denom = 0.0;
        for i in 0..nvar {
            a[i] = 0.0;
            for j in 0..nvar {
                cmat[i * nvar + j] = 0.0;
            }
        }
        let mut nrisk = 0usize;
        let mut deaths = 0i32;
        let time = stop[person];
        let mut k = person;
        while k < n {
            if stop[k] == time {
                deaths += event[k];
            }
            if start[k] < time {
                atrisk[nrisk] = k as i32;
                nrisk += 1;
            }
            if strata[k] == 1 {
                break;
            }
            k += 1;
        }

        if deaths == 1 {
            for l in 0..nrisk {
                let kk = atrisk[l] as usize;
                let weight = score[kk];
                denom += weight;
                for i in 0..nvar {
                    let cvi = covar[kk + i * n];
                    a[i] += weight * cvi;
                    for j in 0..=i {
                        cmat[i * nvar + j] += weight * cvi * covar[kk + j * n];
                    }
                }
            }
        } else {
            let mut doloop = DoLoop::init(0, nrisk as i32);
            while doloop.next(deaths, index) >= 0 {
                for i in 0..nvar {
                    newvar[i] = 0.0;
                }
                let mut weight = 1.0;
                for l in 0..deaths as usize {
                    let kk = atrisk[index[l] as usize] as usize;
                    weight *= score[kk];
                    for i in 0..nvar {
                        newvar[i] += covar[kk + i * n];
                    }
                }
                denom += weight;
                for i in 0..nvar {
                    a[i] += weight * newvar[i];
                    for j in 0..=i {
                        cmat[i * nvar + j] += weight * newvar[i] * newvar[j];
                    }
                }
            }
        }

        loglik -= denom.ln();
        for i in 0..nvar {
            u[i] -= a[i] / denom;
            for j in 0..=i {
                imat[j * nvar + i] += (cmat[i * nvar + j] - a[i] * a[j] / denom) / denom;
            }
        }
        k = person;
        while k < n && stop[k] == time {
            if event[k] == 1 {
                loglik += score[k].ln();
                for i in 0..nvar {
                    u[i] += covar[k + i * n];
                }
            }
            person += 1;
            if strata[k] == 1 {
                break;
            }
            k += 1;
        }
    }
    loglik
}

/// Exact Andersen-Gill Cox partial likelihood.
///
/// `covar` is column-major with `n` rows. `nocenter[j] == 0` leaves column `j`
/// uncentered and stores a zero mean; any other value subtracts the column mean.
/// `strata[i] == 1` marks the last row of a stratum. Data must be sorted by
/// ascending stop time within stratum, with deaths before censored rows at a tie.
///
/// `flag` is the Cholesky rank, `0` when `maxiter` is 0, and `1000` when the
/// iteration limit is reached. `iter` is the iteration count on success and
/// `maxiter` otherwise. When `maxiter` is 0, `beta` is returned unchanged.
pub fn agexact(
    maxiter: i32,
    start: &[f64],
    stop: &[f64],
    event: &[i32],
    covar: &[f64],
    offset: &[f64],
    strata: &[i32],
    beta_init: &[f64],
    eps: f64,
    tol_chol: f64,
    nocenter: &[i32],
) -> AgexactResult {
    let n = start.len();
    let nvar = beta_init.len();
    let mut covar = covar.to_vec();
    let mut means = vec![0.0; nvar];
    for i in 0..nvar {
        if nocenter[i] == 0 {
            means[i] = 0.0;
        } else {
            let mut temp = 0.0;
            for person in 0..n {
                temp += covar[person + i * n];
            }
            temp /= n as f64;
            means[i] = temp;
            for person in 0..n {
                covar[person + i * n] -= temp;
            }
        }
    }

    let mut beta = beta_init.to_vec();
    let mut newbeta = vec![0.0; nvar];
    let mut u = vec![0.0; nvar];
    let mut imat = vec![0.0; nvar * nvar];
    let mut a = vec![0.0; nvar];
    let mut cmat = vec![0.0; nvar * nvar];
    let mut score = vec![0.0; n];
    let mut newvar = vec![0.0; nvar];
    let mut index = vec![0i32; n];
    let mut atrisk = vec![0i32; n];

    let loglik_init = accumulate(
        &beta,
        start,
        stop,
        event,
        &covar,
        offset,
        strata,
        n,
        nvar,
        &mut score,
        &mut a,
        &mut cmat,
        &mut newvar,
        &mut index,
        &mut atrisk,
        &mut u,
        &mut imat,
    );
    let loglik0 = loglik_init;
    let mut loglik1 = loglik_init;

    for i in 0..nvar {
        a[i] = u[i];
    }
    cholesky2(&mut imat, nvar, tol_chol);
    chsolve2(&imat, nvar, &mut a);
    let mut sctest = 0.0;
    for i in 0..nvar {
        sctest += u[i] * a[i];
    }
    for i in 0..nvar {
        newbeta[i] = beta[i] + a[i];
    }

    if maxiter == 0 {
        chinv2(&mut imat, nvar);
        symmetrize(&mut imat, nvar);
        return AgexactResult {
            beta,
            u,
            imat,
            means,
            loglik: [loglik0, loglik1],
            sctest,
            flag: 0,
            iter: 0,
        };
    }

    let mut halving = 0i32;
    let mut iter_done = 0i32;
    let mut newlk = 0.0;
    #[allow(unused_assignments)]
    let mut flag = 0i32;
    for iter in 1..=maxiter {
        iter_done = iter;
        newlk = accumulate(
            &newbeta,
            start,
            stop,
            event,
            &covar,
            offset,
            strata,
            n,
            nvar,
            &mut score,
            &mut a,
            &mut cmat,
            &mut newvar,
            &mut index,
            &mut atrisk,
            &mut u,
            &mut imat,
        );
        flag = cholesky2(&mut imat, nvar, tol_chol);
        if (1.0 - (loglik1 / newlk)).abs() <= eps && halving == 0 {
            loglik1 = newlk;
            chinv2(&mut imat, nvar);
            symmetrize(&mut imat, nvar);
            beta.copy_from_slice(&newbeta);
            return AgexactResult {
                beta,
                u,
                imat,
                means,
                loglik: [loglik0, loglik1],
                sctest,
                flag,
                iter: iter_done,
            };
        }
        if iter == maxiter {
            break;
        }
        if newlk < loglik1 {
            halving = 1;
            for i in 0..nvar {
                newbeta[i] = (newbeta[i] + beta[i]) / 2.0;
            }
        } else {
            halving = 0;
            loglik1 = newlk;
            chsolve2(&imat, nvar, &mut u);
            for i in 0..nvar {
                beta[i] = newbeta[i];
                newbeta[i] += u[i];
            }
        }
    }

    loglik1 = newlk;
    chinv2(&mut imat, nvar);
    symmetrize(&mut imat, nvar);
    beta.copy_from_slice(&newbeta);
    AgexactResult {
        beta,
        u,
        imat,
        means,
        loglik: [loglik0, loglik1],
        sctest,
        flag: 1000,
        iter: iter_done,
    }
}

/// Martingale residuals for a counting-process model (`agmart.c`).
///
/// `method == 1` is the Efron tie correction. `deaths` is accumulated as a
/// double, so `k/deaths` is a floating-point quotient. The last stratum mark
/// is forced to 1. `resid` starts as the event indicator.
pub fn agmart(
    method: i32,
    start: &[f64],
    stop: &[f64],
    event: &[i32],
    score: &[f64],
    weight: &[f64],
    strata: &[i32],
) -> Vec<f64> {
    let nused = start.len();
    if nused == 0 {
        return Vec::new();
    }
    let mut strata = strata.to_vec();
    strata[nused - 1] = 1;
    let mut resid: Vec<f64> = event.iter().map(|&e| e as f64).collect();
    let mut person = 0usize;
    while person < nused {
        if event[person] == 0 {
            person += 1;
            continue;
        }
        let mut denom = 0.0;
        let mut e_denom = 0.0;
        let mut wtsum = 0.0;
        let time = stop[person];
        let mut deaths = 0.0;
        let mut k = person;
        while k < nused {
            if start[k] < time {
                denom += score[k] * weight[k];
                if stop[k] == time && event[k] == 1 {
                    deaths += 1.0;
                    wtsum += weight[k];
                    e_denom += score[k] * weight[k];
                }
            }
            if strata[k] == 1 {
                break;
            }
            k += 1;
        }
        let mut hazard = 0.0;
        let mut e_hazard = 0.0;
        wtsum /= deaths;
        let mut step = 0i32;
        while (step as f64) < deaths {
            let temp = (method as f64) * ((step as f64) / deaths);
            let gap = denom - temp * e_denom;
            hazard += wtsum / gap;
            e_hazard += wtsum * (1.0 - temp) / gap;
            step += 1;
        }
        k = person;
        while k < nused {
            if start[k] < time {
                if stop[k] == time && event[k] == 1 {
                    resid[k] -= score[k] * e_hazard;
                } else {
                    resid[k] -= score[k] * hazard;
                }
            }
            if stop[k] == time {
                person += 1;
            }
            if strata[k] == 1 {
                break;
            }
            k += 1;
        }
    }
    resid
}

#[cfg(feature = "python")]
fn vec_f64(array: PyReadonlyArray1<'_, f64>) -> PyResult<Vec<f64>> {
    if let Ok(slice) = array.as_slice() {
        Ok(slice.to_vec())
    } else {
        Ok(array.as_array().iter().copied().collect())
    }
}

#[cfg(feature = "python")]
fn vec_i32(array: PyReadonlyArray1<'_, i32>) -> PyResult<Vec<i32>> {
    if let Ok(slice) = array.as_slice() {
        Ok(slice.to_vec())
    } else {
        Ok(array.as_array().iter().copied().collect())
    }
}

#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(name = "agexact")]
fn agexact_py(
    maxiter: i32,
    start: PyReadonlyArray1<'_, f64>,
    stop: PyReadonlyArray1<'_, f64>,
    event: PyReadonlyArray1<'_, i32>,
    x: PyReadonlyArray2<'_, f64>,
    offset: PyReadonlyArray1<'_, f64>,
    strata: PyReadonlyArray1<'_, i32>,
    init: PyReadonlyArray1<'_, f64>,
    eps: f64,
    tol_chol: f64,
    nocenter: PyReadonlyArray1<'_, i32>,
) -> PyResult<(
    Py<PyArray1<f64>>,
    Py<PyArray1<f64>>,
    Py<PyArray2<f64>>,
    Py<PyArray1<f64>>,
    Py<PyArray1<f64>>,
    f64,
    i32,
    i32,
    f64,
)> {
    let xview = x.as_array();
    let n = xview.nrows();
    let nvar = xview.ncols();
    let start = vec_f64(start)?;
    let stop = vec_f64(stop)?;
    let event = vec_i32(event)?;
    let offset = vec_f64(offset)?;
    let strata = vec_i32(strata)?;
    let init = vec_f64(init)?;
    let nocenter = vec_i32(nocenter)?;
    if start.len() != n
        || stop.len() != n
        || event.len() != n
        || offset.len() != n
        || strata.len() != n
        || init.len() != nvar
        || nocenter.len() != nvar
    {
        return Err(PyValueError::new_err(
            "agexact lengths must match the rows and columns of x",
        ));
    }
    let mut covar = vec![0.0; n * nvar];
    for person in 0..n {
        for j in 0..nvar {
            covar[person + j * n] = xview[[person, j]];
        }
    }
    let started = Instant::now();
    let fit = agexact(
        maxiter,
        &start,
        &stop,
        &event,
        &covar,
        &offset,
        &strata,
        &init,
        eps,
        tol_chol,
        &nocenter,
    );
    let elapsed_ms = started.elapsed().as_secs_f64() * 1000.0;
    Python::attach(|py| {
        let imat2d: Vec<Vec<f64>> = (0..nvar)
            .map(|i| (0..nvar).map(|j| fit.imat[i * nvar + j]).collect())
            .collect();
        Ok((
            PyArray1::from_vec(py, fit.beta).into(),
            PyArray1::from_vec(py, fit.u).into(),
            PyArray2::from_vec2(py, &imat2d)?.into(),
            PyArray1::from_vec(py, fit.means).into(),
            PyArray1::from_vec(py, fit.loglik.to_vec()).into(),
            fit.sctest,
            fit.flag,
            fit.iter,
            elapsed_ms,
        ))
    })
}

#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(name = "agmart")]
fn agmart_py(
    method: i32,
    start: PyReadonlyArray1<'_, f64>,
    stop: PyReadonlyArray1<'_, f64>,
    event: PyReadonlyArray1<'_, i32>,
    score: PyReadonlyArray1<'_, f64>,
    weight: PyReadonlyArray1<'_, f64>,
    strata: PyReadonlyArray1<'_, i32>,
) -> PyResult<(Py<PyArray1<f64>>, f64)> {
    let start = vec_f64(start)?;
    let n = start.len();
    let stop = vec_f64(stop)?;
    let event = vec_i32(event)?;
    let score = vec_f64(score)?;
    let weight = vec_f64(weight)?;
    let strata = vec_i32(strata)?;
    if stop.len() != n
        || event.len() != n
        || score.len() != n
        || weight.len() != n
        || strata.len() != n
    {
        return Err(PyValueError::new_err("agmart arguments must share one length"));
    }
    let started = Instant::now();
    let resid = agmart(method, &start, &stop, &event, &score, &weight, &strata);
    let elapsed_ms = started.elapsed().as_secs_f64() * 1000.0;
    Python::attach(|py| Ok((PyArray1::from_vec(py, resid).into(), elapsed_ms)))
}

#[cfg(feature = "python")]
#[pymodule]
#[pyo3(name = "agexact")]
fn agexact_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(agexact_py, m)?)?;
    m.add_function(wrap_pyfunction!(agmart_py, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::DoLoop;

    fn combinations(nloops: i32, max: i32) -> Vec<Vec<i32>> {
        let mut doloop = DoLoop::init(0, max);
        let mut index = vec![0i32; nloops as usize];
        let mut out = Vec::new();
        while doloop.next(nloops, &mut index) >= 0 {
            out.push(index.clone());
        }
        out
    }

    #[test]
    fn doloop_matches_lexicographic_combinations() {
        let pairs = combinations(2, 4);
        assert_eq!(
            pairs,
            vec![
                vec![0, 1],
                vec![0, 2],
                vec![0, 3],
                vec![1, 2],
                vec![1, 3],
                vec![2, 3],
            ]
        );
        let triples = combinations(3, 5);
        assert_eq!(triples.len(), 10);
        assert_eq!(triples[0], vec![0, 1, 2]);
        assert_eq!(triples[9], vec![2, 3, 4]);
        assert!(combinations(3, 2).is_empty());
    }
}
