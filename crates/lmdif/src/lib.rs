//! MINPACK Levenberg-Marquardt from minpack.lm 1.2-4 (`lmdif.f` and `lmder.f`).
//!
//! The Fortran is the kernel. This wrapper clamps parameters to bounds, counts
//! iterations the way `nls_lm.c` does, and rebuilds the Hessian from the
//! upper triangle of the factored Jacobian.

use std::cell::Cell;
use std::os::raw::{c_char, c_double, c_int};
use std::sync::Once;

type ResidFn = unsafe extern "C" fn(*const c_double, c_int, *mut c_double, c_int) -> c_int;
type JacFn = unsafe extern "C" fn(*const c_double, c_int, *mut c_double, c_int) -> c_int;

unsafe extern "C" {
    fn nls_lm_set_callbacks(resid: ResidFn, jac: JacFn);
    fn nls_lm_solve(
        par: *mut c_double,
        lower: *const c_double,
        upper: *const c_double,
        n: c_int,
        m: c_int,
        ftol: c_double,
        ptol: c_double,
        gtol: c_double,
        epsfcn: c_double,
        factor: c_double,
        maxfev: c_int,
        maxiter: c_int,
        nprint: c_int,
        mode: c_int,
        diag: *mut c_double,
        fvec: *mut c_double,
        hessian: *mut c_double,
        rsstrace: *mut c_double,
        rsstrace_len: *mut c_int,
        info: *mut c_int,
        niter: *mut c_int,
        message: *mut c_char,
        has_jac: c_int,
    ) -> c_int;
}

struct Slot<'a> {
    resid: &'a mut dyn FnMut(&[f64]) -> Result<Vec<f64>, String>,
    jac: Option<&'a mut dyn FnMut(&[f64]) -> Result<Vec<f64>, String>>,
    error: Option<String>,
}

thread_local! {
    static SLOT: Cell<*mut ()> = const { Cell::new(std::ptr::null_mut()) };
}

struct SlotGuard;
impl Drop for SlotGuard {
    fn drop(&mut self) {
        SLOT.with(|cell| cell.set(std::ptr::null_mut()));
    }
}

fn install_callbacks() {
    static INIT: Once = Once::new();
    INIT.call_once(|| unsafe {
        nls_lm_set_callbacks(c_resid, c_jac);
    });
}

unsafe extern "C" fn c_resid(par: *const c_double, n: c_int, fvec: *mut c_double, m: c_int) -> c_int {
    let slot = SLOT.with(|cell| cell.get()) as *mut Slot;
    if slot.is_null() {
        return -1;
    }
    let slot = unsafe { &mut *slot };
    let x = unsafe { std::slice::from_raw_parts(par, n as usize) };
    let result = (slot.resid)(x);
    match result {
        Ok(values) if values.len() == m as usize => {
            unsafe {
                std::slice::from_raw_parts_mut(fvec, m as usize).copy_from_slice(&values);
            }
            0
        }
        Ok(values) => {
            slot.error = Some(format!(
                "evaluation of fn function returns non-sensible value! length {} != {m}",
                values.len()
            ));
            -1
        }
        Err(err) => {
            slot.error = Some(err);
            -1
        }
    }
}

unsafe extern "C" fn c_jac(par: *const c_double, n: c_int, fjac: *mut c_double, m: c_int) -> c_int {
    let slot = SLOT.with(|cell| cell.get()) as *mut Slot;
    if slot.is_null() {
        return -1;
    }
    let slot = unsafe { &mut *slot };
    let Some(jac) = slot.jac.as_mut() else {
        slot.error = Some("jac is not a function!".to_string());
        return -1;
    };
    let x = unsafe { std::slice::from_raw_parts(par, n as usize) };
    let result = jac(x);
    let need = (m as usize).saturating_mul(n as usize);
    match result {
        Ok(values) if values.len() == need => {
            unsafe {
                std::slice::from_raw_parts_mut(fjac, need).copy_from_slice(&values);
            }
            0
        }
        Ok(values) => {
            slot.error = Some(format!(
                "jac function must return numeric vector with length == length(par) * length(fn(par, ...)). Your function returns one with length {} while {need} expected.",
                values.len()
            ));
            -1
        }
        Err(err) => {
            slot.error = Some(err);
            -1
        }
    }
}

pub struct NlsLmOut {
    pub par: Vec<f64>,
    pub hessian: Vec<f64>,
    pub fvec: Vec<f64>,
    pub info: i32,
    pub message: String,
    pub diag: Vec<f64>,
    pub niter: i32,
    pub rsstrace: Vec<f64>,
}

pub struct NlsLmControl {
    pub ftol: f64,
    pub ptol: f64,
    pub gtol: f64,
    pub epsfcn: f64,
    pub factor: f64,
    pub maxfev: i32,
    pub maxiter: i32,
    pub nprint: i32,
    /// Length `n` selects user scales (mode 2). Any other length, including
    /// empty, asks MINPACK to scale from the first Jacobian (mode 1).
    pub diag: Vec<f64>,
}

