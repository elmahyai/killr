//! pyo3 entry point for the constrained sparse Frisch-Newton loop. The two
//! designs cross as CSR arrays (int64 indices, as scipy.sparse gives them), and
//! the dual crosses as a NumPy array of length m.

use numpy::ndarray::Array1;
use numpy::{PyArray1, PyReadonlyArray1};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use crate::{srqfnc as run_srqfnc, Csr, SfncStart};

fn vec_of(a: &PyReadonlyArray1<'_, f64>) -> Vec<f64> {
    a.as_array().iter().copied().collect()
}

fn check(cond: bool, msg: &str) -> PyResult<()> {
    if cond {
        Ok(())
    } else {
        Err(PyValueError::new_err(msg.to_string()))
    }
}

/// `srqfnc(n1, n2, m, indptr1, indices1, data1, indptr2, indices2, data2, b, c2,
/// x1, x2, s, z1, z2, w, y0, small, tiny, large, maxit)`: the constrained sparse
/// Frisch-Newton loop on the CSR design A1 (n1 x m) and constraint block A2
/// (n2 x m). Returns `(y, it, ierr)`, with `y` the dual of length m.
#[pyfunction]
#[pyo3(name = "sfnc")]
#[allow(clippy::too_many_arguments)]
fn sfnc_py<'py>(
    py: Python<'py>,
    n1: usize,
    n2: usize,
    m: usize,
    indptr1: PyReadonlyArray1<'py, i64>,
    indices1: PyReadonlyArray1<'py, i64>,
    data1: PyReadonlyArray1<'py, f64>,
    indptr2: PyReadonlyArray1<'py, i64>,
    indices2: PyReadonlyArray1<'py, i64>,
    data2: PyReadonlyArray1<'py, f64>,
    b: PyReadonlyArray1<'py, f64>,
    c2: PyReadonlyArray1<'py, f64>,
    x1: PyReadonlyArray1<'py, f64>,
    x2: PyReadonlyArray1<'py, f64>,
    s: PyReadonlyArray1<'py, f64>,
    z1: PyReadonlyArray1<'py, f64>,
    z2: PyReadonlyArray1<'py, f64>,
    w: PyReadonlyArray1<'py, f64>,
    y0: PyReadonlyArray1<'py, f64>,
    small: f64,
    tiny: f64,
    large: f64,
    maxit: usize,
) -> PyResult<(Bound<'py, PyArray1<f64>>, usize, i32)> {
    let indptr1: Vec<usize> = indptr1.as_array().iter().map(|&v| v as usize).collect();
    let indices1: Vec<usize> = indices1.as_array().iter().map(|&v| v as usize).collect();
    let data1 = vec_of(&data1);
    let indptr2: Vec<usize> = indptr2.as_array().iter().map(|&v| v as usize).collect();
    let indices2: Vec<usize> = indices2.as_array().iter().map(|&v| v as usize).collect();
    let data2 = vec_of(&data2);
    check(indptr1.len() == n1 + 1, "indptr1 needs n1 + 1 entries")?;
    check(indptr2.len() == n2 + 1, "indptr2 needs n2 + 1 entries")?;
    check(indices1.len() == data1.len() && indptr1[n1] == data1.len(), "A1 indices and data do not match indptr")?;
    check(indices2.len() == data2.len() && indptr2[n2] == data2.len(), "A2 indices and data do not match indptr")?;
    check(indices1.iter().all(|&j| j < m), "a column index of A1 is outside m")?;
    check(indices2.iter().all(|&j| j < m), "a column index of A2 is outside m")?;
    let (b, c2) = (vec_of(&b), vec_of(&c2));
    let (x1, x2, s) = (vec_of(&x1), vec_of(&x2), vec_of(&s));
    let (z1, z2, w) = (vec_of(&z1), vec_of(&z2), vec_of(&w));
    let y0 = vec_of(&y0);
    check(b.len() == m && y0.len() == m, "b and y need m entries")?;
    check(c2.len() == n2 && x2.len() == n2 && z2.len() == n2, "c2, x2 and z2 need n2 entries")?;
    check(x1.len() == n1 && s.len() == n1 && z1.len() == n1 && w.len() == n1, "x1, s, z1 and w need n1 entries")?;
    let a1 = Csr { n: n1, m, indptr: &indptr1, indices: &indices1, data: &data1 };
    let a2 = Csr { n: n2, m, indptr: &indptr2, indices: &indices2, data: &data2 };
    let start = SfncStart {
        b: &b,
        c2: &c2,
        x1: &x1,
        x2: &x2,
        s: &s,
        z1: &z1,
        z2: &z2,
        w: &w,
        y0: &y0,
        small,
        tiny,
        large,
        maxit,
    };
    let out = run_srqfnc(&a1, &a2, &start);
    Ok((PyArray1::from_owned_array(py, Array1::from(out.y)), out.it, out.ierr))
}

#[pymodule]
#[pyo3(name = "quantreg_sfnc_kernel")]
fn quantreg_sfnc_kernel_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sfnc_py, m)?)?;
    Ok(())
}
