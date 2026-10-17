//! Lagged differences, ported from matrixStats `src/diff2.c`.
//!
//! Index rules are the subset used by `diff2`: `validateIndices` with
//! out-of-bounds indexes allowed. `idxs` are 1-based. Missing indexes and
//! positive indexes past the vector become missing values. The result is
//! computed in float64, which is how R subtracts doubles and how integer
//! values inside the float64 mantissa subtract.

/// R's `NA_INTEGER`. In an integer index vector this is a missing index,
/// not a negative subscript.
const NA_INTEGER: i64 = i32::MIN as i64;

/// Missing 0-based index. Any negative index reaching the lookup is missing.
const NA_IDX: i64 = i64::MIN;

const MIXED: &str = "only 0's may be mixed with negative subscripts";

/// How `idxs` is stored before validation.
///
/// `None` in the Python wrapper is [`Idxs::All`].
pub enum Idxs<'a> {
    /// Every element, in order. This is R's `idxs = NULL`.
    All,
    /// 1-based integer indexes. `NA_INTEGER` (`-2147483648`) is missing.
    Integer(&'a [i64]),
    /// 1-based numeric indexes. `NaN` and both infinities are missing.
    Real(&'a [f64]),
    /// Logical mask. `0` is false, positive is true, negative is `NA`.
    Logical(&'a [i8]),
}

/// Elements of `x` that the lagged differences run over.
enum Selection {
    /// `x` itself, with no index vector.
    All,
    /// 0-based indexes. [`NA_IDX`] and any other negative value are missing.
    Pick(Vec<i64>),
}

/// Lagged and iterated differences of `x`.
///
/// `lag` and `differences` must be positive. The result length is
/// `n - differences * lag` after subsetting, or empty when that is negative.
pub fn diff2(x: &[f64], idxs: Idxs<'_>, lag: i64, differences: i64) -> Result<Vec<f64>, String> {
    if lag < 1 {
        return Err("Argument 'lag' must be a positive integer".to_string());
    }
    if differences < 1 {
        return Err("Argument 'differences' must be a positive integer".to_string());
    }

    let selection = validate(x.len() as i64, idxs)?;
    Ok(match selection {
        Selection::All => lagged_diff(&|i| x[i], x.len(), lag as usize, differences as usize),
        Selection::Pick(indexes) => {
            let nidxs = indexes.len();
            lagged_diff(
                &|i| lookup(x, indexes[i]),
                nidxs,
                lag as usize,
                differences as usize,
            )
        }
    })
}

fn validate(max_idx: i64, idxs: Idxs<'_>) -> Result<Selection, String> {
    match idxs {
        Idxs::All => Ok(Selection::All),
        Idxs::Integer(values) => validate_integer(values, max_idx),
        Idxs::Real(values) => validate_real(values, max_idx),
        Idxs::Logical(values) => Ok(validate_logical(values, max_idx)),
    }
}

fn validate_integer(idxs: &[i64], max_idx: i64) -> Result<Selection, String> {
    let mut state = 0i8;
    for &idx in idxs {
        if idx > 0 || idx == NA_INTEGER {
            if state < 0 {
                return Err(MIXED.to_string());
            }
            state = 1;
        } else if idx < 0 {
            if state > 0 {
                return Err(MIXED.to_string());
            }
            state = -1;
        }
    }
    if state < 0 {
        Ok(exclude_integer(idxs, max_idx))
    } else {
        Ok(include_integer(idxs, max_idx))
    }
}

fn validate_real(idxs: &[f64], max_idx: i64) -> Result<Selection, String> {
    let mut state = 0i8;
    for &idx in idxs {
        // Non-finite values, including -Inf, are missing indexes, not negatives.
        if idx > 0.0 || !idx.is_finite() {
            if state < 0 {
                return Err(MIXED.to_string());
            }
            state = 1;
        } else if idx < 0.0 {
            if state > 0 {
                return Err(MIXED.to_string());
            }
            state = -1;
        }
    }
    if state < 0 {
        Ok(exclude_real(idxs, max_idx))
    } else {
        Ok(include_real(idxs, max_idx))
    }
}

fn include_integer(idxs: &[i64], max_idx: i64) -> Selection {
    let mut out = Vec::new();
    for &idx in idxs {
        if idx > 0 || idx == NA_INTEGER {
            out.push(from_idx_integer(idx, max_idx));
        }
    }
    Selection::Pick(out)
}

fn include_real(idxs: &[f64], max_idx: i64) -> Selection {
    let mut out = Vec::new();
    for &idx in idxs {
        if idx > 0.0 || !idx.is_finite() {
            out.push(from_idx_real(idx, max_idx));
        }
    }
    Selection::Pick(out)
}

fn from_idx_integer(idx: i64, max_idx: i64) -> i64 {
    if idx == NA_INTEGER || idx > max_idx {
        NA_IDX
    } else {
        idx - 1
    }
}

fn from_idx_real(idx: f64, max_idx: i64) -> i64 {
    if !idx.is_finite() || idx > max_idx as f64 {
        NA_IDX
    } else {
        trunc_toward_zero(idx - 1.0)
    }
}

fn exclude_integer(idxs: &[i64], max_idx: i64) -> Selection {
    if max_idx <= 0 {
        return Selection::Pick(Vec::new());
    }
    let mut dropped = vec![false; max_idx as usize];
    for &idx in idxs {
        if idx == NA_INTEGER || idx >= 0 {
            continue;
        }
        let Some(magnitude) = idx.checked_neg() else {
            continue;
        };
        if magnitude > 0 && magnitude <= max_idx {
            dropped[(magnitude as usize) - 1] = true;
        }
    }
    pick_kept(&dropped)
}

fn exclude_real(idxs: &[f64], max_idx: i64) -> Selection {
    if max_idx <= 0 {
        return Selection::Pick(Vec::new());
    }
    let mut dropped = vec![false; max_idx as usize];
    for &idx in idxs {
        if !(idx < 0.0 && idx.is_finite()) {
            continue;
        }
        let magnitude = trunc_toward_zero(-idx);
        if magnitude > 0 && magnitude <= max_idx {
            dropped[(magnitude as usize) - 1] = true;
        }
    }
    pick_kept(&dropped)
}

fn pick_kept(dropped: &[bool]) -> Selection {
    let mut out = Vec::new();
    for (i, &is_dropped) in dropped.iter().enumerate() {
        if !is_dropped {
            out.push(i as i64);
        }
    }
    Selection::Pick(out)
}

fn validate_logical(idxs: &[i8], max_idx: i64) -> Selection {
    let nidxs = idxs.len() as i64;
    if nidxs == 0 || max_idx < 0 {
        return Selection::Pick(Vec::new());
    }
    if nidxs > max_idx {
        // Out-of-range logical values become missing indexes.
        let mut out = Vec::new();
        for (ii, &flag) in idxs.iter().enumerate() {
            if ii as i64 >= max_idx {
                break;
            }
            if flag != 0 {
                out.push(if flag < 0 { NA_IDX } else { ii as i64 });
            }
        }
        let extra = idxs
            .iter()
            .skip(max_idx as usize)
            .filter(|&&flag| flag != 0)
            .count();
        out.extend(std::iter::repeat(NA_IDX).take(extra));
        return Selection::Pick(out);
    }

    let last_part = (max_idx % nidxs) as usize;
    let mut na_count = 0i64;
    let mut count1 = 0i64;
    let mut count2 = 0i64;
    for (ii, &flag) in idxs.iter().enumerate() {
        if flag != 0 {
            if flag < 0 {
                na_count += 1;
            }
            if ii < last_part {
                count1 += 1;
            } else {
                count2 += 1;
            }
        }
    }
    let count = count1 + count2;
    // A logical vector of all TRUE and no NA selects every element.
    if na_count == 0 && count == nidxs {
        return Selection::All;
    }

    let ans_n = (max_idx / nidxs) * count + count1;
    if ans_n <= 0 {
        return Selection::Pick(Vec::new());
    }
    let mut ans = vec![0i64; ans_n as usize];
    let mut jj = 0usize;
    for (ii, &flag) in idxs.iter().enumerate() {
        if flag != 0 {
            ans[jj] = if flag < 0 { NA_IDX } else { ii as i64 };
            jj += 1;
        }
    }

    let count_us = count as usize;
    let mut ii = count_us;
    let mut kk = nidxs;
    while kk + nidxs <= max_idx {
        for j in 0..count_us {
            ans[ii + j] = if ans[j] == NA_IDX { NA_IDX } else { ans[j] + kk };
        }
        ii += count_us;
        kk += nidxs;
    }
    for j in 0..(count1 as usize) {
        ans[ii + j] = if ans[j] == NA_IDX { NA_IDX } else { ans[j] + kk };
    }
    Selection::Pick(ans)
}

fn lookup(x: &[f64], idx: i64) -> f64 {
    if idx < 0 || idx as usize >= x.len() {
        f64::NAN
    } else {
        x[idx as usize]
    }
}

/// `diff2_lowlevel_template.h`: one pass when `differences == 1`, otherwise
/// first order into a work buffer, intermediate orders in place, last order
/// into the result.
fn lagged_diff(get: &dyn Fn(usize) -> f64, nidxs: usize, lag: usize, differences: usize) -> Vec<f64> {
    let nans_signed = nidxs as i128 - differences as i128 * lag as i128;
    if nans_signed <= 0 {
        return Vec::new();
    }
    let nans = nans_signed as usize;
    let mut ans = vec![0.0; nans];
    if differences == 1 {
        for ii in 0..nans {
            ans[ii] = get(ii + lag) - get(ii);
        }
        return ans;
    }

    let mut tmp = vec![0.0; nidxs - lag];
    let mut n_cur = nidxs;
    for ii in 0..(n_cur - lag) {
        tmp[ii] = get(ii + lag) - get(ii);
    }
    n_cur -= lag;

    let mut order = differences;
    while {
        order -= 1;
        order > 1
    } {
        let mut uu = lag;
        let mut tt = 0usize;
        for ii in 0..(n_cur - lag) {
            tmp[ii] = tmp[uu] - tmp[tt];
            uu += 1;
            tt += 1;
        }
        n_cur -= lag;
    }

    let mut uu = lag;
    let mut tt = 0usize;
    for ii in 0..nans {
        ans[ii] = tmp[uu] - tmp[tt];
        uu += 1;
        tt += 1;
    }
    ans
}

fn trunc_toward_zero(value: f64) -> i64 {
    if !value.is_finite() {
        return 0;
    }
    let truncated = value.trunc();
    if truncated >= i64::MAX as f64 {
        i64::MAX
    } else if truncated <= i64::MIN as f64 {
        i64::MIN
    } else {
        truncated as i64
    }
}

#[cfg(feature = "python")]
mod py {
    use numpy::{IntoPyArray, PyReadonlyArray1};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::{diff2 as diff2_values, Idxs};

    #[pyfunction]
    #[pyo3(name = "diff2")]
    fn diff2_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray1<'py, f64>,
        kind: u8,
        idxs: Option<Bound<'py, PyAny>>,
        lag: i64,
        differences: i64,
    ) -> PyResult<Bound<'py, numpy::PyArray1<f64>>> {
        let x = x
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        let result = match kind {
            0 => diff2_values(x, Idxs::All, lag, differences),
            1 => {
                let array = required_array::<i64>(idxs)?;
                let values = array
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                diff2_values(x, Idxs::Integer(values), lag, differences)
            }
            2 => {
                let array = required_array::<f64>(idxs)?;
                let values = array
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                diff2_values(x, Idxs::Real(values), lag, differences)
            }
            3 => {
                let array = required_array::<i8>(idxs)?;
                let values = array
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                diff2_values(x, Idxs::Logical(values), lag, differences)
            }
            _ => {
                return Err(PyValueError::new_err(
                    "idxs can only be integer, numeric, or logical",
                ))
            }
        };
        result
            .map(|values| values.into_pyarray(py))
            .map_err(PyValueError::new_err)
    }

    fn required_array<'py, T: numpy::Element>(
        idxs: Option<Bound<'py, PyAny>>,
    ) -> PyResult<PyReadonlyArray1<'py, T>> {
        let Some(idxs) = idxs else {
            return Err(PyValueError::new_err(
                "idxs can only be integer, numeric, or logical",
            ));
        };
        idxs.extract()
    }

    #[pymodule]
    #[pyo3(name = "diff2")]
    fn diff2_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(diff2_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{diff2, Idxs};

    fn run(x: &[f64], idxs: Idxs<'_>, lag: i64, differences: i64) -> Vec<f64> {
        diff2(x, idxs, lag, differences).unwrap()
    }

    #[test]
    fn first_difference_of_a_sequence() {
        let values = run(&[1.0, 2.0, 4.0, 7.0, 11.0], Idxs::All, 1, 1);
        assert_eq!(values, vec![1.0, 2.0, 3.0, 4.0]);
    }

    #[test]
    fn lag_and_second_difference() {
        let x: Vec<f64> = (1..=12).map(|v| v as f64).collect();
        let values = run(&x, Idxs::All, 3, 2);
        assert_eq!(values, vec![0.0; 6]);
    }

    #[test]
    fn missing_values_propagate() {
        let values = run(&[1.0, f64::NAN, 3.0, 4.0, f64::NAN, 8.0], Idxs::All, 1, 1);
        assert!(values[0].is_nan());
        assert!(values[1].is_nan());
        assert_eq!(values[2], 1.0);
        assert!(values[3].is_nan());
        assert!(values[4].is_nan());
    }

    #[test]
    fn positive_indexes_are_one_based_and_keep_duplicates() {
        let x: Vec<f64> = (1..=6).map(|v| v as f64).collect();
        let idxs = [3i64, 0, 0, 5, 1, 5, 5];
        let values = run(&x, Idxs::Integer(&idxs), 1, 1);
        assert_eq!(values, vec![2.0, -4.0, 4.0, 0.0]);
    }

    #[test]
    fn negative_indexes_drop_positions() {
        let x: Vec<f64> = (1..=6).map(|v| v as f64).collect();
        let idxs = [-4i64, 0, 0, -3, -1, -3, -1];
        let values = run(&x, Idxs::Integer(&idxs), 1, 1);
        assert_eq!(values, vec![3.0, 1.0]);
    }

    #[test]
    fn out_of_range_positive_indexes_are_missing() {
        let x: Vec<f64> = (1..=6).map(|v| v as f64).collect();
        let idxs = [4i64, 5, 6, 7, 8, 9];
        let values = run(&x, Idxs::Integer(&idxs), 1, 1);
        assert_eq!(values[0], 1.0);
        assert_eq!(values[1], 1.0);
        assert!(values[2].is_nan());
        assert!(values[3].is_nan());
        assert!(values[4].is_nan());
    }

    #[test]
    fn fractional_indexes_follow_the_c_cast() {
        let x: Vec<f64> = (1..=6).map(|v| v as f64).collect();
        let idxs = [0.5f64, 2.0];
        let values = run(&x, Idxs::Real(&idxs), 1, 1);
        assert_eq!(values, vec![1.0]);

        let past = [1.0f64, 6.1];
        let values = run(&x, Idxs::Real(&past), 1, 1);
        assert!(values[0].is_nan());
    }

    #[test]
    fn logical_recycling_and_all_true() {
        let x: Vec<f64> = (1..=6).map(|v| v as f64).collect();
        let short = [0i8, 1];
        let values = run(&x, Idxs::Logical(&short), 1, 1);
        assert_eq!(values, vec![2.0, 2.0]);

        let all = [1i8];
        let values = run(&x, Idxs::Logical(&all), 1, 1);
        assert_eq!(values, vec![1.0; 5]);
    }

    #[test]
    fn mixed_signs_are_rejected() {
        let x = [1.0, 2.0, 3.0];
        let idxs = [1i64, -1];
        let err = diff2(&x, Idxs::Integer(&idxs), 1, 1).unwrap_err();
        assert_eq!(err, "only 0's may be mixed with negative subscripts");
    }

    #[test]
    fn too_large_a_lag_is_empty() {
        let x: Vec<f64> = (1..=6).map(|v| v as f64).collect();
        let values = run(&x, Idxs::All, 10, 1);
        assert!(values.is_empty());
    }
}
