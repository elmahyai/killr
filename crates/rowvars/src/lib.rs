//! Row and column variances, ported from matrixStats `src/rowVars.c`.
//!
//! When `center` is omitted, each margin is the unbiased sample variance from
//! `rowVars_lowlevel_template.h`: sum, optional residual refine for doubles,
//! then the sum of squared deviations divided by `n - 1`. Fewer than two
//! finite values, or any NaN when `na.rm` is false, stores R's NA. Integer
//! input forces `refine` off; the Python wrapper casts those values to
//! float64 and passes `refine = false`.
//!
//! A supplied `center` follows `R/rowVars.R` rather than the C routine.
//! The result is `n / (n - 1) * mean((x - center)^2)`. Infinite centers are
//! applied before the row mean and after the column mean. The first call,
//! and then every 50th, also compares that primary formula with
//! `mean(x^2) - center^2`.
//!
//! `rows` and `cols` follow `validateIndices`: missing means every position,
//! values are 1-based, zeros are dropped, and negatives exclude. A missing
//! index reads as R's NA.

use std::sync::Mutex;

/// R's `NA_real_`: a NaN whose low 32 bits are 1954 (`0x7A2`).
const NA_REAL_BITS: u64 = 0x7ff0_0000_0000_07a2;

/// Default of `matrixStats.vars.formula.freq`.
const FORMULA_FREQ: i64 = 50;

static FORMULA_COUNTDOWN: Mutex<Option<i64>> = Mutex::new(None);

/// 1-based subscript vector. `All` selects every position in order.
#[derive(Clone, Debug, PartialEq)]
pub enum Subset {
    All,
    /// 0-based positions. `None` is an NA index.
    At(Vec<Option<usize>>),
}

/// Sample variance of each row, or of each column when `by_row` is false.
///
/// `x` is addressed with the given strides. Column-major storage, matching
/// R, uses `row_stride == 1` and `col_stride == nrow`. `center`, when set,
/// has one value per row (`by_row`) or column, before subscripting.
pub fn vars_f64(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    row_stride: usize,
    col_stride: usize,
    rows: &Subset,
    cols: &Subset,
    na_rm: bool,
    refine: bool,
    by_row: bool,
    center: Option<&[f64]>,
) -> Result<Vec<f64>, String> {
    if nrow > 0 && ncol > 0 {
        ensure_span(x.len(), nrow, ncol, row_stride, col_stride)?;
    }
    let row_pos = positions(rows, nrow);
    let col_pos = positions(cols, ncol);
    let (outer, inner) = if by_row {
        (row_pos, col_pos)
    } else {
        (col_pos, row_pos)
    };
    let n_out = outer.len();
    let n_in = inner.len();

    let Some(center) = center else {
        let mut ans = Vec::with_capacity(n_out);
        for &out_at in &outer {
            ans.push(sample_variance(
                x,
                row_stride,
                col_stride,
                out_at,
                &inner,
                by_row,
                na_rm,
                refine,
            ));
        }
        return Ok(ans);
    };

    let margin = if by_row { nrow } else { ncol };
    if center.len() != margin {
        return Err(format!(
            "Argument 'center' should be of the same length as number of {} of 'x': {} != {}",
            if by_row { "rows" } else { "columns" },
            center.len(),
            margin
        ));
    }
    // `ncol <= 1` returns before the formula check in R/rowVars.R.
    if n_in <= 1 {
        return Ok(vec![na_real(); n_out]);
    }

    let center = take_center(center, if by_row { rows } else { cols }, margin);
    let (n_obs, na_rm) = observation_counts(
        x,
        row_stride,
        col_stride,
        &outer,
        &inner,
        by_row,
        na_rm,
    );
    let when = should_validate();
    // Rows write Inf centers onto the data before the mean, except while the
    // formula check is running. Columns always write them onto the mean.
    let inf_before = by_row && when.is_none();
    let primary = margin_primary(
        x,
        row_stride,
        col_stride,
        &outer,
        &inner,
        by_row,
        &center,
        na_rm,
        inf_before,
    );
    if let Some(when) = when {
        let checked = margin_primary(
            x,
            row_stride,
            col_stride,
            &outer,
            &inner,
            by_row,
            &center,
            na_rm,
            false,
        );
        let alternative = margin_alternative(
            x,
            row_stride,
            col_stride,
            &outer,
            &inner,
            by_row,
            &center,
            na_rm,
        );
        if let Some(reason) = all_equal_numeric(&checked, &alternative) {
            return Err(formula_error(by_row, &reason, &when));
        }
        return Ok(scale_variance(&checked, &n_obs));
    }
    Ok(scale_variance(&primary, &n_obs))
}

