//! Fast mean, ported from matrixStats `src/mean2.c` and `R/mean2.R`.
//!
//! Double data with `refine` uses the two-pass residual correction from the C
//! template. Integer and logical data are averaged in one pass. The accumulator
//! is a double, matching this build of matrixStats.

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

fn f64_at(x: &[f64], pos: i64) -> f64 {
    if pos == NA_POSITION {
        f64::NAN
    } else {
        x[pos as usize]
    }
}

fn i32_at(x: &[i32], pos: i64) -> i32 {
    if pos == NA_POSITION {
        i32::MIN
    } else {
        x[pos as usize]
    }
}

/// Mean of a double vector. An empty mean is NaN.
///
/// `refine` adds the mean of the residuals, which is the second pass in
/// `mean2_dbl`. It runs only when the first average is finite.
pub fn mean2_f64(x: &[f64], visit: &Visit, na_rm: bool, refine: bool) -> f64 {
    let mut sum = 0.0;
    let mut count = 0.0;
    match visit {
        Visit::All => {
            for &value in x {
                if !na_rm || !value.is_nan() {
                    sum += value;
                    count += 1.0;
                }
            }
        }
        Visit::At(pos) => {
            for &p in pos {
                let value = f64_at(x, p);
                if !na_rm || !value.is_nan() {
                    sum += value;
                    count += 1.0;
                }
            }
        }
    }

    if sum > f64::MAX {
        return f64::INFINITY;
    }
    if sum < -f64::MAX {
        return f64::NEG_INFINITY;
    }
    let mut avg = sum / count;
    if refine && avg.is_finite() {
        let mut rsum = 0.0;
        match visit {
            Visit::All => {
                for &value in x {
                    if !na_rm || !value.is_nan() {
                        rsum += value - avg;
                    }
                }
            }
            Visit::At(pos) => {
                for &p in pos {
                    let value = f64_at(x, p);
                    if !na_rm || !value.is_nan() {
                        rsum += value - avg;
                    }
                }
            }
        }
        avg += rsum / count;
    }
    avg
}

/// Mean of an integer or logical vector. `i32::MIN` is R's integer NA.
///
/// The C template does not refine integer data, so `refine` is not an argument.
pub fn mean2_i32(x: &[i32], visit: &Visit, na_rm: bool) -> f64 {
    let mut sum = 0.0;
    let mut count = 0.0;
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
            count += 1.0;
        } else if !na_rm {
            sum = f64::NAN;
            break;
        }
    }
    if sum > f64::MAX {
        return f64::INFINITY;
    }
    if sum < -f64::MAX {
        return f64::NEG_INFINITY;
    }
    sum / count
}

#[cfg(feature = "python")]
mod py {
    use numpy::PyReadonlyArray1;
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::{mean2_f64, mean2_i32, Visit};

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
    #[pyo3(name = "mean2")]
    #[pyo3(signature = (x, x_kind, na_rm, refine, idxs=None, idxs_kind="none"))]
    fn mean2_py<'py>(
        x: Bound<'py, PyAny>,
        x_kind: &str,
        na_rm: bool,
        refine: bool,
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
                Ok(mean2_f64(slice, &visit, na_rm, refine))
            }
            "integer" => {
                let arr: PyReadonlyArray1<'_, i32> = x.extract().map_err(|_| {
                    PyValueError::new_err("Argument 'x' is not numeric or logical: integer")
                })?;
                let slice = arr
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                let visit = resolve(slice.len() as i64, &idxs, idxs_kind)?;
                Ok(mean2_i32(slice, &visit, na_rm))
            }
            _ => Err(PyValueError::new_err(
                "Argument 'x' is not numeric or logical",
            )),
        }
    }

    #[pymodule]
    fn mean2(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(mean2_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_mean_is_nan() {
        assert!(mean2_f64(&[], &Visit::All, false, true).is_nan());
        let x: [i32; 0] = [];
        assert!(mean2_i32(&x, &Visit::All, false).is_nan());
    }

    #[test]
    fn integer_mean_is_one_pass() {
        let x: Vec<i32> = (1..=10).collect();
        assert_eq!(mean2_i32(&x, &Visit::All, false), 5.5);
    }

    #[test]
    fn double_refine_keeps_a_cancelled_sum_at_zero() {
        let x = [1e16, 1.0, -1e16];
        assert_eq!(mean2_f64(&x, &Visit::All, false, true), 0.0);
        assert_eq!(mean2_f64(&x, &Visit::All, false, false), 0.0);
    }

    #[test]
    fn missing_values_and_subset() {
        let x = [1.0, f64::NAN, 3.0, 5.0];
        assert!(mean2_f64(&x, &Visit::All, false, true).is_nan());
        assert_eq!(mean2_f64(&x, &Visit::All, true, true), 3.0);

        let ints = [1, 2, 3, 4, 5, 6];
        let visit = visit_integer(&[1, 2, 3], 6).unwrap();
        assert_eq!(mean2_i32(&ints, &visit, false), 2.0);
        let visit = visit_integer(&[-1, -2, -3, -4, -5, -6], 6).unwrap();
        assert!(mean2_i32(&ints, &visit, false).is_nan());
    }

    #[test]
    fn logical_values_average_as_zero_and_one() {
        let x = [1, 0, 1];
        assert!((mean2_i32(&x, &Visit::All, false) - 2.0 / 3.0).abs() < 1e-15);
    }
}
