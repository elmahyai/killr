//! PORT SUMSL (tseries `dsumsl.f`) and GARCH likelihood kernel (`garch.c`).

#[cfg(feature = "python")]
mod python {
    use numpy::{PyArray1, PyReadonlyArray1};
    use pyo3::prelude::*;

    extern "C" {
        fn tseries_fit_garch(
            y: *mut f64,
            n: *mut i32,
            par: *mut f64,
            p: *mut i32,
            q: *mut i32,
            itmax: *mut i32,
            afctol: *mut f64,
            rfctol: *mut f64,
            xctol: *mut f64,
            xftol: *mut f64,
            fret: *mut f64,
            agrad: *mut i32,
            trace: *mut i32,
        );
        fn tseries_pred_garch(
            y: *mut f64,
            h: *mut f64,
            n: *mut i32,
            par: *mut f64,
            p: *mut i32,
            q: *mut i32,
            genuine: *mut i32,
        );
        fn tseries_ophess_garch(
            y: *mut f64,
            n: *mut i32,
            par: *mut f64,
            he: *mut f64,
            p: *mut i32,
            q: *mut i32,
        );
    }

    #[pyfunction]
    #[pyo3(name = "fit_garch")]
    fn fit_garch_py(
        y: PyReadonlyArray1<f64>,
        coef: PyReadonlyArray1<f64>,
        p: i32,
        q: i32,
        maxiter: i32,
        abstol: f64,
        reltol: f64,
        xtol: f64,
        falsetol: f64,
        analytical_grad: bool,
        trace: bool,
    ) -> PyResult<(Py<PyArray1<f64>>, f64)> {
        let y = y.as_array();
        let mut n = y.len() as i32;
        let mut y_vec = y.to_vec();
        let mut par = coef.as_array().to_vec();
        let mut fret = 0.0_f64;
        let mut agrad = if analytical_grad { 1 } else { 0 };
        let mut trace_i = if trace { 1 } else { 0 };
        let mut p_i = p;
        let mut q_i = q;
        let mut maxiter_i = maxiter;
        let mut abstol = abstol;
        let mut reltol = reltol;
        let mut xtol = xtol;
        let mut falsetol = falsetol;
        unsafe {
            tseries_fit_garch(
                y_vec.as_mut_ptr(),
                &mut n,
                par.as_mut_ptr(),
                &mut p_i,
                &mut q_i,
                &mut maxiter_i,
                &mut abstol,
                &mut reltol,
                &mut xtol,
                &mut falsetol,
                &mut fret,
                &mut agrad,
                &mut trace_i,
            );
        }
        Python::attach(|py| Ok((PyArray1::from_vec(py, par).into(), fret)))
    }

    #[pyfunction]
    #[pyo3(name = "pred_garch")]
    fn pred_garch_py(
        y: PyReadonlyArray1<f64>,
        par: PyReadonlyArray1<f64>,
        p: i32,
        q: i32,
        genuine: bool,
    ) -> PyResult<Py<PyArray1<f64>>> {
        let y = y.as_array();
        let mut n = y.len() as i32;
        let mut y_vec = y.to_vec();
        let par = par.as_array().to_vec();
        let mut genuine_i = if genuine { 1 } else { 0 };
        let mut p_i = p;
        let mut q_i = q;
        let len = if genuine { n + 1 } else { n };
        let mut h = vec![0.0_f64; len as usize];
        unsafe {
            tseries_pred_garch(
                y_vec.as_mut_ptr(),
                h.as_mut_ptr(),
                &mut n,
                par.as_ptr() as *mut f64,
                &mut p_i,
                &mut q_i,
                &mut genuine_i,
            );
        }
        Python::attach(|py| Ok(PyArray1::from_vec(py, h).into()))
    }

    #[pyfunction]
    #[pyo3(name = "ophess_garch")]
    fn ophess_garch_py(
        y: PyReadonlyArray1<f64>,
        par: PyReadonlyArray1<f64>,
        p: i32,
        q: i32,
    ) -> PyResult<Py<PyArray1<f64>>> {
        let y = y.as_array();
        let mut n = y.len() as i32;
        let mut y_vec = y.to_vec();
        let par = par.as_array().to_vec();
        let pq = (p + q + 1) as usize;
        let mut he = vec![0.0_f64; pq * pq];
        let mut p_i = p;
        let mut q_i = q;
        unsafe {
            tseries_ophess_garch(
                y_vec.as_mut_ptr(),
                &mut n,
                par.as_ptr() as *mut f64,
                he.as_mut_ptr(),
                &mut p_i,
                &mut q_i,
            );
        }
        Python::attach(|py| Ok(PyArray1::from_vec(py, he).into()))
    }

    #[pymodule]
    fn sumsl(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(fit_garch_py, m)?)?;
        m.add_function(wrap_pyfunction!(pred_garch_py, m)?)?;
        m.add_function(wrap_pyfunction!(ophess_garch_py, m)?)?;
        Ok(())
    }
}
