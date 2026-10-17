//! Exact conditional Cox partial likelihood (survival `coxexact.c`).

use std::f64;

#[cfg(feature = "python")]
use numpy::{PyArray1, PyArray2, PyReadonlyArray1, PyReadonlyArray2};
#[cfg(feature = "python")]
use pyo3::prelude::*;

const NOTDONE: f64 = -1.1;

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

// covar column-major: var j person i => index i + j*nused in R column storage
#[inline]
fn covar_ij(covar: &[f64], nused: usize, var: usize, person: usize) -> f64 {
    covar[person + var * nused]
}

fn coxd0(d: i32, n: i32, score: &[f64], mem: &mut [f64], dmax: i32) -> f64 {
    if d == 0 {
        return 1.0;
    }
    let d = d as usize;
    let n = n as usize;
    let dmax = dmax as usize;
    let idx = (n - 1) * dmax + d - 1;
    if mem[idx] == NOTDONE {
        mem[idx] = score[n - 1] * coxd0((d - 1) as i32, (n - 1) as i32, score, mem, dmax as i32);
        if d < n {
            mem[idx] += coxd0(d as i32, (n - 1) as i32, score, mem, dmax as i32);
        }
    }
    mem[idx]
}

fn coxd1(
    d: i32,
    n: i32,
    score: &[f64],
    mem: &mut [f64],
    d1_off: usize,
    covar: &[f64],
    dmax: i32,
) -> f64 {
    let d = d as usize;
    let n = n as usize;
    let dmax = dmax as usize;
    let idx = d1_off + (n - 1) * dmax + d - 1;
    if mem[idx] == NOTDONE {
        mem[idx] = score[n - 1] * covar[n - 1] * coxd0((d - 1) as i32, (n - 1) as i32, score, mem, dmax as i32);
        if d < n {
            mem[idx] += coxd1(d as i32, (n - 1) as i32, score, mem, d1_off, covar, dmax as i32);
        }
        if d > 1 {
            mem[idx] += score[n - 1]
                * coxd1((d - 1) as i32, (n - 1) as i32, score, mem, d1_off, covar, dmax as i32);
        }
    }
    mem[idx]
}

fn coxd2(
    d: i32,
    n: i32,
    score: &[f64],
    mem: &mut [f64],
    d1j_off: usize,
    d1k_off: usize,
    d2_off: usize,
    covarj: &[f64],
    covark: &[f64],
    dmax: i32,
) -> f64 {
    let d = d as usize;
    let n = n as usize;
    let dmax = dmax as usize;
    let idx = d2_off + (n - 1) * dmax + d - 1;
    if mem[idx] == NOTDONE {
        mem[idx] = coxd0((d - 1) as i32, (n - 1) as i32, score, mem, dmax as i32)
            * score[n - 1]
            * covarj[n - 1]
            * covark[n - 1];
        if d < n {
            mem[idx] += coxd2(
                d as i32,
                (n - 1) as i32,
                score,
                mem,
                d1j_off,
                d1k_off,
                d2_off,
                covarj,
                covark,
                dmax as i32,
            );
        }
        if d > 1 {
            mem[idx] += score[n - 1]
                * (coxd2(
                    (d - 1) as i32,
                    (n - 1) as i32,
                    score,
                    mem,
                    d1j_off,
                    d1k_off,
                    d2_off,
                    covarj,
                    covark,
                    dmax as i32,
                ) + covarj[n - 1]
                    * coxd1((d - 1) as i32, (n - 1) as i32, score, mem, d1k_off, covark, dmax as i32)
                    + covark[n - 1]
                        * coxd1(
                            (d - 1) as i32,
                            (n - 1) as i32,
                            score,
                            mem,
                            d1j_off,
                            covarj,
                            dmax as i32,
                        ));
        }
    }
    mem[idx]
}

struct ExactScratch {
    dsize: usize,
    dmem0: Vec<f64>,
    dmem1: Vec<usize>,
    d1: Vec<f64>,
}

impl ExactScratch {
    fn new(nvar: usize, dsize: usize) -> Self {
        let dmemtot = dsize * ((nvar * (nvar + 1)) / 2 + nvar + 1);
        let mut dmem1 = vec![0usize; nvar];
        let base = dsize;
        for i in 0..nvar {
            dmem1[i] = base + i * dsize;
        }
        Self {
            dsize,
            dmem0: vec![NOTDONE; dmemtot],
            dmem1,
            d1: vec![0.0; nvar],
        }
    }

    fn reset_dmem(&mut self) {
        self.dmem0.fill(NOTDONE);
    }
}

