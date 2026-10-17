//! ARMA constrained ↔ unconstrained parameter maps and the ARMA correlation
//! factor from nlme ``corStruct.c`` (``ARMA_unconstCoef``, ``ARMA_constCoef``,
//! ``ARMA_factList``, ``ARMA_recalc``).

use linpack::{dqrdc, dqrsl};

fn arma_trans_par(pars: &mut [f64], sgn: f64) {
    let n_len = pars.len();
    for n in (0..n_len).rev() {
        let ps = pars[n] * pars[n];
        if ps >= 1.0 {
            panic!("All parameters must be less than 1 in absolute value");
        }
        if n > 0 {
            let d = 1.0 - ps;
            let n2 = (n - 1) / 2;
            for i in 0..=n2 {
                let j = n - i - 1;
                if j > i {
                    let aux = (pars[i] + sgn * pars[j] * pars[n]) / d;
                    pars[j] = (pars[j] + sgn * pars[i] * pars[n]) / d;
                    pars[i] = aux;
                } else {
                    pars[i] /= 1.0 - sgn * pars[n];
                }
            }
        }
        pars[n] = ((1.0 + pars[n]) / (1.0 - pars[n])).ln();
    }
}

fn arma_untrans_par(pars: &mut [f64], sgn: f64) {
    let n_len = pars.len();
    if n_len == 0 {
        return;
    }
    let mut aux = vec![0.0; n_len];
    for i in 0..n_len {
        pars[i] = (-pars[i]).exp();
        pars[i] = (1.0 - pars[i]) / (1.0 + pars[i]);
        aux[i] = pars[i];
        if i > 0 {
            for j in 0..i {
                pars[j] = aux[j] + sgn * pars[i] * aux[i - j - 1];
            }
            aux[..i].copy_from_slice(&pars[..i]);
        }
    }
}

/// In-place unconstrained reparameterization for ARMA(p,q) (``ARMA_unconstCoef``).
pub fn arma_unconst_coef(p: usize, q: usize, pars: &mut [f64]) {
    assert_eq!(pars.len(), p + q);
    if p > 0 {
        arma_trans_par(&mut pars[..p], 1.0);
    }
    if q > 0 {
        arma_trans_par(&mut pars[p..], -1.0);
    }
}

/// In-place constrained reparameterization for ARMA(p,q) (``ARMA_constCoef``).
pub fn arma_const_coef(p: usize, q: usize, pars: &mut [f64]) {
    assert_eq!(pars.len(), p + q);
    if p > 0 {
        arma_untrans_par(&mut pars[..p], -1.0);
    }
    if q > 0 {
        arma_untrans_par(&mut pars[p..], 1.0);
    }
}

/// ``ARMA_cross``: MA-to-AR convolution terms ``psi`` of length ``max(q + 1, p)``.
fn arma_cross(p: usize, q: usize, pars: &[f64]) -> Vec<f64> {
    let mut m = q + 1;
    if p > m {
        m = p;
    }
    let mut psi = vec![0.0; m];
    psi[0] = 1.0;
    for i in 1..m {
        psi[i] = if q < i { 0.0 } else { pars[p + i - 1] };
        let pm = p.min(i);
        for j in 0..pm {
            psi[i] += pars[j] * psi[i - j - 1];
        }
    }
    psi
}

