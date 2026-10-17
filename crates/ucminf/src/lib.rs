//! UCMINF, ported from ucminf 1.2.3 src/fortran.f.

mod blas;
mod ucminf;

pub use ucminf::{ucminf, UcminfOut};

#[cfg(feature = "python")]
mod python {
    use pyo3::prelude::*;
    use pyo3::types::PyAny;

    #[pyfunction]
    #[pyo3(name = "ucminf")]
    fn ucminf_py(
        py: Python<'_>,
        par: Vec<f64>,
        eps: Vec<f64>,
        mut stepmax: f64,
        mut maxeval: i32,
        mut w: Vec<f64>,
        mut icontr: i32,
        grad_mode: i32,
        grstep: Vec<f64>,
        function: Py<PyAny>,
        gradient: Option<Py<PyAny>>,
    ) -> PyResult<(Vec<f64>, i32, f64, f64, i32, Vec<f64>, f64)> {
        let mut par = par;
        let eps = [eps[0], eps[1]];
        let grstep = [grstep[0], grstep[1]];
        let mut func = |x: &[f64]| -> f64 {
            let value: f64 = function
                .call1(py, (x.to_vec(),))
                .expect("objective")
                .extract(py)
                .expect("numeric objective");
            value
        };
        let mut grad = |x: &[f64]| -> Vec<f64> {
            let gradient = gradient.as_ref().expect("gradient");
            gradient
                .call1(py, (x.to_vec(),))
                .expect("gradient")
                .extract(py)
                .expect("numeric gradient")
        };
        let out = super::ucminf(
            &mut par,
            &mut stepmax,
            eps,
            &mut maxeval,
            &mut w,
            &mut icontr,
            grad_mode,
            grstep,
            &mut func,
            &mut grad,
        );
        Ok((
            par,
            out.convergence,
            out.value,
            out.maxgradient,
            out.neval,
            w,
            stepmax,
        ))
    }

    #[pymodule]
    #[pyo3(name = "ucminf_engine")]
    fn ucminf_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(ucminf_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::ucminf;

    fn rosenbrock(x: &[f64]) -> f64 {
        let a = 1.0 - x[0];
        let b = x[1] - x[0] * x[0];
        a * a + 100.0 * (b * b)
    }

    fn rosenbrock_grad(x: &[f64]) -> Vec<f64> {
        vec![
            -400.0 * x[0] * (x[1] - x[0] * x[0]) - 2.0 * (1.0 - x[0]),
            200.0 * (x[1] - x[0] * x[0]),
        ]
    }

    #[test]
    fn rosenbrock_matches_r() {
        let n = 2usize;
        let half = (n + 12) / 2;
        let iw = n * half.max(n + 1) + 10;
        let mut x = vec![2.0, 0.5];
        let mut dx = 1.0;
        let mut maxfun = 500;
        let mut w = vec![0.0; iw];
        let mut icontr = 1;
        let out = ucminf(
            &mut x,
            &mut dx,
            [1e-6, 1e-12],
            &mut maxfun,
            &mut w,
            &mut icontr,
            0,
            [1e-6, 1e-8],
            &mut rosenbrock,
            &mut rosenbrock_grad,
        );
        assert!((x[0] - 0.99999999986174881).abs() < 1e-8, "x0 {x:?} conv {}", out.convergence);
        assert!((x[1] - 0.99999999974832132).abs() < 1e-8, "x1 {x:?}");
        assert!((out.value - 8.0734992537039702e-20).abs() < 1e-8);
        assert_eq!(out.convergence, 1);
        assert_eq!(out.neval, 21);
        let nn = n * (n + 1) / 2;
        let dn = 4 * n;
        let lower = &w[dn..dn + nn];
        assert!((lower[0] - 0.49753153272096456).abs() < 1e-8);
        assert!((lower[1] - 0.99518767130872576).abs() < 1e-8);
        assert!((lower[2] - 1.9956182663464994).abs() < 1e-8);
        assert!((out.maxgradient - 1.0205981836057282e-08).abs() < 1e-8);
        assert!((out.laststep - 6.4809888236556794e-08).abs() < 1e-8);
        assert!((dx - 0.12249999999999998).abs() < 1e-8);
    }

    #[test]
    fn rosenbrock_forward_difference_matches_r() {
        let n = 2usize;
        let half = (n + 12) / 2;
        let iw = n * half.max(n + 1) + 10;
        let mut x = vec![2.0, 0.5];
        let mut dx = 1.0;
        let mut maxfun = 500;
        let mut w = vec![0.0; iw];
        let mut icontr = 1;
        let out = ucminf(
            &mut x,
            &mut dx,
            [1e-6, 1e-12],
            &mut maxfun,
            &mut w,
            &mut icontr,
            1,
            [1e-6, 1e-8],
            &mut rosenbrock,
            &mut rosenbrock_grad,
        );
        assert!((x[0] - 0.99969996211219614).abs() < 1e-8, "{x:?} {}", out.convergence);
        assert!((x[1] - 0.99939932384757779).abs() < 1e-8, "{x:?}");
        assert!((out.value - 9.007039927147888e-08).abs() < 1e-8);
        assert_eq!(out.convergence, 4);
        assert_eq!(out.neval, 19);
    }
}
