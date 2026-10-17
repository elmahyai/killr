//! Weighted median, ported from matrixStats `src/weightedMedian.c` and
//! `src/weightedMedian_lowlevel_template.h`.
//!
//! Index rules are copied from `src/validateIndices.c`. `weightedMedian` calls
//! that checker with out-of-bounds indices allowed, so a positive index past
//! the end becomes a missing index instead of an error.
//!
//! A weight `<= 0` is dropped, including `-Inf`. A `+Inf` weight restarts the
//! scan: every infinite weight is kept with equal weight (and on that pass
//! `-Inf` counts, because C `isinf` is true for both), and every other point
//! is dropped. The result is then R's partial-sort median of those values.
//! That path ignores `ties`. For an odd count it is not `median()`, because
//! `rPsort` only places one order statistic and the C code reads the element
//! just before it.
//!
//! The manual says a missing weight always makes the result missing. The C
//! code returns NA only when `na.rm` is false. When `na.rm` is true, a missing
//! weight is dropped.

/// 0-based index used when R would store `NA_R_XLEN_T`.
const NA_INDEX: i64 = i64::MIN;

/// Quiet NaN that R treats as `NA_real_`. A plain `0/0` NaN stays a NaN.
fn r_na() -> f64 {
    f64::from_bits(0x7ff8_0000_0000_07a2)
}

/// R's `NA_INTEGER`. Used when a 32-bit integer subscript vector is passed in.
#[cfg(feature = "python")]
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