pub fn solve<R, J>(
    par: &[f64],
    lower: &[f64],
    upper: &[f64],
    control: &NlsLmControl,
    mut resid: R,
    mut jac: Option<J>,
) -> Result<NlsLmOut, String>
where
    R: FnMut(&[f64]) -> Result<Vec<f64>, String>,
    J: FnMut(&[f64]) -> Result<Vec<f64>, String>,
{
    let n = par.len();
    if n == 0 {
        return Err("length(par) must be positive".into());
    }
    if lower.len() != n {
        return Err("length(lower) must be equal to length(par)".into());
    }
    if upper.len() != n {
        return Err("length(upper) must be equal to length(par)".into());
    }
    if par.iter().any(|value| !value.is_finite()) {
        return Err("Non-finite (or null) value for a parameter specified!".into());
    }
    let first = resid(par)?;
    let m = first.len();
    if m == 0 {
        return Err("evaluation of fn function returns non-sensible value!".into());
    }
    if let Some(jac_fn) = jac.as_mut() {
        let trial = jac_fn(par)?;
        let need = m * n;
        if trial.len() != need {
            return Err(format!(
                "jac function must return numeric vector with length == length(par) * length(fn(par, ...)). Your function returns one with length {} while {need} expected.",
                trial.len()
            ));
        }
    }

    install_callbacks();
    let mut resid_fn = resid;
    let mut jac_fn = jac;
    let mut slot = Slot {
        resid: &mut resid_fn,
        jac: jac_fn
            .as_mut()
            .map(|func| func as &mut dyn FnMut(&[f64]) -> Result<Vec<f64>, String>),
        error: None,
    };
    SLOT.with(|cell| cell.set((&mut slot as *mut Slot).cast()));
    let _guard = SlotGuard;

    let mut par_out = par.to_vec();
    let mut diag = if control.diag.len() == n {
        control.diag.clone()
    } else {
        vec![0.0; n]
    };
    let mode: i32 = if control.diag.len() == n { 2 } else { 1 };
    let mut fvec = vec![0.0; m];
    let mut hessian = vec![0.0; n * n];
    let mut rsstrace = vec![0.0; 1025];
    let mut rsstrace_len: i32 = 0;
    let mut info: i32 = 0;
    let mut niter: i32 = 0;
    let mut message = [0u8; 256];
    let code = unsafe {
        nls_lm_solve(
            par_out.as_mut_ptr(),
            lower.as_ptr(),
            upper.as_ptr(),
            n as c_int,
            m as c_int,
            control.ftol,
            control.ptol,
            control.gtol,
            control.epsfcn,
            control.factor,
            control.maxfev,
            control.maxiter,
            control.nprint,
            mode,
            diag.as_mut_ptr(),
            fvec.as_mut_ptr(),
            hessian.as_mut_ptr(),
            rsstrace.as_mut_ptr(),
            &mut rsstrace_len,
            &mut info,
            &mut niter,
            message.as_mut_ptr() as *mut c_char,
            if slot.jac.is_some() { 1 } else { 0 },
        )
    };
    if code != 0 {
        return Err("nls.lm could not allocate work arrays".into());
    }
    if let Some(err) = slot.error.take() {
        return Err(err);
    }
    let len = rsstrace_len.max(0) as usize;
    rsstrace.truncate(len);
    let end = message.iter().position(|byte| *byte == 0).unwrap_or(message.len());
    let text = String::from_utf8_lossy(&message[..end]).into_owned();
    Ok(NlsLmOut {
        par: par_out,
        hessian,
        fvec,
        info,
        message: text,
        diag,
        niter,
        rsstrace,
    })
}

#[cfg(feature = "python")]
mod python {
    use super::{solve, NlsLmControl};
    use pyo3::prelude::*;
    use pyo3::types::{PyDict, PyList};

    fn as_vec(value: &Bound<'_, PyAny>) -> PyResult<Vec<f64>> {
        if let Ok(list) = value.cast::<PyList>() {
            let mut out = Vec::with_capacity(list.len());
            for item in list.iter() {
                out.push(item.extract::<f64>()?);
            }
            return Ok(out);
        }
        value.extract::<Vec<f64>>()
    }

