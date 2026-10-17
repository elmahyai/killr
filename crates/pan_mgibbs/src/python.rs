//! pyo3 entry point for the pan sampler kernels. Arrays cross as NumPy arrays
//! and keep their logical shapes; index arrays are 1-based, as in pan.f.

use std::sync::Mutex;

use numpy::ndarray::{ArrayD, IxDyn, ShapeBuilder};
use numpy::{PyArray, PyReadonlyArrayDyn};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyDict;

use crate::{mgibbs as run_mgibbs, mgibbsbd as run_mgibbsbd, nhyp_bd, nhyp_full, Chain, Problem, Rng, Start};

/// The Fortran SAVE state shared by `rngs`, `gauss`, and `gamm`.
static RNG: Mutex<Rng> = Mutex::new(Rng::new());

/// Logical shape and column-major values of a NumPy float array.
fn colmajor_f64(a: &PyReadonlyArrayDyn<'_, f64>) -> (Vec<usize>, Vec<f64>) {
    let view = a.as_array();
    let shape = view.shape().to_vec();
    let values = view.reversed_axes().iter().copied().collect();
    (shape, values)
}

/// Logical shape and column-major values of a NumPy integer array.
fn colmajor_i64(a: &PyReadonlyArrayDyn<'_, i64>) -> (Vec<usize>, Vec<i64>) {
    let view = a.as_array();
    let shape = view.shape().to_vec();
    let values = view.reversed_axes().iter().copied().collect();
    (shape, values)
}

fn index_vec(values: Vec<i64>, name: &str) -> PyResult<Vec<usize>> {
    values
        .into_iter()
        .map(|v| {
            usize::try_from(v).map_err(|_| PyValueError::new_err(format!("'{name}' must be non-negative")))
        })
        .collect()
}

/// Column-major NumPy array of the given logical shape.
fn to_numpy<'py>(py: Python<'py>, shape: &[usize], values: Vec<f64>) -> PyResult<Bound<'py, PyAny>> {
    let arr = ArrayD::from_shape_vec(IxDyn(shape).f(), values)
        .map_err(|e| PyRuntimeError::new_err(format!("bad output shape: {e}")))?;
    Ok(PyArray::from_owned_array(py, arr).into_any())
}

fn chain_dict<'py>(
    py: Python<'py>,
    chain: Chain,
    rq_shape: &[usize],
    iter: usize,
    p: usize,
    r: usize,
) -> PyResult<Bound<'py, PyDict>> {
    let out = PyDict::new(py);
    let mut iter_shape = rq_shape.to_vec();
    iter_shape.push(iter);
    let beta_shape = [p, r];
    let beta_iter_shape = [p, r, iter];
    let sigma_shape = [r, r];
    let sigma_iter_shape = [r, r, iter];
    let ntot_shape = [chain.y.len() / r, r];
    out.set_item("beta", to_numpy(py, &beta_shape, chain.beta)?)?;
    out.set_item("sigma", to_numpy(py, &sigma_shape, chain.sigma)?)?;
    out.set_item("psi", to_numpy(py, rq_shape, chain.psi)?)?;
    out.set_item("y", to_numpy(py, &ntot_shape, chain.y)?)?;
    out.set_item("betas", to_numpy(py, &beta_iter_shape, chain.betas)?)?;
    out.set_item("sigmas", to_numpy(py, &sigma_iter_shape, chain.sigmas)?)?;
    out.set_item("psis", to_numpy(py, &iter_shape, chain.psis)?)?;
    Ok(out)
}

/// `rngs(seed)`: seeds the Fortran generator as `pan` does before its sampler.
#[pyfunction]
#[pyo3(name = "rngs")]
fn rngs_py(seed: i32) {
    let mut rng = RNG.lock().unwrap_or_else(|e| e.into_inner());
    let _ = rng.rangen(seed);
}

