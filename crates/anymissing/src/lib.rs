//! `anyMissing` from matrixStats `src/anyMissing.c`.
//!
//! A double is missing when it is NaN, which covers R's real NA. An integer is
//! missing when it equals R's `NA_INTEGER` sentinel. The scan returns as soon
//! as one selected value is missing. An NA index counts as missing.
//!
//! Empty input is FALSE before subscripts are validated, matching the C entry
//! point. `idxs = NULL` selects every element.

mod indices;

pub use indices::{
    positions_from_integer, positions_from_logical, positions_from_real, NA_INTEGER, NA_POSITION,
};

/// True when any selected value is missing.
///
/// `positions` is `None` for every element. Otherwise the entries are 0-based
/// indexes, and [`NA_POSITION`] is an NA index.
pub fn any_missing<T, F>(values: &[T], positions: Option<&[i64]>, mut missing: F) -> bool
where
    F: FnMut(&T) -> bool,
{
    if values.is_empty() {
        return false;
    }
    match positions {
        None => values.iter().any(|value| missing(value)),
        Some(indexes) => indexes.iter().any(|&index| {
            if index == NA_POSITION {
                return true;
            }
            let index = index as usize;
            index >= values.len() || missing(&values[index])
        }),
    }
}

pub fn any_missing_f64(values: &[f64], positions: Option<&[i64]>) -> bool {
    any_missing(values, positions, |value| value.is_nan())
}

pub fn any_missing_f32(values: &[f32], positions: Option<&[i64]>) -> bool {
    any_missing(values, positions, |value| value.is_nan())
}

pub fn any_missing_i32(values: &[i32], positions: Option<&[i64]>) -> bool {
    any_missing(values, positions, |value| *value == i32::MIN)
}

pub fn any_missing_i64(values: &[i64], positions: Option<&[i64]>) -> bool {
    any_missing(values, positions, |value| *value == NA_INTEGER)
}

#[cfg(feature = "python")]
mod py {
    use numpy::PyReadonlyArray1;
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::{
        any_missing_f32, any_missing_f64, any_missing_i32, any_missing_i64, positions_from_integer,
        positions_from_logical, positions_from_real,
    };

    fn slice_of<'a, T: numpy::Element>(
        values: &'a PyReadonlyArray1<'a, T>,
    ) -> PyResult<&'a [T]> {
        values
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))
    }

    fn positions_slice<'a>(
        positions: &'a Option<PyReadonlyArray1<'a, i64>>,
    ) -> PyResult<Option<&'a [i64]>> {
        match positions {
            None => Ok(None),
            Some(values) => Ok(Some(slice_of(values)?)),
        }
    }

    #[pyfunction]
    #[pyo3(signature = (values, positions=None))]
    fn scan_f64(
        values: PyReadonlyArray1<'_, f64>,
        positions: Option<PyReadonlyArray1<'_, i64>>,
    ) -> PyResult<bool> {
        Ok(any_missing_f64(slice_of(&values)?, positions_slice(&positions)?))
    }

    #[pyfunction]
    #[pyo3(signature = (values, positions=None))]
    fn scan_f32(
        values: PyReadonlyArray1<'_, f32>,
        positions: Option<PyReadonlyArray1<'_, i64>>,
    ) -> PyResult<bool> {
        Ok(any_missing_f32(slice_of(&values)?, positions_slice(&positions)?))
    }

    #[pyfunction]
    #[pyo3(signature = (values, positions=None))]
    fn scan_i32(
        values: PyReadonlyArray1<'_, i32>,
        positions: Option<PyReadonlyArray1<'_, i64>>,
    ) -> PyResult<bool> {
        Ok(any_missing_i32(slice_of(&values)?, positions_slice(&positions)?))
    }

    #[pyfunction]
    #[pyo3(signature = (values, positions=None))]
    fn scan_i64(
        values: PyReadonlyArray1<'_, i64>,
        positions: Option<PyReadonlyArray1<'_, i64>>,
    ) -> PyResult<bool> {
        Ok(any_missing_i64(slice_of(&values)?, positions_slice(&positions)?))
    }

    #[pyfunction]
    fn positions_integer(
        idxs: PyReadonlyArray1<'_, i64>,
        max_idx: i64,
        allow_out_of_bounds: bool,
    ) -> PyResult<Vec<i64>> {
        positions_from_integer(slice_of(&idxs)?, max_idx, allow_out_of_bounds)
            .map_err(PyValueError::new_err)
    }

    #[pyfunction]
    fn positions_real(
        idxs: PyReadonlyArray1<'_, f64>,
        max_idx: i64,
        allow_out_of_bounds: bool,
    ) -> PyResult<Vec<i64>> {
        positions_from_real(slice_of(&idxs)?, max_idx, allow_out_of_bounds)
            .map_err(PyValueError::new_err)
    }

    #[pyfunction]
    fn positions_logical(
        idxs: PyReadonlyArray1<'_, i8>,
        max_idx: i64,
        allow_out_of_bounds: bool,
    ) -> PyResult<Option<Vec<i64>>> {
        positions_from_logical(slice_of(&idxs)?, max_idx, allow_out_of_bounds)
            .map_err(PyValueError::new_err)
    }

    #[pymodule]
    fn anymissing(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(scan_f64, m)?)?;
        m.add_function(wrap_pyfunction!(scan_f32, m)?)?;
        m.add_function(wrap_pyfunction!(scan_i32, m)?)?;
        m.add_function(wrap_pyfunction!(scan_i64, m)?)?;
        m.add_function(wrap_pyfunction!(positions_integer, m)?)?;
        m.add_function(wrap_pyfunction!(positions_real, m)?)?;
        m.add_function(wrap_pyfunction!(positions_logical, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_and_clean_vectors_are_false() {
        assert!(!any_missing_f64(&[], None));
        assert!(!any_missing_f64(&[1.0, 2.0, f64::INFINITY], None));
        assert!(!any_missing_i32(&[1, 2, 3], None));
    }

    #[test]
    fn nan_and_integer_na_are_missing() {
        assert!(any_missing_f64(&[1.0, f64::NAN, 3.0], None));
        assert!(any_missing_i32(&[1, i32::MIN, 3], None));
        assert!(any_missing_i64(&[1, NA_INTEGER, 3], None));
    }

    #[test]
    fn an_na_index_is_missing_even_when_the_values_are_not() {
        assert!(any_missing_f64(&[1.0, 2.0, 3.0], Some(&[NA_POSITION])));
        assert!(!any_missing_f64(&[1.0, f64::NAN, 3.0], Some(&[0, 2])));
        assert!(any_missing_f64(&[1.0, f64::NAN, 3.0], Some(&[1])));
    }

    #[test]
    fn empty_input_ignores_positions() {
        assert!(!any_missing_f64(&[], Some(&[NA_POSITION])));
    }
}
