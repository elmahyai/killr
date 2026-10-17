//! Row and column median absolute deviations, ported from matrixStats
//! `src/rowMads.c`.
//!
//! `rowMads` calls this routine with `byrow = TRUE` and `colMads` with
//! `byrow = FALSE`. The R wrappers always pass `hasNA = TRUE`, so missing
//! values are always considered. `rows` and `cols` follow `validateIndices`:
//! missing means every position, values are 1-based, zeros are dropped, and
//! negatives exclude. A missing index reads as R's NA.
//!
//! With `center` omitted, each margin is `constant * median(|x - median(x)|)`,
//! the estimator `stats::mad` uses. The default constant is `1.4826`. A margin
//! with no counted value is R's NA. A single counted value is `0`, and that
//! `0` is not multiplied by `constant`. Any missing value with `na.rm = FALSE`
//! is R's NA as well: a plain NaN is not copied through.
//!
//! Integer data stays in `i32` until the final scale. When the two central
//! order statistics differ by an even number, their mean is an `i32`
//! division, and that addition wraps. `i32::MIN` is R's integer NA and is
//! never a counted value.
//!
//! With `center` set, the R wrapper subtracts it, takes the absolute value,
//! then calls `rowMedians` or `colMedians` and multiplies by `constant`.
//! `rowMads` does that subtraction in R, so an integer overflow becomes NA.
//! `colMads` subtracts through `t_tx_OP_y`, which casts to double first.

/// R's integer NA.
const NA_INTEGER: i32 = i32::MIN;

/// R's `NA_real_`: a NaN whose low 32 bits are 1954 (`0x7A2`).
const NA_REAL_BITS: u64 = 0x7ff0_0000_0000_07a2;

/// R's `R_NaN`, the plain quiet NaN `rowMedians` stores for an empty margin.
const R_NAN_BITS: u64 = 0x7ff8_0000_0000_0000;