/// Clear the every-50 formula check so the next `center` call validates.
pub fn reset_formula_check() {
    *FORMULA_COUNTDOWN.lock().expect("formula counter") = None;
}

fn sample_variance(
    x: &[f64],
    row_stride: usize,
    col_stride: usize,
    out_at: Option<usize>,
    inner: &[Option<usize>],
    by_row: bool,
    na_rm: bool,
    refine: bool,
) -> f64 {
    let mut sum = 0.0;
    let mut count = 0u64;
    for &in_at in inner {
        let value = fetch(x, row_stride, col_stride, out_at, in_at, by_row);
        if value.is_nan() {
            if !na_rm {
                return na_real();
            }
        } else {
            sum += value;
            count += 1;
        }
    }
    if count <= 1 {
        return na_real();
    }
    let mut mu = sum / count as f64;
    if refine {
        let mut residual = 0.0;
        for &in_at in inner {
            let value = fetch(x, row_stride, col_stride, out_at, in_at, by_row);
            if !value.is_nan() {
                residual += value - mu;
            }
        }
        mu += residual / count as f64;
    }
    let mut sigma2 = 0.0;
    for &in_at in inner {
        let value = fetch(x, row_stride, col_stride, out_at, in_at, by_row);
        if value.is_nan() {
            continue;
        }
        let mut diff = value - mu;
        diff *= diff;
        sigma2 += diff;
    }
    sigma2 / (count - 1) as f64
}

fn observation_counts(
    x: &[f64],
    row_stride: usize,
    col_stride: usize,
    outer: &[Option<usize>],
    inner: &[Option<usize>],
    by_row: bool,
    na_rm: bool,
) -> (Vec<f64>, bool) {
    let n_in = inner.len();
    let mut n_obs = vec![n_in as f64; outer.len()];
    if !na_rm {
        return (n_obs, false);
    }
    let mut any_na = false;
    for (ii, &out_at) in outer.iter().enumerate() {
        let mut nac = 0usize;
        for &in_at in inner {
            if fetch(x, row_stride, col_stride, out_at, in_at, by_row).is_nan() {
                nac += 1;
            }
        }
        if nac > 0 {
            any_na = true;
            let n = n_in - nac;
            n_obs[ii] = if n <= 1 { na_real() } else { n as f64 };
        }
    }
    if any_na {
        (n_obs, true)
    } else {
        (n_obs, false)
    }
}

fn margin_primary(
    x: &[f64],
    row_stride: usize,
    col_stride: usize,
    outer: &[Option<usize>],
    inner: &[Option<usize>],
    by_row: bool,
    center: &[f64],
    na_rm: bool,
    inf_before: bool,
) -> Vec<f64> {
    let mut ans = Vec::with_capacity(outer.len());
    for (ii, &out_at) in outer.iter().enumerate() {
        let c = center[ii];
        let mean = if inf_before && c.is_infinite() {
            sequential_mean(inner.len(), na_rm, |_| f64::NAN)
        } else {
            let mut mean = sequential_mean(inner.len(), na_rm, |jj| {
                let raw = fetch(x, row_stride, col_stride, out_at, inner[jj], by_row);
                let diff = raw - c;
                diff * diff
            });
            if !inf_before && c.is_infinite() {
                mean = f64::NAN;
            }
            mean
        };
        ans.push(mean);
    }
    ans
}

