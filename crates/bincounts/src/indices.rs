//! One-based vector subscripts, the rules `binCounts` and `binMeans` inherit
//! from R's `[` and from matrixStats `validateIndices`.
//!
//! Positive and missing indexes select, in order, and a zero is ignored.
//! A positive index past the vector is missing. Negative indexes exclude, and
//! a negative index past the vector is ignored. Logical indexes are recycled
//! when they are shorter than the vector; extra `TRUE` values past the end
//! are missing. Missing selections are omitted here because both bin functions
//! drop missing `x` after the subset.

const MIX: &str = "only 0's may be mixed with negative subscripts";

#[derive(Clone, Debug, PartialEq)]
pub enum Subscripts {
    All,
    /// `None` is a missing index.
    Int(Vec<Option<i64>>),
    Real(Vec<f64>),
    /// `None` is a missing logical value.
    Logical(Vec<Option<bool>>),
}

pub fn positions(n: usize, sub: &Subscripts) -> Result<Vec<usize>, String> {
    match sub {
        Subscripts::All => Ok((0..n).collect()),
        Subscripts::Logical(flags) => Ok(positions_logical(n, flags)),
        Subscripts::Int(vals) => positions_numeric(n, vals),
        Subscripts::Real(vals) => {
            let coerced: Vec<Option<i64>> = vals.iter().copied().map(coerce_real).collect();
            positions_numeric(n, &coerced)
        }
    }
}

fn positions_logical(n: usize, flags: &[Option<bool>]) -> Vec<usize> {
    let m = flags.len();
    if m == 0 || n == 0 {
        return Vec::new();
    }
    let mut out = Vec::new();
    if m < n {
        for i in 0..n {
            if flags[i % m] == Some(true) {
                out.push(i);
            }
        }
    } else {
        for (i, flag) in flags.iter().enumerate() {
            if *flag == Some(true) && i < n {
                out.push(i);
            }
        }
    }
    out
}

/// Finite values truncate toward zero. Non-finite values and magnitudes that
/// do not fit in `i64` become missing indexes, except a huge finite negative
/// value, which stays a negative exclusion.
fn coerce_real(value: f64) -> Option<i64> {
    if !value.is_finite() {
        return None;
    }
    let truncated = value.trunc();
    if truncated > i64::MAX as f64 {
        return None;
    }
    if truncated < i64::MIN as f64 {
        return Some(i64::MIN);
    }
    Some(truncated as i64)
}

fn positions_numeric(n: usize, idxs: &[Option<i64>]) -> Result<Vec<usize>, String> {
    let mut state = 0i8;
    for idx in idxs {
        match *idx {
            Some(0) => {}
            Some(value) if value < 0 => {
                if state > 0 {
                    return Err(MIX.to_string());
                }
                state = -1;
            }
            _ => {
                if state < 0 {
                    return Err(MIX.to_string());
                }
                state = 1;
            }
        }
    }

    if state >= 0 {
        let mut out = Vec::new();
        for idx in idxs {
            if let Some(value) = *idx {
                if value >= 1 && (value as usize) <= n {
                    out.push((value as usize) - 1);
                }
            }
        }
        return Ok(out);
    }

    let mut exclude = vec![false; n];
    for idx in idxs {
        if let Some(value) = *idx {
            if value < 0 {
                if let Some(abs) = value.checked_neg() {
                    if abs >= 1 && (abs as usize) <= n {
                        exclude[(abs as usize) - 1] = true;
                    }
                }
            }
        }
    }
    Ok((0..n).filter(|i| !exclude[*i]).collect())
}

pub fn take(values: &[f64], sub: &Subscripts) -> Result<Vec<f64>, String> {
    if matches!(sub, Subscripts::All) {
        return Ok(values.to_vec());
    }
    let index = positions(values.len(), sub)?;
    Ok(index.into_iter().map(|i| values[i]).collect())
}

