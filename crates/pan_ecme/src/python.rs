//! pyo3 entry points. Arrays cross as NumPy arrays and keep their logical shapes. Index
//! arrays are 1-based, as in pan.f, and subjects are run numbers (see the crate docs).

use numpy::ndarray::{ArrayD, IxDyn, ShapeBuilder};
use numpy::{Element, PyArray, PyReadonlyArray1, PyReadonlyArray2, PyReadonlyArrayDyn};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyDict;

use crate::{
    bdiag as bdiag_kernel, ecme3 as ecme3_kernel, nmax_of, nopsi as nopsi_kernel,
    prelim as prelim_kernel, runs, Start,
};

/// Logical shape and column-major values of a NumPy 2-D array.
fn colmajor2<T: Element + Copy>(a: &PyReadonlyArray2<'_, T>) -> (usize, usize, Vec<T>) {
    let view = a.as_array();
    let (rows, cols) = view.dim();
    (rows, cols, view.reversed_axes().iter().copied().collect())
}

/// Column-major values of a NumPy array of any rank.
fn colmajor_dyn(a: &PyReadonlyArrayDyn<'_, f64>) -> (Vec<usize>, Vec<f64>) {
    let view = a.as_array();
    let shape = view.shape().to_vec();
    (shape, view.reversed_axes().iter().copied().collect())
}

fn vec1<T: Element + Copy>(a: &PyReadonlyArray1<'_, T>) -> Vec<T> {
    a.as_array().iter().copied().collect()
}

/// A NumPy array of the given logical shape, filled with column-major values.
fn to_numpy<'py, T: Element>(
    py: Python<'py>,
    shape: &[usize],
    mut values: Vec<T>,
) -> PyResult<Bound<'py, PyAny>> {
    values.truncate(shape.iter().product());
    let arr = ArrayD::from_shape_vec(IxDyn(shape).f(), values)
        .map_err(|e| PyValueError::new_err(format!("bad output shape: {e}")))?;
    Ok(PyArray::from_owned_array(py, arr).into_any())
}

/// Checks the shared inputs: one row per observation, occasions from 1, and 1-based
/// columns of pred, so the Fortran never reads outside an array.
fn check_design(subj: &[i32], occ: &[i32], rows: usize, pcol: usize, cols: &[i32], name: &str) -> PyResult<()> {
    if subj.len() != rows {
        return Err(PyValueError::new_err("pred must have one row per subject value"));
    }
    if occ.len() != rows {
        return Err(PyValueError::new_err("occ must have one value per row"));
    }
    if occ.iter().any(|&o| o < 1) {
        return Err(PyValueError::new_err("occ must hold 1-based occasions"));
    }
    if cols.iter().any(|&c| c < 1 || c as usize > pcol) {
        return Err(PyValueError::new_err(format!("{name} must be 1-based columns of pred")));
    }
    Ok(())
}

fn check_y(y: &[f64], rows: usize) -> PyResult<()> {
    if y.len() != rows {
        return Err(PyValueError::new_err("y must have one value per row"));
    }
    Ok(())
}

/// vmax, which must be nmax x nmax for the largest occasion nmax.
fn read_vmax(vmax: Option<PyReadonlyArray2<'_, f64>>, occ: &[i32]) -> PyResult<Option<Vec<f64>>> {
    let nmax = nmax_of(occ);
    match vmax {
        None => Ok(None),
        Some(v) => {
            let (rows, cols, vals) = colmajor2(&v);
            if rows != nmax || cols != nmax {
                return Err(PyValueError::new_err(format!("vmax must be {nmax} x {nmax}")));
            }
            Ok(Some(vals))
        }
    }
}

