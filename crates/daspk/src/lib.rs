//! DASPK DAE/ODE integrator from deSolve `ddaspk.f` and `call_daspk.c`.

use std::os::raw::{c_double, c_int};

extern "C" {
    fn daspk_integrate(
        n: c_int,
        nt: c_int,
        y: *mut c_double,
        yprime: *mut c_double,
        times: *mut c_double,
        yout: *mut c_double,
        istate23: *mut c_int,
        rstate3: *mut c_double,
        info25: *mut c_int,
        iwork: *mut c_int,
        liw: c_int,
        rwork: *mut c_double,
        lrw: c_int,
        rtol: *mut c_double,
        lrtol: c_int,
        atol: *mut c_double,
        latol: c_int,
        maxit: c_int,
        jac: Option<
            extern "C" fn(
                *mut c_double,
                *mut c_double,
                *mut c_double,
                *mut c_double,
                *mut c_double,
                *mut c_double,
                *mut c_int,
            ),
        >,
    ) -> c_int;
    fn daspk_set_res(
        res: Option<
            extern "C" fn(
                *mut c_double,
                *mut c_double,
                *mut c_double,
                *mut c_double,
                *mut c_double,
                *mut c_int,
                *mut c_double,
                *mut c_int,
            ),
        >,
    );
}

#[cfg(feature = "python")]
mod python {
    use super::{daspk_integrate, daspk_set_res};
    use numpy::{PyArrayMethods, PyReadonlyArray1, PyReadonlyArray2};
    use pyo3::exceptions::{PyRuntimeError, PyValueError};
    use pyo3::prelude::*;
    use pyo3::types::{PyAny, PyList};
    use std::cell::RefCell;
    use std::os::raw::{c_double, c_int};
    use std::slice;

    thread_local! {
        static PY_RES: RefCell<Option<Py<PyAny>>> = const { RefCell::new(None) };
        static PY_JAC: RefCell<Option<Py<PyAny>>> = const { RefCell::new(None) };
        static PY_N: RefCell<usize> = const { RefCell::new(0) };
        static PY_NROWPD: RefCell<usize> = const { RefCell::new(0) };
    }

    fn vec_from_py(obj: &Bound<'_, PyAny>, n: usize) -> PyResult<Vec<f64>> {
        if let Ok(list) = obj.cast::<PyList>() {
            let mut out = Vec::with_capacity(n);
            for item in list.iter() {
                out.push(item.extract::<f64>()?);
            }
            if out.len() != n {
                return Err(PyRuntimeError::new_err(format!(
                    "expected length {n}, got {}",
                    out.len()
                )));
            }
            return Ok(out);
        }
        let array = obj.extract::<PyReadonlyArray1<f64>>()?;
        let data = array.as_slice()?.to_vec();
        if data.len() != n {
            return Err(PyRuntimeError::new_err(format!(
                "expected length {n}, got {}",
                data.len()
            )));
        }
        Ok(data)
    }

    fn matrix_flat_colmajor(value: &Bound<'_, PyAny>, nrow: usize, ncol: usize) -> PyResult<Vec<f64>> {
        if let Ok(arr) = value.extract::<PyReadonlyArray2<f64>>() {
            let view = arr.as_array();
            if view.nrows() == nrow && view.ncols() == ncol {
                let mut out = vec![0.0; nrow * ncol];
                for col in 0..ncol {
                    for row in 0..nrow {
                        out[col * nrow + row] = view[[row, col]];
                    }
                }
                return Ok(out);
            }
        }
        let flat = value.extract::<Vec<f64>>()?;
        if flat.len() != nrow * ncol {
            return Err(PyRuntimeError::new_err("Jacobian size mismatch"));
        }
        Ok(flat)
    }

    extern "C" fn c_res(
        t: *mut c_double,
        y: *mut c_double,
        yprime: *mut c_double,
        cj: *mut c_double,
        delta: *mut c_double,
        ires: *mut c_int,
        _rpar: *mut c_double,
        _ipar: *mut c_int,
    ) {
        let n = PY_N.with(|slot| *slot.borrow());
        let tn = unsafe { *t };
        let cjv = unsafe { *cj };
        let ys = unsafe { slice::from_raw_parts(y, n) }.to_vec();
        let yps = unsafe { slice::from_raw_parts(yprime, n) }.to_vec();
        let mut out = vec![0.0; n];
        Python::attach(|py| {
            PY_RES.with(|slot| {
                let callable = slot.borrow().as_ref().expect("res").clone_ref(py);
                let ans = callable
                    .call1(py, (tn, ys, yps, cjv))
                    .expect("res");
                out = vec_from_py(ans.bind(py), n).expect("res numeric");
            });
        });
        unsafe {
            std::ptr::copy_nonoverlapping(out.as_ptr(), delta, n);
            *ires = 0;
        }
    }

