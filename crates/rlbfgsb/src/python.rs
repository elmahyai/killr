//! pyo3 entry point. The objective is a Python callable that takes a list of
//! floats and returns a float, as R's `fn` does in optim().

use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

use crate::{optim_lbfgsb, Failure};

/// `optim_lbfgsb(fn, par, lower, upper, ndeps, factr, pgtol, lmm, maxit)`.
/// Returns a dict with `par`, `value`, `convergence`, `counts` (function and
/// gradient counts), and `message`, as optim() reports them.
#[pyfunction]
#[pyo3(name = "optim_lbfgsb", signature = (fn_, par, lower, upper, ndeps, factr = 1.0e7, pgtol = 0.0, lmm = 5, maxit = 100))]
fn optim_lbfgsb_py<'py>(
    py: Python<'py>,
    fn_: Bound<'py, PyAny>,
    par: Vec<f64>,
    lower: Vec<f64>,
    upper: Vec<f64>,
    ndeps: Vec<f64>,
    factr: f64,
    pgtol: f64,
    lmm: usize,
    maxit: i64,
) -> PyResult<Bound<'py, PyDict>> {
    let n = par.len();
    if lower.len() != n || upper.len() != n || ndeps.len() != n {
        return Err(PyRuntimeError::new_err(
            "lower, upper and ndeps must have one entry per parameter",
        ));
    }
    let mut fcn = |x: &[f64]| -> PyResult<f64> {
        let arg = PyList::new(py, x)?;
        fn_.call1((arg,))?.extract::<f64>()
    };
    match optim_lbfgsb(&par, &lower, &upper, &ndeps, &mut fcn, factr, pgtol, lmm, maxit) {
        Ok(out) => {
            let dict = PyDict::new(py);
            dict.set_item("par", out.par)?;
            dict.set_item("value", out.value)?;
            dict.set_item("convergence", out.fail)?;
            dict.set_item("fncount", out.fncount)?;
            dict.set_item("grcount", out.grcount)?;
            dict.set_item("message", out.message)?;
            Ok(dict)
        }
        Err(Failure::Callback(err)) => Err(err),
        Err(Failure::Message(msg)) => Err(PyRuntimeError::new_err(msg)),
    }
}

#[pymodule]
#[pyo3(name = "rlbfgsb")]
fn rlbfgsb_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(optim_lbfgsb_py, m)?)?;
    Ok(())
}
