//! Counting-process Cox partial likelihood (`agfit4.c`) and martingale residuals (`agmart3.c`).
//!
//! Matrix storage matches survival's `dmatrix`: column `c`, row `r` is `flat[c * nrow + r]`.

#[cfg(feature = "python")]
use std::time::Instant;

#[cfg(feature = "python")]
use numpy::{PyArray1, PyArray2, PyReadonlyArray1, PyReadonlyArray2};
#[cfg(feature = "python")]
use pyo3::exceptions::PyValueError;
#[cfg(feature = "python")]
use pyo3::prelude::*;

/// Coefficients, score, covariance, log-likelihood, score test, flags, and iterations.
#[derive(Clone, Debug)]
pub struct Agfit4Out {
    pub coef: Vec<f64>,
    pub u: Vec<f64>,
    pub imat: Vec<f64>,
    pub loglik: [f64; 2],
    pub sctest: f64,
    pub flag: [i32; 4],
    pub iter: i32,
}

fn c_isnan(x: f64) -> i32 {
    if x.is_nan() {
        1
    } else {
        0
    }
}

fn c_isinf(x: f64) -> i32 {
    if x == f64::INFINITY {
        1
    } else if x == f64::NEG_INFINITY {
        -1
    } else {
        0
    }
}

fn c_abs(x: i32) -> i32 {
    x.saturating_abs()
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

fn check_index(name: &str, idx: i32, nr: usize) -> Result<usize, String> {
    if idx < 0 || idx as usize >= nr {
        return Err(format!("{name} index {idx} is outside 0..{nr}"));
    }
    Ok(idx as usize)
}

fn sort_usize(name: &str, sort: &[i32], nused: usize, nr: usize) -> Result<Vec<usize>, String> {
    if sort.len() < nused {
        return Err(format!("{name} is shorter than nused"));
    }
    let mut out = Vec::with_capacity(nused);
    for &idx in sort.iter().take(nused) {
        out.push(check_index(name, idx, nr)?);
    }
    Ok(out)
}

/// The generated C leaves the "last stratum" centering step inside the person loop.
/// The first sorted row's covariate is therefore subtracted from every used row.
fn center_scale(
    covar: &mut [f64],
    beta: &mut [f64],
    scale: &mut [f64],
    nr: usize,
    nvar: usize,
    nused: usize,
    weights: &[f64],
    strata: &[i32],
    sort2: &[usize],
    doscale: &[i32],
) {
    for i in 0..nvar {
        if doscale[i] == 0 {
            scale[i] = 1.0;
            continue;
        }
        let mut istrat = strata[sort2[0]];
        let mut k = 0usize;
        let mut temp = 0.0;
        let mut temp2 = 0.0;
        for person in 0..nused {
            let p = sort2[person];
            if strata[p] == istrat {
                temp += weights[p] * covar[i * nr + p];
                temp2 += weights[p];
            } else {
                temp /= temp2;
                while k < person {
                    let pk = sort2[k];
                    covar[i * nr + pk] -= temp;
                    k += 1;
                }
                temp = 0.0;
                temp2 = 0.0;
                istrat = strata[p];
            }
            temp /= temp2;
            while k < nused {
                let pk = sort2[k];
                covar[i * nr + pk] -= temp;
                k += 1;
            }
        }
        temp = 0.0;
        temp2 = 0.0;
        for person in 0..nused {
            let p = sort2[person];
            temp += weights[p] * covar[i * nr + p].abs();
            temp2 += weights[p];
        }
        if temp > 0.0 {
            temp = temp2 / temp;
        } else {
            temp = 1.0;
        }
        scale[i] = temp;
        for &p in sort2.iter().take(nused) {
            covar[i * nr + p] *= temp;
        }
    }
    for i in 0..nvar {
        beta[i] /= scale[i];
    }
}

fn accumulate(
    nused: usize,
    nvar: usize,
    nr: usize,
    method: i32,
    start: &[f64],
    tstop: &[f64],
    event: &[f64],
    weights: &[f64],
    strata: &[i32],
    sort1: &[usize],
    sort2: &[usize],
    covar: &[f64],
    beta: &[f64],
    offset: &[f64],
    u: &mut [f64],
    imat: &mut [f64],
    rescale_count: &mut i32,
) -> Result<f64, String> {
    let mut eta = vec![0.0; nr];
    for &p in sort2.iter().take(nused) {
        let mut zbeta = 0.0;
        for i in 0..nvar {
            zbeta += beta[i] * covar[i * nr + p];
        }
        eta[p] = zbeta + offset[p];
    }

    let mut newlk = 0.0;
    u.fill(0.0);
    imat.fill(0.0);

    let mut a = vec![0.0; nvar];
    let mut a2 = vec![0.0; nvar];
    let mut cmat = vec![0.0; nvar * nvar];
    let mut cmat2 = vec![0.0; nvar * nvar];

    let mut person = 0usize;
    let mut indx1 = 0usize;
    let mut recenter = 0.0;
    let mut denom = 0.0;
    let mut nrisk: i32 = 0;
    let mut etasum = 0.0;
    let mut istrat = strata[sort2[0]];
    let mut dtime = 0.0;

    while person < nused {
        let mut k = person;
        while k < nused {
            let p = sort2[k];
            if strata[p] != istrat {
                istrat = strata[p];
                denom = 0.0;
                nrisk = 0;
                etasum = 0.0;
                a.fill(0.0);
                cmat.fill(0.0);
                person = k;
                indx1 = k;
            }
            if event[p] == 1.0 {
                dtime = tstop[p];
                break;
            }
            k += 1;
        }
        if k == nused {
            break;
        }

        while indx1 < nused {
            let p1 = sort1[indx1];
            if start[p1] < dtime || strata[p1] != istrat {
                break;
            }
            nrisk -= 1;
            if nrisk == 0 {
                etasum = 0.0;
                denom = 0.0;
                a.fill(0.0);
                for i in 0..nvar {
                    for j in 0..=i {
                        cmat[i * nvar + j] = 0.0;
                    }
                }
            } else {
                etasum -= eta[p1];
                let risk = (eta[p1] - recenter).exp() * weights[p1];
                denom -= risk;
                for i in 0..nvar {
                    a[i] -= risk * covar[i * nr + p1];
                    for j in 0..=i {
                        cmat[i * nvar + j] -= risk * covar[i * nr + p1] * covar[j * nr + p1];
                    }
                }
            }
            indx1 += 1;
        }

        let mut denom2 = 0.0;
        let mut meanwt = 0.0;
        let mut deaths: i32 = 0;
        a2.fill(0.0);
        cmat2.fill(0.0);

        while person < nused {
            let p = sort2[person];
            if strata[p] != istrat || tstop[p] < dtime {
                break;
            }
            nrisk += 1;
            etasum += eta[p];
            if (etasum / nrisk as f64 - recenter).abs() > 200.0 {
                *rescale_count += 1;
                let shift = etasum / nrisk as f64 - recenter;
                recenter = etasum / nrisk as f64;
                if denom > 0.0 {
                    if shift.abs() > 709.0 {
                        return Err("exp overflow due to covariates".to_string());
                    }
                    let temp = (-shift).exp();
                    denom *= temp;
                    for i in 0..nvar {
                        a[i] *= temp;
                        for j in 0..nvar {
                            cmat[i * nvar + j] *= temp;
                        }
                    }
                }
            }
            let risk = (eta[p] - recenter).exp() * weights[p];
            if event[p] == 1.0 {
                deaths += 1;
                denom2 += risk;
                meanwt += weights[p];
                newlk += weights[p] * (eta[p] - recenter);
                for i in 0..nvar {
                    u[i] += weights[p] * covar[i * nr + p];
                    a2[i] += risk * covar[i * nr + p];
                    for j in 0..=i {
                        cmat2[i * nvar + j] += risk * covar[i * nr + p] * covar[j * nr + p];
                    }
                }
            } else {
                denom += risk;
                for i in 0..nvar {
                    a[i] += risk * covar[i * nr + p];
                    for j in 0..=i {
                        cmat[i * nvar + j] += risk * covar[i * nr + p] * covar[j * nr + p];
                    }
                }
            }
            person += 1;
        }

        if method == 0 || deaths == 1 {
            denom += denom2;
            newlk -= meanwt * denom.ln();
            for i in 0..nvar {
                a[i] += a2[i];
                let temp = a[i] / denom;
                u[i] -= meanwt * temp;
                for j in 0..=i {
                    cmat[i * nvar + j] += cmat2[i * nvar + j];
                    imat[j * nvar + i] += meanwt * ((cmat[i * nvar + j] - temp * a[j]) / denom);
                }
            }
        } else {
            meanwt /= deaths as f64;
            for _k in 0..deaths {
                denom += denom2 / deaths as f64;
                newlk -= meanwt * denom.ln();
                for i in 0..nvar {
                    a[i] += a2[i] / deaths as f64;
                    let temp = a[i] / denom;
                    u[i] -= meanwt * temp;
                    for j in 0..=i {
                        cmat[i * nvar + j] += cmat2[i * nvar + j] / deaths as f64;
                        imat[j * nvar + i] +=
                            meanwt * ((cmat[i * nvar + j] - temp * a[j]) / denom);
                    }
                }
            }
        }
    }
    Ok(newlk)
}

fn finish(beta: &mut [f64], u: &mut [f64], imat: &mut [f64], scale: &[f64], nvar: usize) {
    chinv2(imat, nvar);
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

/// Newton fit of the counting-process Cox partial likelihood.
///
/// `method` is 1 for Efron and 0 for Breslow. `sort_start` and `sort_end` are 0-based
/// indexes ordered from the largest time to the smallest, with ignored rows after `nused`.
/// `covar` is column-major with `nr` rows.
pub fn agfit4(
    nused: usize,
    start: &[f64],
    tstop: &[f64],
    event: &[f64],
    covar: &[f64],
    nr: usize,
    nvar: usize,
    strata: &[i32],
    weights: &[f64],
    offset: &[f64],
    init: &[f64],
    sort_start: &[i32],
    sort_end: &[i32],
    method: i32,
    maxiter: i32,
    eps: f64,
    toler_chol: f64,
    doscale: &[i32],
) -> Result<Agfit4Out, String> {
    if nvar == 0 {
        return Err("agfit4 needs at least one covariate".to_string());
    }
    if nused == 0 {
        return Err("agfit4 needs at least one observation at risk".to_string());
    }
    if nr == 0 || start.len() < nr || tstop.len() < nr || event.len() < nr {
        return Err("survival vectors are shorter than nr".to_string());
    }
    if weights.len() < nr || offset.len() < nr || strata.len() < nr {
        return Err("weights, offset, or strata are shorter than nr".to_string());
    }
    if covar.len() < nr * nvar {
        return Err("covar is shorter than nr * nvar".to_string());
    }
    if init.len() < nvar || doscale.len() < nvar {
        return Err("init or doscale is shorter than nvar".to_string());
    }
    let sort1 = sort_usize("sort_start", sort_start, nused, nr)?;
    let sort2 = sort_usize("sort_end", sort_end, nused, nr)?;

    let mut covar = covar[..nr * nvar].to_vec();
    let mut beta = init[..nvar].to_vec();
    let mut scale = vec![1.0; nvar];
    center_scale(
        &mut covar,
        &mut beta,
        &mut scale,
        nr,
        nvar,
        nused,
        weights,
        strata,
        &sort2,
        doscale,
    );

    let mut u = vec![0.0; nvar];
    let mut imat = vec![0.0; nvar * nvar];
    let mut oldbeta = vec![0.0; nvar];
    let mut loglik = [0.0; 2];
    let mut sctest = 0.0;
    let mut flag = [0; 4];
    let mut rank = 0i32;
    let mut newlk = 0.0;
    let mut halving = 0i32;
    let mut iter = 0i32;

    loop {
        if iter > maxiter {
            break;
        }
        newlk = accumulate(
            nused,
            nvar,
            nr,
            method,
            start,
            tstop,
            event,
            weights,
            strata,
            &sort1,
            &sort2,
            &covar,
            &beta,
            offset,
            &mut u,
            &mut imat,
            &mut flag[1],
        )?;
        if iter == 0 {
            loglik[0] = newlk;
            loglik[1] = newlk;
            let mut a = u.clone();
            rank = cholesky2(&mut imat, nvar, toler_chol);
            chsolve2(&imat, nvar, &mut a);
            sctest = 0.0;
            for i in 0..nvar {
                sctest += u[i] * a[i];
            }
            if maxiter == 0 {
                break;
            }
            let fail = c_isnan(newlk) + c_isinf(newlk);
            if fail > 0 {
                break;
            }
            for i in 0..nvar {
                oldbeta[i] = beta[i];
                beta[i] += a[i];
            }
        } else {
            let mut fail = 0i32;
            for i in 0..nvar {
                if !imat[i * nvar + i].is_finite() {
                    fail += 1;
                }
            }
            let rank2 = cholesky2(&mut imat, nvar, toler_chol);
            fail += c_isnan(newlk) + c_isinf(newlk) + c_abs(rank - rank2);
            if fail == 0 && halving == 0 && (1.0 - (loglik[1] / newlk)).abs() <= eps {
                break;
            }
            if iter == maxiter {
                flag[3] = 1;
                if maxiter > 1 && ((newlk - loglik[1]) / loglik[1].abs()) < -eps {
                    beta.copy_from_slice(&oldbeta);
                    newlk = accumulate(
                        nused,
                        nvar,
                        nr,
                        method,
                        start,
                        tstop,
                        event,
                        weights,
                        strata,
                        &sort1,
                        &sort2,
                        &covar,
                        &beta,
                        offset,
                        &mut u,
                        &mut imat,
                        &mut flag[1],
                    )?;
                    let _rank2 = cholesky2(&mut imat, nvar, toler_chol);
                }
                break;
            }
            if fail > 0 || newlk < loglik[1] {
                halving += 1;
                flag[2] += 1;
                for i in 0..nvar {
                    beta[i] = (oldbeta[i] * f64::from(halving) + beta[i]) / (f64::from(halving) + 1.0);
                }
            } else {
                halving = 0;
                loglik[1] = newlk;
                chsolve2(&imat, nvar, &mut u);
                for i in 0..nvar {
                    oldbeta[i] = beta[i];
                    beta[i] += u[i];
                }
            }
        }
        iter += 1;
    }

    flag[0] = rank;
    loglik[1] = newlk;
    finish(&mut beta, &mut u, &mut imat, &scale, nvar);
    Ok(Agfit4Out {
        coef: beta,
        u,
        imat,
        loglik,
        sctest,
        flag,
        iter,
    })
}

/// Martingale residuals for a (start, stop] risk set.
///
/// `score` is the subject risk weight, usually `exp(linear predictor)`.
/// `method` is 1 for Efron and 0 for Breslow. Rows at or after `nused` stay zero.
pub fn agmart3(
    nused: usize,
    start: &[f64],
    tstop: &[f64],
    event: &[f64],
    score: &[f64],
    weight: &[f64],
    strata: &[i32],
    sort_start: &[i32],
    sort_end: &[i32],
    method: i32,
) -> Result<Vec<f64>, String> {
    let nr = start.len();
    if tstop.len() < nr || event.len() < nr || score.len() < nr || weight.len() < nr || strata.len() < nr
    {
        return Err("agmart3 inputs are shorter than the survival vector".to_string());
    }
    if nused == 0 {
        return Ok(vec![0.0; nr]);
    }
    if nused > nr {
        return Err("nused is larger than the number of rows".to_string());
    }
    let sort1 = sort_usize("sort_start", sort_start, nused, nr)?;
    let sort2 = sort_usize("sort_end", sort_end, nused, nr)?;

    let mut resid = vec![0.0; nr];
    let mut atrisk = vec![0i32; nr];
    let mut person1 = 0usize;
    let mut denom = 0.0;
    let mut cumhaz = 0.0;
    let mut istrat = strata[sort2[0]];
    let mut person2 = 0usize;
    let mut dtime = 0.0;

    while person2 < nused {
        let mut k = person2;
        while k < nused {
            let p2 = sort2[k];
            if strata[p2] != istrat {
                while person1 < nused {
                    let p1 = sort1[person1];
                    if strata[p1] != istrat {
                        break;
                    }
                    resid[p1] -= cumhaz * score[p1];
                    person1 += 1;
                }
                cumhaz = 0.0;
                denom = 0.0;
                istrat = strata[p2];
                person2 = person1;
            }
            if event[p2] > 0.0 {
                dtime = tstop[p2];
                break;
            }
            k += 1;
        }
        if k == nused {
            break;
        }

        while person1 < nused {
            let p1 = sort1[person1];
            if start[p1] < dtime || strata[p1] != istrat {
                break;
            }
            if atrisk[p1] == 1 {
                denom -= score[p1] * weight[p1];
                resid[p1] -= cumhaz * score[p1];
            }
            person1 += 1;
        }

        let mut deaths = 0.0;
        let mut e_denom = 0.0;
        let mut wtsum = 0.0;
        let mut kend = person2;
        while kend < nused {
            let p2 = sort2[kend];
            if tstop[p2] < dtime || strata[p2] != istrat {
                break;
            }
            if event[p2] == 1.0 {
                atrisk[p2] = 1;
                resid[p2] = 1.0 + cumhaz * score[p2];
                deaths += 1.0;
                denom += score[p2] * weight[p2];
                e_denom += score[p2] * weight[p2];
                wtsum += weight[p2];
            } else if start[p2] < dtime {
                denom += score[p2] * weight[p2];
                atrisk[p2] = 1;
                resid[p2] = cumhaz * score[p2];
            }
            kend += 1;
        }

        let hazard = if method == 0 || deaths == 1.0 {
            person2 = kend;
            wtsum / denom
        } else {
            let mut hazard = 0.0;
            let mut e_hazard = 0.0;
            wtsum /= deaths;
            let mut i = 0i32;
            while f64::from(i) < deaths {
                let temp = f64::from(i) / deaths;
                hazard += wtsum / (denom - temp * e_denom);
                e_hazard += wtsum * (1.0 - temp) / (denom - temp * e_denom);
                i += 1;
            }
            let temp = hazard - e_hazard;
            while person2 < kend {
                let p2 = sort2[person2];
                if event[p2] > 0.0 {
                    resid[p2] += temp * score[p2];
                }
                person2 += 1;
            }
            hazard
        };
        cumhaz += hazard;
    }

    while person1 < nused {
        let p1 = sort1[person1];
        if atrisk[p1] == 1 {
            resid[p1] -= cumhaz * score[p1];
        }
        person1 += 1;
    }
    Ok(resid)
}

fn column_major(x_row_major: &[f64], nr: usize, nvar: usize) -> Vec<f64> {
    let mut covar = vec![0.0; nr * nvar];
    for row in 0..nr {
        for col in 0..nvar {
            covar[col * nr + row] = x_row_major[row * nvar + col];
        }
    }
    covar
}

struct KernelInputs {
    nused: usize,
    start: Vec<f64>,
    tstop: Vec<f64>,
    event: Vec<f64>,
    covar: Vec<f64>,
    nr: usize,
    nvar: usize,
    strata: Vec<i32>,
    weights: Vec<f64>,
    offset: Vec<f64>,
    init: Vec<f64>,
    sort_start: Vec<i32>,
    sort_end: Vec<i32>,
    method: i32,
    maxiter: i32,
    eps: f64,
    toler_chol: f64,
    doscale: Vec<i32>,
}

fn run_fit(inp: &KernelInputs) -> Result<Agfit4Out, String> {
    agfit4(
        inp.nused,
        &inp.start,
        &inp.tstop,
        &inp.event,
        &inp.covar,
        inp.nr,
        inp.nvar,
        &inp.strata,
        &inp.weights,
        &inp.offset,
        &inp.init,
        &inp.sort_start,
        &inp.sort_end,
        inp.method,
        inp.maxiter,
        inp.eps,
        inp.toler_chol,
        &inp.doscale,
    )
}

#[cfg(feature = "python")]
fn read_inputs(
    nused: usize,
    y: PyReadonlyArray2<'_, f64>,
    x: PyReadonlyArray2<'_, f64>,
    strata: PyReadonlyArray1<'_, i32>,
    weights: PyReadonlyArray1<'_, f64>,
    offset: PyReadonlyArray1<'_, f64>,
    init: PyReadonlyArray1<'_, f64>,
    sort_start: PyReadonlyArray1<'_, i32>,
    sort_end: PyReadonlyArray1<'_, i32>,
    method: i32,
    maxiter: i32,
    eps: f64,
    toler_chol: f64,
    doscale: PyReadonlyArray1<'_, i32>,
) -> PyResult<KernelInputs> {
    let yv = y.as_array();
    let xv = x.as_array();
    let nr = yv.nrows();
    let nvar = xv.ncols();
    if yv.ncols() != 3 || xv.nrows() != nr {
        return Err(PyValueError::new_err(
            "y must have three columns and the same number of rows as x",
        ));
    }
    let mut start = vec![0.0; nr];
    let mut tstop = vec![0.0; nr];
    let mut event = vec![0.0; nr];
    let mut xrow = vec![0.0; nr * nvar];
    for row in 0..nr {
        start[row] = yv[[row, 0]];
        tstop[row] = yv[[row, 1]];
        event[row] = yv[[row, 2]];
        for col in 0..nvar {
            xrow[row * nvar + col] = xv[[row, col]];
        }
    }
    let strata = strata.as_slice()?.to_vec();
    let weights = weights.as_slice()?.to_vec();
    let offset = offset.as_slice()?.to_vec();
    let init = init.as_slice()?.to_vec();
    let sort_start = sort_start.as_slice()?.to_vec();
    let sort_end = sort_end.as_slice()?.to_vec();
    let doscale = doscale.as_slice()?.to_vec();
    Ok(KernelInputs {
        nused,
        start,
        tstop,
        event,
        covar: column_major(&xrow, nr, nvar),
        nr,
        nvar,
        strata,
        weights,
        offset,
        init,
        sort_start,
        sort_end,
        method,
        maxiter,
        eps,
        toler_chol,
        doscale,
    })
}

#[cfg(feature = "python")]
fn map_err(err: String) -> PyErr {
    PyValueError::new_err(err)
}

#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(name = "agfit4", signature = (
    nused, y, x, strata, weights, offset, init, sort_start, sort_end,
    method, maxiter, eps, toler_chol, doscale
))]
fn agfit4_py(
    py: Python<'_>,
    nused: usize,
    y: PyReadonlyArray2<'_, f64>,
    x: PyReadonlyArray2<'_, f64>,
    strata: PyReadonlyArray1<'_, i32>,
    weights: PyReadonlyArray1<'_, f64>,
    offset: PyReadonlyArray1<'_, f64>,
    init: PyReadonlyArray1<'_, f64>,
    sort_start: PyReadonlyArray1<'_, i32>,
    sort_end: PyReadonlyArray1<'_, i32>,
    method: i32,
    maxiter: i32,
    eps: f64,
    toler_chol: f64,
    doscale: PyReadonlyArray1<'_, i32>,
) -> PyResult<(
    Py<PyArray1<f64>>,
    Py<PyArray1<f64>>,
    Py<PyArray2<f64>>,
    Py<PyArray1<f64>>,
    f64,
    Py<PyArray1<i32>>,
    i32,
)> {
    let inp = read_inputs(
        nused,
        y,
        x,
        strata,
        weights,
        offset,
        init,
        sort_start,
        sort_end,
        method,
        maxiter,
        eps,
        toler_chol,
        doscale,
    )?;
    let fit = agfit4(
        inp.nused,
        &inp.start,
        &inp.tstop,
        &inp.event,
        &inp.covar,
        inp.nr,
        inp.nvar,
        &inp.strata,
        &inp.weights,
        &inp.offset,
        &inp.init,
        &inp.sort_start,
        &inp.sort_end,
        inp.method,
        inp.maxiter,
        inp.eps,
        inp.toler_chol,
        &inp.doscale,
    )
    .map_err(map_err)?;
    let nvar = fit.coef.len();
    let mut rows = vec![vec![0.0; nvar]; nvar];
    for row in 0..nvar {
        for col in 0..nvar {
            rows[row][col] = fit.imat[col * nvar + row];
        }
    }
    Ok((
        PyArray1::from_vec(py, fit.coef).into(),
        PyArray1::from_vec(py, fit.u).into(),
        PyArray2::from_vec2(py, &rows)?.into(),
        PyArray1::from_vec(py, fit.loglik.to_vec()).into(),
        fit.sctest,
        PyArray1::from_vec(py, fit.flag.to_vec()).into(),
        fit.iter,
    ))
}