/// `prelim(subj, occ, pred, zcol, vmax=None)`: istfin, and the V_i factors of prelim.
#[pyfunction]
#[pyo3(name = "prelim")]
#[pyo3(signature = (subj, occ, pred, zcol, vmax=None))]
fn prelim_py<'py>(
    py: Python<'py>,
    subj: PyReadonlyArray1<'py, i32>,
    occ: PyReadonlyArray1<'py, i32>,
    pred: PyReadonlyArray2<'py, f64>,
    zcol: PyReadonlyArray1<'py, i32>,
    vmax: Option<PyReadonlyArray2<'py, f64>>,
) -> PyResult<Bound<'py, PyDict>> {
    let subj = vec1(&subj);
    let occ = vec1(&occ);
    let (rows, pcol, pred) = colmajor2(&pred);
    let zcol = vec1(&zcol);
    check_design(&subj, &occ, rows, pcol, &zcol, "zcol")?;
    let vmax = read_vmax(vmax, &occ)?;
    let pre = prelim_kernel(&subj, &occ, &pred, pcol, &zcol, vmax.as_deref());
    let (m, nmax, q) = (pre.m, pre.nmax, pre.q);

    let out = PyDict::new(py);
    out.set_item("ist", to_numpy(py, &[m], pre.ist)?)?;
    out.set_item("ifin", to_numpy(py, &[m], pre.ifin)?)?;
    out.set_item("vh", to_numpy(py, &[nmax, nmax, m], pre.vh)?)?;
    out.set_item("vi", to_numpy(py, &[nmax, nmax, m], pre.vi)?)?;
    out.set_item("ztv", to_numpy(py, &[q, nmax, m], pre.ztv)?)?;
    out.set_item("sig0", to_numpy(py, &[q, q, m], pre.sig0)?)?;
    Ok(out)
}

/// `nopsi(subj, occ, pred, xcol, y, vmax=None)`: the GLS branch of ecme() with psi = 0.
#[pyfunction]
#[pyo3(name = "nopsi")]
#[pyo3(signature = (subj, occ, pred, xcol, y, vmax=None))]
fn nopsi_py<'py>(
    py: Python<'py>,
    subj: PyReadonlyArray1<'py, i32>,
    occ: PyReadonlyArray1<'py, i32>,
    pred: PyReadonlyArray2<'py, f64>,
    xcol: PyReadonlyArray1<'py, i32>,
    y: PyReadonlyArray1<'py, f64>,
    vmax: Option<PyReadonlyArray2<'py, f64>>,
) -> PyResult<Bound<'py, PyDict>> {
    let subj = vec1(&subj);
    let occ = vec1(&occ);
    let (rows, pcol, pred) = colmajor2(&pred);
    let xcol = vec1(&xcol);
    let y = vec1(&y);
    check_design(&subj, &occ, rows, pcol, &xcol, "xcol")?;
    check_y(&y, rows)?;
    let vmax = read_vmax(vmax, &occ)?;
    let out = nopsi_kernel(&subj, &occ, &pred, pcol, &xcol, &y, vmax.as_deref());
    let p = xcol.len();

    let dict = PyDict::new(py);
    dict.set_item("beta", to_numpy(py, &[p], out.beta)?)?;
    dict.set_item("sigma2", out.sigma2)?;
    dict.set_item("delta", to_numpy(py, &[rows], out.delta)?)?;
    dict.set_item("xtwxinv", to_numpy(py, &[p, p], out.xtwxinv)?)?;
    dict.set_item("ll", out.ll)?;
    Ok(dict)
}

