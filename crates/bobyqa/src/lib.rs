//! Powell BOBYQA, ported from minqa 1.2.8.
//!
//! Arrays inside the Fortran are 1-based; a slice passed into a subroutine
//! is that subroutine's index 1 at position 0.

mod altmov;
mod arr;
mod bobyqb;
mod prelim;
mod rescue;
mod trsbox;
mod update;

fn split_n<'a>(rest: &mut &'a mut [f64], n: usize) -> &'a mut [f64] {
    let slice = std::mem::replace(rest, &mut []);
    let (head, tail) = slice.split_at_mut(n);
    *rest = tail;
    head
}

pub fn solve(
    x: &mut [f64],
    xl: &[f64],
    xu: &[f64],
    npt: i32,
    rhobeg: f64,
    rhoend: f64,
    iprint: i32,
    maxfun: i32,
    calfun: &mut dyn FnMut(&[f64]) -> f64,
) -> Result<(i32, i32), String> {
    let n = x.len() as i32;
    if xl.len() < x.len() || xu.len() < x.len() {
        return Err("xl and xu must each have one bound per variable".into());
    }
    let np = n + 1;
    if npt < n + 2 || npt > ((n + 2) * np) / 2 {
        return Ok((10, 0));
    }
    let ndim = npt + n;
    let len = (npt + 5) * (npt + n) + 3 * n * (n + 5) / 2;
    if len < 0 {
        return Err("work array length overflowed".into());
    }
    let mut w = vec![0.0; len as usize];
    let mut rest = w.as_mut_slice();
    let xbase = split_n(&mut rest, n as usize);
    let xpt = split_n(&mut rest, (n * npt) as usize);
    let fval = split_n(&mut rest, npt as usize);
    let xopt = split_n(&mut rest, n as usize);
    let gopt = split_n(&mut rest, n as usize);
    let hq = split_n(&mut rest, ((n * np) / 2) as usize);
    let pq = split_n(&mut rest, npt as usize);
    let bmat = split_n(&mut rest, (ndim * n) as usize);
    let zmat = split_n(&mut rest, (npt * (npt - np)) as usize);
    let sl = split_n(&mut rest, n as usize);
    let su = split_n(&mut rest, n as usize);
    let xnew = split_n(&mut rest, n as usize);
    let xalt = split_n(&mut rest, n as usize);
    let d = split_n(&mut rest, n as usize);
    let vlag = split_n(&mut rest, ndim as usize);
    let scratch = rest;

    for j in 1..=n {
        let temp = xu[(j - 1) as usize] - xl[(j - 1) as usize];
        if temp < rhobeg + rhobeg {
            return Ok((20, 0));
        }
        let j0 = (j - 1) as usize;
        sl[j0] = xl[j0] - x[j0];
        su[j0] = xu[j0] - x[j0];
        if sl[j0] >= -rhobeg {
            if sl[j0] >= 0.0 {
                x[j0] = xl[j0];
                sl[j0] = 0.0;
                su[j0] = temp;
            } else {
                x[j0] = xl[j0] + rhobeg;
                sl[j0] = -rhobeg;
                su[j0] = crate::arr::dmax1(xu[j0] - x[j0], rhobeg);
            }
        } else if su[j0] <= rhobeg {
            if su[j0] <= 0.0 {
                x[j0] = xu[j0];
                sl[j0] = -temp;
                su[j0] = 0.0;
            } else {
                x[j0] = xu[j0] - rhobeg;
                sl[j0] = crate::arr::dmin1(xl[j0] - x[j0], -rhobeg);
                su[j0] = rhobeg;
            }
        }
    }

    let mut ierr = 0;
    let nf = bobyqb::bobyqb(
        n, npt, x, xl, xu, rhobeg, rhoend, iprint, maxfun, xbase, xpt, fval, xopt, gopt, hq,
        pq, bmat, zmat, ndim, sl, su, xnew, xalt, d, vlag, scratch, &mut ierr, calfun,
    );
    Ok((ierr, nf))
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
        xl: Vec<f64>,
        xu: Vec<f64>,
        npt: i32,
        rhobeg: f64,
        rhoend: f64,
        iprint: i32,
        maxfun: i32,
        fun: Py<PyAny>,
    ) -> PyResult<(Vec<f64>, i32, i32)> {
        let mut x = x;
        let mut calls = 0i32;
        let mut calfun = |point: &[f64]| {
            calls += 1;
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
            super::solve(
                &mut x,
                &xl,
                &xu,
                npt,
                rhobeg,
                rhoend,
                iprint,
                maxfun,
                &mut calfun,
            )
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
    #[pyo3(name = "bobyqa")]
    fn bobyqa_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(solve_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::solve;

    fn rosenbrock(x: &[f64]) -> f64 {
        100.0 * (x[1] - x[0] * x[0]).powi(2) + (1.0 - x[0]).powi(2)
    }

    #[test]
    fn rosenbrock_box() {
        let mut x = vec![1.0, 2.0];
        let (ierr, nfev) = solve(
            &mut x,
            &[0.0, 0.0],
            &[4.0, 4.0],
            4,
            0.4,
            4e-7,
            0,
            10000,
            &mut rosenbrock,
        )
        .unwrap();
        assert_eq!(ierr, 0);
        assert_eq!(nfev, 341);
        assert!((x[0] - 0.99999996890168075).abs() < 1e-8);
        assert!((x[1] - 0.99999992830554285).abs() < 1e-8);
    }

    #[test]
    fn rosenbrock_maxfun() {
        let mut x = vec![1.0, 2.0];
        let (ierr, nfev) = solve(
            &mut x,
            &[0.0, 0.0],
            &[4.0, 4.0],
            4,
            0.4,
            4e-7,
            0,
            50,
            &mut rosenbrock,
        )
        .unwrap();
        assert_eq!(ierr, 390);
        assert_eq!(nfev, 50);
        assert!((x[0] - 1.3440635953209148).abs() < 1e-8);
        assert!((x[1] - 1.8113512115466119).abs() < 1e-8);
    }
}