/// 1-based subscript vector. `All` selects every position in order.
#[derive(Clone, Debug, PartialEq)]
pub enum Subset {
    All,
    /// 0-based positions. `None` is an NA index.
    At(Vec<Option<usize>>),
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

/// Median absolute deviation of each row, or of each column when `by_row` is
/// false. `center` is one value per margin. `check_i32_overflow` is unused
/// here; the integer entry point uses it for `rowMads`.
pub fn row_mads_f64(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    row_stride: usize,
    col_stride: usize,
    rows: &Subset,
    cols: &Subset,
    by_row: bool,
    scale: f64,
    na_rm: bool,
    center: Option<&[f64]>,
) -> Result<Vec<f64>, String> {
    ensure_span(x.len(), nrow, ncol, row_stride, col_stride)?;
    let margin_len = if by_row { nrow } else { ncol };
    if let Some(values) = center {
        if values.len() != margin_len {
            return Err(center_length_message(values.len(), margin_len, by_row));
        }
    }
    let row_pos = positions(rows, nrow);
    let col_pos = positions(cols, ncol);
    let (margins, alongs) = if by_row {
        (row_pos, col_pos)
    } else {
        (col_pos, row_pos)
    };
    let mut ans = Vec::with_capacity(margins.len());
    let mut buf = Vec::with_capacity(alongs.len());
    for margin in margins {
        buf.clear();
        let mut stop = false;
        let center_value = center.map(|values| match margin {
            Some(index) => values[index],
            None => f64::from_bits(NA_REAL_BITS),
        });
        for along in &alongs {
            if stop {
                break;
            }
            let (row, col) = if by_row {
                (margin, *along)
            } else {
                (*along, margin)
            };
            let value = load_f64(x, row_stride, col_stride, row, col);
            if let Some(origin) = center_value {
                let dev = (value - origin).abs();
                if dev.is_nan() {
                    if !na_rm {
                        stop = true;
                    }
                } else {
                    buf.push(dev);
                }
            } else if value.is_nan() {
                if !na_rm {
                    stop = true;
                }
            } else {
                buf.push(value);
            }
        }
        if stop {
            ans.push(if center.is_some() {
                scale * na_real()
            } else {
                na_real()
            });
        } else if center.is_some() {
            ans.push(median_f64(&mut buf, scale));
        } else {
            ans.push(mad_f64(&mut buf, scale));
        }
    }
    Ok(ans)
}

/// Median absolute deviation of an integer matrix. See [`row_mads_f64`].
///
/// `center` holds one double per original margin. Integer NA in that center
/// is already R's NA. When `check_i32_overflow` is set, a difference that
/// does not fit in `i32` is missing, matching R's `x - center` for
/// `rowMads`. `colMads` casts before subtracting, so it leaves the flag false.
pub fn row_mads_i32(
    x: &[i32],
    nrow: usize,
    ncol: usize,
    row_stride: usize,
    col_stride: usize,
    rows: &Subset,
    cols: &Subset,
    by_row: bool,
    scale: f64,
    na_rm: bool,
    center: Option<&[f64]>,
    check_i32_overflow: bool,
) -> Result<Vec<f64>, String> {
    ensure_span(x.len(), nrow, ncol, row_stride, col_stride)?;
    let margin_len = if by_row { nrow } else { ncol };
    if let Some(values) = center {
        if values.len() != margin_len {
            return Err(center_length_message(values.len(), margin_len, by_row));
        }
    }
    let row_pos = positions(rows, nrow);
    let col_pos = positions(cols, ncol);
    let (margins, alongs) = if by_row {
        (row_pos, col_pos)
    } else {
        (col_pos, row_pos)
    };
    let mut ans = Vec::with_capacity(margins.len());
    let mut buf_i = Vec::with_capacity(alongs.len());
    let mut buf_f = Vec::with_capacity(alongs.len());
    for margin in margins {
        buf_i.clear();
        buf_f.clear();
        let mut stop = false;
        let center_value = center.map(|values| match margin {
            Some(index) => values[index],
            None => f64::from_bits(NA_REAL_BITS),
        });
        for along in &alongs {
            if stop {
                break;
            }
            let (row, col) = if by_row {
                (margin, *along)
            } else {
                (*along, margin)
            };
            let value = load_i32(x, row_stride, col_stride, row, col);
            if let Some(origin) = center_value {
                match integer_deviation(value, origin, check_i32_overflow) {
                    Some(dev) => buf_f.push(dev),
                    None if na_rm => {}
                    None => stop = true,
                }
            } else if value == NA_INTEGER {
                if !na_rm {
                    stop = true;
                }
            } else {
                buf_i.push(value);
            }
        }
        if stop {
            ans.push(if center.is_some() {
                scale * na_real()
            } else {
                na_real()
            });
        } else if center.is_some() {
            ans.push(median_f64(&mut buf_f, scale));
        } else {
            ans.push(mad_i32(&mut buf_i, scale));
        }
    }
    Ok(ans)
}

fn mad_f64(values: &mut [f64], scale: f64) -> f64 {
    let kk = values.len();
    if kk == 0 {
        return na_real();
    }
    if kk == 1 {
        return 0.0;
    }
    let qq = kk / 2 - 1;
    let upper = nth_f64(values, qq + 1);
    if kk % 2 == 1 {
        for value in values.iter_mut() {
            *value = (*value - upper).abs();
        }
        scale * nth_f64(values, qq + 1)
    } else {
        let lower = nth_f64(&mut values[..qq + 1], qq);
        let mu = (lower + upper) / 2.0;
        for value in values.iter_mut() {
            *value = (*value - mu).abs();
        }
        let upper = nth_f64(values, qq + 1);
        let lower = nth_f64(&mut values[..qq + 1], qq);
        scale * (lower + upper) / 2.0
    }
}

fn mad_i32(values: &mut [i32], scale: f64) -> f64 {
    let kk = values.len();
    if kk == 0 {
        return na_real();
    }
    if kk == 1 {
        return 0.0;
    }
    let qq = kk / 2 - 1;
    values.select_nth_unstable(qq + 1);
    let upper = values[qq + 1];
    if kk % 2 == 1 {
        for value in values.iter_mut() {
            *value = value.wrapping_sub(upper).wrapping_abs();
        }
        values.select_nth_unstable(qq + 1);
        scale * (values[qq + 1] as f64)
    } else {
        values[..qq + 1].select_nth_unstable(qq);
        let lower = values[qq];
        if lower.wrapping_sub(upper) % 2 == 0 {
            let mu = lower.wrapping_add(upper) / 2;
            for value in values.iter_mut() {
                *value = value.wrapping_sub(mu).wrapping_abs();
            }
            values.select_nth_unstable(qq + 1);
            values[..qq + 1].select_nth_unstable(qq);
            scale * ((values[qq] as f64) + (values[qq + 1] as f64)) / 2.0
        } else {
            let mu = ((lower as f64) + (upper as f64)) / 2.0;
            let mut devs: Vec<f64> = values.iter().map(|value| (*value as f64 - mu).abs()).collect();
            let upper = nth_f64(&mut devs, qq + 1);
            let lower = nth_f64(&mut devs[..qq + 1], qq);
            scale * (lower + upper) / 2.0
        }
    }
}

/// `rowMedians` of an already absolute sample, then times `scale`.
fn median_f64(values: &mut [f64], scale: f64) -> f64 {
    let kk = values.len();
    if kk == 0 {
        return scale * f64::from_bits(R_NAN_BITS);
    }
    if kk % 2 == 1 {
        scale * nth_f64(values, kk / 2)
    } else {
        let qq = kk / 2 - 1;
        let upper = nth_f64(values, qq + 1);
        let lower = nth_f64(&mut values[..qq + 1], qq);
        scale * (lower + upper) / 2.0
    }
}

fn nth_f64(values: &mut [f64], k: usize) -> f64 {
    values.select_nth_unstable_by(k, |left, right| left.total_cmp(right));
    values[k]
}

fn integer_deviation(value: i32, center: f64, check_i32_overflow: bool) -> Option<f64> {
    if value == NA_INTEGER || center.is_nan() {
        return None;
    }
    let diff = (value as f64) - center;
    if check_i32_overflow && !(diff > (i32::MIN as f64) && diff <= (i32::MAX as f64)) {
        return None;
    }
    Some(diff.abs())
}

fn center_length_message(got: usize, expect: usize, by_row: bool) -> String {
    let margin = if by_row { "rows" } else { "columns" };
    format!(
        "Argument 'center' should be of the same length as number of {margin} of 'x': {got} != {expect}"
    )
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

fn load_f64(
    x: &[f64],
    row_stride: usize,
    col_stride: usize,
    row: Option<usize>,
    col: Option<usize>,
) -> f64 {
    match (row, col) {
        (Some(row), Some(col)) => x[row * row_stride + col * col_stride],
        _ => na_real(),
    }
}

fn load_i32(
    x: &[i32],
    row_stride: usize,
    col_stride: usize,
    row: Option<usize>,
    col: Option<usize>,
) -> i32 {
    match (row, col) {
        (Some(row), Some(col)) => x[row * row_stride + col * col_stride],
        _ => NA_INTEGER,
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
    use numpy::ndarray::Array1;
    use numpy::{IntoPyArray, PyReadonlyArray1, PyReadonlyArray2};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::{validate_int, validate_logical, validate_real, Subset, row_mads_f64, row_mads_i32};

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

    fn contiguous<'a, T: Copy>(view: &'a numpy::ndarray::ArrayView2<'a, T>) -> Option<(&'a [T], usize, usize)> {
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

    fn owned_column_major<T: Copy>(view: numpy::ndarray::ArrayView2<'_, T>) -> Vec<T> {
        let (nrow, ncol) = view.dim();
        let mut flat = Vec::with_capacity(nrow.saturating_mul(ncol));
        for col in 0..ncol {
            for row in 0..nrow {
                flat.push(view[[row, col]]);
            }
        }
        flat
    }

    fn center_slice<'a>(center: &'a Option<PyReadonlyArray1<'a, f64>>) -> PyResult<Option<&'a [f64]>> {
        match center {
            None => Ok(None),
            Some(values) => values
                .as_slice()
                .map(Some)
                .map_err(|err| PyValueError::new_err(err.to_string())),
        }
    }

    fn to_py(py: Python<'_>, values: Vec<f64>) -> PyResult<Py<PyAny>> {
        let arr = Array1::from_shape_vec(values.len(), values)
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        Ok(arr.into_pyarray(py).into_any().unbind())
    }

    #[pyfunction]
    #[pyo3(
        name = "mads_f64",
        signature = (x, by_row, na_rm, scale, center=None, rows=None, rows_kind="all", cols=None, cols_kind="all")
    )]
    fn mads_f64_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        by_row: bool,
        na_rm: bool,
        scale: f64,
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
        let center = center_slice(&center)?;
        let result = if nrow == 0 || ncol == 0 {
            row_mads_f64(
                &[],
                nrow,
                ncol,
                1,
                0,
                &row_subset,
                &col_subset,
                by_row,
                scale,
                na_rm,
                center,
            )
        } else if let Some((slice, row_stride, col_stride)) = contiguous(&view) {
            row_mads_f64(
                slice,
                nrow,
                ncol,
                row_stride,
                col_stride,
                &row_subset,
                &col_subset,
                by_row,
                scale,
                na_rm,
                center,
            )
        } else {
            let owned = owned_column_major(view);
            row_mads_f64(
                &owned,
                nrow,
                ncol,
                1,
                nrow,
                &row_subset,
                &col_subset,
                by_row,
                scale,
                na_rm,
                center,
            )
        }
        .map_err(PyValueError::new_err)?;
        to_py(py, result)
    }

