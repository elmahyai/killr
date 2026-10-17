//! Row and column log-sum-exp, ported from matrixStats `src/rowLogSumExp.c`.
//!
//! `rowLogSumExps` calls the C routine with `byrow = TRUE` and `colLogSumExps`
//! with `byrow = FALSE`. Both pass `hasNA = TRUE`. Each margin is handed to
//! `logSumExp_double`, which lives in the finished `logsumexp` crate: subtract
//! the maximum, then `max + log1p(sum(exp(x - max)))`. The matrix is stored
//! either column-major, as in R, or row-major, as a NumPy C-order array.
//! `rows` and `cols` follow `validateIndices` with out-of-bounds rejected.
//! Missing means every position, values are 1-based, zeros are dropped, and
//! negatives exclude. A missing index contributes the same result as a margin
//! of missing values: `-Inf` when `na_rm` is set or the other margin is empty,
//! and NaN otherwise. A missing double is NaN.

use logsumexp::{log_sum_exp, IndexSpec};

/// Positions along one margin.
///
/// `All` is R's `NULL`. `At` is a validated list of 0-based positions;
/// `None` is an NA index.
#[derive(Clone, Debug, PartialEq)]
pub enum Subset {
    All,
    At(Vec<Option<usize>>),
}

/// Which way the flat buffer is laid out.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Order {
    /// Element `(row, col)` is at `col * nrow + row`. This is R's layout.
    ColumnMajor,
    /// Element `(row, col)` is at `row * ncol + col`.
    RowMajor,
}

/// Log-sum-exp of each row. `x` has `nrow * ncol` values in `order`.
pub fn row_log_sum_exps(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    rows: &Subset,
    cols: &Subset,
    na_rm: bool,
) -> Result<Vec<f64>, String> {
    log_sum_exps(x, nrow, ncol, rows, cols, na_rm, true, Order::ColumnMajor)
}

/// Log-sum-exp of each column. `x` has `nrow * ncol` values in `order`.
pub fn col_log_sum_exps(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    rows: &Subset,
    cols: &Subset,
    na_rm: bool,
) -> Result<Vec<f64>, String> {
    log_sum_exps(x, nrow, ncol, rows, cols, na_rm, false, Order::ColumnMajor)
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
            ans.push(int_to_zero_based(idx, max_idx));
        }
        return Ok(Subset::At(ans));
    }

    if state >= 0 {
        let mut ans = Vec::with_capacity(count);
        for &idx in idxs {
            if idx != 0 {
                ans.push(int_to_zero_based(idx, max_idx));
            }
        }
        return Ok(Subset::At(ans));
    }

    exclude_negatives(idxs.iter().copied(), max_idx)
}

/// 1-based real indices. NaN and both infinities are NA indices. A finite
/// value past the margin is an error, matching `allowOutOfBound = FALSE`.
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
/// A pattern shorter than the margin is recycled. A longer pattern is an error.
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