#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(name = "agmart3", signature = (nused, y, score, weights, strata, sort_start, sort_end, method))]
fn agmart3_py(
    py: Python<'_>,
    nused: usize,
    y: PyReadonlyArray2<'_, f64>,
    score: PyReadonlyArray1<'_, f64>,
    weights: PyReadonlyArray1<'_, f64>,
    strata: PyReadonlyArray1<'_, i32>,
    sort_start: PyReadonlyArray1<'_, i32>,
    sort_end: PyReadonlyArray1<'_, i32>,
    method: i32,
) -> PyResult<Py<PyArray1<f64>>> {
    let yv = y.as_array();
    let nr = yv.nrows();
    if yv.ncols() != 3 {
        return Err(PyValueError::new_err("y must have three columns"));
    }
    let mut start = vec![0.0; nr];
    let mut tstop = vec![0.0; nr];
    let mut event = vec![0.0; nr];
    for row in 0..nr {
        start[row] = yv[[row, 0]];
        tstop[row] = yv[[row, 1]];
        event[row] = yv[[row, 2]];
    }
    let resid = agmart3(
        nused,
        &start,
        &tstop,
        &event,
        score.as_slice()?,
        weights.as_slice()?,
        strata.as_slice()?,
        sort_start.as_slice()?,
        sort_end.as_slice()?,
        method,
    )
    .map_err(map_err)?;
    Ok(PyArray1::from_vec(py, resid).into())
}

