//! Python bindings. Arrays cross as NumPy arrays; the Python package does the R-level argument handling.

use numpy::{PyArray1, PyReadonlyArray1, PyReadonlyArray2};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use crate::grid::Lines;

type Triple = (Py<PyArray1<f64>>, Py<PyArray1<f64>>, Py<PyArray1<i32>>);

fn vec_f64(array: PyReadonlyArray1<'_, f64>) -> Vec<f64> {
    if let Ok(slice) = array.as_slice() {
        slice.to_vec()
    } else {
        array.as_array().iter().copied().collect()
    }
}

fn vec_i32(array: PyReadonlyArray1<'_, i32>) -> Vec<i32> {
    if let Ok(slice) = array.as_slice() {
        slice.to_vec()
    } else {
        array.as_array().iter().copied().collect()
    }
}

fn to_py(py: Python<'_>, lines: Vec<Lines>) -> Vec<Triple> {
    lines
        .into_iter()
        .map(|l| {
            (
                PyArray1::from_vec(py, l.x).into(),
                PyArray1::from_vec(py, l.y).into(),
                PyArray1::from_vec(py, l.id).into(),
            )
        })
        .collect()
}

fn value_error(msg: String) -> PyErr {
    PyValueError::new_err(msg)
}

#[pyfunction]
fn isolines_kernel(
    py: Python<'_>,
    x: PyReadonlyArray1<'_, f64>,
    y: PyReadonlyArray1<'_, f64>,
    z: PyReadonlyArray1<'_, f64>,
    nrow: usize,
    ncol: usize,
    levels: PyReadonlyArray1<'_, f64>,
) -> PyResult<Vec<Triple>> {
    let (x, y, z, levels) = (vec_f64(x), vec_f64(y), vec_f64(z), vec_f64(levels));
    let out = crate::isolines(&x, &y, &z, nrow, ncol, &levels).map_err(value_error)?;
    Ok(to_py(py, out))
}

#[pyfunction]
fn isobands_kernel(
    py: Python<'_>,
    x: PyReadonlyArray1<'_, f64>,
    y: PyReadonlyArray1<'_, f64>,
    z: PyReadonlyArray1<'_, f64>,
    nrow: usize,
    ncol: usize,
    low: PyReadonlyArray1<'_, f64>,
    high: PyReadonlyArray1<'_, f64>,
) -> PyResult<Vec<Triple>> {
    let (x, y, z) = (vec_f64(x), vec_f64(y), vec_f64(z));
    let (low, high) = (vec_f64(low), vec_f64(high));
    let out = crate::isobands(&x, &y, &z, nrow, ncol, &low, &high).map_err(value_error)?;
    Ok(to_py(py, out))
}

#[pyfunction]
fn clip_lines_kernel(
    py: Python<'_>,
    x: PyReadonlyArray1<'_, f64>,
    y: PyReadonlyArray1<'_, f64>,
    id: PyReadonlyArray1<'_, i32>,
    boxes: PyReadonlyArray2<'_, f64>,
    asp: f64,
) -> PyResult<Triple> {
    let (x, y, id) = (vec_f64(x), vec_f64(y), vec_i32(id));
    let flat: Vec<f64> = boxes.as_array().iter().copied().collect();
    if flat.len() % 5 != 0 {
        return Err(value_error("clip boxes must have five columns".into()));
    }
    let rows: Vec<[f64; 5]> = flat
        .chunks_exact(5)
        .map(|c| [c[0], c[1], c[2], c[3], c[4]])
        .collect();
    let out = crate::clip_lines(&x, &y, &id, &rows, asp).map_err(value_error)?;
    let triple: Triple = (
        PyArray1::from_vec(py, out.x).into(),
        PyArray1::from_vec(py, out.y).into(),
        PyArray1::from_vec(py, out.id).into(),
    );
    Ok(triple)
}

#[pymodule]
#[pyo3(name = "isoband_kernel")]
fn isoband_kernel_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(isolines_kernel, m)?)?;
    m.add_function(wrap_pyfunction!(isobands_kernel, m)?)?;
    m.add_function(wrap_pyfunction!(clip_lines_kernel, m)?)?;
    Ok(())
}
