//! R 4.5.0 `nlminb()` without a gradient, on R's own PORT kernel `portsrc.f`.
//!
//! R's `nlminb()` (R/nlminb.R) builds `iv` and `v` with `port_ivset`, applies
//! the control list, and calls `port_nlminb` (port.c). That loop calls `drmnf`
//! or, with bounds, `drmnfb`, then evaluates the objective at `.par` after each
//! call, until `iv[1] >= 3`. This module runs the same loop in Rust. The C
//! helpers that `portsrc.f` calls live in `glue.rs`.

pub mod glue;

use std::os::raw::c_int;

unsafe extern "C" {
    fn drmnf_(
        d: *mut f64,
        fx: *mut f64,
        iv: *mut c_int,
        liv: *const c_int,
        lv: *const c_int,
        n: *const c_int,
        v: *mut f64,
        x: *mut f64,
    );
    fn drmnfb_(
        b: *mut f64,
        d: *mut f64,
        fx: *mut f64,
        iv: *mut c_int,
        liv: *const c_int,
        lv: *const c_int,
        n: *const c_int,
        v: *mut f64,
        x: *mut f64,
    );
}

/// Control names and their `port_cpos` slots (1-based), in R's order.
/// The first four map into `iv`, the rest into `v`.
const PORT_CPOS: [(&str, usize); 13] = [
    ("eval.max", 17),
    ("iter.max", 18),
    ("trace", 19),
    ("maxiter", 18),
    ("abs.tol", 31),
    ("rel.tol", 32),
    ("x.tol", 33),
    ("xf.tol", 34),
    ("step.min", 35),
    ("step.max", 36),
    ("sing.tol", 37),
    ("scale.init", 38),
    ("diff.g", 42),
];

#[derive(Debug, Clone)]
pub struct PortFit {
    pub par: Vec<f64>,
    pub objective: f64,
    pub convergence: i32,
    pub iterations: i32,
    pub evaluations_function: i32,
    pub evaluations_gradient: i32,
    pub message: String,
    /// Control names that did not match any option (R warns and drops them).
    pub unknown_control: Vec<String>,
}

/// Inputs after R's `rep_len` recycling. `lower` and `upper` are empty when
/// there are no finite bounds, which selects `drmnf` as R does.
pub struct Problem<'a> {
    pub start: &'a [f64],
    pub scale: &'a [f64],
    pub lower: &'a [f64],
    pub upper: &'a [f64],
    pub control: &'a [(String, f64)],
}

/// R's `pmatch` of one control name against `port_cpos` names: exact match
/// first, otherwise a unique prefix.
fn pmatch(name: &str) -> Option<usize> {
    if let Some(pos) = PORT_CPOS.iter().position(|(nm, _)| *nm == name) {
        return Some(pos);
    }
    let hits: Vec<usize> = PORT_CPOS
        .iter()
        .enumerate()
        .filter(|(_, (nm, _))| nm.starts_with(name))
        .map(|(i, _)| i)
        .collect();
    if hits.len() == 1 {
        Some(hits[0])
    } else {
        None
    }
}

/// C `%g` with the default precision of 6.
fn fmt_g(x: f64) -> String {
    if x.is_nan() {
        return "nan".to_string();
    }
    if x.is_infinite() {
        return if x > 0.0 { "inf".to_string() } else { "-inf".to_string() };
    }
    if x == 0.0 {
        return "0".to_string();
    }
    let sci = format!("{:.5e}", x);
    let (mant, exp) = sci.split_once('e').unwrap();
    let e: i32 = exp.parse().unwrap();
    if !(-4..6).contains(&e) {
        let mant = trim_zeros(mant);
        let sign = if e < 0 { '-' } else { '+' };
        format!("{}e{}{:02}", mant, sign, e.abs())
    } else {
        let prec = (5 - e).max(0) as usize;
        trim_zeros(&format!("{:.*}", prec, x)).to_string()
    }
}

fn trim_zeros(s: &str) -> &str {
    if s.contains('.') {
        s.trim_end_matches('0').trim_end_matches('.')
    } else {
        s
    }
}