/// `ecme3(subj, occ, pred, xcol, zcol, y, vmax=None, beta=None, sigma2=None, psi=None,
/// eps=1e-4, maxits=1000)`: the ECME loop. Give beta, sigma2 and psi together or not at all.
#[pyfunction]
#[pyo3(name = "ecme3")]
#[pyo3(signature = (subj, occ, pred, xcol, zcol, y, vmax=None, beta=None, sigma2=None, psi=None, eps=0.0001, maxits=1000))]
#[allow(clippy::too_many_arguments)]
fn ecme3_py<'py>(
    py: Python<'py>,
    subj: PyReadonlyArray1<'py, i32>,
    occ: PyReadonlyArray1<'py, i32>,
    pred: PyReadonlyArray2<'py, f64>,
    xcol: PyReadonlyArray1<'py, i32>,
    zcol: PyReadonlyArray1<'py, i32>,
    y: PyReadonlyArray1<'py, f64>,
    vmax: Option<PyReadonlyArray2<'py, f64>>,
    beta: Option<PyReadonlyArray1<'py, f64>>,
    sigma2: Option<f64>,
    psi: Option<PyReadonlyArray2<'py, f64>>,
    eps: f64,
    maxits: usize,
) -> PyResult<Bound<'py, PyDict>> {
    let subj = vec1(&subj);
    let occ = vec1(&occ);
    let (rows, pcol, pred) = colmajor2(&pred);
    let xcol = vec1(&xcol);
    let zcol = vec1(&zcol);
    let y = vec1(&y);
    check_design(&subj, &occ, rows, pcol, &xcol, "xcol")?;
    check_design(&subj, &occ, rows, pcol, &zcol, "zcol")?;
    check_y(&y, rows)?;
    if zcol.is_empty() {
        return Err(PyValueError::new_err("ecme3 needs at least one zcol column"));
    }
    let vmax = read_vmax(vmax, &occ)?;

    let (p, q) = (xcol.len(), zcol.len());
    let start = match (beta, sigma2, psi) {
        (None, None, None) => None,
        (Some(beta), Some(sigma2), Some(psi)) => {
            let beta = vec1(&beta);
            let (psi_rows, psi_cols, psi) = colmajor2(&psi);
            if beta.len() != p || psi_rows != q || psi_cols != q {
                return Err(PyValueError::new_err("start needs beta of length p and psi of q x q"));
            }
            Some(Start { beta, sigma2, psi })
        }
        _ => return Err(PyValueError::new_err("give beta, sigma2 and psi together or not at all")),
    };

    let out = ecme3_kernel(
        &subj,
        &occ,
        &pred,
        pcol,
        &xcol,
        &zcol,
        &y,
        vmax.as_deref(),
        start.as_ref(),
        eps,
        maxits,
    );
    let m = runs(&subj);

    let dict = PyDict::new(py);
    dict.set_item("beta", to_numpy(py, &[p], out.beta)?)?;
    dict.set_item("sigma2", out.sigma2)?;
    dict.set_item("psi", to_numpy(py, &[q, q], out.psi)?)?;
    dict.set_item("llk", to_numpy(py, &[out.iter], out.llk)?)?;
    dict.set_item("iter", out.iter)?;
    dict.set_item("converged", out.converged)?;
    dict.set_item("b", to_numpy(py, &[q, m], out.b)?)?;
    dict.set_item("sig", to_numpy(py, &[q, q, m], out.sig)?)?;
    dict.set_item("xtwxinv", to_numpy(py, &[p, p], out.xtwxinv)?)?;
    Ok(dict)
}

/// `bdiag(sig)`: sig is q x q x m; the lower triangle of each layer is filled from the upper.
#[pyfunction]
#[pyo3(name = "bdiag")]
#[pyo3(signature = (sig))]
fn bdiag_py<'py>(py: Python<'py>, sig: PyReadonlyArrayDyn<'py, f64>) -> PyResult<Bound<'py, PyAny>> {
    let (shape, mut vals) = colmajor_dyn(&sig);
    if shape.len() != 3 || shape[0] != shape[1] {
        return Err(PyValueError::new_err("sig must be q x q x m"));
    }
    let (q, m) = (shape[0], shape[2]);
    bdiag_kernel(q, m, &mut vals);
    to_numpy(py, &shape, vals)
}

#[pymodule]
#[pyo3(name = "pan_ecme")]
fn pan_ecme_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(prelim_py, m)?)?;
    m.add_function(wrap_pyfunction!(nopsi_py, m)?)?;
    m.add_function(wrap_pyfunction!(ecme3_py, m)?)?;
    m.add_function(wrap_pyfunction!(bdiag_py, m)?)?;
    Ok(())
}
