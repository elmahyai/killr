//! Weighted arithmetic mean, ported from matrixStats `src/weightedMean.c`
//! and `src/weightedMean_lowlevel_template.h`.
//!
//! Index rules are ported from `src/validateIndices.c`. `weightedMean` calls
//! that checker with out-of-bounds indices allowed, so a positive index past
//! the end becomes a missing index instead of an error.
//!
//! The manual says a negative weight counts as zero. The C loop only skips a
//! weight that compares equal to zero, and matrixStats 1.5.0 does the same,
//! so a negative weight stays in the sum.

/// 0-based index used when R would store `NA_R_XLEN_T`.
const NA_INDEX: i64 = i64::MIN;

/// Quiet NaN that R treats as `NA_real_`. A plain `0/0` NaN stays a NaN.
fn r_na() -> f64 {
    f64::from_bits(0x7ff8_0000_0000_07a2)
}

/// R's `NA_INTEGER`.
const NA_INTEGER: i64 = i32::MIN as i64;

/// How `idxs` addresses `x`. `All` is R's `NULL`: every element, in order.
pub enum Subscripts {
    All,
    /// 1-based integer subscripts. `na_sentinel` is R's integer NA when the
    /// values came from a 32-bit integer vector.
    Integer {
        values: Vec<i64>,
        na_sentinel: Option<i64>,
    },
    /// 1-based numeric subscripts. Non-finite values are missing indices.
    Real(Vec<f64>),
    /// Logical subscripts recycled to the length of `x`. `0` is false, `1` is
    /// true, and `2` is a missing logical value.
    Logical(Vec<u8>),
}

/// Weighted mean of `x`.
///
/// `w = None` gives every element weight 1. `idxs` is 1-based; `All` uses
/// every element. A weight that is exactly zero is skipped, which also skips
/// a missing `x` paired with that weight. Any other missing weight makes the
/// result missing when the paired `x` is present, whether or not `na_rm` is
/// set. `na_rm` skips elements whose `x` is missing. `refine` adds a second
/// pass over residuals. An empty selection returns NaN.
pub fn weighted_mean(
    x: &[f64],
    w: Option<&[f64]>,
    idxs: Subscripts,
    na_rm: bool,
    refine: bool,
) -> Result<f64, String> {
    if let Some(weights) = w {
        if weights.len() != x.len() {
            return Err(format!(
                "Argument 'x' and 'w' are of different lengths: {} != {}",
                x.len(),
                weights.len()
            ));
        }
    }
    let indices = match idxs {
        Subscripts::All => None,
        Subscripts::Integer {
            values,
            na_sentinel,
        } => Some(validate_integer(&values, x.len() as i64, na_sentinel)?),
        Subscripts::Real(values) => Some(validate_real(&values, x.len() as i64)?),
        Subscripts::Logical(values) => validate_logical(&values, x.len() as i64)?,
    };
    Ok(weighted_mean_selected(x, w, indices.as_deref(), na_rm, refine))
}

fn weighted_mean_selected(
    x: &[f64],
    w: Option<&[f64]>,
    indices: Option<&[i64]>,
    na_rm: bool,
    refine: bool,
) -> f64 {
    let nidxs = match indices {
        Some(idxs) => idxs.len(),
        None => x.len(),
    };
    let mut sum = 0.0;
    let mut wtotal = 0.0;
    // Set when a missing x or w is actually added. The C loop turns that into
    // R's NA through the NA payload. Overflow of the total weight still wins
    // and returns a plain NaN, matching the order of the C checks.
    let mut missing = false;

    for i in 0..nidxs {
        let idx = index_at(indices, i);
        let weight = load_weight(w, idx);
        if weight == 0.0 {
            continue;
        }
        let value = load_value(x, idx);
        if !na_rm {
            if weight.is_nan() || value.is_nan() {
                missing = true;
            }
            sum += weight * value;
            wtotal += weight;
            // Same early exit as the C loop: a NaN sum cannot become finite.
            if i % 1_048_576 == 0 && sum.is_nan() {
                break;
            }
        } else if !value.is_nan() {
            if weight.is_nan() {
                missing = true;
            }
            sum += weight * value;
            wtotal += weight;
        }
    }

    let mut avg = if wtotal > f64::MAX || wtotal < -f64::MAX {
        f64::NAN
    } else if sum > f64::MAX {
        f64::INFINITY
    } else if sum < -f64::MAX {
        f64::NEG_INFINITY
    } else if missing {
        r_na()
    } else {
        sum / wtotal
    };

    if refine && avg.is_finite() {
        sum = 0.0;
        for i in 0..nidxs {
            let idx = index_at(indices, i);
            let weight = load_weight(w, idx);
            if weight == 0.0 {
                continue;
            }
            let value = load_value(x, idx);
            if !na_rm {
                sum += weight * (value - avg);
                if i % 1_048_576 == 0 && sum.is_nan() {
                    break;
                }
            } else if !value.is_nan() {
                sum += weight * (value - avg);
            }
        }
        avg += sum / wtotal;
    }
    avg
}

