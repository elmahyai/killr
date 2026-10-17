//! Mixed-model kernels from nlme `src/nlmefit.c` (`mixed_*`) and `src/nlme.c`
//! (`fit_nlme`). Matrices are column-major. The algorithms live in the sibling
//! modules; this file only publishes them and the pyo3 bindings.

mod dims;
mod fit;
mod linalg;
mod mixed;
mod optif;

pub use dims::Dims;
pub use fit::fit_nlme;
pub use mixed::{
    count_dm_half_pars, generate_dm_half, generate_theta, inner_perc, inner_perc_table,
    jacobi_values, mixed_combined, mixed_decomp, mixed_em, mixed_estimate, mixed_loglik,
    KernelError,
};

#[cfg(feature = "python")]
mod python {
    use super::{
        count_dm_half_pars, fit_nlme, generate_dm_half, generate_theta, inner_perc,
        inner_perc_table, jacobi_values, mixed_combined, mixed_decomp, mixed_em, mixed_estimate,
        mixed_loglik, Dims,
    };
    use pyo3::prelude::*;
    use pyo3::types::PyAny;

    fn value_error(err: super::KernelError) -> PyErr {
        pyo3::exceptions::PyValueError::new_err(err.0)
    }

    #[pyfunction]
    #[pyo3(name = "mixed_decomp")]
    fn mixed_decomp_py(mut zxy: Vec<f64>, pdims: Vec<i32>) -> PyResult<Vec<f64>> {
        Ok(mixed_decomp(&mut zxy, &pdims))
    }

    #[pyfunction]
    #[pyo3(name = "mixed_loglik")]
    fn mixed_loglik_py(
        mut zxy: Vec<f64>,
        pdims: Vec<i32>,
        pars: Vec<f64>,
        settings: Vec<i32>,
        sigma: f64,
    ) -> PyResult<(Vec<f64>, f64)> {
        Ok(mixed_loglik(&mut zxy, &pdims, &pars, &settings, sigma))
    }

    #[pyfunction]
    #[pyo3(name = "mixed_estimate")]
    fn mixed_estimate_py(
        mut zxy: Vec<f64>,
        pdims: Vec<i32>,
        dm_half: Vec<f64>,
        rml: i32,
        invert: i32,
        sigma: f64,
    ) -> PyResult<(f64, Vec<f64>)> {
        mixed_estimate(&mut zxy, &pdims, &dm_half, rml, invert, sigma).map_err(value_error)
    }

    /// Returns the updated precision factor, the profile log-likelihood, the
    /// stored triangular factor, and the log residual sum of squares.
    #[pyfunction]
    #[pyo3(name = "mixed_em")]
    fn mixed_em_py(
        zxy: Vec<f64>,
        pdims: Vec<i32>,
        mut dm_half: Vec<f64>,
        n_iter: i32,
        pd_class: Vec<i32>,
        rml: i32,
        sigma: f64,
    ) -> PyResult<(Vec<f64>, f64, Vec<f64>, f64)> {
        let (lik, ra, lrss) =
            mixed_em(&zxy, &pdims, &mut dm_half, n_iter, &pd_class, rml, sigma).map_err(value_error)?;
        Ok((dm_half, lik, ra, lrss))
    }

    /// Returns log-likelihood, the fixed-effect block, log residual sum of
    /// squares, the optimizer code, the updated precision factor, and `zxy`.
    #[pyfunction]
    #[pyo3(name = "mixed_combined")]
    fn mixed_combined_py(
        mut zxy: Vec<f64>,
        pdims: Vec<i32>,
        mut dm_half: Vec<f64>,
        n_iter: i32,
        pd_class: Vec<i32>,
        rml: i32,
        sigma: f64,
    ) -> PyResult<(f64, Vec<f64>, f64, i32, Vec<f64>, Vec<f64>)> {
        let (log_lik, r0, lrss, info) = mixed_combined(
            &mut zxy,
            &pdims,
            &mut dm_half,
            n_iter,
            &pd_class,
            rml,
            sigma,
        )
        .map_err(value_error)?;
        Ok((log_lik, r0, lrss, info, dm_half, zxy))
    }

    #[pyfunction]
    #[pyo3(name = "inner_perc")]
    fn inner_perc_py(x: Vec<f64>, grp: Vec<i32>) -> f64 {
        inner_perc(&x, &grp)
    }