/// Shared argument handling for `mgibbs` and `mgibbsbd`.
#[allow(clippy::too_many_arguments)]
fn build_problem(
    subj: &PyReadonlyArrayDyn<'_, i64>,
    pred: &PyReadonlyArrayDyn<'_, f64>,
    zcol: &PyReadonlyArrayDyn<'_, i64>,
    xcol: &PyReadonlyArrayDyn<'_, i64>,
    patt: &PyReadonlyArrayDyn<'_, i64>,
    rmat: &PyReadonlyArrayDyn<'_, i64>,
    iposn: &PyReadonlyArrayDyn<'_, i64>,
    pstfin: &PyReadonlyArrayDyn<'_, i64>,
    y: &PyReadonlyArrayDyn<'_, f64>,
    hyp: &PyReadonlyArrayDyn<'_, f64>,
    bd: bool,
) -> PyResult<(Problem, Vec<f64>)> {
    let (_, subj) = colmajor_i64(subj);
    let (pred_shape, pred) = colmajor_f64(pred);
    let (_, zcol) = colmajor_i64(zcol);
    let (_, xcol) = colmajor_i64(xcol);
    let (_, patt) = colmajor_i64(patt);
    let (rmat_shape, rmat) = colmajor_i64(rmat);
    let (_, iposn) = colmajor_i64(iposn);
    let (_, pstfin) = colmajor_i64(pstfin);
    let (y_shape, y_vals) = colmajor_f64(y);
    let (_, hyp) = colmajor_f64(hyp);

    if pred_shape.len() != 2 || y_shape.len() != 2 || rmat_shape.len() != 2 {
        return Err(PyValueError::new_err("pred, y and rmat must be 2-D"));
    }
    let r = y_shape[1];
    let npatt = rmat_shape[0];
    let pcol = pred_shape[1];
    let zcol = index_vec(zcol, "zcol")?;
    let xcol = index_vec(xcol, "xcol")?;
    let patt = index_vec(patt, "patt")?;
    let iposn = index_vec(iposn, "iposn")?;
    let pstfin = index_vec(pstfin, "pstfin")?;
    let ntot = subj.len();
    if y_shape[0] != ntot {
        return Err(PyValueError::new_err("y must have one row per subject row"));
    }
    let q = zcol.len();
    let nhyp = if bd { nhyp_bd(r, q) } else { nhyp_full(r, q) };
    if hyp.len() != nhyp {
        return Err(PyValueError::new_err(format!("hyp must have length {nhyp}")));
    }
    let problem = Problem::new(&subj, pred, pcol, xcol, zcol, patt, rmat, npatt, r, iposn, pstfin, hyp)
        .map_err(PyValueError::new_err)?;
    Ok((problem, y_vals))
}

/// Start values for `sflag == 1`: beta, sigma, psi and the starting eps.
#[allow(clippy::too_many_arguments)]
fn start_values(
    sflag: i64,
    beta: Option<PyReadonlyArrayDyn<'_, f64>>,
    sigma: Option<PyReadonlyArrayDyn<'_, f64>>,
    psi: Option<PyReadonlyArrayDyn<'_, f64>>,
    eps: Option<PyReadonlyArrayDyn<'_, f64>>,
) -> PyResult<Option<Start>> {
    match sflag {
        0 => Ok(None),
        1 => {
            let (Some(beta), Some(sigma), Some(psi), Some(eps)) = (beta, sigma, psi, eps) else {
                return Err(PyValueError::new_err("sflag=1 needs beta, sigma, psi and eps"));
            };
            Ok(Some(Start {
                beta: colmajor_f64(&beta).1,
                sigma: colmajor_f64(&sigma).1,
                psi: colmajor_f64(&psi).1,
                eps: colmajor_f64(&eps).1,
            }))
        }
        _ => Err(PyValueError::new_err("sflag must be 0 or 1")),
    }
}

