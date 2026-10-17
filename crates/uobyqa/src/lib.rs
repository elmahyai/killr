//! Powell UOBYQA, ported from minqa 1.2.8.
//!
//! `solve` keeps the signature, the Python `solve` name, and the Rosenbrock
//! tests. UOBYQA chooses its own interpolation count.

mod fortran;
mod lagmax;
mod trstep;
mod uobyqb;

pub fn solve(
    x: &mut [f64],
    rhobeg: f64,
    rhoend: f64,
    iprint: i32,
    maxfun: i32,
    calfun: &mut dyn FnMut(&[f64]) -> f64,
) -> Result<(i32, i32), String> {
    let n = x.len() as i32;
    if n < 2 {
        return Err("uobyqa requires at least two variables".into());
    }
    let mut ierr = 0;
    let len = (n * (42 + n * (23 + n * (8 + n))) + (2 * n * n + 4).max(18 * n)) / 4;
    let mut w = vec![0.0; len as usize];
    let nfev = uobyqb::uobyqa(
        n, x, rhobeg, rhoend, iprint, maxfun, &mut w, &mut ierr, calfun,
    );
    Ok((ierr, nfev))
}

#[cfg(feature = "python")]
mod python {
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;
    use pyo3::types::{PyAny, PyList};

    #[pyfunction]
    #[pyo3(name = "solve")]
    fn solve_py(
        py: Python<'_>,
        x: Vec<f64>,
        rhobeg: f64,
        rhoend: f64,
        iprint: i32,
        maxfun: i32,
        fun: Py<PyAny>,
    ) -> PyResult<(Vec<f64>, i32, i32)> {
        let mut x = x;
        let mut calfun = |point: &[f64]| {
            if point.iter().any(|value| !value.is_finite()) {
                panic!("non-finite x values not allowed in calfun");
            }
            let list = PyList::new(py, point.iter().copied()).expect("list");
            let value: f64 = fun
                .call1(py, (list,))
                .expect("objective")
                .extract(py)
                .expect("numeric");
            if value.is_finite() {
                value
            } else {
                f64::MAX
            }
        };
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            super::solve(&mut x, rhobeg, rhoend, iprint, maxfun, &mut calfun)
        }));
        match result {
            Ok(Ok((ierr, nfev))) => Ok((x, ierr, nfev)),
            Ok(Err(message)) => Err(PyValueError::new_err(message)),
            Err(_) => Err(PyValueError::new_err(
                "non-finite x values not allowed in calfun",
            )),
        }
    }

    #[pymodule]
    #[pyo3(name = "uobyqa")]
    fn uobyqa_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(solve_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::solve;

    fn rosenbrock_fn(x: &[f64]) -> f64 {
        100.0 * (x[1] - x[0] * x[0]).powi(2) + (1.0 - x[0]).powi(2)
    }

    #[test]
    fn rosenbrock() {
        let mut x = vec![1.0, 2.0];
        let (ierr, nfev) = solve(&mut x, 0.4, 4e-7, 0, 10000, &mut rosenbrock_fn).unwrap();
        assert_eq!(ierr, 0);
        assert_eq!(nfev, 61);
        assert!((x[0] - 0.99999999996671085).abs() < 1e-8);
        assert!((x[1] - 0.99999999994281841).abs() < 1e-8);
    }

    #[test]
    fn rosenbrock_maxfun() {
        let mut x = vec![1.0, 2.0];
        let (ierr, nfev) = solve(&mut x, 0.4, 4e-7, 0, 50, &mut rosenbrock_fn).unwrap();
        assert_eq!(ierr, 390);
        assert_eq!(nfev, 50);
        assert!((x[0] - 0.99996000787958761).abs() < 1e-8);
        assert!((x[1] - 0.99993279742667351).abs() < 1e-8);
    }
}
