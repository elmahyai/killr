//! `signTabulate` from matrixStats `src/signTabulate.c`.
//!
//! A double value contributes to one of negative, zero, positive, or missing.
//! Negative and positive infinities are also counted on their own, and they
//! stay inside the negative and positive totals. An integer value has no
//! infinity counts. Integer missing values are R's `NA_INTEGER` (`i32::MIN`).
//! Double missing values are NaN, which covers R's real NA.
//!
//! `idxs = NULL` selects every element. Validation allows out-of-bounds
//! indexes, and each of those is counted as missing.

mod indices;

use indices::{positions_from_integer, positions_from_logical, positions_from_real, NA_POSITION};

/// Which elements to visit. [`Visit::All`] is R's `idxs = NULL`.
#[derive(Debug, Clone, PartialEq)]
pub enum Visit {
    All,
    At(Vec<i64>),
}

pub fn visit_integer(idxs: &[i64], n: i64) -> Result<Visit, String> {
    Ok(Visit::At(positions_from_integer(idxs, n, true)?))
}

pub fn visit_real(idxs: &[f64], n: i64) -> Result<Visit, String> {
    Ok(Visit::At(positions_from_real(idxs, n, true)?))
}

pub fn visit_logical(flags: &[i8], n: i64) -> Result<Visit, String> {
    match positions_from_logical(flags, n, true)? {
        None => Ok(Visit::All),
        Some(pos) => Ok(Visit::At(pos)),
    }
}

fn value_at<T: Copy>(x: &[T], pos: i64, missing: T) -> T {
    if pos == NA_POSITION {
        missing
    } else {
        x[pos as usize]
    }
}

/// Counts for a double vector, in R's name order.
///
/// `[-1, 0, +1, NA, -Inf, +Inf]`. `-Inf` is included in `-1`, and `+Inf` is
/// included in `+1`.
pub fn sign_tabulate_f64(x: &[f64], visit: &Visit) -> [i64; 6] {
    let mut n_neg = 0i64;
    let mut n_zero = 0i64;
    let mut n_pos = 0i64;
    let mut n_na = 0i64;
    let mut n_neg_inf = 0i64;
    let mut n_pos_inf = 0i64;
    let n = match visit {
        Visit::All => x.len(),
        Visit::At(pos) => pos.len(),
    };
    for ii in 0..n {
        let xi = match visit {
            Visit::All => x[ii],
            Visit::At(pos) => value_at(x, pos[ii], f64::NAN),
        };
        if xi.is_nan() {
            n_na += 1;
        } else if xi > 0.0 {
            n_pos += 1;
            if xi == f64::INFINITY {
                n_pos_inf += 1;
            }
        } else if xi < 0.0 {
            n_neg += 1;
            if xi == f64::NEG_INFINITY {
                n_neg_inf += 1;
            }
        } else if xi == 0.0 {
            n_zero += 1;
        }
    }
    [n_neg, n_zero, n_pos, n_na, n_neg_inf, n_pos_inf]
}

/// Counts for an integer vector, in R's name order `[-1, 0, +1, NA]`.
///
/// There is no infinity pair. `i32::MIN` is missing, not negative.
pub fn sign_tabulate_i32(x: &[i32], visit: &Visit) -> [i64; 4] {
    let mut n_neg = 0i64;
    let mut n_zero = 0i64;
    let mut n_pos = 0i64;
    let mut n_na = 0i64;
    let n = match visit {
        Visit::All => x.len(),
        Visit::At(pos) => pos.len(),
    };
    for ii in 0..n {
        let xi = match visit {
            Visit::All => x[ii],
            Visit::At(pos) => value_at(x, pos[ii], i32::MIN),
        };
        if xi == i32::MIN {
            n_na += 1;
        } else if xi > 0 {
            n_pos += 1;
        } else if xi < 0 {
            n_neg += 1;
        } else if xi == 0 {
            n_zero += 1;
        }
    }
    [n_neg, n_zero, n_pos, n_na]
}

#[cfg(feature = "python")]
mod py {
    use numpy::{IntoPyArray, PyArray1, PyReadonlyArray1};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::{sign_tabulate_f64, sign_tabulate_i32, Visit};