fn index_at(indices: Option<&[i64]>, i: usize) -> i64 {
    match indices {
        Some(idxs) => idxs[i],
        None => i as i64,
    }
}

fn load_weight(w: Option<&[f64]>, idx: i64) -> f64 {
    if idx == NA_INDEX {
        f64::NAN
    } else if let Some(weights) = w {
        weights[idx as usize]
    } else {
        1.0
    }
}

fn load_value(x: &[f64], idx: i64) -> f64 {
    if idx == NA_INDEX {
        f64::NAN
    } else {
        x[idx as usize]
    }
}

fn validate_integer(
    idxs: &[i64],
    max_idx: i64,
    na_sentinel: Option<i64>,
) -> Result<Vec<i64>, String> {
    let mut saw_positive = false;
    let mut saw_negative = false;
    for &idx in idxs {
        if is_missing_int(idx, na_sentinel) || idx > 0 {
            if saw_negative {
                return Err("only 0's may be mixed with negative subscripts".to_string());
            }
            saw_positive = true;
        } else if idx < 0 {
            if saw_positive {
                return Err("only 0's may be mixed with negative subscripts".to_string());
            }
            saw_negative = true;
        }
    }

    if saw_negative {
        return Ok(exclude_integer(idxs, max_idx));
    }

    let mut ans = Vec::new();
    for &idx in idxs {
        if idx == 0 {
            continue;
        }
        ans.push(if is_missing_int(idx, na_sentinel) || idx > max_idx {
            NA_INDEX
        } else {
            idx - 1
        });
    }
    Ok(ans)
}

fn is_missing_int(idx: i64, na_sentinel: Option<i64>) -> bool {
    na_sentinel == Some(idx)
}

fn exclude_integer(idxs: &[i64], max_idx: i64) -> Vec<i64> {
    if max_idx <= 0 {
        return Vec::new();
    }
    let mut excluded = vec![false; max_idx as usize];
    let mut keep = max_idx;
    for &raw in idxs {
        if raw >= 0 {
            continue;
        }
        let Some(idx) = raw.checked_neg() else {
            continue;
        };
        if idx > 0 && idx <= max_idx {
            let pos = (idx as usize) - 1;
            if !excluded[pos] {
                excluded[pos] = true;
                keep -= 1;
            }
        }
    }
    kept_positions(&excluded, keep, max_idx)
}

fn validate_real(idxs: &[f64], max_idx: i64) -> Result<Vec<i64>, String> {
    let mut saw_positive = false;
    let mut saw_negative = false;
    for &idx in idxs {
        // Infinite subscripts are missing indices, including -Inf. That matches
        // the C classifier (`IS_INF` is on the positive side). The C checker
        // forgets to mark the result as containing NA and then reads off the
        // end of `x`; the index stored here is missing, so the read is skipped.
        if idx > 0.0 || !idx.is_finite() {
            if saw_negative {
                return Err("only 0's may be mixed with negative subscripts".to_string());
            }
            saw_positive = true;
        } else if idx < 0.0 {
            if saw_positive {
                return Err("only 0's may be mixed with negative subscripts".to_string());
            }
            saw_negative = true;
        }
    }

    if saw_negative {
        return Ok(exclude_real(idxs, max_idx));
    }

    let mut ans = Vec::new();
    for &idx in idxs {
        // A zero is false in the C fill condition. NaN is not zero, so it stays.
        if idx == 0.0 {
            continue;
        }
        ans.push(real_to_index(idx, max_idx));
    }
    Ok(ans)
}

