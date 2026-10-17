//! pyo3 entry point for the pbivnorm kernel. Arrays cross as NumPy float64 vectors.

use numpy::{PyArray1, PyReadonlyArray1};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

fn vec_f64(array: PyReadonlyArray1<'_, f64>) -> Vec<f64> {
    array.as_array().iter().copied().collect()
}

/// `pbivnorm(x, y, rho)`: standard bivariate normal CDF over equal-length arrays.
#[pyfunction]
#[pyo3(name = "pbivnorm")]
fn pbivnorm_py<'py>(
    py: Python<'py>,
    x: PyReadonlyArray1<'py, f64>,
    y: PyReadonlyArray1<'py, f64>,
    rho: PyReadonlyArray1<'py, f64>,
) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let x = vec_f64(x);
    let y = vec_f64(y);
    let rho = vec_f64(rho);
    if x.len() != y.len() || x.len() != rho.len() {
        return Err(PyValueError::new_err(
            "'x', 'y', and 'rho' must have the same length",
        ));
    }
    let out = crate::pbivnorm(&x, &y, &rho);
    Ok(PyArray1::from_vec(py, out))
}

#[pymodule]
#[pyo3(name = "pbivnorm")]
fn pbivnorm_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(pbivnorm_py, m)?)?;
    Ok(())
}