/// ``ARMA_corr``: autocorrelations ``crr[0..=maxlag]`` from constrained ``pars``.
/// The linear system is solved with the LINPACK QR from the workspace ``linpack``
/// crate (``dqrdc`` with no pivoting, then ``dqrsl`` with job 100).
fn arma_corr(p: usize, q: usize, maxlag: usize, pars: &[f64], psi: &[f64], crr: &mut [f64]) -> Result<(), String> {
    let pp = p + 1;
    let maxpq = p.max(q);
    if maxpq > 0 {
        let mlag = p.max(q).max(maxlag) + 1;
        if crr.len() < mlag {
            return Err("correlation buffer too short".to_string());
        }
        let mut coef = vec![0.0; pp * pp];
        for i in 0..pp {
            crr[i] = 0.0;
            coef[i + i * pp] = 1.0;
        }
        for i in pp..mlag {
            crr[i] = 0.0;
        }
        crr[0] = 1.0;
        for i in 1..=q {
            crr[0] += pars[p + i - 1] * psi[i];
        }
        if p > 0 {
            let minpq = p.min(q);
            for i in 1..=minpq {
                for j in i..=q {
                    crr[i] += pars[p - 1 + j] * psi[j - i];
                }
            }
            for i in 0..pp {
                for j in 0..p {
                    let k = (i as isize - j as isize - 1).unsigned_abs();
                    coef[i + k * pp] -= pars[j];
                }
            }
            let mut qraux = vec![0.0; pp];
            let mut jpvt = vec![0_i32; pp];
            let mut work = vec![0.0; pp];
            dqrdc(&mut coef, pp, pp, pp, &mut qraux, &mut jpvt, &mut work, 0);
            for i in 0..pp {
                if coef[i + i * pp] == 0.0 {
                    return Err("Coefficient matrix not invertible".to_string());
                }
            }
            let y: Vec<f64> = crr[..pp].to_vec();
            let mut qy: Vec<f64> = Vec::new();
            let mut qty = vec![0.0; pp];
            let mut work1 = vec![0.0; mlag];
            let mut rsd: Vec<f64> = Vec::new();
            let mut xb: Vec<f64> = Vec::new();
            dqrsl(&mut coef, pp, pp, pp, &qraux, &y, &mut qy, &mut qty, &mut work1, &mut rsd, &mut xb, 100);
            crr[..mlag].copy_from_slice(&work1);
        }
        for i in pp..=q {
            for j in 0..p {
                crr[i] += pars[j] * crr[i - j - 1];
            }
            for j in i..=q {
                crr[i] += pars[j - 1] * psi[j - i];
            }
        }
        for i in (maxpq + 1)..mlag {
            for j in 0..p {
                crr[i] += pars[j] * crr[i - j - 1];
            }
        }
        for i in 1..mlag {
            crr[i] /= crr[0];
        }
    }
    crr[0] = 1.0;
    Ok(())
}

/// ``ARMA_fullCorr`` on constrained parameters. Returns ``maxlag + 1`` values.
fn arma_full_corr(p: usize, q: usize, maxlag: usize, pars: &[f64]) -> Result<Vec<f64>, String> {
    let psi = arma_cross(p, q, pars);
    let mut crr = vec![0.0; maxlag.max(p).max(q) + 1];
    arma_corr(p, q, maxlag, pars, &psi, &mut crr)?;
    Ok(crr)
}

/// ``ARMA_mat``: the n-by-n correlation block for the observation times of one group.
fn arma_mat(crr: &[f64], time: &[i32], n: usize) -> Vec<f64> {
    let mut mat = vec![0.0; n * n];
    for i in 0..n {
        for j in i..n {
            let k = (time[j] as i64 - time[i] as i64).unsigned_abs() as usize;
            mat[i + j * n] = crr[k];
            mat[j + i * n] = crr[k];
        }
    }
    mat
}

/// Upper Cholesky factor ``U`` with ``U' U = a``, ordered as LINPACK ``dpofa``.
fn chol_upper(a: &[f64], n: usize) -> Result<Vec<f64>, String> {
    let mut a = a.to_vec();
    for j in 0..n {
        let mut s = 0.0;
        for k in 0..j {
            let mut t = a[k + j * n];
            for i in 0..k {
                t -= a[i + k * n] * a[i + j * n];
            }
            t /= a[k + k * n];
            a[k + j * n] = t;
            s += t * t;
        }
        s = a[j + j * n] - s;
        if s <= 0.0 {
            return Err("correlation matrix is not positive definite".to_string());
        }
        a[j + j * n] = s.sqrt();
    }
    for j in 0..n {
        for i in (j + 1)..n {
            a[i + j * n] = 0.0;
        }
    }
    Ok(a)
}

/// ``ARMA_fact`` for one group: the lower factor ``U^{-T}`` (column-major) and
/// the running ``logdet -= sum(log |U_ii|)``.
fn arma_fact(crr: &[f64], time: &[i32], n: usize, logdet: &mut f64) -> Result<Vec<f64>, String> {
    let mat = arma_mat(crr, time, n);
    let u = chol_upper(&mat, n)?;
    let mut out = vec![0.0; n * n];
    for i in 0..n {
        let mut x = vec![0.0; n];
        x[i] = 1.0;
        // Solve U' x = e_i by forward substitution (LINPACK dtrsl, job 11).
        for r in 0..n {
            let mut s = x[r];
            for c in 0..r {
                s -= u[c + r * n] * x[c];
            }
            x[r] = s / u[r + r * n];
        }
        out[i * n..(i + 1) * n].copy_from_slice(&x);
        *logdet -= u[i + i * n].abs().ln();
    }
    Ok(out)
}

