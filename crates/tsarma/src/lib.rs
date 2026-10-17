//! Conditional ARMA residuals from tseries `src/arma.c`.

pub fn tseries_arma(
    x: &[f64],
    ar: &[i32],
    ma: &[i32],
    coef: &[f64],
    intercept: bool,
    u: &mut [f64],
) {
    let n = x.len();
    let arl = ar.len();
    let mal = ma.len();
    let max_order = ar
        .iter()
        .chain(ma.iter())
        .copied()
        .max()
        .unwrap_or(0)
        .max(0) as usize;
    for i in max_order..n {
        let mut sum = if intercept { coef[mal + arl] } else { 0.0 };
        for (j, &lag) in ar.iter().enumerate() {
            sum += coef[j] * x[i - lag as usize];
        }
        for (j, &lag) in ma.iter().enumerate() {
            sum += coef[j + arl] * u[i - lag as usize];
        }
        u[i] = x[i] - sum;
    }
}

#[cfg(feature = "python")]
mod py {
    use numpy::{IntoPyArray, PyArray1, PyReadonlyArray1};
    use pyo3::prelude::*;

    use crate::tseries_arma;

    #[pyfunction]
    #[pyo3(signature = (x, ar, ma, coef, intercept))]
    fn arma_css<'py>(
        py: Python<'py>,
        x: PyReadonlyArray1<'py, f64>,
        ar: Vec<i32>,
        ma: Vec<i32>,
        coef: PyReadonlyArray1<'py, f64>,
        intercept: bool,
    ) -> PyResult<Bound<'py, PyArray1<f64>>> {
        let x = x.as_slice()?;
        let coef = coef.as_slice()?;
        let mut u = vec![0.0; x.len()];
        tseries_arma(x, &ar, &ma, coef, intercept, &mut u);
        Ok(u.into_pyarray(py))
    }

    #[pymodule]
    fn tsarma(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(arma_css, m)?)?;
        Ok(())
    }
}