fn margin_alternative(
    x: &[f64],
    row_stride: usize,
    col_stride: usize,
    outer: &[Option<usize>],
    inner: &[Option<usize>],
    by_row: bool,
    center: &[f64],
    na_rm: bool,
) -> Vec<f64> {
    let mut ans = Vec::with_capacity(outer.len());
    for (ii, &out_at) in outer.iter().enumerate() {
        let mean_sq = sequential_mean(inner.len(), na_rm, |jj| {
            let raw = fetch(x, row_stride, col_stride, out_at, inner[jj], by_row);
            raw * raw
        });
        let c = center[ii];
        ans.push(mean_sq - c * c);
    }
    ans
}

fn sequential_mean(n_full: usize, na_rm: bool, mut value: impl FnMut(usize) -> f64) -> f64 {
    if !na_rm {
        let mut sum = 0.0;
        for jj in 0..n_full {
            sum += value(jj);
        }
        return sum / n_full as f64;
    }
    let mut sum = 0.0;
    let mut count = 0u64;
    for jj in 0..n_full {
        let item = value(jj);
        if !item.is_nan() {
            sum += item;
            count += 1;
        }
    }
    if count == 0 {
        0.0 / 0.0
    } else {
        sum / count as f64
    }
}

fn scale_variance(means: &[f64], n_obs: &[f64]) -> Vec<f64> {
    means
        .iter()
        .zip(n_obs.iter())
        .map(|(&mean, &n)| mean * (n / (n - 1.0)))
        .collect()
}

/// `Some(reason)` when `all.equal.numeric` would not return TRUE.
fn all_equal_numeric(target: &[f64], current: &[f64]) -> Option<String> {
    let tolerance = f64::EPSILON.sqrt();
    if target.len() != current.len() {
        return Some(format!(
            "Numeric: lengths ({}, {}) differ",
            target.len(),
            current.len()
        ));
    }
    let target_na = target.iter().filter(|v| v.is_nan()).count();
    let current_na = current.iter().filter(|v| v.is_nan()).count();
    if target.iter().zip(current.iter()).any(|(t, c)| t.is_nan() != c.is_nan()) {
        return Some(format!(
            "'is.NA' value mismatch: {current_na} in current {target_na} in target"
        ));
    }
    let mut kept_t = Vec::new();
    let mut kept_c = Vec::new();
    for (&t, &c) in target.iter().zip(current.iter()) {
        if !(t.is_nan() || t == c) {
            kept_t.push(t);
            kept_c.push(c);
        }
    }
    if kept_t.is_empty() {
        return None;
    }
    let n = kept_t.len() as f64;
    let mut scale = kept_t.iter().map(|v| v.abs()).sum::<f64>() / n;
    let what = if scale.is_finite() && scale > tolerance {
        "relative"
    } else {
        scale = 1.0;
        "absolute"
    };
    let xy = kept_t
        .iter()
        .zip(kept_c.iter())
        .map(|(t, c)| (t - c).abs())
        .sum::<f64>()
        / (n * scale);
    if xy.is_nan() || xy > tolerance {
        Some(format!("Mean {what} difference: {xy}"))
    } else {
        None
    }
}

fn formula_error(by_row: bool, reason: &str, when: &str) -> String {
    let who = if by_row {
        "rowVars() or rowSds()"
    } else {
        "colVars() or colSds()"
    };
    format!(
        "Detected incorrect use of argument 'center' for {who}. The value of 'center' does not meet the assumption that estimating the variance using the 'primary' or the 'alternative' formula does not matter as they should give the same results, which suggests a misunderstanding on what argument 'center' should be. Please see help(\"rowVars\", package = \"matrixStats\"). The reason was: {reason} (this validation is performed {when} per R option 'matrixStats.vars.formula.freq')"
    )
}

fn should_validate() -> Option<String> {
    let mut countdown = FORMULA_COUNTDOWN.lock().expect("formula counter");
    if let Some(left) = countdown.as_mut() {
        *left -= 1;
        if *left > 0 {
            return None;
        }
    }
    *countdown = Some(FORMULA_FREQ);
    Some(format!("every {FORMULA_FREQ} call to this function"))
}

