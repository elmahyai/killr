//! pyo3 entry point for the parametric process. The design and response cross as
//! NumPy arrays, and the process crosses as NumPy arrays in their R shapes.

use numpy::ndarray::Array2;
use numpy::{PyArray2, PyReadonlyArray1, PyReadonlyArray2};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use crate::{rqbr_process as run_rqbr_process, FLAG_BOOKKEEPING, FLAG_EMPTY, FLAG_TOO_MANY};

/// `rqbr_process(x, y, tol)`: the Barrodale-Roberts parametric process of `rq.fit.br`
/// for `tau` outside `[0, 1]`. `x` is the n x p design, `y` the response, and `tol`
/// is R's `.Machine$double.eps^(2/3)`. Returns `(sol, dsol, lsol, ift)`:
/// `sol` is (p + 3) x lsol (rows tau, Qbar, Obj.Fun, then the coefficients),
/// `dsol` is n x lsol (the duals), `lsol` the number of breakpoints, and `ift`
/// the Fortran flag (0 clean, 1 possibly nonunique, 2 premature end).
#[pyfunction]
#[pyo3(name = "rqbr_process")]
fn rqbr_process_py<'py>(
    py: Python<'py>,
    x: PyReadonlyArray2<'py, f64>,
    y: PyReadonlyArray1<'py, f64>,
    tol: f64,
) -> PyResult<(Bound<'py, PyArray2<f64>>, Bound<'py, PyArray2<f64>>, usize, i32)> {
    let design = x.as_array();
    let (m, n) = design.dim();
    // Row-major copy of the design, whatever the NumPy layout.
    let a: Vec<f64> = design.iter().copied().collect();
    let b: Vec<f64> = y.as_array().iter().copied().collect();
    if b.len() != m {
        return Err(PyValueError::new_err("x and y don't match n"));
    }
    if !tol.is_finite() || tol < 0.0 {
        return Err(PyValueError::new_err("tol must be a finite non-negative number"));
    }
    let out = run_rqbr_process(m, n, &a, &b, tol);
    match out.ift {
        FLAG_EMPTY => return Err(PyValueError::new_err("the design and response must not be empty")),
        FLAG_BOOKKEEPING => return Err(PyValueError::new_err("the parametric basis lost its bookkeeping")),
        FLAG_TOO_MANY => return Err(PyValueError::new_err("the parametric process has too many breakpoints")),
        _ => {}
    }
    let lsol = out.lsol;
    let sol = Array2::from_shape_fn((out.sol_rows, lsol), |(r, c)| out.sol[c * out.sol_rows + r]);
    let dsol = Array2::from_shape_fn((out.dsol_rows, lsol), |(r, c)| out.dsol[c * out.dsol_rows + r]);
    Ok((
        PyArray2::from_owned_array(py, sol),
        PyArray2::from_owned_array(py, dsol),
        lsol,
        out.ift,
    ))
}

#[pymodule]
#[pyo3(name = "quantreg_br_kernel")]
fn quantreg_br_kernel_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(rqbr_process_py, m)?)?;
    Ok(())
}