fn covar_col<'a>(covar: &'a [f64], nused: usize, var: usize) -> &'a [f64] {
    &covar[var * nused..(var + 1) * nused]
}

pub fn fit_coxexact(
    maxiter: i32,
    time: &[f64],
    status: &[i32],
    covar: &[f64],
    nused: usize,
    nvar: usize,
    offset: &[f64],
    strata: &mut [i32],
    beta: &mut [f64],
    eps: f64,
    toler: f64,
) -> (Vec<f64>, Vec<f64>, Vec<f64>, [f64; 5], i32) {
    let mut score = vec![0.0; nused];
    let mut oldbeta = vec![0.0; nvar];
    let mut u = vec![0.0; nvar];
    let mut imat = vec![0.0; nvar * nvar];
    let mut loglik = [0.0; 5];

    strata[0] = 1;
    let mut temp_max = 0usize;
    let mut j_stratum = 0usize;
    let mut maxdeath = 0i32;
    let mut nrisk = 0i32;
    let mut i = 0usize;
    while i < nused {
        if strata[i] == 1 {
            if i > 0 {
                if maxdeath > 1 {
                    strata[j_stratum] = maxdeath;
                }
                j_stratum = i;
                let prod = maxdeath as usize * nrisk as usize;
                if prod > temp_max {
                    temp_max = prod;
                }
            }
            maxdeath = 0;
            nrisk = 0;
        }
        let dtime = time[i];
        let mut ndeath = 0i32;
        while time[i] == dtime {
            nrisk += 1;
            ndeath += status[i];
            i += 1;
            if i >= nused || strata[i] > 0 {
                break;
            }
        }
        if ndeath > maxdeath {
            maxdeath = ndeath;
        }
    }
    let prod = maxdeath as usize * nrisk as usize;
    if prod > temp_max {
        temp_max = prod;
    }
    if maxdeath > 1 {
        strata[j_stratum] = maxdeath;
    }

    let dsize = temp_max;
    let mut scratch = ExactScratch::new(nvar, dsize);

    let mut newlk = 0.0;
    for j in 0..nvar {
        u[j] = 0.0;
        for k in 0..nvar {
            imat[j * nvar + k] = 0.0;
        }
    }
    let mut sstart = 0usize;
    i = 0;
    while i < nused {
        if strata[i] > 0 {
            maxdeath = strata[i];
            scratch.reset_dmem();
            sstart = i;
            nrisk = 0;
        }
        let dtime = time[i];
        let mut ndeath = 0i32;
        while time[i] == dtime {
            let mut zbeta = offset[i];
            for j in 0..nvar {
                zbeta += covar_ij(covar, nused, j, i) * beta[j];
            }
            score[i] = zbeta.exp();
            if status[i] == 1 {
                newlk += zbeta;
                for j in 0..nvar {
                    u[j] += covar_ij(covar, nused, j, i);
                }
                ndeath += 1;
            }
            nrisk += 1;
            i += 1;
            if i >= nused || strata[i] > 0 {
                break;
            }
        }
        if ndeath > 0 {
            let nd = ndeath as i32;
            let nr = nrisk as i32;
            let md = maxdeath as i32;
            let d0 = coxd0(nd, nr, &score[sstart..], &mut scratch.dmem0, md);
            newlk -= d0.ln();
            let mut dmem2_off = (nvar + 1) * scratch.dsize;
            for j in 0..nvar {
                let col = covar_col(covar, nused, j);
                scratch.d1[j] = coxd1(
                    nd,
                    nr,
                    &score[sstart..],
                    &mut scratch.dmem0,
                    scratch.dmem1[j],
                    &col[sstart..],
                    md,
                ) / d0;
                u[j] -= scratch.d1[j];
                for k in 0..=j {
                    let colk = covar_col(covar, nused, k);
                    let temp = coxd2(
                        nd,
                        nr,
                        &score[sstart..],
                        &mut scratch.dmem0,
                        scratch.dmem1[j],
                        scratch.dmem1[k],
                        dmem2_off,
                        &col[sstart..],
                        &colk[sstart..],
                        md,
                    );
                    imat[k * nvar + j] += temp / d0 - scratch.d1[j] * scratch.d1[k];
                    dmem2_off += scratch.dsize;
                }
            }
        }
    }

    loglik[0] = newlk;
    loglik[1] = newlk;
    let u0: Vec<f64> = u.clone();
    loglik[3] = cholesky2(&mut imat, nvar, toler) as f64;
    chsolve2(&imat, nvar, &mut u);
    loglik[2] = u.iter().zip(u0.iter()).map(|(a, b)| a * b).sum();

    if maxiter == 0 || !loglik[0].is_finite() {
        loglik[4] = 0.0;
        chinv2(&mut imat, nvar);
        symmetrize(&mut imat, nvar);
        return (beta.to_vec(), u0, imat, loglik, 0);
    }

    for j in 0..nvar {
        oldbeta[j] = beta[j];
        beta[j] += u[j];
    }
    let mut halving = 0i32;
    let mut iter = 0i32;
    for it in 1..=maxiter {
        iter = it;
        newlk = 0.0;
        for j in 0..nvar {
            u[j] = 0.0;
            for k in 0..nvar {
                imat[j * nvar + k] = 0.0;
            }
        }
        sstart = 0;
        i = 0;
        while i < nused {
            if strata[i] > 0 {
                maxdeath = strata[i];
                scratch.reset_dmem();
                sstart = i;
                nrisk = 0;
            }
            let dtime = time[i];
            let mut ndeath = 0i32;
            while time[i] == dtime {
                let mut zbeta = offset[i];
                for j in 0..nvar {
                    zbeta += covar_ij(covar, nused, j, i) * beta[j];
                }
                score[i] = zbeta.exp();
                if status[i] == 1 {
                    newlk += zbeta;
                    for j in 0..nvar {
                        u[j] += covar_ij(covar, nused, j, i);
                    }
                    ndeath += 1;
                }
                nrisk += 1;
                i += 1;
                if i >= nused || strata[i] > 0 {
                    break;
                }
            }
            if ndeath > 0 {
                let nd = ndeath as i32;
                let nr = nrisk as i32;
                let md = maxdeath as i32;
                let d0 = coxd0(nd, nr, &score[sstart..], &mut scratch.dmem0, md);
                newlk -= d0.ln();
                let mut dmem2_off = (nvar + 1) * scratch.dsize;
                for j in 0..nvar {
                    let col = covar_col(covar, nused, j);
                    scratch.d1[j] = coxd1(
                        nd,
                        nr,
                        &score[sstart..],
                        &mut scratch.dmem0,
                        scratch.dmem1[j],
                        &col[sstart..],
                        md,
                    ) / d0;
                    u[j] -= scratch.d1[j];
                    for k in 0..=j {
                        let colk = covar_col(covar, nused, k);
                        let temp = coxd2(
                            nd,
                            nr,
                            &score[sstart..],
                            &mut scratch.dmem0,
                            scratch.dmem1[j],
                            scratch.dmem1[k],
                            dmem2_off,
                            &col[sstart..],
                            &colk[sstart..],
                            md,
                        );
                        imat[k * nvar + j] += temp / d0 - scratch.d1[j] * scratch.d1[k];
                        dmem2_off += scratch.dsize;
                    }
                }
            }
        }

        loglik[3] = cholesky2(&mut imat, nvar, toler) as f64;
        let mut notfinite = 0;
        for j in 0..nvar {
            if !u[j].is_finite() {
                notfinite = 2;
            }
            for k in 0..nvar {
                if !imat[j * nvar + k].is_finite() {
                    notfinite = 3;
                }
            }
        }
        if !newlk.is_finite() {
            notfinite = 4;
        }

        if notfinite == 0 && (1.0 - (loglik[1] / newlk)).abs() <= eps && halving == 0 {
            loglik[1] = newlk;
            loglik[4] = iter as f64;
            chinv2(&mut imat, nvar);
            symmetrize(&mut imat, nvar);
            return (beta.to_vec(), u0, imat, loglik, iter);
        }

        if it == maxiter {
            break;
        }

        if notfinite > 0 || newlk < loglik[1] {
            halving = 1;
            for j in 0..nvar {
                beta[j] = (oldbeta[j] + beta[j]) / 2.0;
            }
        } else {
            halving = 0;
            loglik[1] = newlk;
            chsolve2(&imat, nvar, &mut u);
            for j in 0..nvar {
                oldbeta[j] = beta[j];
                beta[j] += u[j];
            }
        }
    }

    if maxiter > 1 {
        for j in 0..nvar {
            beta[j] = oldbeta[j];
        }
        newlk = 0.0;
        for j in 0..nvar {
            u[j] = 0.0;
            for k in 0..nvar {
                imat[j * nvar + k] = 0.0;
            }
        }
        sstart = 0;
        i = 0;
        while i < nused {
            if strata[i] > 0 {
                maxdeath = strata[i];
                scratch.reset_dmem();
                sstart = i;
                nrisk = 0;
            }
            let dtime = time[i];
            let mut ndeath = 0i32;
            while time[i] == dtime {
                let mut zbeta = offset[i];
                for j in 0..nvar {
                    zbeta += covar_ij(covar, nused, j, i) * beta[j];
                }
                score[i] = zbeta.exp();
                if status[i] == 1 {
                    newlk += zbeta;
                    for j in 0..nvar {
                        u[j] += covar_ij(covar, nused, j, i);
                    }
                    ndeath += 1;
                }
                nrisk += 1;
                i += 1;
                if i >= nused || strata[i] > 0 {
                    break;
                }
            }
            if ndeath > 0 {
                let nd = ndeath as i32;
                let nr = nrisk as i32;
                let md = maxdeath as i32;
                let d0 = coxd0(nd, nr, &score[sstart..], &mut scratch.dmem0, md);
                newlk -= d0.ln();
                let mut dmem2_off = (nvar + 1) * scratch.dsize;
                for j in 0..nvar {
                    let col = covar_col(covar, nused, j);
                    scratch.d1[j] = coxd1(
                        nd,
                        nr,
                        &score[sstart..],
                        &mut scratch.dmem0,
                        scratch.dmem1[j],
                        &col[sstart..],
                        md,
                    ) / d0;
                    u[j] -= scratch.d1[j];
                    for k in 0..=j {
                        let colk = covar_col(covar, nused, k);
                        let temp = coxd2(
                            nd,
                            nr,
                            &score[sstart..],
                            &mut scratch.dmem0,
                            scratch.dmem1[j],
                            scratch.dmem1[k],
                            dmem2_off,
                            &col[sstart..],
                            &colk[sstart..],
                            md,
                        );
                        imat[k * nvar + j] += temp / d0 - scratch.d1[j] * scratch.d1[k];
                        dmem2_off += scratch.dsize;
                    }
                }
            }
        }
    }
    loglik[1] = newlk;
    loglik[3] = 1000.0;
    loglik[4] = iter as f64;
    chinv2(&mut imat, nvar);
    symmetrize(&mut imat, nvar);
    (beta.to_vec(), u0, imat, loglik, iter)
}