/// `port_msg` and the out-of-range branch of R's `nlminb()`.
fn port_message(iv1: i32, v: &[f64]) -> String {
    match iv1 {
        3 => "X-convergence (3)".to_string(),
        4 => "relative convergence (4)".to_string(),
        5 => "both X-convergence and relative convergence (5)".to_string(),
        6 => "absolute function convergence (6)".to_string(),
        7 => "singular convergence (7)".to_string(),
        8 => "false convergence (8)".to_string(),
        9 => "function evaluation limit reached without convergence (9)".to_string(),
        10 => "iteration limit reached without convergence (10)".to_string(),
        14 => "storage only has been allocated (14)".to_string(),
        15 => "LIV too small (15)".to_string(),
        16 => "LV too small (16)".to_string(),
        63 => "fn cannot be computed at initial par (63)".to_string(),
        65 => "gr cannot be computed at initial par (65)".to_string(),
        300 => "initial par violates constraints".to_string(),
        19..=43 => {
            if let Some((nm, _)) = PORT_CPOS.iter().find(|(_, slot)| *slot as i32 == iv1) {
                let val = v.get(iv1 as usize - 1).copied().unwrap_or(f64::NAN);
                format!("'control' component '{}' = {}, is out of range", nm, fmt_g(val))
            } else {
                let val = v.get(iv1 as usize - 1).copied().unwrap_or(f64::NAN);
                format!(
                    "V[IV[1]] = V[{}] = {} is out of range (see PORT docu.)",
                    iv1,
                    fmt_g(val)
                )
            }
        }
        _ => format!("See PORT documentation.  Code ({})", iv1),
    }
}

/// Run R's `nlminb()` loop. `objective` gets `.par` and returns the value
/// R's `asReal()` would give (NaN handling is the caller's job).
pub fn nlminb<E>(
    problem: &Problem,
    mut objective: impl FnMut(&[f64]) -> Result<f64, E>,
) -> Result<PortFit, E> {
    let n = problem.start.len();
    let mut iv = vec![0i32; 78 + 3 * n];
    let mut v = vec![0f64; 130 + n * (n + 27) / 2];
    glue::divset(2, &mut iv, &mut v);

    // Control options: iv entries are truncated to integers, as as.integer() does.
    let mut unknown_control = Vec::new();
    for (name, value) in problem.control {
        match pmatch(name) {
            Some(pos) => {
                let (_, slot) = PORT_CPOS[pos];
                if pos < 4 {
                    iv[slot - 1] = *value as i32;
                } else {
                    v[slot - 1] = *value;
                }
            }
            None => unknown_control.push(name.clone()),
        }
    }

    let mut x = problem.start.to_vec();
    let mut d = problem.scale.to_vec();
    let bounded = !problem.lower.is_empty();
    let mut b = Vec::with_capacity(2 * n);
    if bounded {
        for i in 0..n {
            b.push(problem.lower[i]);
            b.push(problem.upper[i]);
        }
    }

    let liv = iv.len() as c_int;
    let lv = v.len() as c_int;
    let nn = n as c_int;
    let mut fx = f64::INFINITY;
    loop {
        // SAFETY: every array is sized as R sizes it (iv, v, b, d, x) and the
        // lengths passed match those allocations.
        unsafe {
            if bounded {
                drmnfb_(
                    b.as_mut_ptr(),
                    d.as_mut_ptr(),
                    &mut fx,
                    iv.as_mut_ptr(),
                    &liv,
                    &lv,
                    &nn,
                    v.as_mut_ptr(),
                    x.as_mut_ptr(),
                );
            } else {
                drmnf_(
                    d.as_mut_ptr(),
                    &mut fx,
                    iv.as_mut_ptr(),
                    &liv,
                    &lv,
                    &nn,
                    v.as_mut_ptr(),
                    x.as_mut_ptr(),
                );
            }
        }
        fx = objective(&x)?;
        if iv[0] >= 3 {
            break;
        }
    }

    let iv1 = iv[0];
    let convergence = if (3..=6).contains(&iv1) { 0 } else { 1 };
    let message = port_message(iv1, &v);
    Ok(PortFit {
        par: x,
        objective: v[9],
        convergence,
        iterations: iv[30],
        evaluations_function: iv[5],
        evaluations_gradient: iv[29],
        message,
        unknown_control,
    })
}