fn take_center(center: &[f64], subset: &Subset, margin: usize) -> Vec<f64> {
    match subset {
        Subset::All => {
            debug_assert_eq!(center.len(), margin);
            center.to_vec()
        }
        Subset::At(idx) => idx
            .iter()
            .map(|pos| match pos {
                Some(i) => center[*i],
                None => na_real(),
            })
            .collect(),
    }
}

fn fetch(
    x: &[f64],
    row_stride: usize,
    col_stride: usize,
    out_at: Option<usize>,
    in_at: Option<usize>,
    by_row: bool,
) -> f64 {
    let (row, col) = if by_row {
        (out_at, in_at)
    } else {
        (in_at, out_at)
    };
    match (row, col) {
        (Some(row), Some(col)) => x[row * row_stride + col * col_stride],
        _ => na_real(),
    }
}

fn na_real() -> f64 {
    f64::from_bits(NA_REAL_BITS)
}

fn positions(subset: &Subset, n: usize) -> Vec<Option<usize>> {
    match subset {
        Subset::All => (0..n).map(Some).collect(),
        Subset::At(idx) => idx.clone(),
    }
}

fn ensure_span(
    len: usize,
    nrow: usize,
    ncol: usize,
    row_stride: usize,
    col_stride: usize,
) -> Result<(), String> {
    if nrow == 0 || ncol == 0 {
        return Ok(());
    }
    let last = (nrow - 1)
        .checked_mul(row_stride)
        .and_then(|head| {
            (ncol - 1)
                .checked_mul(col_stride)
                .and_then(|tail| head.checked_add(tail))
        })
        .ok_or_else(|| "dimension overflow".to_string())?;
    if last < len {
        Ok(())
    } else {
        Err("Argument 'dim.' does not match length of argument 'x'".to_string())
    }
}

/// 1-based integer indices. `i32::MIN` is R's integer NA.
pub fn validate_int(idxs: &[i64], max_idx: usize) -> Result<Subset, String> {
    if idxs.is_empty() {
        return Ok(Subset::At(Vec::new()));
    }

    let mut state = 0_i8;
    let mut count = 0_usize;
    let mut need_realloc = false;

    for &idx in idxs {
        if idx > 0 || is_int_na(idx) {
            if state < 0 {
                return Err("only 0's may be mixed with negative subscripts".to_string());
            }
            if !is_int_na(idx) && idx as usize > max_idx {
                return Err("subscript out of bounds".to_string());
            }
            state = 1;
            count += 1;
        } else if idx < 0 {
            if state > 0 {
                return Err("only 0's may be mixed with negative subscripts".to_string());
            }
            state = -1;
            need_realloc = true;
        } else {
            need_realloc = true;
        }
    }

    if state >= 0 && !need_realloc {
        let mut ans = Vec::with_capacity(count);
        for &idx in idxs {
            ans.push(int_to_zero_based(idx));
        }
        return Ok(Subset::At(ans));
    }

    if state >= 0 {
        let mut ans = Vec::with_capacity(count);
        for &idx in idxs {
            if idx != 0 {
                ans.push(int_to_zero_based(idx));
            }
        }
        return Ok(Subset::At(ans));
    }

    exclude_negatives(idxs.iter().copied(), max_idx)
}

/// 1-based real indices. NaN and both infinities are NA indices.
pub fn validate_real(idxs: &[f64], max_idx: usize) -> Result<Subset, String> {
    if idxs.is_empty() {
        return Ok(Subset::At(Vec::new()));
    }

    let mut state = 0_i8;
    let mut count = 0_usize;
    let mut need_realloc = false;

    for &idx in idxs {
        if idx > 0.0 || !idx.is_finite() {
            if state < 0 {
                return Err("only 0's may be mixed with negative subscripts".to_string());
            }
            if idx.is_finite() && idx > max_idx as f64 {
                return Err("subscript out of bounds".to_string());
            }
            state = 1;
            count += 1;
        } else if idx < 0.0 {
            if state > 0 {
                return Err("only 0's may be mixed with negative subscripts".to_string());
            }
            state = -1;
            need_realloc = true;
        } else {
            need_realloc = true;
        }
    }

    if state >= 0 && !need_realloc {
        let mut ans = Vec::with_capacity(count);
        for &idx in idxs {
            ans.push(real_to_zero_based(idx));
        }
        return Ok(Subset::At(ans));
    }

    if state >= 0 {
        let mut ans = Vec::with_capacity(count);
        for &idx in idxs {
            if idx != 0.0 {
                ans.push(real_to_zero_based(idx));
            }
        }
        return Ok(Subset::At(ans));
    }

    let mut drop = vec![false; max_idx];
    let mut kept = max_idx;
    for &idx in idxs {
        let excl = (-idx).trunc();
        if excl > 0.0 && excl <= max_idx as f64 {
            let pos = (excl as usize) - 1;
            if !drop[pos] {
                drop[pos] = true;
                kept -= 1;
            }
        }
    }
    if kept == 0 {
        return Ok(Subset::At(Vec::new()));
    }
    let mut ans = Vec::with_capacity(kept);
    for (pos, dropped) in drop.into_iter().enumerate() {
        if !dropped {
            ans.push(Some(pos));
        }
    }
    Ok(Subset::At(ans))
}

