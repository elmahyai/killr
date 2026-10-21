//! Python bindings. Leaves cross as NumPy arrays of the C specialization's type.

use numpy::{IntoPyArray, PyArray1, PyReadonlyArray1};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use crate::{Kind, SlideOpts};

fn kind_of(name: &str) -> PyResult<Kind> {
    Kind::from_name(name).ok_or_else(|| PyValueError::new_err(format!("unknown summary `{name}`")))
}

fn to_vec_f64(a: &PyReadonlyArray1<'_, f64>) -> Vec<f64> {
    a.as_array().iter().copied().collect()
}

fn to_vec_i32(a: &PyReadonlyArray1<'_, i32>) -> Vec<i32> {
    a.as_array().iter().copied().collect()
}

/// `slide_dbl(kind, x, before, before_unbounded, after, after_unbounded, step, complete, na_rm)`
#[pyfunction]
#[pyo3(name = "slide_dbl", signature = (kind, x, before, before_unbounded, after, after_unbounded, step, complete, na_rm=false))]
#[allow(clippy::too_many_arguments)]
fn slide_dbl_py<'py>(
    py: Python<'py>,
    kind: &str,
    x: PyReadonlyArray1<'py, f64>,
    before: i64,
    before_unbounded: bool,
    after: i64,
    after_unbounded: bool,
    step: i64,
    complete: bool,
    na_rm: bool,
) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let values = to_vec_f64(&x);
    let opts = SlideOpts::new(before, before_unbounded, after, after_unbounded, step, complete);
    let out = crate::slide_dbl(kind_of(kind)?, &values, opts, na_rm);
    Ok(out.into_pyarray(py))
}

/// `slide_lgl(kind, x, ...)` with R logicals: 0, 1, or `NA_LGL`.
#[pyfunction]
#[pyo3(name = "slide_lgl", signature = (kind, x, before, before_unbounded, after, after_unbounded, step, complete, na_rm=false))]
#[allow(clippy::too_many_arguments)]
fn slide_lgl_py<'py>(
    py: Python<'py>,
    kind: &str,
    x: PyReadonlyArray1<'py, i32>,
    before: i64,
    before_unbounded: bool,
    after: i64,
    after_unbounded: bool,
    step: i64,
    complete: bool,
    na_rm: bool,
) -> PyResult<Bound<'py, PyArray1<i32>>> {
    let values = to_vec_i32(&x);
    let opts = SlideOpts::new(before, before_unbounded, after, after_unbounded, step, complete);
    let out = crate::slide_lgl(kind_of(kind)?, &values, opts, na_rm);
    Ok(out.into_pyarray(py))
}

/// `slide_index_dbl(kind, x, keys, peer_sizes, starts, stops, complete, na_rm)`
///
/// `starts` and `stops` are `None` for R's unbounded `NULL` endpoints.
#[pyfunction]
#[pyo3(name = "slide_index_dbl", signature = (kind, x, keys, peer_sizes, starts, stops, complete=false, na_rm=false))]
#[allow(clippy::too_many_arguments)]
fn slide_index_dbl_py<'py>(
    py: Python<'py>,
    kind: &str,
    x: PyReadonlyArray1<'py, f64>,
    keys: PyReadonlyArray1<'py, i32>,
    peer_sizes: PyReadonlyArray1<'py, i32>,
    starts: Option<PyReadonlyArray1<'py, i32>>,
    stops: Option<PyReadonlyArray1<'py, i32>>,
    complete: bool,
    na_rm: bool,
) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let values = to_vec_f64(&x);
    let keys = to_vec_i32(&keys);
    let peer_sizes = to_vec_i32(&peer_sizes);
    let starts = starts.as_ref().map(to_vec_i32);
    let stops = stops.as_ref().map(to_vec_i32);
    let out = crate::slide_index_dbl(
        kind_of(kind)?,
        &values,
        &keys,
        &peer_sizes,
        starts.as_deref(),
        stops.as_deref(),
        complete,
        na_rm,
    );
    Ok(out.into_pyarray(py))
}

/// `slide_index_lgl(kind, x, keys, peer_sizes, starts, stops, complete, na_rm)`
#[pyfunction]
#[pyo3(name = "slide_index_lgl", signature = (kind, x, keys, peer_sizes, starts, stops, complete=false, na_rm=false))]
#[allow(clippy::too_many_arguments)]
fn slide_index_lgl_py<'py>(
    py: Python<'py>,
    kind: &str,
    x: PyReadonlyArray1<'py, i32>,
    keys: PyReadonlyArray1<'py, i32>,
    peer_sizes: PyReadonlyArray1<'py, i32>,
    starts: Option<PyReadonlyArray1<'py, i32>>,
    stops: Option<PyReadonlyArray1<'py, i32>>,
    complete: bool,
    na_rm: bool,
) -> PyResult<Bound<'py, PyArray1<i32>>> {
    let values = to_vec_i32(&x);
    let keys = to_vec_i32(&keys);
    let peer_sizes = to_vec_i32(&peer_sizes);
    let starts = starts.as_ref().map(to_vec_i32);
    let stops = stops.as_ref().map(to_vec_i32);
    let out = crate::slide_index_lgl(
        kind_of(kind)?,
        &values,
        &keys,
        &peer_sizes,
        starts.as_deref(),
        stops.as_deref(),
        complete,
        na_rm,
    );
    Ok(out.into_pyarray(py))
}

/// `peer_bounds(peer_sizes)` -> `(starts, stops)`, the C `fill_peer_info`.
#[pyfunction]
#[pyo3(name = "peer_bounds")]
fn peer_bounds_py<'py>(
    py: Python<'py>,
    peer_sizes: PyReadonlyArray1<'py, i32>,
) -> (Bound<'py, PyArray1<i32>>, Bound<'py, PyArray1<i32>>) {
    let (starts, stops) = crate::peer_bounds(&to_vec_i32(&peer_sizes));
    (starts.into_pyarray(py), stops.into_pyarray(py))
}

/// `compute_from(starts, first, n, before_unbounded)`, the `complete` trim.
#[pyfunction]
#[pyo3(name = "compute_from", signature = (starts, first, n, before_unbounded=false))]
fn compute_from_py(starts: PyReadonlyArray1<'_, i32>, first: i32, n: usize, before_unbounded: bool) -> i32 {
    crate::opts::compute_from(&to_vec_i32(&starts), first, n, before_unbounded)
}

/// `compute_to(stops, last, n, after_unbounded)`.
#[pyfunction]
#[pyo3(name = "compute_to", signature = (stops, last, n, after_unbounded=false))]
fn compute_to_py(stops: PyReadonlyArray1<'_, i32>, last: i32, n: usize, after_unbounded: bool) -> i32 {
    crate::opts::compute_to(&to_vec_i32(&stops), last, n, after_unbounded)
}

#[pymodule]
fn slider_kernels(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(slide_dbl_py, m)?)?;
    m.add_function(wrap_pyfunction!(slide_lgl_py, m)?)?;
    m.add_function(wrap_pyfunction!(slide_index_dbl_py, m)?)?;
    m.add_function(wrap_pyfunction!(slide_index_lgl_py, m)?)?;
    m.add_function(wrap_pyfunction!(peer_bounds_py, m)?)?;
    m.add_function(wrap_pyfunction!(compute_from_py, m)?)?;
    m.add_function(wrap_pyfunction!(compute_to_py, m)?)?;
    m.add("NA_LGL", crate::NA_LGL)?;
    Ok(())
}
