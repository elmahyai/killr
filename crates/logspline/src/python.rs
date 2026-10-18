//! pyo3 binding of the logspline kernels. Each function takes the same
//! arguments as the R `.C` call, in the same order, and returns a dict with
//! the arguments the C routine may change (named as in the R wrapper). Vectors
//! are padded the same way the R wrapper pads them.

use numpy::{IntoPyArray, PyReadonlyArray1};
use pyo3::prelude::*;
use pyo3::types::PyDict;

use crate::lsdall::Lsd;
use crate::nlsd;

fn to_f64(a: &PyReadonlyArray1<'_, f64>) -> Vec<f64> {
    a.as_array().iter().copied().collect()
}

fn to_i32(a: &PyReadonlyArray1<'_, i32>) -> Vec<i32> {
    a.as_array().iter().copied().collect()
}

/// `.C("logcensor", ...)`: the oldlogspline fit. Returns the 13 `.C` arguments.
#[pyfunction]
#[pyo3(signature = (delete, iautoknot, sample, nsample, bd, sorc, nk, kt, cf, penalty, wk, wk2, logl))]
#[allow(clippy::too_many_arguments)]
fn logcensor<'py>(
    py: Python<'py>,
    delete: PyReadonlyArray1<'py, i32>,
    iautoknot: PyReadonlyArray1<'py, i32>,
    sample: PyReadonlyArray1<'py, f64>,
    nsample: PyReadonlyArray1<'py, i32>,
    bd: PyReadonlyArray1<'py, f64>,
    sorc: PyReadonlyArray1<'py, i32>,
    nk: i32,
    kt: PyReadonlyArray1<'py, f64>,
    cf: PyReadonlyArray1<'py, f64>,
    penalty: PyReadonlyArray1<'py, f64>,
    wk: PyReadonlyArray1<'py, f64>,
    wk2: PyReadonlyArray1<'py, f64>,
    logl: PyReadonlyArray1<'py, f64>,
) -> PyResult<Bound<'py, PyDict>> {
    let mut sample = to_f64(&sample);
    let mut nsample = to_i32(&nsample);
    let mut bd = to_f64(&bd);
    let mut sorc = to_i32(&sorc);
    let mut nk = nk;
    let mut kt = to_f64(&kt);
    let mut cf = to_f64(&cf);
    let mut wk = to_f64(&wk);
    let mut wk2 = to_f64(&wk2);
    let mut logl = to_f64(&logl);
    let idelete = to_i32(&delete)[0];
    let iknotauto = to_i32(&iautoknot)[0];
    let alpha = penalty.as_array()[0];

    Lsd::default().logcensor(
        idelete,
        iknotauto,
        &mut sample,
        &mut nsample,
        &mut bd,
        &mut sorc,
        &mut nk,
        &mut kt,
        &mut cf,
        alpha,
        &mut wk,
        &mut wk2,
        &mut logl,
    );

    let out = PyDict::new(py);
    out.set_item("delete", to_i32(&delete).into_pyarray(py))?;
    out.set_item("iautoknot", to_i32(&iautoknot).into_pyarray(py))?;
    out.set_item("sample", sample.into_pyarray(py))?;
    out.set_item("nsample", nsample.into_pyarray(py))?;
    out.set_item("bd", bd.into_pyarray(py))?;
    out.set_item("SorC", sorc.into_pyarray(py))?;
    out.set_item("nk", nk)?;
    out.set_item("kt", kt.into_pyarray(py))?;
    out.set_item("cf", cf.into_pyarray(py))?;
    out.set_item("penalty", penalty.as_array().to_owned().into_pyarray(py))?;
    out.set_item("wk", wk.into_pyarray(py))?;
    out.set_item("wk2", wk2.into_pyarray(py))?;
    out.set_item("logl", logl.into_pyarray(py))?;
    Ok(out)
}

/// `.C("nlogcensorx", ...)`: the maximum number of knots in `z[0]`.
#[pyfunction]
#[pyo3(signature = (z))]
fn nlogcensorx<'py>(py: Python<'py>, z: PyReadonlyArray1<'py, i32>) -> PyResult<Bound<'py, PyDict>> {
    let mut z = to_i32(&z);
    nlsd::nlogcensorx(&mut z);
    let out = PyDict::new(py);
    out.set_item("z", z.into_pyarray(py))?;
    Ok(out)
}

/// `.C("nlogcensor", ...)`: the new logspline fit. Returns the six `.C` arguments.
#[pyfunction]
#[pyo3(signature = (ip, coef, dp, logl, ad, kts))]
fn nlogcensor<'py>(
    py: Python<'py>,
    ip: PyReadonlyArray1<'py, i32>,
    coef: PyReadonlyArray1<'py, f64>,
    dp: PyReadonlyArray1<'py, f64>,
    logl: PyReadonlyArray1<'py, f64>,
    ad: PyReadonlyArray1<'py, i32>,
    kts: PyReadonlyArray1<'py, f64>,
) -> PyResult<Bound<'py, PyDict>> {
    let mut ip = to_i32(&ip);
    let mut coef = to_f64(&coef);
    let mut dp = to_f64(&dp);
    let mut logl = to_f64(&logl);
    let mut ad = to_i32(&ad);
    let mut kts = to_f64(&kts);
    nlsd::nlogcensor(&mut ip, &mut coef, &mut dp, &mut logl, &mut ad, &mut kts);

    let out = PyDict::new(py);
    out.set_item("ip", ip.into_pyarray(py))?;
    out.set_item("coef", coef.into_pyarray(py))?;
    out.set_item("dp", dp.into_pyarray(py))?;
    out.set_item("logl", logl.into_pyarray(py))?;
    out.set_item("ad", ad.into_pyarray(py))?;
    out.set_item("kts", kts.into_pyarray(py))?;
    Ok(out)
}

/// `.C("rpqlsd", ...)`: density (`ipq == 0`) or quantiles (`ipq != 0`) into `pq`.
#[pyfunction]
#[pyo3(signature = (coef, knots, bnd, ipq, pq, lk, lp))]
#[allow(clippy::too_many_arguments)]
fn rpqlsd<'py>(
    py: Python<'py>,
    coef: PyReadonlyArray1<'py, f64>,
    knots: PyReadonlyArray1<'py, f64>,
    bnd: PyReadonlyArray1<'py, f64>,
    ipq: i32,
    pq: PyReadonlyArray1<'py, f64>,
    lk: i32,
    lp: i32,
) -> PyResult<Bound<'py, PyDict>> {
    let coef = to_f64(&coef);
    let knots = to_f64(&knots);
    let bnd = to_f64(&bnd);
    let mut pq = to_f64(&pq);
    nlsd::rpqlsd(&coef, &knots, &bnd, ipq, &mut pq, lk, lp);
    let out = PyDict::new(py);
    out.set_item("pq", pq.into_pyarray(py))?;
    Ok(out)
}

#[pymodule]
fn logspline(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(logcensor, m)?)?;
    m.add_function(wrap_pyfunction!(nlogcensorx, m)?)?;
    m.add_function(wrap_pyfunction!(nlogcensor, m)?)?;
    m.add_function(wrap_pyfunction!(rpqlsd, m)?)?;
    Ok(())
}
