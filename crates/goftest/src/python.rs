use numpy::{IntoPyArray, PyArray1, PyReadonlyArray1};
use pyo3::prelude::*;

/// Asymptotic null CDF of A_n, the `ADprobApproxInf` entry point.
#[pyfunction]
fn adinf<'py>(py: Python<'py>, a: PyReadonlyArray1<'py, f64>) -> Bound<'py, PyArray1<f64>> {
    let out: Vec<f64> = a.as_array().iter().map(|&z| crate::adinf(z)).collect();
    out.into_pyarray(py)
}

/// Exact limiting null CDF of A_n, the `ADprobExactInf` entry point.
#[pyfunction]
fn ad_inf<'py>(py: Python<'py>, a: PyReadonlyArray1<'py, f64>) -> Bound<'py, PyArray1<f64>> {
    let out: Vec<f64> = a.as_array().iter().map(|&z| crate::ad_inf(z)).collect();
    out.into_pyarray(py)
}

/// Null CDF of A_n for sample size `n`, the `ADprobN` entry point.
#[pyfunction]
fn ad_prob_n<'py>(
    py: Python<'py>,
    a: PyReadonlyArray1<'py, f64>,
    n: i32,
) -> Bound<'py, PyArray1<f64>> {
    let out: Vec<f64> = a.as_array().iter().map(|&z| crate::ad_prob(n, z)).collect();
    out.into_pyarray(py)
}

/// `errfix(n, x)` from AnDarl.c.
#[pyfunction]
fn errfix(n: i32, x: f64) -> f64 {
    crate::errfix(n, x)
}

/// Anderson-Darling statistic of a sorted sample.
#[pyfunction]
fn ad_statistic(x: PyReadonlyArray1<'_, f64>) -> f64 {
    let v: Vec<f64> = x.as_array().iter().copied().collect();
    crate::ad_statistic(&v)
}

/// `(statistic, p-value)` of a sorted sample, as `ADtestR`.
#[pyfunction]
fn ad_test(x: PyReadonlyArray1<'_, f64>) -> (f64, f64) {
    let v: Vec<f64> = x.as_array().iter().copied().collect();
    crate::ad_test(&v)
}

/// Standard normal upper tail `cPhi(x)` from ADinf.c.
#[pyfunction]
fn c_phi(x: f64) -> f64 {
    crate::c_phi(x)
}

#[pymodule]
fn goftest_kernels(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(adinf, m)?)?;
    m.add_function(wrap_pyfunction!(ad_inf, m)?)?;
    m.add_function(wrap_pyfunction!(ad_prob_n, m)?)?;
    m.add_function(wrap_pyfunction!(errfix, m)?)?;
    m.add_function(wrap_pyfunction!(ad_statistic, m)?)?;
    m.add_function(wrap_pyfunction!(ad_test, m)?)?;
    m.add_function(wrap_pyfunction!(c_phi, m)?)?;
    Ok(())
}