    fn resolve<'py>(n: i64, idxs: &Option<Bound<'py, PyAny>>, kind: &str) -> PyResult<Visit> {
        if kind == "none" {
            return Ok(Visit::All);
        }
        let Some(idxs) = idxs else {
            return Err(PyValueError::new_err(
                "idxs can only be integer, numeric, or logical",
            ));
        };
        match kind {
            "integer" => {
                let arr: PyReadonlyArray1<'_, i64> = idxs.extract().map_err(|err| {
                    PyValueError::new_err(format!(
                        "idxs can only be integer, numeric, or logical ({err})"
                    ))
                })?;
                let slice = arr
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                crate::visit_integer(slice, n).map_err(PyValueError::new_err)
            }
            "double" => {
                let arr: PyReadonlyArray1<'_, f64> = idxs.extract().map_err(|err| {
                    PyValueError::new_err(format!(
                        "idxs can only be integer, numeric, or logical ({err})"
                    ))
                })?;
                let slice = arr
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                crate::visit_real(slice, n).map_err(PyValueError::new_err)
            }
            "logical" => {
                let arr: PyReadonlyArray1<'_, i8> = idxs.extract().map_err(|err| {
                    PyValueError::new_err(format!(
                        "idxs can only be integer, numeric, or logical ({err})"
                    ))
                })?;
                let slice = arr
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                crate::visit_logical(slice, n).map_err(PyValueError::new_err)
            }
            _ => Err(PyValueError::new_err(
                "idxs can only be integer, numeric, or logical",
            )),
        }
    }

    #[pyfunction]
    #[pyo3(name = "sign_tabulate")]
    #[pyo3(signature = (x, x_kind, idxs=None, idxs_kind="none"))]
    fn sign_tabulate_py<'py>(
        py: Python<'py>,
        x: Bound<'py, PyAny>,
        x_kind: &str,
        idxs: Option<Bound<'py, PyAny>>,
        idxs_kind: &str,
    ) -> PyResult<Bound<'py, PyArray1<i64>>> {
        let counts = match x_kind {
            "double" => {
                let arr: PyReadonlyArray1<'_, f64> = x.extract().map_err(|_| {
                    PyValueError::new_err("Argument 'x' is not numeric: double")
                })?;
                let slice = arr
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                let visit = resolve(slice.len() as i64, &idxs, idxs_kind)?;
                sign_tabulate_f64(slice, &visit).to_vec()
            }
            "integer" => {
                let arr: PyReadonlyArray1<'_, i32> = x.extract().map_err(|_| {
                    PyValueError::new_err("Argument 'x' is not numeric: integer")
                })?;
                let slice = arr
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                let visit = resolve(slice.len() as i64, &idxs, idxs_kind)?;
                sign_tabulate_i32(slice, &visit).to_vec()
            }
            _ => {
                return Err(PyValueError::new_err(
                    "Argument 'x' must be of type integer or numeric",
                ))
            }
        };
        Ok(counts.into_pyarray(py))
    }

    #[pymodule]
    fn signtabulate(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(sign_tabulate_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn doubles_count_infinities_inside_the_sign_bins() {
        let x = [
            -2.0,
            f64::NEG_INFINITY,
            -0.0,
            0.0,
            1.0,
            f64::INFINITY,
            f64::NAN,
            f64::NAN,
        ];
        assert_eq!(sign_tabulate_f64(&x, &Visit::All), [2, 2, 2, 2, 1, 1]);
    }

    #[test]
    fn integers_have_no_infinity_bins() {
        let x = [-2, -1, 0, 1, i32::MIN, 5];
        let counts = sign_tabulate_i32(&x, &Visit::All);
        assert_eq!(counts.len(), 4);
        assert_eq!(counts, [2, 1, 2, 1]);
    }

    #[test]
    fn an_na_index_counts_as_missing() {
        let x = [1.0, -2.0];
        let visit = Visit::At(vec![NA_POSITION, 1]);
        assert_eq!(sign_tabulate_f64(&x, &visit), [1, 0, 0, 1, 0, 0]);
    }

    #[test]
    fn empty_vectors_are_zeros_of_the_storage_length() {
        assert_eq!(sign_tabulate_f64(&[], &Visit::All), [0, 0, 0, 0, 0, 0]);
        let empty: [i32; 0] = [];
        assert_eq!(sign_tabulate_i32(&empty, &Visit::All), [0, 0, 0, 0]);
    }
}
