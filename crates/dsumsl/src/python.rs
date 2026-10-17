use numpy::{PyArray1, PyReadonlyArray1};
use pyo3::prelude::*;

use crate::garch::{fit_garch, ophess_garch, pred_garch};

#[pyfunction]
#[pyo3(name = "fit_garch")]
fn fit_garch_py(
    y: PyReadonlyArray1<f64>,
    coef: PyReadonlyArray1<f64>,
    p: i32,
    q: i32,
    maxiter: i32,
    abstol: f64,
    reltol: f64,
    xtol: f64,
    falsetol: f64,
    analytical_grad: bool,
    trace: bool,
) -> PyResult<(Py<PyArray1<f64>>, f64)> {
    let y = y.as_array().to_vec();
    let start = coef.as_array().to_vec();
    let (par, fret) = fit_garch(
        &y,
        &start,
        p,
        q,
        maxiter,
        abstol,
        reltol,
        xtol,
        falsetol,
        analytical_grad,
        trace,
    );
    Python::attach(|py| Ok((PyArray1::from_vec(py, par).into(), fret)))
}

#[pyfunction]
#[pyo3(name = "pred_garch")]
fn pred_garch_py(
    y: PyReadonlyArray1<f64>,
    par: PyReadonlyArray1<f64>,
    p: i32,
    q: i32,
    genuine: bool,
) -> PyResult<Py<PyArray1<f64>>> {
    let y = y.as_array().to_vec();
    let par = par.as_array().to_vec();
    let h = pred_garch(&y, &par, p, q, genuine);
    Python::attach(|py| Ok(PyArray1::from_vec(py, h).into()))
}

#[pyfunction]
#[pyo3(name = "ophess_garch")]
fn ophess_garch_py(
    y: PyReadonlyArray1<f64>,
    par: PyReadonlyArray1<f64>,
    p: i32,
    q: i32,
) -> PyResult<Py<PyArray1<f64>>> {
    let y = y.as_array().to_vec();
    let par = par.as_array().to_vec();
    let he = ophess_garch(&y, &par, p, q);
    Python::attach(|py| Ok(PyArray1::from_vec(py, he).into()))
}

#[pymodule]
fn dsumsl(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(fit_garch_py, m)?)?;
    m.add_function(wrap_pyfunction!(pred_garch_py, m)?)?;
    m.add_function(wrap_pyfunction!(ophess_garch_py, m)?)?;
    Ok(())
}