    #[pyfunction]
    #[pyo3(name = "solve", signature = (
        par,
        lower,
        upper,
        ftol,
        ptol,
        gtol,
        epsfcn,
        factor,
        maxfev,
        maxiter,
        nprint,
        diag,
        function,
        jacobian = None
    ))]
    fn solve_py(
        py: Python<'_>,
        par: Vec<f64>,
        lower: Vec<f64>,
        upper: Vec<f64>,
        ftol: f64,
        ptol: f64,
        gtol: f64,
        epsfcn: f64,
        factor: f64,
        maxfev: i32,
        maxiter: i32,
        nprint: i32,
        diag: Option<Vec<f64>>,
        function: Py<PyAny>,
        jacobian: Option<Py<PyAny>>,
    ) -> PyResult<Py<PyAny>> {
        let control = NlsLmControl {
            ftol,
            ptol,
            gtol,
            epsfcn,
            factor,
            maxfev,
            maxiter,
            nprint,
            diag: diag.unwrap_or_default(),
        };
        let call = |func: &Py<PyAny>, x: &[f64]| -> Result<Vec<f64>, String> {
            let obj = func
                .call1(py, (x.to_vec(),))
                .map_err(|err| err.to_string())?;
            as_vec(&obj.bind(py)).map_err(|err| err.to_string())
        };
        let resid = |x: &[f64]| call(&function, x);
        let out = if let Some(jacobian) = jacobian {
            let jac = |x: &[f64]| call(&jacobian, x);
            solve(&par, &lower, &upper, &control, resid, Some(jac))
        } else {
            solve(&par, &lower, &upper, &control, resid, None::<fn(&[f64]) -> Result<Vec<f64>, String>>)
        };
        let out = out.map_err(pyo3::exceptions::PyRuntimeError::new_err)?;
        let dict = PyDict::new(py);
        dict.set_item("par", out.par)?;
        dict.set_item("hessian", out.hessian)?;
        dict.set_item("fvec", out.fvec)?;
        dict.set_item("info", out.info)?;
        dict.set_item("message", out.message)?;
        dict.set_item("diag", out.diag)?;
        dict.set_item("niter", out.niter)?;
        dict.set_item("rsstrace", out.rsstrace)?;
        Ok(dict.into())
    }

    #[pymodule]
    #[pyo3(name = "lmdif")]
    fn lmdif_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(solve_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{solve, NlsLmControl};

    fn rosenbrock(p: &[f64]) -> Result<Vec<f64>, String> {
        Ok(vec![1.0 - p[0], 10.0 * (p[1] - p[0] * p[0])])
    }

    fn rosenbrock_jac(p: &[f64]) -> Result<Vec<f64>, String> {
        Ok(vec![-1.0, -20.0 * p[0], 0.0, 10.0])
    }

    fn defaults(maxiter: i32) -> NlsLmControl {
        NlsLmControl {
            ftol: 1.4901161193847656e-8,
            ptol: 1.4901161193847656e-8,
            gtol: 0.0,
            epsfcn: 0.0,
            factor: 100.0,
            maxfev: 300,
            maxiter,
            nprint: 0,
            diag: Vec::new(),
        }
    }

    fn close(got: &[f64], expect: &[f64]) {
        assert_eq!(got.len(), expect.len(), "len {got:?} vs {expect:?}");
        for (left, right) in got.iter().zip(expect) {
            assert!(
                (left - right).abs() <= 1e-8,
                "{left} != {right} in {got:?}"
            );
        }
    }

    #[test]
    fn finite_difference_rosenbrock_matches_r() {
        let lower = vec![f64::NEG_INFINITY, f64::NEG_INFINITY];
        let upper = vec![f64::INFINITY, f64::INFINITY];
        let out = solve(&[-1.2, 1.0], &lower, &upper, &defaults(50), rosenbrock, None::<fn(&[f64]) -> _>)
            .unwrap();
        close(&out.par, &[1.0, 1.0]);
        assert_eq!(out.info, 2);
        assert_eq!(out.niter, 16);
        close(&out.fvec, &[0.0, 0.0]);
        close(
            &out.hessian,
            &[
                401.00000595871512,
                -200.00000148398169,
                -200.00000148398169,
                99.999999994301817,
            ],
        );
        close(&out.diag, &[24.020824259794601, 10.000000042604881]);
        close(
            &out.rsstrace,
            &[
                24.199998688697832,
                4.3981472967893058,
                3.1723046304937088,
                2.6243410750659288,
                2.1840575010479335,
                1.771644171861297,
                1.4225687484711689,
                1.1213598078317335,
                0.86177578222613949,
                0.65782761417175462,
                0.42236637956730627,
                0.24698477140608555,
                0.12795573910135191,
                0.059790110010993526,
                0.019228719033926922,
                2.2282939156168653e-14,
                0.0,
            ],
        );
        assert_eq!(
            out.message,
            "Relative error between `par' and the solution is at most `ptol'."
        );
    }

    #[test]
    fn analytic_jacobian_rosenbrock_matches_r() {
        let lower = vec![f64::NEG_INFINITY, f64::NEG_INFINITY];
        let upper = vec![f64::INFINITY, f64::INFINITY];
        let out = solve(
            &[-1.2, 1.0],
            &lower,
            &upper,
            &defaults(50),
            rosenbrock,
            Some(rosenbrock_jac),
        )
        .unwrap();
        close(&out.par, &[1.0, 1.0]);
        assert_eq!(out.info, 4);
        assert_eq!(out.niter, 16);
        close(
            &out.hessian,
            &[401.00000000000006, -200.0, -200.0, 99.999999999999986],
        );
        close(&out.diag, &[24.020824298928627, 10.0]);
        assert!(out.rsstrace[0] - 24.199999999999996 < 1e-12);
    }
}
