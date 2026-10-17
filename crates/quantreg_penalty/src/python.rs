//! pyo3 entry point for the triogram penalty. The triangulation crosses as int64
//! arrays with 1-based vertex numbers, as the triSht2tri lists are in R.

use numpy::{PyArray1, PyReadonlyArray1};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use crate::penalty as run_penalty;

fn vec_of_f64(a: &PyReadonlyArray1<'_, f64>) -> Vec<f64> {
    a.as_array().iter().copied().collect()
}

fn vec_of_i64(a: &PyReadonlyArray1<'_, i64>) -> Vec<i64> {
    a.as_array().iter().copied().collect()
}

/// `penalty(n, m, x, y, bnd, tlist, tlptr, tlend, eps)`: returns `(rax, jax, ned, ierr)`.
/// `rax` and `jax` have length `m`; `jax` holds 1-based vertex numbers.
#[pyfunction]
#[pyo3(name = "penalty")]
fn penalty_py<'py>(
    py: Python<'py>,
    n: usize,
    m: usize,
    x: PyReadonlyArray1<'py, f64>,
    y: PyReadonlyArray1<'py, f64>,
    bnd: PyReadonlyArray1<'py, i64>,
    tlist: PyReadonlyArray1<'py, i64>,
    tlptr: PyReadonlyArray1<'py, i64>,
    tlend: PyReadonlyArray1<'py, i64>,
    eps: f64,
) -> PyResult<(Bound<'py, PyArray1<f64>>, Bound<'py, PyArray1<i64>>, usize, i32)> {
    let (x, y) = (vec_of_f64(&x), vec_of_f64(&y));
    let bnd = vec_of_i64(&bnd);
    let tlist = vec_of_i64(&tlist);
    let tlptr = vec_of_i64(&tlptr);
    let tlend = vec_of_i64(&tlend);
    let out = run_penalty(n, m, &x, &y, &bnd, &tlist, &tlptr, &tlend, eps)
        .map_err(PyValueError::new_err)?;
    Ok((
        PyArray1::from_vec(py, out.rax),
        PyArray1::from_vec(py, out.jax),
        out.ned,
        out.ierr,
    ))
}

#[pymodule]
#[pyo3(name = "quantreg_penalty_kernel")]
fn quantreg_penalty_kernel_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(penalty_py, m)?)?;
    Ok(())
}
