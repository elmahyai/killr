//! pyo3 entry points for the quantreg kernels. Matrices cross as NumPy arrays in
//! their logical shapes. Indices and counters are returned as integer arrays.
//! The R random stream crosses as its 624 state words and its position, and
//! the call returns the advanced state, so the caller can store it back.

use numpy::ndarray::{Array1, Array2};
use numpy::{PyArray, PyArray1, PyArray2, PyReadonlyArray1, PyReadonlyArray2};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use crate::{bootnp as run_bootnp, pfnb as run_pfnb, pwxy as run_pwxy, rqfnb as run_rqfnb, Rng};

/// Row-major values of a 2-D NumPy array, whatever its memory layout.
fn rows_of(a: &PyReadonlyArray2<'_, f64>) -> (usize, usize, Vec<f64>) {
    let view = a.as_array();
    let (r, c) = view.dim();
    (r, c, view.iter().copied().collect())
}

fn vec_of(a: &PyReadonlyArray1<'_, f64>) -> Vec<f64> {
    a.as_array().iter().copied().collect()
}

fn rng_from(mt: Vec<u32>, mti: usize) -> PyResult<Rng> {
    Rng::from_state(&mt, mti).map_err(PyValueError::new_err)
}

fn check(cond: bool, msg: &str) -> PyResult<()> {
    if cond {
        Ok(())
    } else {
        Err(PyValueError::new_err(msg.to_string()))
    }
}

/// `rqfnb(a, c, rhs, u, x0, beta, eps)`: one Frisch-Newton dual solve.
/// Returns `(y, nit, info)`, where `y` is the dual and the coefficient is `-y`.
#[pyfunction]
#[pyo3(name = "rqfnb")]
fn rqfnb_py<'py>(
    py: Python<'py>,
    a: PyReadonlyArray2<'py, f64>,
    c: PyReadonlyArray1<'py, f64>,
    rhs: PyReadonlyArray1<'py, f64>,
    u: PyReadonlyArray1<'py, f64>,
    x0: PyReadonlyArray1<'py, f64>,
    beta: f64,
    eps: f64,
) -> PyResult<(Bound<'py, PyArray1<f64>>, Bound<'py, PyArray1<i32>>, i32)> {
    let (n, p, a) = rows_of(&a);
    let c = vec_of(&c);
    let rhs = vec_of(&rhs);
    let u = vec_of(&u);
    let x0 = vec_of(&x0);
    check(c.len() == n && u.len() == n && x0.len() == n, "c, u and x0 must have one entry per row of a")?;
    check(rhs.len() == p, "rhs must have one entry per column of a")?;
    let out = run_rqfnb(n, p, &a, &c, &rhs, &u, &x0, beta, eps);
    Ok((
        PyArray1::from_owned_array(py, Array1::from(out.y)),
        PyArray1::from_owned_array(py, Array1::from(out.nit.to_vec())),
        out.info,
    ))
}

/// `pfnb(a, y, tau, r, band, m0)`: the preprocessed Frisch-Newton fit for each tau.
/// Returns `(b, nit, info)` with `b` of shape p x m (the duals) and `nit` of shape 5 x m.
#[pyfunction]
#[pyo3(name = "pfnb")]
fn pfnb_py<'py>(
    py: Python<'py>,
    a: PyReadonlyArray2<'py, f64>,
    y: PyReadonlyArray1<'py, f64>,
    tau: PyReadonlyArray1<'py, f64>,
    r: PyReadonlyArray1<'py, f64>,
    band: PyReadonlyArray1<'py, f64>,
    m0: usize,
) -> PyResult<(Bound<'py, PyArray2<f64>>, Bound<'py, PyArray2<i32>>, i32)> {
    let (n, p, a) = rows_of(&a);
    let y = vec_of(&y);
    let tau = vec_of(&tau);
    let r = vec_of(&r);
    let band = vec_of(&band);
    check(y.len() == n && r.len() == n && band.len() == n, "y, r and band must have one entry per row of a")?;
    check(!tau.is_empty(), "tau must not be empty")?;
    let m = tau.len();
    let out = run_pfnb(n, p, &a, &y, &tau, &r, &band, m0);
    let b = Array2::from_shape_fn((p, m), |(k, iq)| out.b[iq * p + k]);
    let nit = Array2::from_shape_fn((5, m), |(s, iq)| out.nit[iq * 5 + s]);
    Ok((
        PyArray::from_owned_array(py, b),
        PyArray::from_owned_array(py, nit),
        out.info,
    ))
}

/// `pwxy(a, y, tau, r, m0, reps, mt, mti)`: the preprocessed pairs bootstrap.
/// `a`, `y` and `r` are already sorted by the scaled residual. Returns
/// `(b, nit, info, mt, mti)`, with `b` of shape p x reps, `nit` of shape 5 x reps,
/// and the advanced R generator state.
#[pyfunction]
#[pyo3(name = "pwxy")]
fn pwxy_py<'py>(
    py: Python<'py>,
    a: PyReadonlyArray2<'py, f64>,
    y: PyReadonlyArray1<'py, f64>,
    tau: f64,
    r: PyReadonlyArray1<'py, f64>,
    m0: usize,
    reps: usize,
    mt: Vec<u32>,
    mti: usize,
) -> PyResult<(Bound<'py, PyArray2<f64>>, Bound<'py, PyArray2<i32>>, Bound<'py, PyArray1<i32>>, Vec<u32>, usize)> {
    let (n, p, a) = rows_of(&a);
    let y = vec_of(&y);
    let r = vec_of(&r);
    check(y.len() == n && r.len() == n, "y and r must have one entry per row of a")?;
    let mut rng = rng_from(mt, mti)?;
    let out = run_pwxy(n, p, &a, &y, tau, &r, reps, m0, &mut rng);
    let (mt, mti) = rng.state();
    let b = Array2::from_shape_fn((p, reps), |(k, ir)| out.b[ir * p + k]);
    let nit = Array2::from_shape_fn((5, reps), |(s, ir)| out.nit[ir * 5 + s]);
    Ok((
        PyArray::from_owned_array(py, b),
        PyArray::from_owned_array(py, nit),
        PyArray1::from_owned_array(py, Array1::from(out.info)),
        mt,
        mti,
    ))
}

