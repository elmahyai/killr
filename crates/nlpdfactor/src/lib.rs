//! Square-root factors for nlme ``pdMat`` classes, ported from ``src/pdMat.c``.

fn chol_pd_packed(l: &mut [f64], q: usize, params: &[f64]) {
    let mut src = 0usize;
    for i in 0..q {
        let row = i * q;
        l[row..row + i + 1].copy_from_slice(&params[src..src + i + 1]);
        src += i + 1;
    }
}

fn copy_trans(y: &mut [f64], ldy: usize, x: &[f64], ldx: usize, nrow: usize, ncol: usize) {
    for i in 0..nrow {
        for j in 0..ncol {
            y[i * ldy + j] = x[i + j * ldx];
        }
    }
}

/// Upper Cholesky factor ``R`` with ``A = R' R`` (Linpack ``dpofa`` layout).
fn dpofa_upper(a: &mut [f64], lda: usize, n: usize) -> Result<(), ()> {
    for j in 0..n {
        let mut s = 0.0;
        for k in 0..j {
            let mut r = 0.0;
            for i in 0..k {
                r += a[i * lda + k] * a[i * lda + j];
            }
            let t = a[k * lda + j] - r;
            a[k * lda + j] = t / a[k * lda + k];
            s += t * a[k * lda + j];
        }
        s = a[j * lda + j] - s;
        if s <= 0.0 {
            return Err(());
        }
        a[j * lda + j] = s.sqrt();
    }
    Ok(())
}

fn cholesky_upper_from_sym(a: &[f64], q: usize) -> Result<Vec<f64>, ()> {
    let mut v = vec![0.0; q * q];
    for i in 0..q {
        for j in 0..q {
            if i <= j {
                v[i * q + j] = a[i * q + j];
            }
        }
    }
    dpofa_upper(&mut v, q, q)?;
    Ok(v)
}

pub fn log_chol_pd(params: &[f64], q: usize) -> Vec<f64> {
    let mut l = vec![0.0; q * q];
    if q == 0 {
        return l;
    }
    l[0] = params[0].exp();
    let mut ll = q;
    for i in 1..q {
        l[i * (q + 1)] = params[i].exp();
        let start = ll;
        let len = i;
        l[i * q..i * q + len].copy_from_slice(&params[start..start + len]);
        ll += i;
    }
    l
}

pub fn natural_pd(params: &[f64], q: usize) -> Vec<f64> {
    let mut l = vec![0.0; q * q];
    if q == 0 {
        return l;
    }
    let std: Vec<f64> = params[..q].iter().map(|v| v.exp()).collect();
    let mut corr = q;
    for i in 0..q {
        l[i * (q + 1)] = std[i] * std[i];
        for j in (i + 1)..q {
            let mut c = params[corr].exp();
            c = (c - 1.0) / (c + 1.0);
            l[i * q + j] = std[i] * std[j] * c;
            l[j * q + i] = l[i * q + j];
            corr += 1;
        }
    }
    cholesky_upper_from_sym(&l, q).unwrap_or(l)
}

pub fn comp_symm_pd(params: &[f64], q: usize) -> Vec<f64> {
    let mut l = vec![0.0; q * q];
    if q == 0 {
        return l;
    }
    let mut aux = params[0].exp();
    let mut aux1 = params[1].exp();
    aux1 = (aux1 - 1.0 / ((q as f64) - 1.0)) / (aux1 + 1.0);
    let aux2 = aux * (1.0 - aux1).sqrt();
    let aux1 = aux * ((1.0 + ((q as f64) - 1.0) * aux1) / (q as f64)).sqrt();
    for i in 0..q {
        l[i * q] = aux1;
    }
    for i in 1..q {
        aux = -aux2 / ((i * (i + 1)) as f64).sqrt();
        for j in 0..i {
            l[i + j * q] = aux;
        }
        l[i * (q + 1)] = -aux * (i as f64);
    }
    l
}

/// ``matrixLog_pd`` without the SVD step (``q == 1`` only in Rust; larger ``q`` uses Python).
pub fn matrix_log_pd_small(params: &[f64], q: usize) -> Vec<f64> {
    let mut l = vec![0.0; q * q];
    if q == 1 {
        l[0] = params[0].exp();
    }
    l
}

#[cfg(feature = "python")]
mod python {
    use super::*;
    use pyo3::prelude::*;

    #[pyfunction]
    fn log_chol_pd_py(params: Vec<f64>, q: usize) -> PyResult<Vec<f64>> {
        Ok(log_chol_pd(&params, q))
    }

    #[pyfunction]
    fn natural_pd_py(params: Vec<f64>, q: usize) -> PyResult<Vec<f64>> {
        Ok(natural_pd(&params, q))
    }

    #[pyfunction]
    fn comp_symm_pd_py(params: Vec<f64>, q: usize) -> PyResult<Vec<f64>> {
        Ok(comp_symm_pd(&params, q))
    }

    #[pymodule]
    fn nlpdfactor(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(log_chol_pd_py, m)?)?;
        m.add_function(wrap_pyfunction!(natural_pd_py, m)?)?;
        m.add_function(wrap_pyfunction!(comp_symm_pd_py, m)?)?;
        Ok(())
    }
}