    extern "C" fn c_jac(
        t: *mut c_double,
        y: *mut c_double,
        yprime: *mut c_double,
        pd: *mut c_double,
        cj: *mut c_double,
        _rpar: *mut c_double,
        _ipar: *mut c_int,
    ) {
        let n = PY_N.with(|slot| *slot.borrow());
        let nrowpd = PY_NROWPD.with(|slot| *slot.borrow());
        let tn = unsafe { *t };
        let cjv = unsafe { *cj };
        let ys = unsafe { slice::from_raw_parts(y, n) }.to_vec();
        let yps = unsafe { slice::from_raw_parts(yprime, n) }.to_vec();
        let mut flat = vec![0.0; nrowpd * n];
        Python::attach(|py| {
            PY_JAC.with(|slot| {
                let callable = slot.borrow().as_ref().expect("jac").clone_ref(py);
                let ans = callable
                    .call1(py, (tn, ys, yps, cjv))
                    .expect("jac");
                flat = matrix_flat_colmajor(ans.bind(py), nrowpd, n).expect("jac matrix");
            });
        });
        unsafe {
            std::ptr::copy_nonoverlapping(flat.as_ptr(), pd, flat.len());
        }
    }

    #[pyfunction]
    #[pyo3(signature = (
        y,
        dy,
        times,
        residual,
        rtol,
        atol,
        info,
        iwork,
        rwork,
        maxit,
        nrowpd,
        jac=None,
    ))]
    fn integrate_daspk(
        py: Python<'_>,
        y: Vec<f64>,
        dy: Vec<f64>,
        mut times: Vec<f64>,
        residual: Py<PyAny>,
        rtol: Vec<f64>,
        atol: Vec<f64>,
        info: Vec<i32>,
        iwork: Vec<i32>,
        rwork: Vec<f64>,
        maxit: i32,
        nrowpd: i32,
        jac: Option<Py<PyAny>>,
    ) -> PyResult<(Vec<f64>, i32, Vec<i32>, Vec<f64>)> {
        let n = y.len();
        if dy.len() != n {
            return Err(PyValueError::new_err("`dy' length must match `y'"));
        }
        let nt = times.len();
        if n == 0 || nt == 0 {
            return Err(PyValueError::new_err("empty state or times"));
        }
        if info.len() != 25 {
            return Err(PyValueError::new_err("info must have length 25"));
        }
        let mut y_mut = y;
        let mut dy_mut = dy;
        let mut rtol_mut = rtol;
        let mut atol_mut = atol;
        let mut info_mut: Vec<i32> = info;
        let mut iwork_mut = iwork;
        let mut rwork_mut = rwork;
        let mut yout = vec![0.0; nt * (n + 1)];
        let mut istate23 = vec![0i32; 23];
        let mut rstate3 = vec![0.0; 3];

        PY_N.with(|slot| *slot.borrow_mut() = n);
        PY_NROWPD.with(|slot| *slot.borrow_mut() = nrowpd as usize);
        PY_RES.with(|slot| *slot.borrow_mut() = Some(residual.clone_ref(py)));
        PY_JAC.with(|slot| {
            *slot.borrow_mut() = jac.as_ref().map(|j| j.clone_ref(py));
        });

        let use_jac = info_mut[4] == 1 && jac.is_some();
        unsafe {
            daspk_set_res(Some(c_res));
        }
        let jac_fn = if use_jac {
            Some(c_jac as extern "C" fn(_, _, _, _, _, _, _))
        } else {
            None
        };

        let idid = unsafe {
            daspk_integrate(
                n as c_int,
                nt as c_int,
                y_mut.as_mut_ptr(),
                dy_mut.as_mut_ptr(),
                times.as_mut_ptr(),
                yout.as_mut_ptr(),
                istate23.as_mut_ptr(),
                rstate3.as_mut_ptr(),
                info_mut.as_mut_ptr(),
                iwork_mut.as_mut_ptr(),
                iwork_mut.len() as c_int,
                rwork_mut.as_mut_ptr(),
                rwork_mut.len() as c_int,
                rtol_mut.as_mut_ptr(),
                rtol_mut.len() as c_int,
                atol_mut.as_mut_ptr(),
                atol_mut.len() as c_int,
                maxit,
                jac_fn,
            )
        };

        unsafe {
            daspk_set_res(None);
        }
        PY_RES.with(|slot| *slot.borrow_mut() = None);
        PY_JAC.with(|slot| *slot.borrow_mut() = None);

        Ok((yout, idid, istate23, rstate3))
    }

    #[pymodule]
    #[pyo3(name = "daspk")]
    fn daspk_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(integrate_daspk, m)?)?;
        Ok(())
    }
}