/// `bootnp(x, y, tau, theta_tilde, zstar, sumxij, sumabsxij, reps, mt, mti)`: the
/// Markov chain marginal bootstrap. `x` is the transformed n x p design, and
/// `zstar` is ZTilda in column-major order as a flat array. Returns
/// `(theta, mt, mti)`, with `theta` of shape p x (reps + 1), first column `theta_tilde`.
#[pyfunction]
#[pyo3(name = "bootnp")]
fn bootnp_py<'py>(
    py: Python<'py>,
    x: PyReadonlyArray2<'py, f64>,
    y: PyReadonlyArray1<'py, f64>,
    tau: f64,
    theta_tilde: PyReadonlyArray1<'py, f64>,
    zstar: PyReadonlyArray1<'py, f64>,
    sumxij: PyReadonlyArray1<'py, f64>,
    sumabsxij: PyReadonlyArray1<'py, f64>,
    reps: usize,
    mt: Vec<u32>,
    mti: usize,
) -> PyResult<(Bound<'py, PyArray2<f64>>, Vec<u32>, usize)> {
    let (n, p, x) = rows_of(&x);
    let y = vec_of(&y);
    let theta_tilde = vec_of(&theta_tilde);
    let zstar = vec_of(&zstar);
    let sumxij = vec_of(&sumxij);
    let sumabsxij = vec_of(&sumabsxij);
    check(y.len() == n && zstar.len() == n * p, "y needs n entries and zstar n * p entries")?;
    check(theta_tilde.len() == p && sumxij.len() == p && sumabsxij.len() == p, "theta_tilde, sumxij and sumabsxij need p entries")?;
    let mut rng = rng_from(mt, mti)?;
    let theta = run_bootnp(n, p, &x, &y, tau, &theta_tilde, &zstar, &sumxij, &sumabsxij, reps, &mut rng)
        .map_err(PyValueError::new_err)?;
    let (mt, mti) = rng.state();
    let out = Array2::from_shape_fn((p, reps + 1), |(k, c)| theta[c * p + k]);
    Ok((PyArray::from_owned_array(py, out), mt, mti))
}

/// `sfn(n, m, indptr, indices, data, rhs, x, s, y, z, w, small, tiny, large, maxit)`:
/// the sparse Frisch-Newton loop `srqfn` on the CSR design (n x m, int64 indices).
/// Returns `(y, it, ierr)`, with `y` the dual of length m.
#[pyfunction]
#[pyo3(name = "sfn")]
fn sfn_py<'py>(
    py: Python<'py>,
    n: usize,
    m: usize,
    indptr: PyReadonlyArray1<'py, i64>,
    indices: PyReadonlyArray1<'py, i64>,
    data: PyReadonlyArray1<'py, f64>,
    rhs: PyReadonlyArray1<'py, f64>,
    x: PyReadonlyArray1<'py, f64>,
    s: PyReadonlyArray1<'py, f64>,
    y: PyReadonlyArray1<'py, f64>,
    z: PyReadonlyArray1<'py, f64>,
    w: PyReadonlyArray1<'py, f64>,
    small: f64,
    tiny: f64,
    large: f64,
    maxit: usize,
) -> PyResult<(Bound<'py, PyArray1<f64>>, usize, i32)> {
    let indptr: Vec<usize> = indptr.as_array().iter().map(|&v| v as usize).collect();
    let indices: Vec<usize> = indices.as_array().iter().map(|&v| v as usize).collect();
    let data = vec_of(&data);
    check(indptr.len() == n + 1, "indptr needs n + 1 entries")?;
    check(indices.len() == data.len() && indptr[n] == data.len(), "indices and data do not match indptr")?;
    check(indices.iter().all(|&j| j < m), "a column index is outside m")?;
    let rhs = vec_of(&rhs);
    let (x, s, y0, z, w) = (vec_of(&x), vec_of(&s), vec_of(&y), vec_of(&z), vec_of(&w));
    check(rhs.len() == m && y0.len() == m, "rhs and y need m entries")?;
    check(x.len() == n && s.len() == n && z.len() == n && w.len() == n, "x, s, z and w need n entries")?;
    let a = crate::sfn::Csr { n, m, indptr: &indptr, indices: &indices, data: &data };
    let out = crate::sfn::srqfn(&a, &rhs, &x, &s, &y0, &z, &w, small, tiny, large, maxit);
    Ok((PyArray1::from_owned_array(py, Array1::from(out.y)), out.it, out.ierr))
}

#[pymodule]
#[pyo3(name = "quantreg_kernel")]
fn quantreg_kernel_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(rqfnb_py, m)?)?;
    m.add_function(wrap_pyfunction!(pfnb_py, m)?)?;
    m.add_function(wrap_pyfunction!(pwxy_py, m)?)?;
    m.add_function(wrap_pyfunction!(bootnp_py, m)?)?;
    m.add_function(wrap_pyfunction!(sfn_py, m)?)?;
    Ok(())
}
