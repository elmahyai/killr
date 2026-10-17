//! Blocked polynomial estimates, ported from KernSmooth `src/blkest.f`.
//!
//! The `(x, y)` pairs must already be sorted by `x`, as the Fortran routine
//! assumes. Each block is a degree-`q` least-squares fit. The QR factorization
//! is LINPACK `dqrdc` and `dqrsl` with `job = 100`.

use linpack::{dqrdc, dqrsl};

/// Estimates from a blocked polynomial fit.
///
/// `nval` is the number of blocks and `q` is the polynomial degree. KernSmooth
/// calls this with `q = 4`. Returns `(sigsqe, th22e, th24e)`.
pub fn blkest(x: &[f64], y: &[f64], nval: usize, q: usize) -> Result<(f64, f64, f64), String> {
    if x.len() != y.len() {
        return Err("x and y must have the same length".into());
    }
    let n = x.len();
    if n == 0 || nval == 0 {
        return Err("x and the number of blocks must be non-empty".into());
    }
    if q < 4 {
        return Err("q must be at least 4".into());
    }
    let qq = q + 1;
    if qq > n {
        return Err("q requires more observations than x contains".into());
    }

    let mut rss = 0.0;
    let mut th22 = 0.0;
    let mut th24 = 0.0;
    let mut xmat = vec![0.0; n * qq];
    let mut qraux = vec![0.0; qq];
    let mut coef = vec![0.0; qq];
    let mut qty = vec![0.0; n];
    let idiv = n / nval;
    for block in 1..=nval {
        let start = (block - 1) * idiv;
        let end = if block == nval { n } else { block * idiv };
        let nj = end - start;
        if nj == 0 {
            continue;
        }
        xmat.fill(0.0);
        qraux.fill(0.0);
        coef.fill(0.0);
        qty.fill(0.0);
        for (row, &xj) in x[start..end].iter().enumerate() {
            xmat[row] = 1.0;
            for column in 2..=qq {
                xmat[(column - 1) * n + row] = xj.powi((column as i32) - 1);
            }
        }
        dqrdc(
            &mut xmat,
            n,
            nj,
            qq,
            &mut qraux,
            &mut [],
            &mut [],
            0,
        );
        dqrsl(
            &mut xmat,
            n,
            nj,
            qq,
            &qraux,
            &y[start..end],
            &mut [],
            &mut qty,
            &mut coef,
            &mut [],
            &mut [],
            100,
        );
        for (offset, &xj) in x[start..end].iter().enumerate() {
            let mut fit = coef[0];
            let mut second = 2.0 * coef[2];
            let mut fourth = 24.0 * coef[4];
            for k in 2..=qq {
                let power = xj.powi((k as i32) - 1);
                fit += coef[k - 1] * power;
                if k <= q - 1 {
                    second += (k as f64) * ((k + 1) as f64) * coef[k + 1] * power;
                    if k <= q - 3 {
                        fourth += (k as f64)
                            * ((k + 1) as f64)
                            * ((k + 2) as f64)
                            * ((k + 3) as f64)
                            * coef[k + 3]
                            * power;
                    }
                }
            }
            let residual = y[start + offset] - fit;
            rss += residual * residual;
            th22 += second * second;
            th24 += second * fourth;
        }
    }

    let denominator = n as f64 - (qq * nval) as f64;
    Ok((rss / denominator, th22 / n as f64, th24 / n as f64))
}

#[cfg(feature = "python")]
mod py {
    use numpy::PyReadonlyArray1;
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    #[pyfunction]
    #[pyo3(name = "blkest")]
    fn blkest_py(
        x: PyReadonlyArray1<'_, f64>,
        y: PyReadonlyArray1<'_, f64>,
        nval: usize,
        q: usize,
    ) -> PyResult<(f64, f64, f64)> {
        let xs = x
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        let ys = y
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        crate::blkest(xs, ys, nval, q).map_err(PyValueError::new_err)
    }

    #[pymodule]
    fn blkest(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(blkest_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::blkest;

    #[test]
    fn quartic_block_recovers_the_fourth_derivative() {
        let x: Vec<f64> = (0..21).map(|i| -1.0 + 0.1 * i as f64).collect();
        let y: Vec<f64> = x.iter().map(|value| value.powi(4)).collect();
        let (sigsqe, th22e, th24e) = blkest(&x, &y, 1, 4).unwrap();
        let mean22 = x
            .iter()
            .map(|value| {
                let second = 12.0 * value * value;
                second * second
            })
            .sum::<f64>()
            / x.len() as f64;
        let mean24 = x
            .iter()
            .map(|value| 12.0 * value * value * 24.0)
            .sum::<f64>()
            / x.len() as f64;
        assert!(sigsqe.abs() < 1e-8, "sigsqe={sigsqe}");
        assert!((th22e - mean22).abs() < 1e-6, "th22e={th22e} expected={mean22}");
        assert!((th24e - mean24).abs() < 1e-6, "th24e={th24e} expected={mean24}");
    }
}