#[cfg(feature = "python")]
use pyo3::prelude::*;
#[cfg(feature = "python")]
use pyo3::types::PyAnyMethods;

#[cfg(feature = "python")]
pub fn parse_subscripts(obj: &Bound<'_, PyAny>) -> PyResult<Subscripts> {
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    if obj.is_none() {
        return Ok(Subscripts::All);
    }
    let py = obj.py();
    let numpy = py.import("numpy")?;
    let arr = numpy.call_method1("asarray", (obj,))?;
    let ndim: usize = arr.getattr("ndim")?.extract()?;
    if ndim > 1 {
        return Err(PyValueError::new_err(
            "idxs can only be integer, numeric, or logical",
        ));
    }
    let arr = if ndim == 0 {
        arr.call_method1("reshape", ((1,),))?
    } else {
        arr
    };
    let kind: String = arr.getattr("dtype")?.getattr("kind")?.extract()?;
    let items: Vec<Py<PyAny>> = arr.call_method0("tolist")?.extract()?;
    match kind.as_str() {
        "b" => {
            let flags = items
                .iter()
                .map(|item| item.bind(py).extract::<bool>().map(Some))
                .collect::<PyResult<Vec<_>>>()?;
            Ok(Subscripts::Logical(flags))
        }
        "i" | "u" => Ok(Subscripts::Int(py_ints(py, &items)?)),
        "f" => {
            let values = items
                .iter()
                .map(|item| item.bind(py).extract::<f64>())
                .collect::<PyResult<Vec<_>>>()?;
            Ok(Subscripts::Real(values))
        }
        "O" => parse_objects(py, &items),
        _ => Err(PyValueError::new_err(
            "idxs can only be integer, numeric, or logical",
        )),
    }
}

#[cfg(feature = "python")]
fn py_ints(py: Python<'_>, items: &[Py<PyAny>]) -> PyResult<Vec<Option<i64>>> {
    items.iter().map(|item| py_index_int(item.bind(py))).collect()
}

#[cfg(feature = "python")]
fn py_index_int(obj: &Bound<'_, PyAny>) -> PyResult<Option<i64>> {
    if obj.is_none() {
        return Ok(None);
    }
    if let Ok(value) = obj.extract::<i64>() {
        return Ok(Some(value));
    }
    let positive = obj.call_method1("__gt__", (0,))?.is_truthy()?;
    if positive {
        Ok(None)
    } else {
        Ok(Some(i64::MIN))
    }
}

#[cfg(feature = "python")]
fn parse_objects(py: Python<'_>, items: &[Py<PyAny>]) -> PyResult<Subscripts> {
    use pyo3::exceptions::PyValueError;
    use pyo3::types::{PyBool, PyFloat, PyInt};

    let mut logical = true;
    let mut integer = true;
    for item in items {
        let obj = item.bind(py);
        if obj.is_none() {
            continue;
        }
        if obj.is_instance_of::<PyBool>() {
            continue;
        }
        if obj.is_instance_of::<PyInt>() {
            logical = false;
            continue;
        }
        if obj.is_instance_of::<PyFloat>() {
            logical = false;
            integer = false;
            continue;
        }
        return Err(PyValueError::new_err(
            "idxs can only be integer, numeric, or logical",
        ));
    }
    if logical {
        let flags = items
            .iter()
            .map(|item| {
                let obj = item.bind(py);
                if obj.is_none() {
                    Ok(None)
                } else {
                    obj.extract::<bool>().map(Some)
                }
            })
            .collect::<pyo3::PyResult<Vec<_>>>()?;
        return Ok(Subscripts::Logical(flags));
    }
    if integer {
        let mut values = Vec::with_capacity(items.len());
        for item in items {
            let obj = item.bind(py);
            if obj.is_none() {
                values.push(None);
            } else if obj.is_instance_of::<PyBool>() {
                values.push(Some(if obj.is_truthy()? { 1 } else { 0 }));
            } else {
                values.push(py_index_int(obj)?);
            }
        }
        return Ok(Subscripts::Int(values));
    }
    let mut values = Vec::with_capacity(items.len());
    for item in items {
        let obj = item.bind(py);
        if obj.is_none() {
            values.push(f64::NAN);
        } else if obj.is_instance_of::<PyBool>() {
            values.push(if obj.is_truthy()? { 1.0 } else { 0.0 });
        } else {
            values.push(obj.extract::<f64>()?);
        }
    }
    Ok(Subscripts::Real(values))
}