    #[pyfunction]
    #[pyo3(name = "inner_perc_table")]
    fn inner_perc_table_py(x: Vec<f64>, grps: Vec<i32>, p: usize, q: usize, n: usize) -> Vec<f64> {
        inner_perc_table(&x, &grps, p, q, n)
    }

    #[pyfunction]
    #[pyo3(name = "jacobi_values")]
    fn jacobi_values_py(a: Vec<f64>, q: usize) -> Vec<f64> {
        jacobi_values(&a, q)
    }

    #[pyfunction]
    #[pyo3(name = "factor_from_parameters")]
    fn factor_from_parameters_py(
        pdims: Vec<i32>,
        pd_class: Vec<i32>,
        pars: Vec<f64>,
    ) -> PyResult<Vec<f64>> {
        let dims = Dims::parse(&pdims);
        let dm_len = dims.dm_off[dims.q as usize] as usize;
        let mut dm = vec![0.0; dm_len];
        generate_dm_half(&mut dm, &dims, &pd_class, &pars);
        Ok(dm)
    }

    #[pyfunction]
    #[pyo3(name = "parameters_from_factor")]
    fn parameters_from_factor_py(
        pdims: Vec<i32>,
        pd_class: Vec<i32>,
        mut dm_half: Vec<f64>,
    ) -> PyResult<Vec<f64>> {
        let dims = Dims::parse(&pdims);
        let npar = count_dm_half_pars(&dims, &pd_class);
        let mut theta = vec![0.0; npar];
        generate_theta(&mut theta, &dims, &pd_class, &mut dm_half).map_err(value_error)?;
        Ok(theta)
    }

    #[pyfunction]
    #[pyo3(name = "fit_nlme")]
    fn fit_nlme_py(
        py: Python<'_>,
        mut theta: Vec<f64>,
        mut dm_half: Vec<f64>,
        mut groups: Vec<i32>,
        pdims: Vec<i32>,
        pd_class: Vec<i32>,
        cor_factor: Vec<f64>,
        var_weights: Vec<f64>,
        cor_dims: Vec<i32>,
        mut settings: Vec<f64>,
        mut additional: Vec<f64>,
        cor_opt: i32,
        var_opt: i32,
        sigma: f64,
        model: Py<PyAny>,
    ) -> PyResult<(Vec<f64>, Vec<f64>, Vec<i32>, Vec<f64>, Vec<f64>)> {
        let mut callback_error: Option<String> = None;
        let result = py.detach(|| {
            fit_nlme(
                &mut theta,
                &mut dm_half,
                &mut groups,
                &pdims,
                &pd_class,
                &cor_factor,
                &var_weights,
                &cor_dims,
                &mut settings,
                &mut additional,
                cor_opt,
                var_opt,
                sigma,
                |pars| match call_model(&model, pars) {
                    Ok(values) => values,
                    Err(message) => {
                        callback_error = Some(message);
                        Vec::new()
                    }
                },
            )
        });
        if let Some(message) = callback_error {
            return Err(pyo3::exceptions::PyValueError::new_err(message));
        }
        result.map_err(value_error)?;
        Ok((theta, dm_half, groups, settings, additional))
    }

    fn call_model(model: &Py<PyAny>, pars: &[f64]) -> Result<Vec<f64>, String> {
        Python::attach(|py| {
            let obj = model
                .call1(py, (pars.to_vec(),))
                .map_err(|err| err.to_string())?;
            obj.extract::<Vec<f64>>(py).map_err(|err| err.to_string())
        })
    }

    #[pymodule]
    fn nlmemixed(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(mixed_decomp_py, m)?)?;
        m.add_function(wrap_pyfunction!(mixed_loglik_py, m)?)?;
        m.add_function(wrap_pyfunction!(mixed_estimate_py, m)?)?;
        m.add_function(wrap_pyfunction!(mixed_em_py, m)?)?;
        m.add_function(wrap_pyfunction!(mixed_combined_py, m)?)?;
        m.add_function(wrap_pyfunction!(inner_perc_py, m)?)?;
        m.add_function(wrap_pyfunction!(inner_perc_table_py, m)?)?;
        m.add_function(wrap_pyfunction!(jacobi_values_py, m)?)?;
        m.add_function(wrap_pyfunction!(factor_from_parameters_py, m)?)?;
        m.add_function(wrap_pyfunction!(parameters_from_factor_py, m)?)?;
        m.add_function(wrap_pyfunction!(fit_nlme_py, m)?)?;
        Ok(())
    }
}
