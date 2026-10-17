//! Powell NEWUOA, ported from minqa 1.2.8.

mod bigden;
mod biglag;
mod fortran;
mod newuob;
mod trsapp;
mod update;

pub fn solve(
    x: &mut [f64],
    npt: i32,
    rhobeg: f64,
    rhoend: f64,
    iprint: i32,
    maxfun: i32,
    calfun: &mut dyn FnMut(&[f64]) -> f64,
) -> Result<(i32, i32), String> {
    let n = x.len() as i32;
    let np = n + 1;
    if npt < n + 2 || npt > ((n + 2) * np) / 2 {
        return Ok((10, 0));
    }
    let nu = x.len();
    let npt_u = npt as usize;
    let len = (npt_u + 13) * (npt_u + nu) + 3 * nu * (nu + 3) / 2;
    let mut w = vec![0.0; len];
    let mut ierr = 0;
    let nfev = newuob::newuob(
        n, npt, x, rhobeg, rhoend, iprint, maxfun, &mut w, &mut ierr, calfun,
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
        npt: i32,
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
            super::solve(&mut x, npt, rhobeg, rhoend, iprint, maxfun, &mut calfun)
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
    #[pyo3(name = "newuoa")]
    fn newuoa_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(solve_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
fn rosenbrock(x: &[f64]) -> f64 {
    100.0 * (x[1] - x[0] * x[0]).powi(2) + (1.0 - x[0]).powi(2)
}

#[cfg(test)]
mod tests {
    use super::solve;

    #[test]
    fn rosenbrock() {
        let mut x = vec![1.0, 2.0];
        let (ierr, nfev) = solve(&mut x, 4, 0.4, 4e-7, 0, 10000, &mut super::rosenbrock).unwrap();
        assert_eq!(ierr, 0);
        assert_eq!(nfev, 136);
        assert!((x[0] - 1.0000011621217628).abs() < 1e-8);
        assert!((x[1] - 1.0000023168272665).abs() < 1e-8);
    }

    #[test]
    fn rosenbrock_maxfun() {
        let mut x = vec![1.0, 2.0];
        let (ierr, nfev) = solve(&mut x, 4, 0.4, 4e-7, 0, 50, &mut super::rosenbrock).unwrap();
        assert_eq!(ierr, 390);
        assert_eq!(nfev, 50);
        assert!((x[0] - 1.3732077479495206).abs() < 1e-8);
        assert!((x[1] - 1.8869792152398259).abs() < 1e-8);
    }
}