    #[pyfunction]
    #[pyo3(
        name = "mads_i32",
        signature = (x, by_row, na_rm, scale, center=None, check_i32_overflow=false, rows=None, rows_kind="all", cols=None, cols_kind="all")
    )]
    fn mads_i32_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, i32>,
        by_row: bool,
        na_rm: bool,
        scale: f64,
        center: Option<PyReadonlyArray1<'py, f64>>,
        check_i32_overflow: bool,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
    ) -> PyResult<Py<PyAny>> {
        let view = x.as_array();
        let (nrow, ncol) = view.dim();
        let row_subset = parse_subset(rows.as_ref(), rows_kind, nrow)?;
        let col_subset = parse_subset(cols.as_ref(), cols_kind, ncol)?;
        let center = center_slice(&center)?;
        let result = if nrow == 0 || ncol == 0 {
            row_mads_i32(
                &[],
                nrow,
                ncol,
                1,
                0,
                &row_subset,
                &col_subset,
                by_row,
                scale,
                na_rm,
                center,
                check_i32_overflow,
            )
        } else if let Some((slice, row_stride, col_stride)) = contiguous(&view) {
            row_mads_i32(
                slice,
                nrow,
                ncol,
                row_stride,
                col_stride,
                &row_subset,
                &col_subset,
                by_row,
                scale,
                na_rm,
                center,
                check_i32_overflow,
            )
        } else {
            let owned = owned_column_major(view);
            row_mads_i32(
                &owned,
                nrow,
                ncol,
                1,
                nrow,
                &row_subset,
                &col_subset,
                by_row,
                scale,
                na_rm,
                center,
                check_i32_overflow,
            )
        }
        .map_err(PyValueError::new_err)?;
        to_py(py, result)
    }

    #[pymodule]
    fn rowmads(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(mads_f64_py, m)?)?;
        m.add_function(wrap_pyfunction!(mads_i32_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{
        Subset, mad_f64, mad_i32, na_real, row_mads_f64, row_mads_i32, validate_int, NA_INTEGER,
        NA_REAL_BITS, R_NAN_BITS,
    };

    fn scale() -> f64 {
        1.4826
    }

    #[test]
    fn double_row_matches_stats_mad_shape() {
        let x = vec![1.0, 2.0, 3.0, 4.0, 10.0, 20.0, 30.0, 40.0];
        let got = row_mads_f64(&x, 2, 4, 1, 2, &Subset::All, &Subset::All, true, scale(), false, None)
            .unwrap();
        assert!((got[0] - scale() * 4.5).abs() < 1e-12);
        assert!((got[1] - scale() * 9.0).abs() < 1e-12);
        let cols = row_mads_f64(&x, 2, 4, 1, 2, &Subset::All, &Subset::All, false, scale(), false, None)
            .unwrap();
        assert!((cols[0] - scale() * 0.5).abs() < 1e-12);
        assert!((cols[2] - scale() * 5.0).abs() < 1e-12);
    }

    #[test]
    fn one_value_is_zero_and_empty_is_na() {
        let one = mad_f64(&mut [5.0], scale());
        assert_eq!(one.to_bits(), 0);
        let empty = mad_f64(&mut [], 0.0);
        assert_eq!(empty.to_bits(), NA_REAL_BITS);
        let missing = mad_f64(&mut [], scale());
        assert_eq!(missing.to_bits(), na_real().to_bits());
    }

    #[test]
    fn nan_becomes_r_na_and_na_rm_drops_it() {
        let x = vec![1.0, f64::NAN, 3.0];
        let got = row_mads_f64(&x, 1, 3, 1, 1, &Subset::All, &Subset::All, true, scale(), false, None)
            .unwrap();
        assert_eq!(got[0].to_bits(), NA_REAL_BITS);
        let kept = row_mads_f64(&x, 1, 3, 1, 1, &Subset::All, &Subset::All, true, scale(), true, None)
            .unwrap();
        assert!((kept[0] - scale()).abs() < 1e-12);
    }

    #[test]
    fn integer_even_mean_wraps_before_the_parity_test() {
        let mut values = [2_000_000_000, 2_000_000_002];
        let got = mad_i32(&mut values, 1.0);
        assert_eq!(got, 2_147_483_647.0);
        let mut even = [1, 3, 5, 7];
        assert_eq!(mad_i32(&mut even, 1.0), 2.0);
        let mut odd_diff = [1, 2, 4, 7];
        assert_eq!(mad_i32(&mut odd_diff, 1.0), 1.5);
    }

    #[test]
    fn centered_row_overflows_and_column_keeps_the_double_difference() {
        let x = vec![2_000_000_000, 1, -2_000_000_000, 2];
        let center = vec![-2_000_000_000.0, 0.0];
        let rows = row_mads_i32(
            &x,
            2,
            2,
            1,
            2,
            &Subset::All,
            &Subset::All,
            true,
            1.0,
            false,
            Some(&center),
            true,
        )
        .unwrap();
        // R multiplies the median by `constant`, which sets the quiet bit on NA.
        assert_eq!(rows[0].to_bits(), 0x7ff8_0000_0000_07a2);
        assert_eq!(rows[1], 1.5);
        let cols = row_mads_i32(
            &x,
            2,
            2,
            1,
            2,
            &Subset::All,
            &Subset::All,
            false,
            1.0,
            false,
            Some(&[2_000_000_000.0, -2_000_000_000.0]),
            false,
        )
        .unwrap();
        assert!(cols[0].is_finite() && cols[1].is_finite());
    }

    #[test]
    fn centered_empty_margin_is_plain_nan_times_scale() {
        let got = row_mads_f64(
            &[],
            1,
            0,
            1,
            0,
            &Subset::All,
            &Subset::All,
            true,
            scale(),
            true,
            Some(&[0.0]),
        )
        .unwrap();
        assert_eq!(got[0].to_bits(), R_NAN_BITS);
        let bare = row_mads_f64(&[], 1, 0, 1, 0, &Subset::All, &Subset::All, true, scale(), false, None)
            .unwrap();
        assert_eq!(bare[0].to_bits(), NA_REAL_BITS);
    }

    #[test]
    fn index_rules_match_validate_indices() {
        assert_eq!(validate_int(&[0, 2, 0], 2).unwrap(), Subset::At(vec![Some(1)]));
        assert_eq!(validate_int(&[-2], 2).unwrap(), Subset::At(vec![Some(0)]));
        assert!(validate_int(&[1, 9], 2).is_err());
        let x: Vec<i32> = (1..=6).collect();
        let rows = validate_int(&[1, NA_INTEGER as i64], 2).unwrap();
        let got = row_mads_i32(&x, 2, 3, 1, 2, &rows, &Subset::All, true, 1.0, false, None, false)
            .unwrap();
        assert!(got[0].is_finite());
        assert_eq!(got[1].to_bits(), NA_REAL_BITS);
    }
}
