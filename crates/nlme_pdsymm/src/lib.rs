//! R nlme `matrixLog_pd` (src/pdMat.c) on the EISPACK `rs` kernel (src/rs.f).
//!
//! `pdSymm` stores the upper triangle of half the matrix logarithm, column by
//! column. `matrixLog_pd` builds that symmetric matrix (`Chol_pd`, then the
//! lower triangle copied from the upper), takes its eigendecomposition with
//! `rs`, scales eigenvector column `i` by `exp(value_i)`, and returns the
//! transpose. The result `L` satisfies `crossprod(L)` = the pd matrix. Signs
//! and scaling come from the Fortran kernel itself, so they match R.

#![allow(clippy::many_single_char_names)]

use std::os::raw::c_int;

unsafe extern "C" {
    /// EISPACK `rs`: `CALL RS(NM, N, A, W, MATZ, Z, FV1, FV2, IERR)`.
    fn rs_(
        nm: *const c_int,
        n: *const c_int,
        a: *mut f64,
        w: *mut f64,
        matz: *const c_int,
        z: *mut f64,
        fv1: *mut f64,
        fv2: *mut f64,
        ierr: *mut c_int,
    );
}

/// Order `q` from the number of pdSymm parameters, `q (q + 1) / 2`.
pub fn order_from_length(len: usize) -> Option<usize> {
    let mut q = 0usize;
    while q * (q + 1) / 2 < len {
        q += 1;
    }
    if q * (q + 1) / 2 == len { Some(q) } else { None }
}

/// `matrixLog_pd(L, q, l)` for `q` columns. `params` holds `l` in R's order.
///
/// Returns `L` in column-major order, the same layout as R's `Factor`.
pub fn matrix_log_pd(params: &[f64], q: usize) -> Result<Vec<f64>, String> {
    if params.len() != q * (q + 1) / 2 {
        return Err(format!(
            "an object of length {} does not match the required parameter size for order {}",
            params.len(),
            q
        ));
    }
    if q == 0 {
        return Ok(Vec::new());
    }
    if q == 1 {
        return Ok(vec![params[0].exp()]);
    }

    // Chol_pd: column i receives the first i + 1 parameters (upper triangle).
    let mut sym = vec![0.0f64; q * q];
    let mut src = 0usize;
    for i in 0..q {
        for r in 0..=i {
            sym[r + i * q] = params[src];
            src += 1;
        }
    }
    // copy_mat loop: lower column i takes upper row i, so the matrix is symmetric.
    for i in 0..(q - 1) {
        for k in 0..(q - (i + 1)) {
            sym[(i + 1 + k) + i * q] = sym[i + (i + 1 + k) * q];
        }
    }

    let n = q as c_int;
    let nm = q as c_int;
    let matz: c_int = 1;
    let mut values = vec![0.0f64; q];
    let mut vectors = vec![0.0f64; q * q];
    let mut work1 = vec![0.0f64; q];
    let mut work2 = vec![0.0f64; q];
    let mut ierr: c_int = 0;
    unsafe {
        rs_(
            &nm,
            &n,
            sym.as_mut_ptr(),
            values.as_mut_ptr(),
            &matz,
            vectors.as_mut_ptr(),
            work1.as_mut_ptr(),
            work2.as_mut_ptr(),
            &mut ierr,
        );
    }

    // values[i] = exp(values[i]); vectors[i * qq + j] *= values[i].
    for i in 0..q {
        values[i] = values[i].exp();
        for j in 0..q {
            vectors[j + i * q] *= values[i];
        }
    }

    // copy_trans(L, qq, vectors, qq, qq, qq): L = t(vectors).
    let mut out = vec![0.0f64; q * q];
    for i in 0..q {
        for j in 0..q {
            out[j + i * q] = vectors[i + j * q];
        }
    }
    Ok(out)
}

#[cfg(feature = "python")]
mod python {
    use super::{matrix_log_pd as kernel, order_from_length};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    /// `matrix_log_pd(M, q=None)`: pdSymm factor, R's `pdFactor.pdSymm`.
    ///
    /// `M` is the pdSymm parameter vector (R's `object`), upper triangle of
    /// half the matrix log in column-major order. Returns the q x q factor in
    /// column-major order as a flat list (R's `Factor`).
    #[pyfunction]
    #[pyo3(name = "matrix_log_pd", signature = (m, q = None))]
    fn matrix_log_pd_py(m: Vec<f64>, q: Option<usize>) -> PyResult<Vec<f64>> {
        let order = match q {
            Some(order) => order,
            None => order_from_length(m.len()).ok_or_else(|| {
                PyValueError::new_err(format!(
                    "an object of length {} does not match the required parameter size",
                    m.len()
                ))
            })?,
        };
        kernel(&m, order).map_err(PyValueError::new_err)
    }

    #[pymodule]
    fn nlme_pdsymm(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(matrix_log_pd_py, m)?)?;
        Ok(())
    }
}
