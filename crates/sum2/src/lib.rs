//! Fast sum, ported from matrixStats `src/sum2.c` and `R/sum2.R`.
//!
//! The running total is a double, which is what this build of matrixStats uses
//! for the C `long double` accumulator. Integer results still use R's integer
//! range: outside `-2147483647` to `2147483647` the sum is missing.

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

fn i32_at(x: &[i32], pos: i64) -> i32 {
    if pos == NA_POSITION {
        i32::MIN
    } else {
        x[pos as usize]
    }
}

fn f64_at(x: &[f64], pos: i64) -> f64 {
    if pos == NA_POSITION {
        f64::NAN
    } else {
        x[pos as usize]
    }
}

/// Sum a double vector. Missing values are NaN. An empty sum is 0.
pub fn sum2_f64(x: &[f64], visit: &Visit, na_rm: bool) -> f64 {
    let mut sum = 0.0;
    match visit {
        Visit::All => {
            for &value in x {
                if !na_rm || !value.is_nan() {
                    sum += value;
                }
            }
        }
        Visit::At(pos) => {
            for &p in pos {
                let value = f64_at(x, p);
                if !na_rm || !value.is_nan() {
                    sum += value;
                }
            }
        }
    }
    sum
}

/// Sum an integer or logical vector. `i32::MIN` is R's integer NA.
///
/// The returned double is the accumulator. Casting it to an R integer, including
/// the overflow warning, is done by the Python wrapper.
pub fn sum2_i32(x: &[i32], visit: &Visit, na_rm: bool) -> f64 {
    let mut sum = 0.0;
    let n = match visit {
        Visit::All => x.len(),
        Visit::At(pos) => pos.len(),
    };
    for ii in 0..n {
        let value = match visit {
            Visit::All => x[ii],
            Visit::At(pos) => i32_at(x, pos[ii]),
        };
        if value != i32::MIN {
            sum += f64::from(value);
        } else if !na_rm {
            return f64::NAN;
        }
    }
    sum
}

#[cfg(feature = "python")]
mod py {
    use numpy::PyReadonlyArray1;
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::{sum2_f64, sum2_i32, Visit};

    fn resolve<'py>(
        n: i64,
        idxs: &Option<Bound<'py, PyAny>>,
        kind: &str,
    ) -> PyResult<Visit> {
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
    #[pyo3(name = "sum2")]
    #[pyo3(signature = (x, x_kind, na_rm, idxs=None, idxs_kind="none"))]
    fn sum2_py<'py>(
        x: Bound<'py, PyAny>,
        x_kind: &str,
        na_rm: bool,
        idxs: Option<Bound<'py, PyAny>>,
        idxs_kind: &str,
    ) -> PyResult<f64> {
        match x_kind {
            "double" => {
                let arr: PyReadonlyArray1<'_, f64> = x.extract().map_err(|_| {
                    PyValueError::new_err("Argument 'x' is not numeric or logical: double")
                })?;
                let slice = arr
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                let visit = resolve(slice.len() as i64, &idxs, idxs_kind)?;
                Ok(sum2_f64(slice, &visit, na_rm))
            }
            "integer" => {
                let arr: PyReadonlyArray1<'_, i32> = x.extract().map_err(|_| {
                    PyValueError::new_err("Argument 'x' is not numeric or logical: integer")
                })?;
                let slice = arr
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                let visit = resolve(slice.len() as i64, &idxs, idxs_kind)?;
                Ok(sum2_i32(slice, &visit, na_rm))
            }
            _ => Err(PyValueError::new_err(
                "Argument 'x' is not numeric or logical",
            )),
        }
    }

    #[pymodule]
    fn sum2(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(sum2_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_double_sum_is_zero() {
        assert_eq!(sum2_f64(&[], &Visit::All, false), 0.0);
    }

    #[test]
    fn empty_integer_sum_is_zero() {
        let x: [i32; 0] = [];
        assert_eq!(sum2_i32(&x, &Visit::All, false), 0.0);
    }

    #[test]
    fn double_missing_values() {
        let x = [1.0, f64::NAN, 3.0];
        assert!(sum2_f64(&x, &Visit::All, false).is_nan());
        assert_eq!(sum2_f64(&x, &Visit::All, true), 4.0);
    }

    #[test]
    fn integer_missing_values() {
        let x = [1, i32::MIN, 3];
        assert!(sum2_i32(&x, &Visit::All, false).is_nan());
        assert_eq!(sum2_i32(&x, &Visit::All, true), 4.0);
    }

    #[test]
    fn integer_total_can_pass_the_32_bit_range() {
        let x = [i32::MAX, 1, -i32::MAX];
        assert_eq!(sum2_i32(&x[..2], &Visit::All, false), 2_147_483_648.0);
        assert_eq!(sum2_i32(&x, &Visit::All, false), 1.0);
    }

    #[test]
    fn positive_negative_and_out_of_range_indexes() {
        let x = [1, 2, 3, 4, 5, 6];
        let visit = visit_integer(&[3, 5, 1], 6).unwrap();
        assert_eq!(sum2_i32(&x, &visit, false), 9.0);

        let visit = visit_integer(&[-4, 0, 0, -3, -1, -3, -1], 6).unwrap();
        assert_eq!(sum2_i32(&x, &visit, false), 13.0);

        let visit = visit_integer(&[-5, 0, -3, -1, -9], 6).unwrap();
        assert_eq!(sum2_i32(&x, &visit, false), 12.0);

        let visit = visit_integer(&[4, 5, 6, 7, 8, 9], 6).unwrap();
        assert!(sum2_i32(&x, &visit, false).is_nan());
        assert_eq!(sum2_i32(&x, &visit, true), 15.0);

        assert!(visit_integer(&[-4, 0, 1], 6).is_err());
    }

    #[test]
    fn fractional_and_logical_indexes() {
        let x = [1, 2, 3, 4, 5, 6];
        let visit = visit_real(&[1.9, 2.1], 6).unwrap();
        assert_eq!(sum2_i32(&x, &visit, false), 3.0);
        let visit = visit_real(&[0.5], 6).unwrap();
        assert_eq!(sum2_i32(&x, &visit, false), 1.0);
        let visit = visit_real(&[-1.9, -0.5], 5).unwrap();
        assert_eq!(sum2_i32(&x[..5], &visit, false), 14.0);

        let visit = visit_logical(&[0, 1], 6).unwrap();
        assert_eq!(sum2_i32(&x, &visit, false), 12.0);
        let visit = visit_logical(&[0, 1, 0, 1, 1, 1, 0, 1], 6).unwrap();
        assert!(sum2_i32(&x, &visit, false).is_nan());
        assert_eq!(sum2_i32(&x, &visit, true), 17.0);
        assert!(matches!(visit_logical(&[1], 6).unwrap(), Visit::All));
    }

    #[test]
    fn infinities_follow_ieee_addition() {
        assert!(sum2_f64(&[f64::INFINITY, f64::NEG_INFINITY], &Visit::All, false).is_nan());
        assert_eq!(
            sum2_f64(&[f64::INFINITY, 1.0], &Visit::All, true),
            f64::INFINITY
        );
    }
}
