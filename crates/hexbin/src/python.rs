//! Python bindings. Arrays cross as NumPy arrays; Fortran integers are int32.

use numpy::{IntoPyArray, PyArray1, PyReadonlyArray1};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

fn to_vec_f64(a: &PyReadonlyArray1<'_, f64>) -> Vec<f64> {
    a.as_array().iter().copied().collect()
}

fn to_vec_i32(a: &PyReadonlyArray1<'_, i32>) -> Vec<i32> {
    a.as_array().iter().copied().collect()
}

/// `hbin(x, y, size, shape, rx, ry, dim, keep_ids=False)`
///
/// Returns `(cell, cnt, xcm, ycm, nrow, cell_ids)`. `cell`, `cnt`, `xcm`, `ycm`
/// hold the non-empty cells only. `nrow` is the revised `dim[0]`. `cell_ids` is
/// the per-point cell id when `keep_ids` is true, else `None`.
#[pyfunction]
#[pyo3(name = "hbin", signature = (x, y, size, shape, rx, ry, dim, keep_ids=false))]
#[allow(clippy::type_complexity)]
fn hbin_py<'py>(
    py: Python<'py>,
    x: PyReadonlyArray1<'py, f64>,
    y: PyReadonlyArray1<'py, f64>,
    size: f64,
    shape: f64,
    rx: (f64, f64),
    ry: (f64, f64),
    dim: (i32, i32),
    keep_ids: bool,
) -> PyResult<(
    Bound<'py, PyArray1<i32>>,
    Bound<'py, PyArray1<i32>>,
    Bound<'py, PyArray1<f64>>,
    Bound<'py, PyArray1<f64>>,
    i32,
    Option<Bound<'py, PyArray1<i32>>>,
)> {
    let xs = to_vec_f64(&x);
    let ys = to_vec_f64(&y);
    let out = crate::hbin(
        &xs,
        &ys,
        size,
        shape,
        [rx.0, rx.1],
        [ry.0, ry.1],
        [dim.0, dim.1],
        keep_ids,
    )
    .map_err(PyValueError::new_err)?;
    Ok((
        out.cell.into_pyarray(py),
        out.cnt.into_pyarray(py),
        out.xcm.into_pyarray(py),
        out.ycm.into_pyarray(py),
        out.nrow,
        out.cell_ids.map(|ids| ids.into_pyarray(py)),
    ))
}

/// `hcell(x, y, size, shape, rx, ry, dim)` -> `(cell, nrow)`
#[pyfunction]
#[pyo3(name = "hcell")]
fn hcell_py<'py>(
    py: Python<'py>,
    x: PyReadonlyArray1<'py, f64>,
    y: PyReadonlyArray1<'py, f64>,
    size: f64,
    shape: f64,
    rx: (f64, f64),
    ry: (f64, f64),
    dim: (i32, i32),
) -> PyResult<(Bound<'py, PyArray1<i32>>, i32)> {
    let xs = to_vec_f64(&x);
    let ys = to_vec_f64(&y);
    let out = crate::hcell(
        &xs,
        &ys,
        size,
        shape,
        [rx.0, rx.1],
        [ry.0, ry.1],
        [dim.0, dim.1],
    )
    .map_err(PyValueError::new_err)?;
    Ok((out.cell.into_pyarray(py), out.nrow))
}

/// `herode(cell, cnt, dim)` -> erosion order per input cell, int32 array.
#[pyfunction]
#[pyo3(name = "herode")]
fn herode_py<'py>(
    py: Python<'py>,
    cell: PyReadonlyArray1<'py, i32>,
    cnt: PyReadonlyArray1<'py, i32>,
    dim: (i32, i32),
) -> PyResult<Bound<'py, PyArray1<i32>>> {
    let cells = to_vec_i32(&cell);
    let counts = to_vec_i32(&cnt);
    let out = crate::herode(&cells, &counts, [dim.0, dim.1]).map_err(PyValueError::new_err)?;
    Ok(out.into_pyarray(py))
}

/// `hsm(cell, cnt, nmax, ncol, wts)` -> `(cell, cnt)` of surviving cells.
///
/// `cell` must already be padded as R's `smooth.hexbin` pads it.
#[pyfunction]
#[pyo3(name = "hsm")]
fn hsm_py<'py>(
    py: Python<'py>,
    cell: PyReadonlyArray1<'py, i32>,
    cnt: PyReadonlyArray1<'py, i32>,
    nmax: usize,
    ncol: i64,
    wts: (i32, i32, i32),
) -> PyResult<(Bound<'py, PyArray1<i32>>, Bound<'py, PyArray1<i32>>)> {
    let cells = to_vec_i32(&cell);
    let counts = to_vec_i32(&cnt);
    let (out_cell, out_cnt) = crate::hsm(&cells, &counts, nmax, ncol, [wts.0, wts.1, wts.2])
        .map_err(PyValueError::new_err)?;
    Ok((out_cell.into_pyarray(py), out_cnt.into_pyarray(py)))
}

#[pymodule]
fn hexbin_kernels(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(hbin_py, m)?)?;
    m.add_function(wrap_pyfunction!(hcell_py, m)?)?;
    m.add_function(wrap_pyfunction!(herode_py, m)?)?;
    m.add_function(wrap_pyfunction!(hsm_py, m)?)?;
    Ok(())
}