#[cfg(feature = "python")]
mod python {
    use super::{nlminb, Problem};
    use pyo3::prelude::*;
    use pyo3::types::{PyDict, PyList};

    /// R's `rep_len(as.double(x), n)`, with `default` when `x` is None.
    fn rep_len(value: Option<&Bound<'_, PyAny>>, n: usize, default: f64) -> PyResult<Vec<f64>> {
        let Some(value) = value else {
            return Ok(vec![default; n]);
        };
        let src: Vec<f64> = match value.extract::<f64>() {
            Ok(x) => vec![x],
            Err(_) => value.extract::<Vec<f64>>()?,
        };
        if src.is_empty() {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "bound or scale must have length >= 1",
            ));
        }
        Ok((0..n).map(|i| src[i % src.len()]).collect())
    }

    fn warn(py: Python<'_>, message: &str) -> PyResult<()> {
        py.import("warnings")?.call_method1("warn", (message,))?;
        Ok(())
    }

    /// nlminb_port(objective, start, lower=None, upper=None, control=None, scale=None)
    ///
    /// Same driver as `stats::nlminb` without a gradient. `objective` takes
    /// the parameter list and returns a scalar. Returns a dict with `par`,
    /// `objective`, `convergence`, `iterations`, `evaluations` (`function`,
    /// `gradient`), and `message`.
    #[pyfunction]
    #[pyo3(name = "nlminb_port", signature = (objective, start, lower=None, upper=None, control=None, scale=None))]
    fn nlminb_port_py(
        py: Python<'_>,
        objective: Py<PyAny>,
        start: Vec<f64>,
        lower: Option<Bound<'_, PyAny>>,
        upper: Option<Bound<'_, PyAny>>,
        control: Option<Bound<'_, PyDict>>,
        scale: Option<Bound<'_, PyAny>>,
    ) -> PyResult<Py<PyAny>> {
        let n = start.len();
        if n < 1 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "'d' must be a nonempty numeric (double) vector",
            ));
        }
        let scale_v = rep_len(scale.as_ref(), n, 1.0)?;

        // R sets bounds only when some are finite; otherwise it uses drmnf.
        let lo = rep_len(lower.as_ref(), n, f64::NEG_INFINITY)?;
        let up = rep_len(upper.as_ref(), n, f64::INFINITY)?;
        let bounded = lo.iter().any(|&x| x != f64::NEG_INFINITY)
            || up.iter().any(|&x| x != f64::INFINITY);
        let (lo, up) = if bounded { (lo, up) } else { (Vec::new(), Vec::new()) };

        let mut control_v: Vec<(String, f64)> = Vec::new();
        if let Some(dict) = control.as_ref() {
            for (key, value) in dict.iter() {
                let name: String = key.extract()?;
                let val: f64 = value.extract()?;
                control_v.push((name, val));
            }
        }

        let problem = Problem {
            start: &start,
            scale: &scale_v,
            lower: &lo,
            upper: &up,
            control: &control_v,
        };

        let fit = nlminb(&problem, |x: &[f64]| -> PyResult<f64> {
            let arg = PyList::new(py, x.to_vec())?;
            let value = objective.call1(py, (arg,))?;
            let mut fx: f64 = value.bind(py).extract()?;
            if fx.is_nan() {
                warn(py, "NA/NaN function evaluation")?;
                fx = f64::INFINITY;
            }
            Ok(fx)
        })?;

        for name in &fit.unknown_control {
            warn(
                py,
                &format!("unrecognized control element named '{}' ignored", name),
            )?;
        }

        let out = PyDict::new(py);
        out.set_item("par", fit.par)?;
        out.set_item("objective", fit.objective)?;
        out.set_item("convergence", fit.convergence)?;
        out.set_item("iterations", fit.iterations)?;
        let evals = PyDict::new(py);
        evals.set_item("function", fit.evaluations_function)?;
        evals.set_item("gradient", fit.evaluations_gradient)?;
        out.set_item("evaluations", evals)?;
        out.set_item("message", fit.message)?;
        Ok(out.into())
    }

    #[pymodule]
    #[pyo3(name = "nlminb_port")]
    fn nlminb_port_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(nlminb_port_py, m)?)?;
        Ok(())
    }
}