/// Weighted median of `x`.
///
/// `w = None` gives every element weight 1. `idxs` is 1-based; `All` uses
/// every element. `ties` is 1 weighted, 2 min, 4 max, or 8 mean, and is used
/// only when `interpolate` is false. An empty selection, or one whose weights
/// were all dropped, returns R's NA.
pub fn weighted_median(
    x: &[f64],
    w: Option<&[f64]>,
    idxs: Subscripts,
    na_rm: bool,
    interpolate: bool,
    ties: i32,
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
    if !interpolate && !matches!(ties, 1 | 2 | 4 | 8) {
        return Err(format!("Unknown value of argument 'ties': {ties}"));
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
    Ok(weighted_median_selected(
        x,
        w,
        indices.as_deref(),
        na_rm,
        interpolate,
        ties,
    ))
}

fn weighted_median_selected(
    x: &[f64],
    w: Option<&[f64]>,
    indices: Option<&[i64]>,
    na_rm: bool,
    interpolate: bool,
    ties: i32,
) -> f64 {
    let nidxs = match indices {
        Some(idxs) => idxs.len(),
        None => x.len(),
    };
    let mut kept_x: Vec<f64> = Vec::with_capacity(nidxs);
    let mut kept_w: Vec<f64> = Vec::with_capacity(nidxs);
    let mut equal = false;

    for i in 0..nidxs {
        let idx = index_at(indices, i);
        let weight = load_weight(w, idx);
        if weight.is_nan() {
            if !na_rm {
                return r_na();
            }
        } else if weight <= 0.0 {
            // Drop non-positive weights, including -Inf. This runs before
            // isinf, so -Inf does not start the equal-weight path by itself.
        } else if weight.is_infinite() {
            kept_x.clear();
            kept_w.clear();
            equal = true;
            for j in 0..nidxs {
                let jdx = index_at(indices, j);
                let wj = load_weight(w, jdx);
                if wj.is_infinite() {
                    let value = load_value(x, jdx);
                    if value.is_nan() {
                        if !na_rm {
                            return r_na();
                        }
                    } else {
                        kept_x.push(value);
                    }
                } else if wj.is_nan() {
                    if !na_rm {
                        return r_na();
                    }
                }
            }
            break;
        } else {
            let value = load_value(x, idx);
            if value.is_nan() {
                if !na_rm {
                    return r_na();
                }
            } else {
                kept_x.push(value);
                kept_w.push(weight);
            }
        }
    }

    if kept_x.is_empty() {
        return r_na();
    }
    if kept_x.len() == 1 {
        return kept_x[0];
    }
    if equal {
        return partial_sort_median(&mut kept_x);
    }

    // Total weight is the sum in the order the points were kept, before the
    // sort. The C loop adds each weight as it compacts the kept points.
    let mut wtotal = 0.0;
    for weight in &kept_w {
        wtotal += *weight;
    }
    r_qsort(&mut kept_x, &mut kept_w);
    interpolate_or_ties(&kept_x, &kept_w, wtotal, interpolate, ties)
}

/// R `rPsort` median used when every kept weight is `+Inf`.
fn partial_sort_median(x: &mut [f64]) -> f64 {
    let nx = x.len();
    let half = (nx + 1) / 2;
    r_psort(x, nx, half);
    if nx % 2 == 1 {
        x[half - 1]
    } else {
        r_psort(x, half, half - 1);
        (x[half - 1] + x[half]) / 2.0
    }
}

fn interpolate_or_ties(xs: &[f64], ws: &[f64], wtotal: f64, interpolate: bool, ties: i32) -> f64 {
    let nx = xs.len();
    // C's default `half = nx + 1` means "the last value" if the scan never
    // crosses the threshold. The scan itself only stores an index `< nx`.
    let mut half = nx + 1;
    let mut tmp = 0.0;
    let mut wcum_prev = 0.0;
    let mut wcum_at = 0.0;
    if interpolate {
        for ii in 0..nx {
            let tmp_d = ws[ii] / wtotal;
            tmp += tmp_d;
            wcum_at = tmp - tmp_d / 2.0;
            if wcum_at >= 0.5 {
                half = ii;
                break;
            }
            wcum_prev = wcum_at;
        }
    } else {
        for ii in 0..nx {
            tmp += ws[ii] / wtotal;
            wcum_at = tmp;
            if tmp > 0.5 {
                half = ii;
                break;
            }
            wcum_prev = wcum_at;
        }
    }

    if half == 0 {
        return xs[0];
    }
    if half >= nx {
        return xs[nx - 1];
    }

    if interpolate {
        let mut dx = xs[half] - xs[half - 1];
        let dy_span = wcum_at - wcum_prev;
        let dy = 0.5 - wcum_at;
        dx = (dy / dy_span) * dx;
        return dx + xs[half];
    }

    let wlow = wcum_prev;
    let whigh = 1.0 - wlow;
    if whigh > 0.5 {
        xs[half]
    } else if ties == 1 {
        wlow * xs[half - 1] + whigh * xs[half]
    } else if ties == 2 {
        xs[half - 1]
    } else if ties == 4 {
        xs[half]
    } else {
        (xs[half - 1] + xs[half]) / 2.0
    }
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

/// R's `rPsort`: after the call, `x[k]` is in its sorted place among the first
/// `n` elements, with smaller values before it and larger values after it.
/// Elements before `k` are not fully sorted.
fn r_psort(x: &mut [f64], n: usize, k: usize) {
    if n <= 1 {
        return;
    }
    let mut lo: isize = 0;
    let mut hi = n as isize - 1;
    let k = k as isize;
    while lo < hi {
        let v = x[k as usize];
        let mut i = lo;
        let mut j = hi;
        while i <= j {
            while x[i as usize] < v {
                i += 1;
            }
            while v < x[j as usize] {
                j -= 1;
            }
            if i <= j {
                x.swap(i as usize, j as usize);
                i += 1;
                j -= 1;
            }
        }
        if j < k {
            lo = i;
        }
        if k < i {
            hi = j;
        }
    }
}

/// R's `R_qsort_I`, sorting `values` and applying the same swaps to `weights`.
///
/// The pivot fraction starts at 0.375 and steps by 0.0390625 until it passes
/// 0.5898437, then steps back by 0.21875. An interval is insertion-sorted when
/// it is at most 10 long, unless its start is still the original left edge:
/// that spine is partitioned again. This is what decides the order of tied
/// `x` values, which the interpolated median can see.
fn r_qsort(values: &mut [f64], weights: &mut [f64]) {
    let n = values.len() as isize;
    if n <= 1 {
        return;
    }
    let original_i: isize = 0;
    let mut r = 0.375;
    let mut stack: Vec<(isize, isize)> = Vec::new();
    let mut i: isize = 0;
    let mut j = n - 1;
    let mut state = 0; // 0 check, 1 pop, 2 size, 3 maybe insert, 4 r update, 5 partition
    loop {
        if state == 0 {
            state = if i < j { 4 } else { 1 };
            continue;
        }
        if state == 1 {
            if stack.is_empty() {
                return;
            }
            let range = stack.pop().unwrap();
            i = range.0;
            j = range.1;
            state = 2;
            continue;
        }
        if state == 2 {
            state = if j - i > 10 { 5 } else { 3 };
            continue;
        }
        if state == 3 {
            if i == original_i {
                state = 0;
                continue;
            }
            if i != j {
                insertion(values, weights, i, j);
            }
            state = 1;
            continue;
        }
        if state == 4 {
            if r < 0.5898437 {
                r += 0.0390625;
            } else {
                r -= 0.21875;
            }
            state = 5;
            continue;
        }
        let k = i + (r * (j - i) as f64) as isize;
        let mut vt = values[k as usize];
        if values[i as usize] > vt {
            swap_pair(values, weights, k, i);
            vt = values[k as usize];
        }
        if values[j as usize] < vt {
            swap_pair(values, weights, k, j);
            vt = values[k as usize];
            if values[i as usize] > vt {
                swap_pair(values, weights, k, i);
                vt = values[k as usize];
            }
        }
        let mut l = i;
        let mut ij = j;
        loop {
            l += 1;
            while values[l as usize] < vt {
                l += 1;
            }
            ij -= 1;
            while values[ij as usize] > vt {
                ij -= 1;
            }
            if l > ij {
                break;
            }
            swap_pair(values, weights, l, ij);
        }
        if ij - i > j - l {
            stack.push((i, ij));
            i = l;
        } else {
            stack.push((l, j));
            j = ij;
        }
        state = 2;
    }
}

fn swap_pair(values: &mut [f64], weights: &mut [f64], a: isize, b: isize) {
    values.swap(a as usize, b as usize);
    weights.swap(a as usize, b as usize);
}

fn insertion(values: &mut [f64], weights: &mut [f64], i: isize, j: isize) {
    let mut ii = i + 1;
    while ii <= j {
        let vt = values[ii as usize];
        let wt = weights[ii as usize];
        let mut ij = ii;
        while ij > i && values[(ij - 1) as usize] > vt {
            values[ij as usize] = values[(ij - 1) as usize];
            weights[ij as usize] = weights[(ij - 1) as usize];
            ij -= 1;
        }
        values[ij as usize] = vt;
        weights[ij as usize] = wt;
        ii += 1;
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
    #[pyo3(
        name = "weighted_median",
        signature = (x, w=None, idxs=None, na_rm=false, interpolate=true, ties=1)
    )]
    fn weighted_median_py<'py>(
        x: PyReadonlyArray1<'py, f64>,
        w: Option<PyReadonlyArray1<'py, f64>>,
        idxs: Option<Bound<'py, PyAny>>,
        na_rm: bool,
        interpolate: bool,
        ties: i32,
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
                crate::weighted_median(
                    values,
                    Some(weight_slice),
                    subscripts,
                    na_rm,
                    interpolate,
                    ties,
                )
            }
            None => crate::weighted_median(values, None, subscripts, na_rm, interpolate, ties),
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
    fn weightedmedian(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(weighted_median_py, m)?)?;
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

    fn med(x: &[f64], w: Option<&[f64]>, idxs: Subscripts, na_rm: bool, interpolate: bool, ties: i32) -> f64 {
        weighted_median(x, w, idxs, na_rm, interpolate, ties).unwrap()
    }

    fn is_r_na(value: f64) -> bool {
        value.to_bits() == 0x7ff8_0000_0000_07a2
    }

    #[test]
    fn tied_qsort_matches_r_qsort_i() {
        let mut values = [3.0, 3.0, 5.0, 1.0, 2.0, 1.0, 1.0, 3.0];
        let mut weights = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0];
        r_qsort(&mut values, &mut weights);
        assert_eq!(weights, [6.0, 3.0, 5.0, 4.0, 0.0, 7.0, 1.0, 2.0]);
        assert!(values.windows(2).all(|pair| pair[0] <= pair[1]));
    }

    #[test]
    fn psort_places_only_the_requested_index() {
        let mut x = [5.0, 1.0, 4.0, 2.0, 3.0, 9.0, 8.0, 7.0, 6.0];
        r_psort(&mut x, 9, 5);
        assert_eq!(x[5], 6.0);
        assert!(x[..5].iter().all(|v| *v <= 6.0));
        assert!(x[6..].iter().all(|v| *v >= 6.0));
    }

    #[test]
    fn equal_weights_interpolate_to_the_midpoint() {
        let x: Vec<f64> = (1..=10).map(|v| v as f64).collect();
        let value = med(&x, None, Subscripts::All, false, true, 1);
        assert!((value - 5.5).abs() < 1e-12);
    }

    #[test]
    fn ties_choose_min_or_max() {
        let x: Vec<f64> = (1..=10).map(|v| v as f64).collect();
        assert!((med(&x, None, Subscripts::All, false, false, 2) - 5.0).abs() < 1e-12);
        assert!((med(&x, None, Subscripts::All, false, false, 4) - 6.0).abs() < 1e-12);
    }

    #[test]
    fn non_positive_weight_is_dropped_and_inf_uses_partial_sort() {
        let x: Vec<f64> = (1..=10).map(|v| v as f64).collect();
        let mut w = vec![1.0; 10];
        w[0] = -1.0;
        assert!((med(&x, Some(&w), Subscripts::All, false, true, 1) - 6.0).abs() < 1e-12);

        w[0] = f64::INFINITY;
        assert!((med(&x, Some(&w), Subscripts::All, false, true, 1) - 1.0).abs() < 1e-12);

        let zeros = vec![0.0; 10];
        assert!(is_r_na(med(&x, Some(&zeros), Subscripts::All, false, true, 1)));
    }

    #[test]
    fn odd_infinite_weights_do_not_match_the_ordinary_median() {
        let x = [
            -0.6264538107423324,
            0.1836433242220822,
            -0.8356286124100472,
            1.5952808021377917,
            0.3295077718153605,
        ];
        let w = [f64::INFINITY; 5];
        let value = med(&x, Some(&w), Subscripts::All, false, true, 1);
        assert!((value - (-0.83562861241004716)).abs() < 1e-12);
    }

    #[test]
    fn missing_weight_is_dropped_only_when_na_rm_is_set() {
        let x = [1.0, 5.0, 9.0];
        let w = [1.0, f64::NAN, 1.0];
        assert!(is_r_na(med(&x, Some(&w), Subscripts::All, false, true, 1)));
        assert!((med(&x, Some(&w), Subscripts::All, true, true, 1) - 5.0).abs() < 1e-12);
    }

    #[test]
    fn zero_weight_skips_a_missing_x() {
        let x = [1.0, f64::NAN, 4.0];
        let w = [1.0, 0.0, 1.0];
        let value = med(&x, Some(&w), Subscripts::All, false, true, 1);
        assert!((value - 2.5).abs() < 1e-12);
    }

    #[test]
    fn one_based_indices() {
        let x = [1.0, 2.0, 3.0, 4.0, 5.0];
        assert!((med(&x, None, ints(&[2, 4]), false, true, 1) - 3.0).abs() < 1e-12);
        assert!((med(&x, None, ints(&[-2]), false, true, 1) - 3.5).abs() < 1e-12);
        assert!((med(&x, None, real(&[0.5, 2.9]), false, true, 1) - 1.5).abs() < 1e-12);
    }
}
