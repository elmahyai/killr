//! Row and column medians, ported from matrixStats `src/rowMedians.c`.
//!
//! `colMedians` calls the same routine with `byrow = FALSE` after swapping
//! the two margins. Here `by_row` false walks each selected column. The R
//! wrappers always pass `hasNA = TRUE`, so missing values are always
//! examined. `rows` and `cols` follow `validateIndices`: missing means every
//! position, values are 1-based, zeros are dropped, and negatives exclude.
//! A missing index reads as a missing value.
//!
//! Any NaN, including R's NA, makes that margin `NA_real_` when `na.rm` is
//! false. A margin with no remaining values is plain NaN. An even count
//! averages the two central order statistics. Integers are cast to double
//! before that average. The result is always double.

/// R's `NA_real_`: a NaN whose low 32 bits are 1954 (`0x7A2`).
const NA_REAL_BITS: u64 = 0x7ff0_0000_0000_07a2;

/// Plain `NaN` from R's `R_NaN`, used when a margin has no values.
const R_NAN_BITS: u64 = 0x7ff8_0000_0000_0000;

/// R's integer NA.
const NA_INTEGER: i32 = i32::MIN;

/// 1-based subscript vector. `All` selects every position in order.
#[derive(Clone, Debug, PartialEq)]
pub enum Subset {
    All,
    /// 0-based positions. `None` is an NA index.
    At(Vec<Option<usize>>),
}

/// Median of each row, or of each column when `by_row` is false.
///
/// `x` is addressed with the given strides. Column-major storage, matching
/// R, uses `row_stride == 1` and `col_stride == nrow`. A NaN is missing.
/// The result is one double per selected row, or per selected column.
pub fn medians_f64(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    row_stride: usize,
    col_stride: usize,
    rows: &Subset,
    cols: &Subset,
    na_rm: bool,
    by_row: bool,
) -> Result<Vec<f64>, String> {
    medians(
        x,
        nrow,
        ncol,
        row_stride,
        col_stride,
        rows,
        cols,
        na_rm,
        by_row,
        |value| value.is_nan(),
        median_f64,
    )
}

/// Median of each row of an integer matrix, or of each column when `by_row`
/// is false.
///
/// `i32::MIN` is R's NA. The result is still double: each kept integer is
/// cast with a C `(double)` conversion before the even-count average.
pub fn medians_i32(
    x: &[i32],
    nrow: usize,
    ncol: usize,
    row_stride: usize,
    col_stride: usize,
    rows: &Subset,
    cols: &Subset,
    na_rm: bool,
    by_row: bool,
) -> Result<Vec<f64>, String> {
    medians(
        x,
        nrow,
        ncol,
        row_stride,
        col_stride,
        rows,
        cols,
        na_rm,
        by_row,
        |value| value == NA_INTEGER,
        median_i32,
    )
}

fn medians<T: Copy>(
    x: &[T],
    nrow: usize,
    ncol: usize,
    row_stride: usize,
    col_stride: usize,
    rows: &Subset,
    cols: &Subset,
    na_rm: bool,
    by_row: bool,
    is_missing: impl Fn(T) -> bool,
    median: impl Fn(&mut [T]) -> f64,
) -> Result<Vec<f64>, String> {
    ensure_span(x.len(), nrow, ncol, row_stride, col_stride)?;
    let row_pos = positions(rows, nrow);
    let col_pos = positions(cols, ncol);
    let (outer, inner) = if by_row {
        (row_pos, col_pos)
    } else {
        (col_pos, row_pos)
    };
    let mut buf = Vec::with_capacity(inner.len());
    let mut ans = Vec::with_capacity(outer.len());
    for outer_at in &outer {
        buf.clear();
        let mut seen_missing = false;
        for inner_at in &inner {
            let (row, col) = if by_row {
                (*outer_at, *inner_at)
            } else {
                (*inner_at, *outer_at)
            };
            let loaded = match (row, col) {
                (Some(row), Some(col)) => Some(x[row * row_stride + col * col_stride]),
                _ => None,
            };
            match loaded {
                Some(value) if !is_missing(value) => buf.push(value),
                _ => {
                    if !na_rm {
                        seen_missing = true;
                        break;
                    }
                }
            }
        }
        if seen_missing {
            ans.push(f64::from_bits(NA_REAL_BITS));
        } else if buf.is_empty() {
            ans.push(f64::from_bits(R_NAN_BITS));
        } else {
            ans.push(median(&mut buf));
        }
    }
    Ok(ans)
}

