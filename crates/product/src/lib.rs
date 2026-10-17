//! Product of a numeric vector, ported from matrixStats `src/productExpSumLog.c`.
//!
//! The product is `exp(sum(log(abs(x))))` with a separate sign. Empty input
//! returns 1. Index rules from `src/validateIndices.c` live in this crate.

mod indices;
mod prod;

pub use indices::{Idxs, IndexError, NA_INTEGER};
pub use prod::{product, product_integers, r_na, R_NA_BITS};

#[cfg(feature = "python")]
mod py {
    use numpy::PyReadonlyArray1;
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::indices::Idxs;
    use crate::{product as product_values, product_integers};

    fn as_slice<'a, T: numpy::Element>(array: &'a PyReadonlyArray1<'a, T>) -> PyResult<&'a [T]> {
        array
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))
    }

    fn finish(result: Result<f64, crate::IndexError>) -> PyResult<f64> {
        result.map_err(|err| PyValueError::new_err(err.message))
    }

    #[pyfunction]
    fn product_f64(x: PyReadonlyArray1<'_, f64>, na_rm: bool) -> PyResult<f64> {
        let slice = as_slice(&x)?;
        finish(product_values(slice, Idxs::All, na_rm))
    }

    #[pyfunction]
    fn product_f64_i64(
        x: PyReadonlyArray1<'_, f64>,
        idxs: PyReadonlyArray1<'_, i64>,
        na_rm: bool,
    ) -> PyResult<f64> {
        let values = as_slice(&x)?;
        let index = as_slice(&idxs)?;
        finish(product_values(values, Idxs::Integer(index), na_rm))
    }

    #[pyfunction]
    fn product_f64_f64(
        x: PyReadonlyArray1<'_, f64>,
        idxs: PyReadonlyArray1<'_, f64>,
        na_rm: bool,
    ) -> PyResult<f64> {
        let values = as_slice(&x)?;
        let index = as_slice(&idxs)?;
        finish(product_values(values, Idxs::Real(index), na_rm))
    }

    #[pyfunction]
    fn product_f64_logical(
        x: PyReadonlyArray1<'_, f64>,
        idxs: PyReadonlyArray1<'_, i8>,
        na_rm: bool,
    ) -> PyResult<f64> {
        let values = as_slice(&x)?;
        let index = as_slice(&idxs)?;
        finish(product_values(values, Idxs::Logical(index), na_rm))
    }

    #[pyfunction]
    fn product_i64(x: PyReadonlyArray1<'_, i64>, na_rm: bool) -> PyResult<f64> {
        let slice = as_slice(&x)?;
        finish(product_integers(slice, Idxs::All, na_rm))
    }

    #[pyfunction]
    fn product_i64_i64(
        x: PyReadonlyArray1<'_, i64>,
        idxs: PyReadonlyArray1<'_, i64>,
        na_rm: bool,
    ) -> PyResult<f64> {
        let values = as_slice(&x)?;
        let index = as_slice(&idxs)?;
        finish(product_integers(values, Idxs::Integer(index), na_rm))
    }

    #[pyfunction]
    fn product_i64_f64(
        x: PyReadonlyArray1<'_, i64>,
        idxs: PyReadonlyArray1<'_, f64>,
        na_rm: bool,
    ) -> PyResult<f64> {
        let values = as_slice(&x)?;
        let index = as_slice(&idxs)?;
        finish(product_integers(values, Idxs::Real(index), na_rm))
    }

    #[pyfunction]
    fn product_i64_logical(
        x: PyReadonlyArray1<'_, i64>,
        idxs: PyReadonlyArray1<'_, i8>,
        na_rm: bool,
    ) -> PyResult<f64> {
        let values = as_slice(&x)?;
        let index = as_slice(&idxs)?;
        finish(product_integers(values, Idxs::Logical(index), na_rm))
    }

    #[pymodule]
    fn product(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(product_f64, m)?)?;
        m.add_function(wrap_pyfunction!(product_f64_i64, m)?)?;
        m.add_function(wrap_pyfunction!(product_f64_f64, m)?)?;
        m.add_function(wrap_pyfunction!(product_f64_logical, m)?)?;
        m.add_function(wrap_pyfunction!(product_i64, m)?)?;
        m.add_function(wrap_pyfunction!(product_i64_i64, m)?)?;
        m.add_function(wrap_pyfunction!(product_i64_f64, m)?)?;
        m.add_function(wrap_pyfunction!(product_i64_logical, m)?)?;
        Ok(())
    }
}