/// Logical indices. `1` is TRUE, `0` is FALSE, and any negative value is NA.
/// A pattern shorter than the margin is recycled, matching R.
pub fn validate_logical(idxs: &[i8], max_idx: usize) -> Result<Subset, String> {
    let nidxs = idxs.len();
    if nidxs == 0 {
        return Ok(Subset::At(Vec::new()));
    }
    if nidxs > max_idx {
        return Err("logical subscript too long".to_string());
    }

    let last_part = max_idx % nidxs;
    let mut count1 = 0_usize;
    let mut count2 = 0_usize;
    let mut na_count = 0_usize;
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
    if na_count == 0 && count == nidxs {
        return Ok(Subset::All);
    }

    let ans_n = (max_idx / nidxs) * count + count1;
    let mut first = Vec::with_capacity(count);
    for (ii, &flag) in idxs.iter().enumerate() {
        if flag != 0 {
            if flag < 0 {
                first.push(None);
            } else {
                first.push(Some(ii));
            }
        }
    }

    let mut ans = Vec::with_capacity(ans_n);
    ans.extend_from_slice(&first);
    let mut kk = nidxs;
    while kk + nidxs <= max_idx {
        for item in &first {
            ans.push(item.map(|pos| pos + kk));
        }
        kk += nidxs;
    }
    for item in first.iter().take(count1) {
        ans.push(item.map(|pos| pos + kk));
    }
    Ok(Subset::At(ans))
}

fn is_int_na(idx: i64) -> bool {
    idx == i32::MIN as i64
}

fn int_to_zero_based(idx: i64) -> Option<usize> {
    if is_int_na(idx) {
        None
    } else {
        Some((idx as usize) - 1)
    }
}

fn real_to_zero_based(idx: f64) -> Option<usize> {
    if !idx.is_finite() {
        None
    } else {
        let zero_based = (idx - 1.0).trunc();
        if zero_based <= 0.0 {
            Some(0)
        } else {
            Some(zero_based as usize)
        }
    }
}

fn exclude_negatives(idxs: impl Iterator<Item = i64>, max_idx: usize) -> Result<Subset, String> {
    let mut drop = vec![false; max_idx];
    let mut kept = max_idx;
    for idx in idxs {
        let Some(excl) = idx.checked_neg() else {
            continue;
        };
        if excl > 0 && (excl as usize) <= max_idx {
            let pos = (excl as usize) - 1;
            if !drop[pos] {
                drop[pos] = true;
                kept -= 1;
            }
        }
    }
    if kept == 0 {
        return Ok(Subset::At(Vec::new()));
    }
    let mut ans = Vec::with_capacity(kept);
    for (pos, dropped) in drop.into_iter().enumerate() {
        if !dropped {
            ans.push(Some(pos));
        }
    }
    Ok(Subset::At(ans))
}

#[cfg(feature = "python")]
mod py {
    use numpy::ndarray::{Array1, ArrayView2};
    use numpy::{IntoPyArray, PyReadonlyArray1, PyReadonlyArray2};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::{validate_int, validate_logical, validate_real, reset_formula_check, Subset, vars_f64};