/// Two central order statistics, matching `rPsort` then a second `rPsort`
/// on the values to the left of the upper one.
fn median_f64(values: &mut [f64]) -> f64 {
    let n = values.len();
    let upper_at = n / 2;
    values.select_nth_unstable_by(upper_at, |left, right| left.total_cmp(right));
    let upper = values[upper_at];
    if n % 2 == 1 {
        return upper;
    }
    let lower_at = upper_at - 1;
    let lower = &mut values[..upper_at];
    lower.select_nth_unstable_by(lower_at, |left, right| left.total_cmp(right));
    (lower[lower_at] + upper) / 2.0
}

fn median_i32(values: &mut [i32]) -> f64 {
    let n = values.len();
    let upper_at = n / 2;
    values.select_nth_unstable(upper_at);
    let upper = values[upper_at] as f64;
    if n % 2 == 1 {
        return upper;
    }
    let lower_at = upper_at - 1;
    let lower = &mut values[..upper_at];
    lower.select_nth_unstable(lower_at);
    (lower[lower_at] as f64 + upper) / 2.0
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

    use crate::{medians_f64, medians_i32, validate_int, validate_logical, validate_real, Subset};

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

    fn contiguous<'a, T: Copy>(view: &'a ArrayView2<'a, T>) -> Option<(&'a [T], usize, usize)> {
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

    fn owned_column_major<T: Copy>(view: ArrayView2<'_, T>) -> Vec<T> {
        let (nrow, ncol) = view.dim();
        let mut flat = Vec::with_capacity(nrow.saturating_mul(ncol));
        for col in 0..ncol {
            for row in 0..nrow {
                flat.push(view[[row, col]]);
            }
        }
        flat
    }

    fn vector_f64(py: Python<'_>, values: Vec<f64>) -> PyResult<Py<PyAny>> {
        let arr = Array1::from_shape_vec(values.len(), values)
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        Ok(arr.into_pyarray(py).into_any().unbind())
    }

    fn run_f64<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        na_rm: bool,
        by_row: bool,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
    ) -> PyResult<Py<PyAny>> {
        let view = x.as_array();
        let (nrow, ncol) = view.dim();
        let row_subset = parse_subset(rows.as_ref(), rows_kind, nrow)?;
        let col_subset = parse_subset(cols.as_ref(), cols_kind, ncol)?;
        let result = if nrow == 0 || ncol == 0 {
            medians_f64(&[], nrow, ncol, 1, 0, &row_subset, &col_subset, na_rm, by_row)
        } else if let Some((slice, row_stride, col_stride)) = contiguous(&view) {
            medians_f64(
                slice,
                nrow,
                ncol,
                row_stride,
                col_stride,
                &row_subset,
                &col_subset,
                na_rm,
                by_row,
            )
        } else {
            let owned = owned_column_major(view);
            medians_f64(
                &owned,
                nrow,
                ncol,
                1,
                nrow,
                &row_subset,
                &col_subset,
                na_rm,
                by_row,
            )
        }
        .map_err(PyValueError::new_err)?;
        vector_f64(py, result)
    }

    fn run_i32<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, i32>,
        na_rm: bool,
        by_row: bool,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
    ) -> PyResult<Py<PyAny>> {
        let view = x.as_array();
        let (nrow, ncol) = view.dim();
        let row_subset = parse_subset(rows.as_ref(), rows_kind, nrow)?;
        let col_subset = parse_subset(cols.as_ref(), cols_kind, ncol)?;
        let result = if nrow == 0 || ncol == 0 {
            medians_i32(&[], nrow, ncol, 1, 0, &row_subset, &col_subset, na_rm, by_row)
        } else if let Some((slice, row_stride, col_stride)) = contiguous(&view) {
            medians_i32(
                slice,
                nrow,
                ncol,
                row_stride,
                col_stride,
                &row_subset,
                &col_subset,
                na_rm,
                by_row,
            )
        } else {
            let owned = owned_column_major(view);
            medians_i32(
                &owned,
                nrow,
                ncol,
                1,
                nrow,
                &row_subset,
                &col_subset,
                na_rm,
                by_row,
            )
        }
        .map_err(PyValueError::new_err)?;
        vector_f64(py, result)
    }

    #[pyfunction]
    #[pyo3(
        name = "medians_f64",
        signature = (x, na_rm, by_row, rows=None, rows_kind="all", cols=None, cols_kind="all")
    )]
    fn medians_f64_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        na_rm: bool,
        by_row: bool,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
    ) -> PyResult<Py<PyAny>> {
        run_f64(
            py, x, na_rm, by_row, rows, rows_kind, cols, cols_kind,
        )
    }

    #[pyfunction]
    #[pyo3(
        name = "medians_i32",
        signature = (x, na_rm, by_row, rows=None, rows_kind="all", cols=None, cols_kind="all")
    )]
    fn medians_i32_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, i32>,
        na_rm: bool,
        by_row: bool,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
    ) -> PyResult<Py<PyAny>> {
        run_i32(
            py, x, na_rm, by_row, rows, rows_kind, cols, cols_kind,
        )
    }

    #[pymodule]
    fn rowmedians(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(medians_f64_py, m)?)?;
        m.add_function(wrap_pyfunction!(medians_i32_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{medians_f64, medians_i32, Subset, NA_REAL_BITS, R_NAN_BITS};

    fn rows(x: &[f64], nrow: usize, ncol: usize, na_rm: bool) -> Vec<f64> {
        medians_f64(x, nrow, ncol, 1, nrow, &Subset::All, &Subset::All, na_rm, true).unwrap()
    }

    #[test]
    fn printed_integer_matrix_matches_both_margins() {
        let x: Vec<i32> = (1..=12).collect();
        let row = medians_i32(&x, 4, 3, 1, 4, &Subset::All, &Subset::All, false, true).unwrap();
        assert_eq!(row, vec![5.0, 6.0, 7.0, 8.0]);
        let col = medians_i32(&x, 4, 3, 1, 4, &Subset::All, &Subset::All, false, false).unwrap();
        assert_eq!(col, vec![2.5, 6.5, 10.5]);
    }

    #[test]
    fn even_integer_average_casts_before_adding() {
        let x = [2_147_483_646, 2_147_483_647];
        let med = medians_i32(&x, 1, 2, 1, 1, &Subset::All, &Subset::All, false, true).unwrap();
        assert_eq!(med, vec![2_147_483_646.5]);
    }

    #[test]
    fn nan_becomes_na_real_and_an_empty_margin_is_plain_nan() {
        let na = f64::from_bits(NA_REAL_BITS);
        let stopped = rows(&[1.0, f64::NAN, 3.0], 1, 3, false);
        assert_eq!(stopped[0].to_bits(), NA_REAL_BITS);
        let kept = rows(&[1.0, f64::NAN, 3.0], 1, 3, true);
        assert_eq!(kept, vec![2.0]);
        let empty = rows(&[na, f64::NAN], 1, 2, true);
        assert_eq!(empty[0].to_bits(), R_NAN_BITS);
        let no_cols = medians_f64(&[], 2, 0, 1, 0, &Subset::All, &Subset::All, false, true).unwrap();
        assert_eq!(no_cols[0].to_bits(), R_NAN_BITS);
        assert_eq!(no_cols.len(), 2);
    }

    #[test]
    fn opposite_infinities_average_to_a_negative_nan() {
        let med = rows(&[f64::NEG_INFINITY, f64::INFINITY], 1, 2, false);
        assert_eq!(med[0].to_bits(), 0xfff8_0000_0000_0000);
    }

    #[test]
    fn duplicates_use_the_two_central_order_statistics() {
        assert_eq!(rows(&[1.0, 2.0, 2.0, 9.0], 1, 4, false), vec![2.0]);
        assert_eq!(rows(&[3.0, 1.0, 3.0, 3.0], 1, 4, false), vec![3.0]);
        assert_eq!(rows(&[1.0, 100.0, 2.0, 200.0], 1, 4, false), vec![51.0]);
    }
}