#[cfg(test)]
mod tests {
    use super::{positions, Subscripts};

    #[test]
    fn positive_indexes_keep_order_and_duplicates() {
        let sub = Subscripts::Int(vec![
            Some(3),
            Some(0),
            Some(0),
            Some(5),
            Some(1),
            Some(5),
            Some(5),
        ]);
        assert_eq!(positions(6, &sub).unwrap(), vec![2, 4, 0, 4, 4]);
    }

    #[test]
    fn positive_out_of_range_is_dropped() {
        let sub = Subscripts::Int((4..=9).map(Some).collect());
        assert_eq!(positions(6, &sub).unwrap(), vec![3, 4, 5]);
    }

    #[test]
    fn negative_indexes_exclude_and_ignore_zeros() {
        let sub = Subscripts::Int(vec![
            Some(-4),
            Some(0),
            Some(0),
            Some(-3),
            Some(-1),
            Some(-3),
            Some(-1),
        ]);
        assert_eq!(positions(6, &sub).unwrap(), vec![1, 4, 5]);
    }

    #[test]
    fn negative_out_of_range_is_ignored() {
        let sub = Subscripts::Int(vec![Some(-5), Some(0), Some(-3), Some(-1), Some(-9)]);
        assert_eq!(positions(6, &sub).unwrap(), vec![1, 3, 5]);
    }

    #[test]
    fn mixed_signs_and_missing_with_negative_are_errors() {
        let mixed = Subscripts::Int(vec![Some(1), Some(-1)]);
        assert!(positions(6, &mixed).is_err());
        let missing = Subscripts::Real(vec![f64::NEG_INFINITY, -1.0]);
        assert!(positions(6, &missing).is_err());
    }

    #[test]
    fn real_indexes_truncate_toward_zero() {
        let sub = Subscripts::Real(vec![1.9, -0.2, 4.0]);
        assert_eq!(positions(6, &sub).unwrap(), vec![0, 3]);
        let kept = Subscripts::Real(vec![-1.2]);
        assert_eq!(positions(6, &kept).unwrap(), vec![1, 2, 3, 4, 5]);
    }

    #[test]
    fn logical_indexes_recycle_and_drop_missing() {
        let recycled = Subscripts::Logical(vec![Some(false), Some(true)]);
        assert_eq!(positions(6, &recycled).unwrap(), vec![1, 3, 5]);
        let with_na = Subscripts::Logical(vec![Some(false), Some(true), None]);
        assert_eq!(positions(6, &with_na).unwrap(), vec![1, 4]);
        let long = Subscripts::Logical(vec![
            Some(false),
            Some(true),
            Some(false),
            Some(true),
            Some(true),
            Some(true),
            Some(false),
            Some(true),
        ]);
        assert_eq!(positions(6, &long).unwrap(), vec![1, 3, 4, 5]);
    }

    #[test]
    fn empty_and_all_false_select_nothing() {
        assert!(positions(6, &Subscripts::Int(vec![Some(0)])).unwrap().is_empty());
        assert!(positions(6, &Subscripts::Int(vec![])).unwrap().is_empty());
        assert!(positions(6, &Subscripts::Logical(vec![Some(false)]))
            .unwrap()
            .is_empty());
        assert_eq!(positions(6, &Subscripts::All).unwrap(), vec![0, 1, 2, 3, 4, 5]);
    }
}
