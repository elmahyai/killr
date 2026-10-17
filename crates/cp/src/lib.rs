//! Mallows' Cp for blocked polynomial fits, ported from KernSmooth `src/cp.f`.
//!
//! The `(x, y)` pairs must already be sorted by `x`. `qq` is one more than the
//! polynomial degree. The QR factorization is LINPACK `dqrdc` and `dqrsl`
//! with `job = 100`.

use linpack::{dqrdc, dqrsl};

/// Mallows' Cp for `nmax` choices of the number of blocks.
///
/// The `i`-th entry, counting from zero, is the Cp value for `i + 1` blocks.
/// KernSmooth selects the first minimum.
pub fn cp(x: &[f64], y: &[f64], qq: usize, nmax: usize) -> Result<Vec<f64>, String> {
    if x.len() != y.len() {
        return Err("x and y must have the same length".into());
    }
    let n = x.len();
    if n == 0 || qq == 0 || nmax == 0 {
        return Err("x, qq, and nmax must be non-empty".into());
    }
    if qq > n {
        return Err("qq requires more observations than x contains".into());
    }

    let mut rss = vec![0.0; nmax];
    let mut xmat = vec![0.0; n * qq];
    let mut qraux = vec![0.0; qq];
    let mut coef = vec![0.0; qq];
    let mut qty = vec![0.0; n];
    for nval in 1..=nmax {
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
            let mut residual_sum = 0.0;
            for (offset, &xj) in x[start..end].iter().enumerate() {
                let mut fit = coef[0];
                for column in 2..=qq {
                    fit += coef[column - 1] * xj.powi((column as i32) - 1);
                }
                let residual = y[start + offset] - fit;
                residual_sum += residual * residual;
            }
            rss[nval - 1] += residual_sum;
        }
    }

    let scale = n as f64 - (qq * nmax) as f64;
    let denom = rss[nmax - 1];
    let mut cpvals = vec![0.0; nmax];
    for i in 1..=nmax {
        cpvals[i - 1] = scale * rss[i - 1] / denom + (2 * qq * i) as f64 - n as f64;
    }
    Ok(cpvals)
}

#[cfg(feature = "python")]
mod py {
    use numpy::{IntoPyArray, PyReadonlyArray1};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    #[pyfunction]
    #[pyo3(name = "cp")]
    fn cp_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray1<'py, f64>,
        y: PyReadonlyArray1<'py, f64>,
        qq: usize,
        nmax: usize,
    ) -> PyResult<Bound<'py, numpy::PyArray1<f64>>> {
        let xs = x
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        let ys = y
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        let values = crate::cp(xs, ys, qq, nmax).map_err(PyValueError::new_err)?;
        Ok(values.into_pyarray(py))
    }

    #[pymodule]
    fn cp(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(cp_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::cp;

    #[test]
    fn one_block_has_cp_equal_to_the_number_of_coefficients() {
        let x: Vec<f64> = (0..10).map(|i| i as f64).collect();
        let y: Vec<f64> = x.iter().map(|value| value.sin()).collect();
        let values = cp(&x, &y, 5, 1).unwrap();
        assert!((values[0] - 5.0).abs() < 1e-8, "cp={}", values[0]);
    }
}
