//! pyo3 bindings. Each column is passed as `(kind, array)` with kind one of
//! `"lgl"`, `"int"`, `"dbl"`, `"str"`. Logical, integer and factor columns
//! are int32 arrays with `NA` = `-2147483648`. Double columns are float64
//! (NaN = NA). Character columns are object arrays of `str` / `None`.

use std::ffi::CString;

use numpy::ndarray::Array2;
use numpy::{Element, IntoPyArray, PyArray1, PyArray2, PyReadonlyArray1};
use pyo3::exceptions::{PyUserWarning, PyValueError};
use pyo3::prelude::*;

use crate::kernel::{self, Col, KernelError, Params};

enum OwnedCol<'py> {
    Lgl(PyReadonlyArray1<'py, i32>),
    Int(PyReadonlyArray1<'py, i32>),
    Dbl(PyReadonlyArray1<'py, f64>),
    Str(Vec<Option<String>>),
}

fn to_py(e: KernelError) -> PyErr {
    PyValueError::new_err(e.0)
}

fn slice_of<'a, T: Element>(a: &'a PyReadonlyArray1<'_, T>) -> PyResult<&'a [T]> {
    a.as_slice()
        .map_err(|e| PyValueError::new_err(format!("array must be contiguous: {e}")))
}

fn extract_col<'py>(item: &Bound<'py, PyAny>) -> PyResult<OwnedCol<'py>> {
    let (kind, arr): (String, Bound<'py, PyAny>) = item.extract()?;
    Ok(match kind.as_str() {
        "lgl" => OwnedCol::Lgl(arr.extract()?),
        "int" => OwnedCol::Int(arr.extract()?),
        "dbl" => OwnedCol::Dbl(arr.extract()?),
        "str" => OwnedCol::Str(arr.extract()?),
        other => {
            return Err(PyValueError::new_err(format!(
                "unknown column kind {other:?}; expected 'lgl', 'int', 'dbl' or 'str'"
            )))
        }
    })
}

fn extract_cols<'py>(seq: &Bound<'py, PyAny>) -> PyResult<Vec<OwnedCol<'py>>> {
    seq.try_iter()?
        .map(|item| extract_col(&item?))
        .collect()
}

fn views<'a>(cols: &'a [OwnedCol<'_>]) -> PyResult<Vec<Col<'a>>> {
    cols.iter()
        .map(|c| {
            Ok(match c {
                OwnedCol::Lgl(a) => Col::Lgl(slice_of(a)?),
                OwnedCol::Int(a) => Col::Int(slice_of(a)?),
                OwnedCol::Dbl(a) => Col::Dbl(slice_of(a)?),
                OwnedCol::Str(v) => Col::Str(v.as_slice()),
            })
        })
        .collect()
}

fn emit_warnings(py: Python<'_>, msgs: &[&'static str]) -> PyResult<()> {
    let mut seen: Vec<&str> = Vec::new();
    for m in msgs {
        if seen.contains(m) {
            continue;
        }
        seen.push(m);
        let c = CString::new(*m).map_err(|e| PyValueError::new_err(e.to_string()))?;
        let category = py.get_type::<PyUserWarning>();
        PyErr::warn(py, category.as_any(), &c, 1)?;
    }
    Ok(())
}

/// Range of one column pair, as `R_get_xy_range`.
#[pyfunction]
fn xy_range<'py>(x: Bound<'py, PyAny>, y: Bound<'py, PyAny>) -> PyResult<f64> {
    let xo = extract_col(&x)?;
    let yo = extract_col(&y)?;
    let xv = views(std::slice::from_ref(&xo))?;
    let yv = views(std::slice::from_ref(&yo))?;
    Ok(kernel::xy_range(xv[0], yv[0]))
}

/// Gower's distance for every record: `R_gower`.
#[pyfunction]
#[pyo3(signature = (x, y, ranges, pair, factor_pair, eps, weights, nthread=1))]
fn gower_dist<'py>(
    py: Python<'py>,
    x: Bound<'py, PyAny>,
    y: Bound<'py, PyAny>,
    ranges: PyReadonlyArray1<'py, f64>,
    pair: PyReadonlyArray1<'py, i64>,
    factor_pair: PyReadonlyArray1<'py, i32>,
    eps: f64,
    weights: PyReadonlyArray1<'py, f64>,
    nthread: usize,
) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let xo = extract_cols(&x)?;
    let yo = extract_cols(&y)?;
    let xv = views(&xo)?;
    let yv = views(&yo)?;
    let params = Params {
        ranges: slice_of(&ranges)?,
        pair: slice_of(&pair)?,
        factor_pair: slice_of(&factor_pair)?,
        eps,
        weights: slice_of(&weights)?,
    };
    let pool = kernel::make_pool(nthread).map_err(to_py)?;
    let (out, warns) = kernel::gower_dist(&xv, &yv, &params, pool.as_ref()).map_err(to_py)?;
    emit_warnings(py, &warns)?;
    Ok(out.into_pyarray(py))
}

/// Top-n matches of each record in `x` among `y`: `R_gower_topn`.
///
/// Returns `(index, distance)`, both shaped `(n, nrow(x))`. `index` is 1-based,
/// as in R. Unfilled slots (when `n > nrow(y)`) are 0 and +Inf.
#[pyfunction]
#[pyo3(signature = (x, y, ranges, pair, factor_pair, n, eps, weights, nthread=1))]
fn gower_topn<'py>(
    py: Python<'py>,
    x: Bound<'py, PyAny>,
    y: Bound<'py, PyAny>,
    ranges: PyReadonlyArray1<'py, f64>,
    pair: PyReadonlyArray1<'py, i64>,
    factor_pair: PyReadonlyArray1<'py, i32>,
    n: usize,
    eps: f64,
    weights: PyReadonlyArray1<'py, f64>,
    nthread: usize,
) -> PyResult<(Bound<'py, PyArray2<i32>>, Bound<'py, PyArray2<f64>>)> {
    let xo = extract_cols(&x)?;
    let yo = extract_cols(&y)?;
    let xv = views(&xo)?;
    let yv = views(&yo)?;
    let nrowx = xv.first().map_or(0, |c| c.len());
    let params = Params {
        ranges: slice_of(&ranges)?,
        pair: slice_of(&pair)?,
        factor_pair: slice_of(&factor_pair)?,
        eps,
        weights: slice_of(&weights)?,
    };
    let pool = kernel::make_pool(nthread).map_err(to_py)?;
    let (flat_index, flat_value, warns) =
        kernel::gower_topn(&xv, &yv, &params, n, pool.as_ref()).map_err(to_py)?;
    emit_warnings(py, &warns)?;

    // The kernel stores record i, slot t at i*n + t. Return C-order (n, nrowx).
    let mut index = vec![0i32; n * nrowx];
    let mut value = vec![0.0f64; n * nrowx];
    for i in 0..nrowx {
        for t in 0..n {
            index[t * nrowx + i] = flat_index[i * n + t];
            value[t * nrowx + i] = flat_value[i * n + t];
        }
    }
    let index = Array2::from_shape_vec((n, nrowx), index)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    let value = Array2::from_shape_vec((n, nrowx), value)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    Ok((index.into_pyarray(py), value.into_pyarray(py)))
}

#[pymodule]
fn gower_kernel(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(xy_range, m)?)?;
    m.add_function(wrap_pyfunction!(gower_dist, m)?)?;
    m.add_function(wrap_pyfunction!(gower_topn, m)?)?;
    Ok(())
}