#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(signature = (
    nused, y, x, strata, weights, offset, init, sort_start, sort_end,
    method, maxiter, eps, toler_chol, doscale, score
))]
fn kernel_ms(
    nused: usize,
    y: PyReadonlyArray2<'_, f64>,
    x: PyReadonlyArray2<'_, f64>,
    strata: PyReadonlyArray1<'_, i32>,
    weights: PyReadonlyArray1<'_, f64>,
    offset: PyReadonlyArray1<'_, f64>,
    init: PyReadonlyArray1<'_, f64>,
    sort_start: PyReadonlyArray1<'_, i32>,
    sort_end: PyReadonlyArray1<'_, i32>,
    method: i32,
    maxiter: i32,
    eps: f64,
    toler_chol: f64,
    doscale: PyReadonlyArray1<'_, i32>,
    score: PyReadonlyArray1<'_, f64>,
) -> PyResult<f64> {
    let inp = read_inputs(
        nused,
        y,
        x,
        strata,
        weights,
        offset,
        init,
        sort_start,
        sort_end,
        method,
        maxiter,
        eps,
        toler_chol,
        doscale,
    )?;
    let score = score.as_slice()?.to_vec();
    let started = Instant::now();
    let fit = run_fit(&inp).map_err(map_err)?;
    let resid = agmart3(
        inp.nused,
        &inp.start,
        &inp.tstop,
        &inp.event,
        &score,
        &inp.weights,
        &inp.strata,
        &inp.sort_start,
        &inp.sort_end,
        inp.method,
    )
    .map_err(map_err)?;
    std::hint::black_box(&fit.coef);
    std::hint::black_box(&fit.imat);
    std::hint::black_box(&resid);
    Ok(started.elapsed().as_secs_f64() * 1000.0)
}

#[cfg(feature = "python")]
#[pymodule]
#[pyo3(name = "agfit4")]
fn agfit4_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(agfit4_py, m)?)?;
    m.add_function(wrap_pyfunction!(agmart3_py, m)?)?;
    m.add_function(wrap_pyfunction!(kernel_ms, m)?)?;
    Ok(())
}