/// `mgibbs(...)`: the conventional Gibbs sampler of pan, returning the chains
/// (`betas`, `sigmas`, `psis`) and the final imputed `y`.
#[pyfunction]
#[pyo3(name = "mgibbs")]
#[pyo3(signature = (subj, pred, zcol, xcol, patt, rmat, iposn, pstfin, y, hyp, iter, sflag=0, beta=None, sigma=None, psi=None, eps=None))]
#[allow(clippy::too_many_arguments)]
fn mgibbs_py<'py>(
    py: Python<'py>,
    subj: PyReadonlyArrayDyn<'py, i64>,
    pred: PyReadonlyArrayDyn<'py, f64>,
    zcol: PyReadonlyArrayDyn<'py, i64>,
    xcol: PyReadonlyArrayDyn<'py, i64>,
    patt: PyReadonlyArrayDyn<'py, i64>,
    rmat: PyReadonlyArrayDyn<'py, i64>,
    iposn: PyReadonlyArrayDyn<'py, i64>,
    pstfin: PyReadonlyArrayDyn<'py, i64>,
    y: PyReadonlyArrayDyn<'py, f64>,
    hyp: PyReadonlyArrayDyn<'py, f64>,
    iter: usize,
    sflag: i64,
    beta: Option<PyReadonlyArrayDyn<'py, f64>>,
    sigma: Option<PyReadonlyArrayDyn<'py, f64>>,
    psi: Option<PyReadonlyArrayDyn<'py, f64>>,
    eps: Option<PyReadonlyArrayDyn<'py, f64>>,
) -> PyResult<Bound<'py, PyDict>> {
    let (problem, y_vals) = build_problem(&subj, &pred, &zcol, &xcol, &patt, &rmat, &iposn, &pstfin, &y, &hyp, false)?;
    let start = start_values(sflag, beta, sigma, psi, eps)?;
    let (p, r, q) = (problem.p, problem.r, problem.q);
    let mut rng = RNG.lock().unwrap_or_else(|e| e.into_inner());
    let chain = run_mgibbs(&problem, &mut rng, &y_vals, start, iter);
    drop(rng);
    let rq = r * q;
    chain_dict(py, chain, &[rq, rq], iter, p, r)
}

/// `mgibbsbd(...)`: the block-diagonal Gibbs sampler of pan.bd.
#[pyfunction]
#[pyo3(name = "mgibbsbd")]
#[pyo3(signature = (subj, pred, zcol, xcol, patt, rmat, iposn, pstfin, y, hyp, iter, sflag=0, beta=None, sigma=None, psi=None, eps=None))]
#[allow(clippy::too_many_arguments)]
fn mgibbsbd_py<'py>(
    py: Python<'py>,
    subj: PyReadonlyArrayDyn<'py, i64>,
    pred: PyReadonlyArrayDyn<'py, f64>,
    zcol: PyReadonlyArrayDyn<'py, i64>,
    xcol: PyReadonlyArrayDyn<'py, i64>,
    patt: PyReadonlyArrayDyn<'py, i64>,
    rmat: PyReadonlyArrayDyn<'py, i64>,
    iposn: PyReadonlyArrayDyn<'py, i64>,
    pstfin: PyReadonlyArrayDyn<'py, i64>,
    y: PyReadonlyArrayDyn<'py, f64>,
    hyp: PyReadonlyArrayDyn<'py, f64>,
    iter: usize,
    sflag: i64,
    beta: Option<PyReadonlyArrayDyn<'py, f64>>,
    sigma: Option<PyReadonlyArrayDyn<'py, f64>>,
    psi: Option<PyReadonlyArrayDyn<'py, f64>>,
    eps: Option<PyReadonlyArrayDyn<'py, f64>>,
) -> PyResult<Bound<'py, PyDict>> {
    let (problem, y_vals) = build_problem(&subj, &pred, &zcol, &xcol, &patt, &rmat, &iposn, &pstfin, &y, &hyp, true)?;
    let start = start_values(sflag, beta, sigma, psi, eps)?;
    let (p, r, q) = (problem.p, problem.r, problem.q);
    let mut rng = RNG.lock().unwrap_or_else(|e| e.into_inner());
    let chain = run_mgibbsbd(&problem, &mut rng, &y_vals, start, iter);
    drop(rng);
    chain_dict(py, chain, &[q, q, r], iter, p, r)
}

#[pymodule]
#[pyo3(name = "pan_mgibbs")]
fn pan_mgibbs_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(rngs_py, m)?)?;
    m.add_function(wrap_pyfunction!(mgibbs_py, m)?)?;
    m.add_function(wrap_pyfunction!(mgibbsbd_py, m)?)?;
    Ok(())
}
