//! RADAU5 integrator from deSolve `src/radau5.f` and `call_radau.c`.

use std::os::raw::c_int;

extern "C" {
    fn radau5_integrate(
        n: c_int,
        nt: c_int,
        y0: *const f64,
        times: *const f64,
        yout: *mut f64,
        istate7: *mut c_int,
        rstate5: *mut f64,
        rtol: *const f64,
        atol: *const f64,
        itol: c_int,
        hmax: f64,
        hini: f64,
        maxsteps: c_int,
        nind3: *const c_int,
        ijac: c_int,
        mljac: c_int,
        mujac: c_int,
        imas: c_int,
        mlmas: c_int,
        mumas: c_int,
        deriv: Option<extern "C" fn(*mut c_int, *mut f64, *mut f64, *mut f64, *mut f64, *mut c_int)>,
        jac: Option<
            extern "C" fn(
                *mut c_int,
                *mut f64,
                *mut f64,
                *mut c_int,
                *mut c_int,
                *mut f64,
                *mut c_int,
                *mut f64,
                *mut c_int,
            ),
        >,
        dense_out: c_int,
    ) -> c_int;
}

#[cfg(feature = "python")]
mod python {
    use super::radau5_integrate;
    use numpy::PyReadonlyArray2;
    use pyo3::prelude::*;
    use pyo3::types::PyAny;
    use std::cell::RefCell;
    use std::os::raw::c_int;
    use std::slice;

    thread_local! {
        static PY_DERIV: RefCell<Option<Py<PyAny>>> = const { RefCell::new(None) };
        static PY_JAC: RefCell<Option<Py<PyAny>>> = const { RefCell::new(None) };
    }

    fn matrix_colmajor(value: &Bound<'_, PyAny>, n: usize) -> Vec<f64> {
        if let Ok(vec) = value.extract::<Vec<f64>>() {
            if vec.len() == n {
                return vec;
            }
        }
        if let Ok(arr) = value.extract::<PyReadonlyArray2<f64>>() {
            let view = arr.as_array();
            if view.nrows() == n && view.ncols() == n {
                let mut out = vec![0.0; n * n];
                for col in 0..n {
                    for row in 0..n {
                        out[col * n + row] = view[[row, col]];
                    }
                }
                return out;
            }
        }
        panic!("Jacobian function 'jacfunc' must return a matrix");
    }

    extern "C" fn c_deriv(
        neq: *mut c_int,
        t: *mut f64,
        y: *mut f64,
        ydot: *mut f64,
        _rpar: *mut f64,
        _ipar: *mut c_int,
    ) {
        let n = unsafe { *neq } as usize;
        let tn = unsafe { *t };
        let ys = unsafe { slice::from_raw_parts(y, n) };
        let mut out = vec![0.0; n];
        Python::attach(|py| {
            PY_DERIV.with(|slot| {
                let binding = slot.borrow();
                let callable = binding.as_ref().expect("deriv");
                let ans = callable
                    .call1(py, (tn, ys.to_vec()))
                    .expect("deriv")
                    .extract::<Vec<f64>>(py)
                    .expect("deriv numeric");
                assert_eq!(ans.len(), n);
                out.copy_from_slice(&ans);
            });
        });
        unsafe {
            std::ptr::copy_nonoverlapping(out.as_ptr(), ydot, n);
        }
    }

    extern "C" fn c_jac(
        neq: *mut c_int,
        t: *mut f64,
        y: *mut f64,
        _ml: *mut c_int,
        _mu: *mut c_int,
        pd: *mut f64,
        ldpd: *mut c_int,
        _rpar: *mut f64,
        _ipar: *mut c_int,
    ) {
        let n = unsafe { *neq } as usize;
        let tn = unsafe { *t };
        let ld = unsafe { *ldpd } as usize;
        let ys = unsafe { slice::from_raw_parts(y, n) };
        let mut flat = vec![0.0; ld * n];
        Python::attach(|py| {
            PY_JAC.with(|slot| {
                let binding = slot.borrow();
                let callable = binding.as_ref().expect("jac");
                let ans = callable.call1(py, (tn, ys.to_vec())).expect("jac");
                flat = matrix_colmajor(&ans.bind(py), n);
            });
        });
        unsafe {
            std::ptr::copy_nonoverlapping(flat.as_ptr(), pd, flat.len());
        }
    }

    #[pyfunction]
    #[pyo3(signature = (
        y,
        times,
        deriv,
        rtol,
        atol,
        hmax,
        hini=0.0,
        maxsteps=5000,
        nind=None,
        ijac=0,
        mljac=0,
        mujac=0,
        imas=0,
        mlmas=0,
        mumas=0,
        jac=None,
        dense_out=true,
    ))]
    fn integrate_radau(
        py: Python<'_>,
        y: Vec<f64>,
        times: Vec<f64>,
        deriv: Py<PyAny>,
        rtol: Vec<f64>,
        atol: Vec<f64>,
        hmax: f64,
        hini: f64,
        maxsteps: i32,
        nind: Option<Vec<i32>>,
        ijac: i32,
        mljac: i32,
        mujac: i32,
        imas: i32,
        mlmas: i32,
        mumas: i32,
        jac: Option<Py<PyAny>>,
        dense_out: bool,
    ) -> PyResult<(Vec<f64>, i32, Vec<i32>, Vec<f64>)> {
        let n = y.len();
        let mut times = times;
        let nt = times.len();
        if n == 0 || nt == 0 {
            return Err(pyo3::exceptions::PyValueError::new_err("empty state or times"));
        }
        let nind3: Vec<i32> = if let Some(v) = nind {
            if v.len() != 3 {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    "length of `nind' must be =3",
                ));
            }
            v
        } else {
            vec![n as i32, 0, 0]
        };
        if nind3.iter().sum::<i32>() != n as i32 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "sum of of `nind' must equal n, the number of equations",
            ));
        }
        let itol = if rtol.len() == 1 && atol.len() == 1 { 0 } else { 1 };
        let maxsteps_i = (maxsteps as i64 * nt as i64).min(i32::MAX as i64) as i32;
        let mut yout = vec![0.0; nt * (n + 1)];
        let mut istate7 = vec![0i32; 7];
        let mut rstate5 = vec![0.0; 5];
        PY_DERIV.with(|slot| *slot.borrow_mut() = Some(deriv.clone_ref(py)));
        PY_JAC.with(|slot| {
            *slot.borrow_mut() = jac.as_ref().map(|j| j.clone_ref(py));
        });
        let jac_fn = if ijac == 1 && jac.is_some() {
            Some(c_jac as extern "C" fn(_, _, _, _, _, _, _, _, _))
        } else {
            None
        };
        let idid = unsafe {
            radau5_integrate(
                n as c_int,
                nt as c_int,
                y.as_ptr(),
                times.as_mut_ptr(),
                yout.as_mut_ptr(),
                istate7.as_mut_ptr(),
                rstate5.as_mut_ptr(),
                rtol.as_ptr(),
                atol.as_ptr(),
                itol,
                hmax,
                hini,
                maxsteps_i,
                nind3.as_ptr(),
                ijac,
                mljac,
                mujac,
                imas,
                mlmas,
                mumas,
                Some(c_deriv),
                jac_fn,
                if dense_out { 1 } else { 0 },
            )
        };
        PY_DERIV.with(|slot| *slot.borrow_mut() = None);
        PY_JAC.with(|slot| *slot.borrow_mut() = None);
        Ok((yout, idid, istate7, rstate5))
    }

    #[pymodule]
    #[pyo3(name = "radau5")]
    fn radau5_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(integrate_radau, m)?)?;
        Ok(())
    }
}