pub(crate) fn log_sum_exps(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    rows: &Subset,
    cols: &Subset,
    na_rm: bool,
    byrow: bool,
    order: Order,
) -> Result<Vec<f64>, String> {
    let Some(n) = nrow.checked_mul(ncol) else {
        return Err("dimension overflow".to_string());
    };
    if x.len() != n {
        return Err("lx length does not match nrow * ncol".to_string());
    }

    let n_rows = side_len(rows, nrow);
    let n_cols = side_len(cols, ncol);
    if byrow {
        let mut ans = Vec::with_capacity(n_rows);
        let mut buf = Vec::with_capacity(n_cols);
        for ii in 0..n_rows {
            let Some(row) = side_get(rows, ii) else {
                ans.push(missing_index(n_cols, na_rm));
                continue;
            };
            if matches!(cols, Subset::All) && order == Order::RowMajor {
                let start = row * ncol;
                ans.push(sum_exp(&x[start..start + ncol], na_rm));
                continue;
            }
            buf.clear();
            for jj in 0..n_cols {
                buf.push(match side_get(cols, jj) {
                    Some(col) => value_at(x, nrow, ncol, row, col, order),
                    None => f64::NAN,
                });
            }
            ans.push(sum_exp(&buf, na_rm));
        }
        Ok(ans)
    } else {
        let mut ans = Vec::with_capacity(n_cols);
        let mut buf = Vec::with_capacity(n_rows);
        for jj in 0..n_cols {
            let Some(col) = side_get(cols, jj) else {
                ans.push(missing_index(n_rows, na_rm));
                continue;
            };
            if matches!(rows, Subset::All) && order == Order::ColumnMajor {
                let start = col * nrow;
                ans.push(sum_exp(&x[start..start + nrow], na_rm));
                continue;
            }
            buf.clear();
            for ii in 0..n_rows {
                buf.push(match side_get(rows, ii) {
                    Some(row) => value_at(x, nrow, ncol, row, col, order),
                    None => f64::NAN,
                });
            }
            ans.push(sum_exp(&buf, na_rm));
        }
        Ok(ans)
    }
}

fn sum_exp(values: &[f64], na_rm: bool) -> f64 {
    log_sum_exp(values, &IndexSpec::All, na_rm)
}

/// A missing row or column index. This matches `logSumExp` on that many
/// missing values, which is what `rowLogSumExps_double` stores in `navalue`.
fn missing_index(n: usize, na_rm: bool) -> f64 {
    if n == 0 || na_rm {
        f64::NEG_INFINITY
    } else {
        f64::NAN
    }
}

fn side_len(subset: &Subset, n: usize) -> usize {
    match subset {
        Subset::All => n,
        Subset::At(idx) => idx.len(),
    }
}

fn side_get(subset: &Subset, i: usize) -> Option<usize> {
    match subset {
        Subset::All => Some(i),
        Subset::At(idx) => idx[i],
    }
}

fn value_at(x: &[f64], nrow: usize, ncol: usize, row: usize, col: usize, order: Order) -> f64 {
    match order {
        Order::ColumnMajor => x[col * nrow + row],
        Order::RowMajor => x[row * ncol + col],
    }
}

fn is_int_na(idx: i64) -> bool {
    idx == i32::MIN as i64
}

