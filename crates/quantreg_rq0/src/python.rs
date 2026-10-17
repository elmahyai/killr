//! pyo3 entry point for the dense simplex. The design crosses as a NumPy array in
//! its R shape (rows are observations), the response as a NumPy vector, and the
//! coefficients come back as a NumPy vector of length p.

use numpy::ndarray::Array1;
use numpy::{PyArray1, PyReadonlyArray1, PyReadonlyArray2};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use crate::{rq0 as run_rq0, FLAG_EMPTY, FLAG_TAU};

/// `rq0(x, y, tau, toler)`: the dense simplex of R's `rq0` for one `tau`. `x` is the
/// m x n design, `y` the response of length m, and `toler` is R's `TOLER` (R's `pwy`
/// passes `1e-4`). Returns `(coef, ift)`, `coef` of length n, and `ift` the Fortran flag.
#[pyfunction]
#[pyo3(name = "rq0")]
fn rq0_py<'py>(
    py: Python<'py>,
    x: PyReadonlyArray2<'py, f64>,
    y: PyReadonlyArray1<'py, f64>,
    tau: f64,
    toler: f64,
) -> PyResult<(Bound<'py, PyArray1<f64>>, i32)> {
    let design = x.as_array();
    let (m, n) = design.dim();
    // Row-major copy of the design, whatever the NumPy layout.
    let a: Vec<f64> = design.iter().copied().collect();
    let b: Vec<f64> = y.as_array().iter().copied().collect();
    if b.len() != m {
        return Err(PyValueError::new_err("x and y don't match n"));
    }
    if !toler.is_finite() || toler < 0.0 {
        return Err(PyValueError::new_err("toler must be a finite non-negative number"));
    }
    let out = run_rq0(m, n, &a, &b, tau, toler);
    match out.ift {
        FLAG_EMPTY => return Err(PyValueError::new_err("the design and response must not be empty")),
        FLAG_TAU => return Err(PyValueError::new_err("tau must lie in [0, 1]")),
        _ => {}
    }
    Ok((PyArray1::from_owned_array(py, Array1::from(out.coef)), out.ift))
}

#[pymodule]
#[pyo3(name = "quantreg_rq0_kernel")]
fn quantreg_rq0_kernel_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(rq0_py, m)?)?;
    Ok(())
}