fn real_to_index(idx: f64, max_idx: i64) -> i64 {
    if !idx.is_finite() || idx > max_idx as f64 {
        return NA_INDEX;
    }
    // C converts through `R_xlen_t`, which truncates toward zero.
    (idx - 1.0) as i64
}

fn exclude_real(idxs: &[f64], max_idx: i64) -> Vec<i64> {
    if max_idx <= 0 {
        return Vec::new();
    }
    let mut excluded = vec![false; max_idx as usize];
    let mut keep = max_idx;
    for &raw in idxs {
        if !(raw < 0.0) || !raw.is_finite() {
            continue;
        }
        let flipped = -raw;
        if !flipped.is_finite() {
            continue;
        }
        let idx = flipped as i64;
        if idx > 0 && idx <= max_idx {
            let pos = (idx as usize) - 1;
            if !excluded[pos] {
                excluded[pos] = true;
                keep -= 1;
            }
        }
    }
    kept_positions(&excluded, keep, max_idx)
}

fn kept_positions(excluded: &[bool], keep: i64, max_idx: i64) -> Vec<i64> {
    if keep == 0 {
        return Vec::new();
    }
    let mut upper = max_idx - 1;
    while upper >= 0 && excluded[upper as usize] {
        upper -= 1;
    }
    upper += 1;
    let mut ans = Vec::with_capacity(keep as usize);
    for ii in 0..upper {
        if !excluded[ii as usize] {
            ans.push(ii);
        }
    }
    ans
}

fn validate_logical(idxs: &[u8], max_idx: i64) -> Result<Option<Vec<i64>>, String> {
    let nidxs = idxs.len() as i64;
    if nidxs == 0 {
        return Ok(Some(Vec::new()));
    }

    if nidxs > max_idx {
        let mut ans = Vec::new();
        for ii in 0..max_idx {
            let flag = idxs[ii as usize];
            if flag != 0 {
                ans.push(if flag == 2 { NA_INDEX } else { ii });
            }
        }
        for ii in max_idx..nidxs {
            if idxs[ii as usize] != 0 {
                ans.push(NA_INDEX);
            }
        }
        return Ok(Some(ans));
    }

    let last_part = (max_idx % nidxs) as usize;
    let nidxs_us = nidxs as usize;
    let mut na_count = 0i64;
    let mut count1 = 0i64;
    let mut count2 = 0i64;
    for (ii, &flag) in idxs.iter().enumerate() {
        if flag == 0 {
            continue;
        }
        if flag == 2 {
            na_count += 1;
        }
        if ii < last_part {
            count1 += 1;
        } else {
            count2 += 1;
        }
    }
    let count = count1 + count2;
    if na_count == 0 && count == nidxs {
        return Ok(None);
    }

    let mut pattern = Vec::with_capacity(count as usize);
    for (ii, &flag) in idxs.iter().take(nidxs_us).enumerate() {
        if flag != 0 {
            pattern.push(if flag == 2 { NA_INDEX } else { ii as i64 });
        }
    }

    let mut ans = Vec::with_capacity(((max_idx / nidxs) * count + count1) as usize);
    ans.extend_from_slice(&pattern);
    let mut kk = nidxs;
    while kk + nidxs <= max_idx {
        for &base in &pattern {
            ans.push(if base == NA_INDEX { NA_INDEX } else { base + kk });
        }
        kk += nidxs;
    }
    for &base in pattern.iter().take(count1 as usize) {
        ans.push(if base == NA_INDEX { NA_INDEX } else { base + kk });
    }
    Ok(Some(ans))
}

