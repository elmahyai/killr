use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyDict;

/// `shull_deltri(x, y)` -> dict with status, nt, trlist, cclist, nch, ch, na, a1, a2.
#[pyfunction]
#[pyo3(name = "shull_deltri")]
fn shull_deltri_py<'py>(
    py: Python<'py>,
    x: Vec<f64>,
    y: Vec<f64>,
) -> PyResult<Bound<'py, PyDict>> {
    let t = crate::triangulate(&x, &y).map_err(PyValueError::new_err)?;
    let d = PyDict::new(py);
    d.set_item("status", t.status)?;
    d.set_item("nt", t.nt)?;
    d.set_item("trlist", t.trlist)?;
    d.set_item("cclist", t.cclist)?;
    d.set_item("nch", t.nch)?;
    d.set_item("ch", t.ch)?;
    d.set_item("na", t.na)?;
    d.set_item("a1", t.a1)?;
    d.set_item("a2", t.a2)?;
    Ok(d)
}

#[pymodule]
fn interp_kernels(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(shull_deltri_py, m)?)?;
    Ok(())
}