    fn parse_subset(
        obj: Option<&Bound<'_, PyAny>>,
        kind: &str,
        max_idx: usize,
    ) -> PyResult<Subset> {
        if kind == "all" {
            return Ok(Subset::All);
        }
        let Some(obj) = obj else {
            return Ok(Subset::All);
        };
        let subset = match kind {
            "int" => {
                let arr = obj.extract::<PyReadonlyArray1<i64>>()?;
                let slice = arr
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                validate_int(slice, max_idx)
            }
            "real" => {
                let arr = obj.extract::<PyReadonlyArray1<f64>>()?;
                let slice = arr
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                validate_real(slice, max_idx)
            }
            "logical" => {
                let arr = obj.extract::<PyReadonlyArray1<i8>>()?;
                let slice = arr
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                validate_logical(slice, max_idx)
            }
            _ => {
                return Err(PyValueError::new_err(
                    "idxs can only be integer, numeric, or logical",
                ))
            }
        };
        subset.map_err(PyValueError::new_err)
    }

    fn contiguous<'a>(view: &'a ArrayView2<'a, f64>) -> Option<(&'a [f64], usize, usize)> {
        let (nrow, ncol) = view.dim();
        if nrow == 0 || ncol == 0 {
            return None;
        }
        let slice = view.as_slice_memory_order()?;
        let row_stride = view.strides()[0];
        let col_stride = view.strides()[1];
        if row_stride == 1 && col_stride == nrow as isize {
            return Some((slice, 1, nrow));
        }
        if col_stride == 1 && row_stride == ncol as isize {
            return Some((slice, ncol, 1));
        }
        None
    }

    fn owned_column_major(view: ArrayView2<'_, f64>) -> Vec<f64> {
        let (nrow, ncol) = view.dim();
        let mut flat = Vec::with_capacity(nrow.saturating_mul(ncol));
        for col in 0..ncol {
            for row in 0..nrow {
                flat.push(view[[row, col]]);
            }
        }
        flat
    }

    #[pyfunction]
    #[pyo3(name = "vars_f64", signature = (x, na_rm, refine, by_row, center=None, rows=None, rows_kind="all", cols=None, cols_kind="all"))]
    fn vars_f64_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        na_rm: bool,
        refine: bool,
        by_row: bool,
        center: Option<PyReadonlyArray1<'py, f64>>,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
    ) -> PyResult<Py<PyAny>> {
        let view = x.as_array();
        let (nrow, ncol) = view.dim();
        let row_subset = parse_subset(rows.as_ref(), rows_kind, nrow)?;
        let col_subset = parse_subset(cols.as_ref(), cols_kind, ncol)?;
        let center_owned = match center.as_ref() {
            Some(arr) => Some(
                arr.as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?
                    .to_vec(),
            ),
            None => None,
        };
        let center_ref = center_owned.as_deref();
        let result = if nrow == 0 || ncol == 0 {
            vars_f64(
                &[],
                nrow,
                ncol,
                1,
                0,
                &row_subset,
                &col_subset,
                na_rm,
                refine,
                by_row,
                center_ref,
            )
        } else if let Some((slice, row_stride, col_stride)) = contiguous(&view) {
            vars_f64(
                slice,
                nrow,
                ncol,
                row_stride,
                col_stride,
                &row_subset,
                &col_subset,
                na_rm,
                refine,
                by_row,
                center_ref,
            )
        } else {
            let owned = owned_column_major(view);
            vars_f64(
                &owned,
                nrow,
                ncol,
                1,
                nrow,
                &row_subset,
                &col_subset,
                na_rm,
                refine,
                by_row,
                center_ref,
            )
        }
        .map_err(PyValueError::new_err)?;
        let arr = Array1::from_shape_vec(result.len(), result)
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        Ok(arr.into_pyarray(py).into_any().unbind())
    }

    #[pyfunction]
    fn reset_formula_check_py() {
        reset_formula_check();
    }

    #[pymodule]
    fn rowvars(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(vars_f64_py, m)?)?;
        m.add_function(wrap_pyfunction!(reset_formula_check_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{reset_formula_check, validate_int, vars_f64, Subset, NA_REAL_BITS};

    fn col_major_1_to_12() -> Vec<f64> {
        (1..=12).map(|v| v as f64).collect()
    }

    #[test]
    fn integer_rows_are_sixteen_and_columns_are_five_thirds() {
        let x = col_major_1_to_12();
        let rows = vars_f64(&x, 4, 3, 1, 4, &Subset::All, &Subset::All, false, false, true, None)
            .unwrap();
        assert_eq!(rows, vec![16.0, 16.0, 16.0, 16.0]);
        let cols = vars_f64(&x, 4, 3, 1, 4, &Subset::All, &Subset::All, false, false, false, None)
            .unwrap();
        assert_eq!(cols, vec![5.0 / 3.0, 5.0 / 3.0, 5.0 / 3.0]);
    }

    #[test]
    fn one_column_and_a_missing_value_are_r_na() {
        let x = col_major_1_to_12();
        let cols = validate_int(&[1], 3).unwrap();
        let one = vars_f64(&x, 4, 3, 1, 4, &Subset::All, &cols, false, true, true, None).unwrap();
        assert!(one.iter().all(|v| v.to_bits() == NA_REAL_BITS));

        let mut with_na = x.clone();
        with_na[4] = f64::NAN;
        let vars = vars_f64(
            &with_na,
            4,
            3,
            1,
            4,
            &Subset::All,
            &Subset::All,
            false,
            true,
            true,
            None,
        )
        .unwrap();
        assert_eq!(vars[0].to_bits(), NA_REAL_BITS);
        assert_eq!(&vars[1..], &[16.0, 16.0, 16.0]);
        let kept = vars_f64(
            &with_na,
            4,
            3,
            1,
            4,
            &Subset::All,
            &Subset::All,
            true,
            true,
            true,
            None,
        )
        .unwrap();
        assert_eq!(kept[0], 32.0);
    }

    #[test]
    fn repeated_columns_and_an_na_index() {
        let x = col_major_1_to_12();
        let cols = validate_int(&[1, 1, 2], 3).unwrap();
        let vars = vars_f64(&x, 4, 3, 1, 4, &Subset::All, &cols, false, false, true, None).unwrap();
        assert!(vars.iter().all(|v| (*v - 16.0 / 3.0).abs() < 1e-12));

        let cols = validate_int(&[1, i32::MIN as i64, 2], 3).unwrap();
        let stopped = vars_f64(&x, 4, 3, 1, 4, &Subset::All, &cols, false, false, true, None).unwrap();
        assert!(stopped.iter().all(|v| v.to_bits() == NA_REAL_BITS));
        let dropped = vars_f64(&x, 4, 3, 1, 4, &Subset::All, &cols, true, false, true, None).unwrap();
        assert_eq!(dropped, vec![8.0, 8.0, 8.0, 8.0]);
    }

    #[test]
    fn center_equal_to_the_mean_matches_the_c_path() {
        reset_formula_check();
        let x = col_major_1_to_12();
        let center = [5.0, 6.0, 7.0, 8.0];
        let vars = vars_f64(
            &x,
            4,
            3,
            1,
            4,
            &Subset::All,
            &Subset::All,
            false,
            true,
            true,
            Some(&center),
        )
        .unwrap();
        assert_eq!(vars, vec![16.0, 16.0, 16.0, 16.0]);
    }

    #[test]
    fn a_wrong_center_is_rejected_on_the_first_check() {
        reset_formula_check();
        let x = col_major_1_to_12();
        let err = vars_f64(
            &x,
            4,
            3,
            1,
            4,
            &Subset::All,
            &Subset::All,
            false,
            true,
            true,
            Some(&[1.0, 1.0, 1.0, 1.0]),
        )
        .unwrap_err();
        assert!(err.contains("incorrect use of argument 'center'"));
        let biased = vars_f64(
            &x,
            4,
            3,
            1,
            4,
            &Subset::All,
            &Subset::All,
            false,
            true,
            true,
            Some(&[1.0, 1.0, 1.0, 1.0]),
        )
        .unwrap();
        assert!((biased[0] - 40.0).abs() < 1e-12);
    }
}