#[cfg(feature = "python")]
mod py {
    use numpy::{PyArray1, PyArrayMethods, PyReadonlyArray1};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::{Subscripts, NA_INTEGER};

    #[pyfunction]
    #[pyo3(name = "weighted_mean", signature = (x, w=None, idxs=None, na_rm=false, refine=false))]
    fn weighted_mean_py<'py>(
        x: PyReadonlyArray1<'py, f64>,
        w: Option<PyReadonlyArray1<'py, f64>>,
        idxs: Option<Bound<'py, PyAny>>,
        na_rm: bool,
        refine: bool,
    ) -> PyResult<f64> {
        let values = x
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        let subscripts = match idxs.as_ref() {
            None => Subscripts::All,
            Some(obj) => subscripts_from_py(obj)?,
        };
        let computed = match &w {
            Some(weights) => {
                let weight_slice = weights
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                crate::weighted_mean(values, Some(weight_slice), subscripts, na_rm, refine)
            }
            None => crate::weighted_mean(values, None, subscripts, na_rm, refine),
        };
        computed.map_err(PyValueError::new_err)
    }

    fn owned_slice<T: numpy::Element + Copy>(array: &Bound<'_, PyArray1<T>>) -> PyResult<Vec<T>> {
        let view = array.readonly();
        let slice = view
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        Ok(slice.to_vec())
    }

    fn subscripts_from_py(idxs: &Bound<'_, PyAny>) -> PyResult<Subscripts> {
        if let Ok(array) = idxs.cast::<PyArray1<bool>>() {
            let flags = owned_slice(array)?
                .into_iter()
                .map(|flag| u8::from(flag))
                .collect();
            return Ok(Subscripts::Logical(flags));
        }
        if let Ok(array) = idxs.cast::<PyArray1<i32>>() {
            let values = owned_slice(array)?
                .into_iter()
                .map(i64::from)
                .collect();
            return Ok(Subscripts::Integer {
                values,
                na_sentinel: Some(NA_INTEGER),
            });
        }
        if let Ok(array) = idxs.cast::<PyArray1<i64>>() {
            return Ok(Subscripts::Integer {
                values: owned_slice(array)?,
                na_sentinel: None,
            });
        }
        if let Ok(array) = idxs.cast::<PyArray1<f64>>() {
            return Ok(Subscripts::Real(owned_slice(array)?));
        }
        Err(PyValueError::new_err(
            "idxs can only be integer, numeric, or logical",
        ))
    }

    #[pymodule]
    fn weightedmean(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(weighted_mean_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn real(idxs: &[f64]) -> Subscripts {
        Subscripts::Real(idxs.to_vec())
    }

    fn ints(idxs: &[i64]) -> Subscripts {
        Subscripts::Integer {
            values: idxs.to_vec(),
            na_sentinel: None,
        }
    }

    fn mean(x: &[f64], w: Option<&[f64]>, idxs: Subscripts, na_rm: bool, refine: bool) -> f64 {
        weighted_mean(x, w, idxs, na_rm, refine).unwrap()
    }

    #[test]
    fn empty_input_is_nan() {
        let value = mean(&[], None, Subscripts::All, false, false);
        assert!(value.is_nan());
    }

    #[test]
    fn equal_weights_match_the_arithmetic_mean() {
        let x = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0];
        assert!((mean(&x, None, Subscripts::All, false, false) - 5.5).abs() < 1e-12);
    }

    #[test]
    fn negative_weight_stays_in_the_sum() {
        let x = [4.0, 1.0];
        let w = [1.0, -0.5];
        let value = mean(&x, Some(&w), Subscripts::All, false, false);
        assert!((value - 7.0).abs() < 1e-12);
    }

    #[test]
    fn zero_weight_skips_a_missing_x_even_without_na_rm() {
        let x = [1.0, f64::NAN, 3.0];
        let w = [1.0, 0.0, 1.0];
        let value = mean(&x, Some(&w), Subscripts::All, false, false);
        assert!((value - 2.0).abs() < 1e-12);
    }

    #[test]
    fn missing_weight_with_present_x_is_missing() {
        let x = [1.0, 2.0, 3.0];
        let w = [1.0, f64::NAN, 1.0];
        assert!(is_r_na(mean(&x, Some(&w), Subscripts::All, false, false)));
        assert!(is_r_na(mean(&x, Some(&w), Subscripts::All, true, false)));
    }

    fn is_r_na(value: f64) -> bool {
        let bits = value.to_bits();
        bits == 0x7ff8_0000_0000_07a2 || bits == 0x7ff0_0000_0000_07a2
    }

    #[test]
    fn na_rm_skips_missing_x_and_a_paired_missing_weight() {
        let x = [f64::NAN, 2.0, 3.0];
        let w = [f64::NAN, 1.0, 1.0];
        assert!(is_r_na(mean(&x, Some(&w), Subscripts::All, false, false)));
        let value = mean(&x, Some(&w), Subscripts::All, true, false);
        assert!((value - 2.5).abs() < 1e-12);
    }

    #[test]
    fn infinite_total_weight_beats_a_later_missing_value() {
        let early_na = mean(&[f64::NAN, 1.0], Some(&[1.0, f64::INFINITY]), Subscripts::All, false, false);
        assert!(is_r_na(early_na));
        let early_inf = mean(&[1.0, f64::NAN], Some(&[f64::INFINITY, 1.0]), Subscripts::All, false, false);
        assert!(early_inf.is_nan() && !is_r_na(early_inf));
    }

    #[test]
    fn refine_recovers_a_digit_lost_by_the_first_pass() {
        let x = [1e16, 1.0, -1e16, 2.0];
        let w = [1.0, 1.0, 1.0, 1.0];
        let plain = mean(&x, Some(&w), Subscripts::All, false, false);
        let refined = mean(&x, Some(&w), Subscripts::All, false, true);
        assert!((plain - 0.5).abs() < 1e-12);
        assert!((refined - 0.875).abs() < 1e-12);
    }

    #[test]
    fn one_based_positive_and_negative_indices() {
        let x = [1.0, 2.0, 3.0, 4.0, 5.0];
        let picked = mean(&x, None, ints(&[2, 4]), false, false);
        assert!((picked - 3.0).abs() < 1e-12);
        let dropped = mean(&x, None, ints(&[-2]), false, false);
        assert!((dropped - 3.25).abs() < 1e-12);
    }

    #[test]
    fn logical_subscripts_recycle() {
        let x = [1.0, 2.0, 3.0, 4.0, 5.0];
        let flags = vec![1u8, 0u8];
        let value = mean(&x, None, Subscripts::Logical(flags), false, false);
        assert!((value - 3.0).abs() < 1e-12);
    }

    #[test]
    fn logical_na_recycles_like_r() {
        let x = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0];
        let flags = vec![0u8, 1, 2];
        assert!(is_r_na(mean(&x, None, Subscripts::Logical(flags.clone()), false, false)));
        let kept = mean(&x, None, Subscripts::Logical(flags), true, false);
        assert!((kept - 3.5).abs() < 1e-12);

        let only = vec![2u8];
        let y = [1.0, 2.0, 3.0, 4.0];
        assert!(is_r_na(mean(&y, None, Subscripts::Logical(only.clone()), false, false)));
        assert!(mean(&y, None, Subscripts::Logical(only), true, false).is_nan());
    }

    #[test]
    fn infinite_index_is_missing_and_does_not_panic() {
        let x = [10.0, 20.0, 30.0];
        let only = mean(&x, None, real(&[f64::INFINITY]), false, false);
        assert!(only.is_nan());
        let kept = mean(&x, None, real(&[1.0, f64::INFINITY]), true, false);
        assert!((kept - 10.0).abs() < 1e-12);
    }

    #[test]
    fn mixed_signs_are_rejected() {
        let x = [1.0, 2.0, 3.0];
        let err = weighted_mean(&x, None, ints(&[1, -1]), false, false).unwrap_err();
        assert!(err.contains("negative subscripts"));
    }
}
