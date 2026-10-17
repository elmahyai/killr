//! Fortran kernels from mclust 6.1.3 (CRAN), linked for Python via maturin.

#[cfg(feature = "python")]
use numpy::{PyArray2, PyArray3, PyReadonlyArray1, PyReadonlyArray2, PyReadonlyArray3};
#[cfg(feature = "python")]
use pyo3::prelude::*;

#[cfg(feature = "python")]
unsafe extern "C" {
    fn uncholf_(upper: *mut i32, t: *mut f64, l: *mut i32, n: *mut i32, info: *mut i32);
    fn shapeo_(
        transp: *mut i32,
        s: *mut f64,
        o: *mut f64,
        l: *mut i32,
        m: *mut i32,
        w: *mut f64,
        info: *mut i32,
    );
}

#[cfg(feature = "python")]
fn fortran_matrix(view: numpy::ndarray::ArrayView2<'_, f64>) -> Vec<f64> {
    let (nrows, ncols) = view.dim();
    let mut out = vec![0.0; nrows * ncols];
    for j in 0..ncols {
        for i in 0..nrows {
            out[j * nrows + i] = view[[i, j]];
        }
    }
    out
}

#[cfg(feature = "python")]
fn matrix_from_fortran(values: &[f64], nrows: usize, ncols: usize) -> Vec<Vec<f64>> {
    let mut rows = vec![vec![0.0; ncols]; nrows];
    for j in 0..ncols {
        for i in 0..nrows {
            rows[i][j] = values[j * nrows + i];
        }
    }
    rows
}

#[cfg(feature = "python")]
fn fortran_cube(view: numpy::ndarray::ArrayView3<'_, f64>) -> Vec<f64> {
    let (n0, n1, n2) = view.dim();
    let mut out = vec![0.0; n0 * n1 * n2];
    for k in 0..n2 {
        for j in 0..n1 {
            for i in 0..n0 {
                out[k * n0 * n1 + j * n0 + i] = view[[i, j, k]];
            }
        }
    }
    out
}

/// Rebuild the symmetric product of a triangular factor.
///
/// `upper` is the Fortran logical: true means `T' T`, false means `T T'`.
/// The matrix is copied into column-major storage; the leading dimension is
/// the first axis.
#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(name = "uncholf")]
fn uncholf_py(upper: bool, x: PyReadonlyArray2<f64>) -> PyResult<Py<PyArray2<f64>>> {
    let view = x.as_array();
    let (nrows, ncols) = view.dim();
    let mut mat = fortran_matrix(view);
    let mut upper_i = if upper { 1_i32 } else { 0_i32 };
    let mut lead = nrows as i32;
    let mut n = ncols as i32;
    let mut info = 0_i32;
    unsafe {
        uncholf_(
            &mut upper_i,
            mat.as_mut_ptr(),
            &mut lead,
            &mut n,
            &mut info,
        );
    }
    let rows = matrix_from_fortran(&mat, nrows, ncols);
    Python::attach(|py| Ok(PyArray2::from_vec2(py, &rows)?.into()))
}

/// Scale orientation slices by `shape` and replace each slice with the
/// symmetric product. `transpose` false is `O diag(s) O'`.
#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(name = "shapeo")]
fn shapeo_py(
    transpose: bool,
    shape: PyReadonlyArray1<f64>,
    o: PyReadonlyArray3<f64>,
) -> PyResult<Py<PyArray3<f64>>> {
    let oview = o.as_array();
    let (lead, width, slices) = oview.dim();
    if lead != width {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "leading dimensions of O are unequal",
        ));
    }
    let mut scale: Vec<f64> = shape.as_array().iter().copied().collect();
    let mut buf = fortran_cube(oview);
    let mut work = vec![0.0; lead * lead];
    let mut transp = if transpose { 1_i32 } else { 0_i32 };
    let mut l = lead as i32;
    let mut m = slices as i32;
    let mut info = 0_i32;
    unsafe {
        shapeo_(
            &mut transp,
            scale.as_mut_ptr(),
            buf.as_mut_ptr(),
            &mut l,
            &mut m,
            work.as_mut_ptr(),
            &mut info,
        );
    }
    let mut cube = vec![vec![vec![0.0; slices]; width]; lead];
    for k in 0..slices {
        for j in 0..lead {
            for i in 0..lead {
                cube[i][j][k] = buf[k * lead * lead + j * lead + i];
            }
        }
    }
    Python::attach(|py| Ok(PyArray3::from_vec3(py, &cube)?.into()))
}

#[cfg(feature = "python")]
#[pymodule]
fn mclustbootstraplrt(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__doc__", "Linked mclust Fortran from CRAN 6.1.3")?;
    m.add_function(wrap_pyfunction!(uncholf_py, m)?)?;
    m.add_function(wrap_pyfunction!(shapeo_py, m)?)?;
    Ok(())
}
