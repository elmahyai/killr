//! pyo3 binding for the deldir kernels. Module name: `deldir_engine`.
//!
//! Arrays are float64 numpy arrays (one dimension). Indices are int64.
//! Errors raise `RuntimeError` with the message the Fortran `rexit` printed.

use std::borrow::Cow;

use numpy::ndarray::Array2;
use numpy::{IntoPyArray, PyArray1, PyArray2, PyReadonlyArray1};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;

use crate::triangulation as tri;

/// Borrow a contiguous float64 array; copy only when it is strided.
fn as_cow<'a>(a: &'a PyReadonlyArray1<'_, f64>) -> Cow<'a, [f64]> {
    match a.as_slice() {
        Ok(s) => Cow::Borrowed(s),
        Err(_) => Cow::Owned(a.as_array().iter().copied().collect()),
    }
}

fn rw4(rw: &PyReadonlyArray1<'_, f64>) -> PyResult<[f64; 4]> {
    let v = as_cow(rw);
    if v.len() != 4 {
        return Err(PyValueError::new_err("rw must have four values"));
    }
    Ok([v[0], v[1], v[2], v[3]])
}

fn rows_to_array2<'py, const C: usize>(
    py: Python<'py>,
    rows: Vec<[f64; C]>,
) -> PyResult<Bound<'py, PyArray2<f64>>> {
    let r = rows.len();
    let flat: Vec<f64> = rows.into_iter().flatten().collect();
    let arr = Array2::from_shape_vec((r, C), flat)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    Ok(PyArray2::from_owned_array(py, arr))
}

/// `binsrt(x, y, rw)` -> `(tx, ty, ind, rind)`. `ind` and `rind` are 1-based.
#[pyfunction]
fn binsrt<'py>(
    py: Python<'py>,
    x: PyReadonlyArray1<'py, f64>,
    y: PyReadonlyArray1<'py, f64>,
    rw: PyReadonlyArray1<'py, f64>,
) -> PyResult<(
    Bound<'py, PyArray1<f64>>,
    Bound<'py, PyArray1<f64>>,
    Bound<'py, PyArray1<i64>>,
    Bound<'py, PyArray1<i64>>,
)> {
    let out = tri::binsrt(&as_cow(&x), &as_cow(&y), rw4(&rw)?)
        .map_err(PyRuntimeError::new_err)?;
    Ok((
        out.tx.into_pyarray(py),
        out.ty.into_pyarray(py),
        out.ind.into_pyarray(py),
        out.rind.into_pyarray(py),
    ))
}

/// `master(x, y, rw, eps)` with bin-sorted, unpadded `x` and `y`.
///
/// Returns `(delsgs, delsum, dirsgs, dirsum)`:
///   * `delsgs`: (ndel, 6), columns `x1, y1, x2, y2, ind1, ind2`.
///   * `delsum`: (n, 4), columns `x, y, n.tri, del.area`.
///   * `dirsgs`: (ndir, 10), columns `x1, y1, x2, y2, ind1, ind2, bp1, bp2, thirdv1, thirdv2`.
///   * `dirsum`: (n, 3), columns `n.tside, nbpt, dir.area`.
#[pyfunction]
fn master<'py>(
    py: Python<'py>,
    x: PyReadonlyArray1<'py, f64>,
    y: PyReadonlyArray1<'py, f64>,
    rw: PyReadonlyArray1<'py, f64>,
    eps: f64,
) -> PyResult<(
    Bound<'py, PyArray2<f64>>,
    Bound<'py, PyArray2<f64>>,
    Bound<'py, PyArray2<f64>>,
    Bound<'py, PyArray2<f64>>,
)> {
    let out = tri::master(&as_cow(&x), &as_cow(&y), rw4(&rw)?, eps)
        .map_err(PyRuntimeError::new_err)?;
    Ok((
        rows_to_array2(py, out.delsgs)?,
        rows_to_array2(py, out.delsum)?,
        rows_to_array2(py, out.dirsgs)?,
        rows_to_array2(py, out.dirsum)?,
    ))
}

/// `intri(x3, y3, u, v)` -> `okay` (0 or 1). `x3`, `y3` are the three
/// triangle vertices; `u`, `v` are all the points.
#[pyfunction]
fn intri(
    x3: PyReadonlyArray1<'_, f64>,
    y3: PyReadonlyArray1<'_, f64>,
    u: PyReadonlyArray1<'_, f64>,
    v: PyReadonlyArray1<'_, f64>,
) -> PyResult<i32> {
    let xa = as_cow(&x3);
    let ya = as_cow(&y3);
    if xa.len() != 3 || ya.len() != 3 {
        return Err(PyValueError::new_err("x3 and y3 must have three values"));
    }
    tri::intri(
        [xa[0], xa[1], xa[2]],
        [ya[0], ya[1], ya[2]],
        &as_cow(&u),
        &as_cow(&v),
    )
    .map_err(PyRuntimeError::new_err)
}

#[pymodule]
#[pyo3(name = "deldir_engine")]
fn deldir_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(binsrt, m)?)?;
    m.add_function(wrap_pyfunction!(master, m)?)?;
    m.add_function(wrap_pyfunction!(intri, m)?)?;
    Ok(())
}