/// ``ARMA_factList``: concatenated group factors and the log determinant term.
/// ``pars`` are unconstrained. ``pdims`` is ``c(N, M, maxLen, sumLenSq, len[M])``.
pub fn arma_fact_list(
    pars: &[f64],
    p: usize,
    q: usize,
    time: &[i32],
    maxlag: usize,
    pdims: &[i32],
) -> Result<(Vec<f64>, f64), String> {
    let mut cpars = pars.to_vec();
    arma_const_coef(p, q, &mut cpars);
    let crr = arma_full_corr(p, q, maxlag, &cpars)?;
    let m = pdims[1] as usize;
    let len: Vec<usize> = pdims[4..4 + m].iter().map(|&v| v as usize).collect();
    let mut out = vec![0.0; pdims[3] as usize];
    let mut logdet = 0.0;
    let mut offset = 0;
    let mut start = 0;
    for &l in &len {
        let f = arma_fact(&crr, &time[start..start + l], l, &mut logdet)?;
        out[offset..offset + l * l].copy_from_slice(&f);
        offset += l * l;
        start += l;
    }
    Ok((out, logdet))
}

/// ``ARMA_recalc``: multiply each group block of ``Xy`` by its factor and
/// accumulate the log determinant term onto ``logdet0``. ``xy`` is N-by-zxcol column-major.
pub fn arma_recalc(
    xy: &mut [f64],
    pdims: &[i32],
    zxcol: usize,
    pars: &[f64],
    p: usize,
    q: usize,
    time: &[i32],
    maxlag: usize,
    logdet0: f64,
) -> Result<f64, String> {
    let n = pdims[0] as usize;
    let m = pdims[1] as usize;
    let len: Vec<usize> = pdims[4..4 + m].iter().map(|&v| v as usize).collect();
    let start: Vec<usize> = pdims[4 + m..4 + 2 * m].iter().map(|&v| v as usize).collect();
    let mut cpars = pars.to_vec();
    arma_const_coef(p, q, &mut cpars);
    let crr = arma_full_corr(p, q, maxlag, &cpars)?;
    let mut logdet = logdet0;
    for i in 0..m {
        let l = len[i];
        let s = start[i];
        let factor = arma_fact(&crr, &time[s..s + l], l, &mut logdet)?;
        for c in 0..zxcol {
            let off = c * n + s;
            let block: Vec<f64> = xy[off..off + l].to_vec();
            for r in 0..l {
                let mut acc = 0.0;
                for k in 0..l {
                    acc += factor[r + k * l] * block[k];
                }
                xy[off + r] = acc;
            }
        }
    }
    Ok(logdet)
}

#[cfg(feature = "python")]
mod python {
    use super::{arma_const_coef, arma_fact_list, arma_recalc, arma_unconst_coef};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    #[pyfunction]
    fn arma_unconst_coef_py(p: usize, q: usize, mut pars: Vec<f64>) -> PyResult<Vec<f64>> {
        arma_unconst_coef(p, q, &mut pars);
        Ok(pars)
    }

    #[pyfunction]
    fn arma_const_coef_py(p: usize, q: usize, mut pars: Vec<f64>) -> PyResult<Vec<f64>> {
        arma_const_coef(p, q, &mut pars);
        Ok(pars)
    }

    /// Returns the concatenated group factors (column-major) and the log determinant term.
    #[pyfunction]
    fn arma_fact_list_py(
        pars: Vec<f64>,
        p: usize,
        q: usize,
        time: Vec<i32>,
        maxlag: usize,
        pdims: Vec<i32>,
    ) -> PyResult<(Vec<f64>, f64)> {
        arma_fact_list(&pars, p, q, &time, maxlag, &pdims).map_err(PyValueError::new_err)
    }

    /// Returns the updated ``Xy`` (column-major) and the accumulated log-likelihood term.
    #[pyfunction]
    fn arma_recalc_py(
        mut xy: Vec<f64>,
        pdims: Vec<i32>,
        zxcol: usize,
        pars: Vec<f64>,
        p: usize,
        q: usize,
        time: Vec<i32>,
        maxlag: usize,
        logdet: f64,
    ) -> PyResult<(Vec<f64>, f64)> {
        let out = arma_recalc(&mut xy, &pdims, zxcol, &pars, p, q, &time, maxlag, logdet)
            .map_err(PyValueError::new_err)?;
        Ok((xy, out))
    }

    #[pymodule]
    fn nlcorarma(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(arma_unconst_coef_py, m)?)?;
        m.add_function(wrap_pyfunction!(arma_const_coef_py, m)?)?;
        m.add_function(wrap_pyfunction!(arma_fact_list_py, m)?)?;
        m.add_function(wrap_pyfunction!(arma_recalc_py, m)?)?;
        Ok(())
    }
}