fn symmetrize(imat: &mut [f64], n: usize) {
    for i in 1..n {
        for j in 0..i {
            imat[i * n + j] = imat[j * n + i];
        }
    }
}

#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(signature = (maxiter, y, x, offset, strata, init, eps, toler))]
fn coxexact_py(
    maxiter: i32,
    y: PyReadonlyArray2<'_, f64>,
    x: PyReadonlyArray2<'_, f64>,
    offset: PyReadonlyArray1<'_, f64>,
    mut strata: PyReadonlyArray1<'_, i32>,
    init: PyReadonlyArray1<'_, f64>,
    eps: f64,
    toler: f64,
) -> PyResult<(
    Py<PyArray1<f64>>,
    Py<PyArray1<f64>>,
    Py<PyArray2<f64>>,
    Py<PyArray1<f64>>,
    i32,
)> {
    let yview = y.as_array();
    let nused = yview.nrows();
    let xview = x.as_array();
    let nvar = xview.ncols();
    let mut covar = vec![0.0; nused * nvar];
    for i in 0..nused {
        for j in 0..nvar {
            covar[i + j * nused] = xview[[i, j]];
        }
    }
    let time: Vec<f64> = (0..nused).map(|i| yview[[i, 0]]).collect();
    let status: Vec<i32> = (0..nused).map(|i| yview[[i, 1]] as i32).collect();
    let offset = offset.as_slice()?.to_vec();
    let mut strata_vec = strata.as_slice()?.to_vec();
    let mut beta = init.as_slice()?.to_vec();
    let (beta, u, imat, loglik, iter) = fit_coxexact(
        maxiter,
        &time,
        &status,
        &covar,
        nused,
        nvar,
        &offset,
        &mut strata_vec,
        &mut beta,
        eps,
        toler,
    );
    Python::attach(|py| {
        let imat2d: Vec<Vec<f64>> = (0..nvar)
            .map(|i| (0..nvar).map(|j| imat[i * nvar + j]).collect())
            .collect();
        Ok((
            PyArray1::from_vec(py, beta).into(),
            PyArray1::from_vec(py, u).into(),
            PyArray2::from_vec2(py, &imat2d)?.into(),
            PyArray1::from_vec(py, loglik.to_vec()).into(),
            iter,
        ))
    })
}

#[cfg(feature = "python")]
#[pymodule]
fn coxexact(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(coxexact_py, m)?)?;
    Ok(())
}