fn int_to_zero_based(idx: i64, max_idx: usize) -> Option<usize> {
    if is_int_na(idx) || idx > max_idx as i64 {
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
    use numpy::{IntoPyArray, PyReadonlyArray1, PyReadonlyArray2};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::{
        log_sum_exps, validate_int, validate_logical, validate_real, Order, Subset,
    };

    fn owned_column_major(view: numpy::ndarray::ArrayView2<'_, f64>) -> Vec<f64> {
        let (nrow, ncol) = view.dim();
        let mut flat = Vec::with_capacity(nrow * ncol);
        for col in 0..ncol {
            for row in 0..nrow {
                flat.push(view[[row, col]]);
            }
        }
        flat
    }

    fn subset_from_py(obj: Option<&Bound<'_, PyAny>>, max_idx: usize) -> PyResult<Subset> {
        let Some(obj) = obj else {
            return Ok(Subset::All);
        };
        if obj.is_none() {
            return Ok(Subset::All);
        }
        if let Ok(arr) = obj.extract::<PyReadonlyArray1<bool>>() {
            let slice = arr
                .as_slice()
                .map_err(|err| PyValueError::new_err(err.to_string()))?;
            let flags: Vec<i8> = slice.iter().map(|&flag| i8::from(flag)).collect();
            return validate_logical(&flags, max_idx).map_err(PyValueError::new_err);
        }
        if let Ok(arr) = obj.extract::<PyReadonlyArray1<i64>>() {
            let slice = arr
                .as_slice()
                .map_err(|err| PyValueError::new_err(err.to_string()))?;
            return validate_int(slice, max_idx).map_err(PyValueError::new_err);
        }
        if let Ok(arr) = obj.extract::<PyReadonlyArray1<f64>>() {
            let slice = arr
                .as_slice()
                .map_err(|err| PyValueError::new_err(err.to_string()))?;
            return validate_real(slice, max_idx).map_err(PyValueError::new_err);
        }
        Err(PyValueError::new_err(
            "idxs can only be integer, numeric, or logical",
        ))
    }

    fn margins_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        rows: Option<Bound<'py, PyAny>>,
        cols: Option<Bound<'py, PyAny>>,
        na_rm: bool,
        byrow: bool,
    ) -> PyResult<Bound<'py, numpy::PyArray1<f64>>> {
        let view = x.as_array();
        let (nrow, ncol) = view.dim();
        let row_subset = subset_from_py(rows.as_ref(), nrow)?;
        let col_subset = subset_from_py(cols.as_ref(), ncol)?;
        let (stride_row, stride_col) = if view.strides().len() == 2 {
            (view.strides()[0], view.strides()[1])
        } else {
            (0, 0)
        };
        let ans = if let Some(slice) = view.as_slice_memory_order() {
            let cells = nrow.saturating_mul(ncol);
            if slice.len() == cells && stride_row == ncol as isize && stride_col == 1 {
                log_sum_exps(
                    slice,
                    nrow,
                    ncol,
                    &row_subset,
                    &col_subset,
                    na_rm,
                    byrow,
                    Order::RowMajor,
                )
            } else if slice.len() == cells && stride_row == 1 && stride_col == nrow as isize {
                log_sum_exps(
                    slice,
                    nrow,
                    ncol,
                    &row_subset,
                    &col_subset,
                    na_rm,
                    byrow,
                    Order::ColumnMajor,
                )
            } else {
                let flat = owned_column_major(view);
                log_sum_exps(
                    &flat,
                    nrow,
                    ncol,
                    &row_subset,
                    &col_subset,
                    na_rm,
                    byrow,
                    Order::ColumnMajor,
                )
            }
        } else {
            let flat = owned_column_major(view);
            log_sum_exps(
                &flat,
                nrow,
                ncol,
                &row_subset,
                &col_subset,
                na_rm,
                byrow,
                Order::ColumnMajor,
            )
        }
        .map_err(PyValueError::new_err)?;
        Ok(ans.into_pyarray(py))
    }

    #[pyfunction]
    #[pyo3(name = "row_log_sum_exps", signature = (lx, rows=None, cols=None, na_rm=false))]
    fn row_log_sum_exps_py<'py>(
        py: Python<'py>,
        lx: PyReadonlyArray2<'py, f64>,
        rows: Option<Bound<'py, PyAny>>,
        cols: Option<Bound<'py, PyAny>>,
        na_rm: bool,
    ) -> PyResult<Bound<'py, numpy::PyArray1<f64>>> {
        margins_py(py, lx, rows, cols, na_rm, true)
    }

    #[pyfunction]
    #[pyo3(name = "col_log_sum_exps", signature = (lx, rows=None, cols=None, na_rm=false))]
    fn col_log_sum_exps_py<'py>(
        py: Python<'py>,
        lx: PyReadonlyArray2<'py, f64>,
        rows: Option<Bound<'py, PyAny>>,
        cols: Option<Bound<'py, PyAny>>,
        na_rm: bool,
    ) -> PyResult<Bound<'py, numpy::PyArray1<f64>>> {
        margins_py(py, lx, rows, cols, na_rm, false)
    }

    #[pymodule]
    fn rowlogsumexps(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(row_log_sum_exps_py, m)?)?;
        m.add_function(wrap_pyfunction!(col_log_sum_exps_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{
        col_log_sum_exps, log_sum_exps, row_log_sum_exps, validate_int, validate_logical,
        validate_real, Order, Subset,
    };

    fn close(actual: f64, expected: f64) -> bool {
        if expected.is_nan() {
            actual.is_nan()
        } else if expected.is_infinite() {
            actual == expected
        } else {
            (actual - expected).abs() <= 1e-8
        }
    }

    fn close_all(actual: &[f64], expected: &[f64]) -> bool {
        actual.len() == expected.len() && actual.iter().zip(expected).all(|(a, e)| close(*a, *e))
    }

    fn sample() -> Vec<f64> {
        // Printed layout, column-major:
        // 0  log(2)
        // 0  log(3)
        vec![0.0, 0.0, 2.0_f64.ln(), 3.0_f64.ln()]
    }

    #[test]
    fn rows_and_columns_match_r() {
        let x = sample();
        let rows = row_log_sum_exps(&x, 2, 2, &Subset::All, &Subset::All, false).unwrap();
        let cols = col_log_sum_exps(&x, 2, 2, &Subset::All, &Subset::All, false).unwrap();
        assert!(close_all(&rows, &[3.0_f64.ln(), 4.0_f64.ln()]));
        assert!(close_all(&cols, &[2.0_f64.ln(), 5.0_f64.ln()]));
    }

    #[test]
    fn row_major_layout_matches_column_major() {
        let column = sample();
        let row_major = vec![0.0, 2.0_f64.ln(), 0.0, 3.0_f64.ln()];
        let from_columns =
            row_log_sum_exps(&column, 2, 2, &Subset::All, &Subset::All, false).unwrap();
        let from_rows = log_sum_exps(
            &row_major,
            2,
            2,
            &Subset::All,
            &Subset::All,
            false,
            true,
            Order::RowMajor,
        )
        .unwrap();
        assert!(close_all(&from_rows, &from_columns));
    }

    #[test]
    fn empty_margins_are_negative_infinity() {
        let x = sample();
        let no_rows = Subset::At(Vec::new());
        let no_cols = Subset::At(Vec::new());
        assert!(row_log_sum_exps(&x, 2, 2, &no_rows, &Subset::All, false)
            .unwrap()
            .is_empty());
        assert!(close_all(
            &row_log_sum_exps(&x, 2, 2, &Subset::All, &no_cols, false).unwrap(),
            &[f64::NEG_INFINITY, f64::NEG_INFINITY]
        ));
        assert!(close_all(
            &col_log_sum_exps(&x, 2, 2, &no_rows, &Subset::All, false).unwrap(),
            &[f64::NEG_INFINITY, f64::NEG_INFINITY]
        ));
        assert!(col_log_sum_exps(&x, 2, 2, &Subset::All, &no_cols, false)
            .unwrap()
            .is_empty());
        assert!(close_all(
            &col_log_sum_exps(&[], 0, 3, &Subset::All, &Subset::All, false).unwrap(),
            &[f64::NEG_INFINITY, f64::NEG_INFINITY, f64::NEG_INFINITY]
        ));
        assert!(close_all(
            &row_log_sum_exps(&[], 4, 0, &Subset::All, &Subset::All, false).unwrap(),
            &[
                f64::NEG_INFINITY,
                f64::NEG_INFINITY,
                f64::NEG_INFINITY,
                f64::NEG_INFINITY
            ]
        ));
    }

    #[test]
    fn missing_values_and_missing_indices() {
        let x = vec![f64::NAN, 1.0, 2.0, 3.0];
        let kept = row_log_sum_exps(&x, 2, 2, &Subset::All, &Subset::All, true).unwrap();
        let dropped = row_log_sum_exps(&x, 2, 2, &Subset::All, &Subset::All, false).unwrap();
        assert!(close_all(&kept, &[2.0, (1.0_f64.exp() + 3.0_f64.exp()).ln()]));
        assert!(dropped[0].is_nan());
        assert!(close(dropped[1], (1.0_f64.exp() + 3.0_f64.exp()).ln()));

        let all_nan = vec![f64::NAN; 4];
        assert!(close_all(
            &row_log_sum_exps(&all_nan, 2, 2, &Subset::All, &Subset::All, true).unwrap(),
            &[f64::NEG_INFINITY, f64::NEG_INFINITY]
        ));
        assert!(row_log_sum_exps(&all_nan, 2, 2, &Subset::All, &Subset::All, false)
            .unwrap()
            .iter()
            .all(|v| v.is_nan()));

        let missing = validate_int(&[i32::MIN as i64, 2], 2).unwrap();
        let na_false = row_log_sum_exps(&x, 2, 2, &missing, &Subset::All, false).unwrap();
        let na_true = row_log_sum_exps(&x, 2, 2, &missing, &Subset::All, true).unwrap();
        assert!(na_false[0].is_nan());
        assert!(close(na_false[1], (1.0_f64.exp() + 3.0_f64.exp()).ln()));
        assert_eq!(na_true[0], f64::NEG_INFINITY);
        assert!(close(na_true[1], (1.0_f64.exp() + 3.0_f64.exp()).ln()));
    }

    #[test]
    fn infinities_and_the_maximum_subtraction() {
        let x = vec![0.0, 1.0, f64::INFINITY, 2.0];
        let rows = row_log_sum_exps(&x, 2, 2, &Subset::All, &Subset::All, false).unwrap();
        assert_eq!(rows[0], f64::INFINITY);
        assert!(close(rows[1], (1.0_f64.exp() + 2.0_f64.exp()).ln()));

        let neg = vec![f64::NEG_INFINITY, f64::NEG_INFINITY, 5.0, f64::NEG_INFINITY];
        let rows = row_log_sum_exps(&neg, 2, 2, &Subset::All, &Subset::All, false).unwrap();
        assert_eq!(rows[0], 5.0);
        assert_eq!(rows[1], f64::NEG_INFINITY);

        let big = row_log_sum_exps(&[1000.01, 1000.02], 1, 2, &Subset::All, &Subset::All, false)
            .unwrap();
        assert!(close(big[0], 1000.7081596805078));
        let small =
            row_log_sum_exps(&[-1000.01, -1000.02], 1, 2, &Subset::All, &Subset::All, false)
                .unwrap();
        assert!(close(small[0], -999.32184031949214));
        let dup = row_log_sum_exps(&[2.0, 2.0], 1, 2, &Subset::All, &Subset::All, false).unwrap();
        assert!(close(dup[0], 2.6931471805599454));
    }

    #[test]
    fn subsets_follow_r_index_rules() {
        let x = vec![0.0, 1.0, 2.0, 3.0];
        let rows = validate_int(&[2, 2], 2).unwrap();
        let cols = validate_int(&[2], 2).unwrap();
        let repeated = row_log_sum_exps(&x, 2, 2, &rows, &cols, false).unwrap();
        assert!(close_all(&repeated, &[3.0, 3.0]));

        let dropped = validate_int(&[0, 2, 0], 2).unwrap();
        let one = row_log_sum_exps(&x, 2, 2, &dropped, &Subset::All, false).unwrap();
        assert!(close(one[0], (1.0_f64.exp() + 3.0_f64.exp()).ln()));

        let excluded = validate_int(&[-1], 2).unwrap();
        let kept = row_log_sum_exps(&x, 2, 2, &excluded, &Subset::All, false).unwrap();
        assert!(close(kept[0], (1.0_f64.exp() + 3.0_f64.exp()).ln()));

        assert!(validate_int(&[1, 9], 2).is_err());
        assert!(validate_int(&[-1, 1], 2).is_err());
        let frac = validate_real(&[1.9], 2).unwrap();
        assert_eq!(frac, Subset::At(vec![Some(0)]));
        let inf = validate_real(&[f64::INFINITY, 2.0], 2).unwrap();
        assert_eq!(inf, Subset::At(vec![None, Some(1)]));
        assert!(validate_logical(&[1, 0, 1], 2).is_err());
        assert_eq!(
            validate_logical(&[0, 1], 4).unwrap(),
            Subset::At(vec![Some(1), Some(3)])
        );
    }
}
