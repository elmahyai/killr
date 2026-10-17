//! Lagged row and column differences, ported from matrixStats `src/rowDiffs.c`.
//!
//! `rowDiffs` calls the C routine with `byrow = TRUE` and `colDiffs` with
//! `byrow = FALSE`. The slice API stores `x` column-major, as in R. `rows`
//! and `cols` follow `validateIndices`: missing means every position, values
//! are 1-based, zeros are dropped, and negatives exclude. A missing index
//! contributes a missing value.
//!
//! The manual calls the result numeric. matrixStats 1.5.0 returns an integer
//! matrix for integer `x`. Integer subtraction wraps, and a wrapped
//! `i32::MIN` is R's integer NA. There is no overflow warning. Double missing
//! values are NaN.
//!
//! Higher-order differences subset only on the first order. Later orders are
//! the dense walk in `rowDiffs_lowlevel_template.h`: for columns the source
//! stride is `nrow_y + lag`.

/// Positions along one margin.
///
/// `All` is R's `NULL`. `At` is a validated list of 0-based positions;
/// `None` is an NA index.
#[derive(Clone, Debug, PartialEq)]
pub enum Subset {
    All,
    At(Vec<Option<usize>>),
}

/// Row-major lagged differences. `values[row * ncol + col]` is one cell.
#[derive(Clone, Debug, PartialEq)]
pub struct RealDiffs {
    pub values: Vec<f64>,
    pub nrow: usize,
    pub ncol: usize,
}

/// Row-major integer lagged differences. `i32::MIN` is R's integer NA.
#[derive(Clone, Debug, PartialEq)]
pub struct IntegerDiffs {
    pub values: Vec<i32>,
    pub nrow: usize,
    pub ncol: usize,
}

const NA_INTEGER: i32 = i32::MIN;

#[derive(Clone, Copy, PartialEq, Eq)]
enum Order {
    ColumnMajor,
    RowMajor,
}

trait DiffValue: Copy {
    fn missing() -> Self;
    fn diff(later: Self, earlier: Self) -> Self;
}

impl DiffValue for f64 {
    fn missing() -> Self {
        f64::NAN
    }

    fn diff(later: Self, earlier: Self) -> Self {
        later - earlier
    }
}

impl DiffValue for i32 {
    fn missing() -> Self {
        NA_INTEGER
    }

    fn diff(later: Self, earlier: Self) -> Self {
        if later == NA_INTEGER || earlier == NA_INTEGER {
            NA_INTEGER
        } else {
            later.wrapping_sub(earlier)
        }
    }
}

struct Matrix<T> {
    values: Vec<T>,
    nrow: usize,
    ncol: usize,
}

/// Lagged differences across each row. `x` is column-major with `nrow * ncol` values.
pub fn row_diffs_f64(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    rows: &Subset,
    cols: &Subset,
    lag: usize,
    differences: usize,
) -> Result<RealDiffs, String> {
    let got = diffs(x, Order::ColumnMajor, nrow, ncol, rows, cols, lag, differences, true)?;
    Ok(RealDiffs {
        values: got.values,
        nrow: got.nrow,
        ncol: got.ncol,
    })
}

/// Lagged differences down each column. `x` is column-major with `nrow * ncol` values.
pub fn col_diffs_f64(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    rows: &Subset,
    cols: &Subset,
    lag: usize,
    differences: usize,
) -> Result<RealDiffs, String> {
    let got = diffs(x, Order::ColumnMajor, nrow, ncol, rows, cols, lag, differences, false)?;
    Ok(RealDiffs {
        values: got.values,
        nrow: got.nrow,
        ncol: got.ncol,
    })
}

/// Lagged integer differences across each row. `x` is column-major.
pub fn row_diffs_i32(
    x: &[i32],
    nrow: usize,
    ncol: usize,
    rows: &Subset,
    cols: &Subset,
    lag: usize,
    differences: usize,
) -> Result<IntegerDiffs, String> {
    let got = diffs(x, Order::ColumnMajor, nrow, ncol, rows, cols, lag, differences, true)?;
    Ok(IntegerDiffs {
        values: got.values,
        nrow: got.nrow,
        ncol: got.ncol,
    })
}

/// Lagged integer differences down each column. `x` is column-major.
pub fn col_diffs_i32(
    x: &[i32],
    nrow: usize,
    ncol: usize,
    rows: &Subset,
    cols: &Subset,
    lag: usize,
    differences: usize,
) -> Result<IntegerDiffs, String> {
    let got = diffs(x, Order::ColumnMajor, nrow, ncol, rows, cols, lag, differences, false)?;
    Ok(IntegerDiffs {
        values: got.values,
        nrow: got.nrow,
        ncol: got.ncol,
    })
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

/// 1-based real indices. NaN is an NA index. Both infinities are NA indices.
///
/// A negative index is truncated toward zero after negation, matching the cast
/// in `validateIndices` before the bounds check. `-0.4` excludes nothing.
/// `-4.9` excludes index 4.
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

    exclude_negative_reals(idxs, max_idx)
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

fn diffs<T: DiffValue>(
    x: &[T],
    order: Order,
    nrow: usize,
    ncol: usize,
    rows: &Subset,
    cols: &Subset,
    lag: usize,
    differences: usize,
    byrow: bool,
) -> Result<Matrix<T>, String> {
    check_len(x.len(), nrow, ncol)?;
    if lag < 1 {
        return Err("Argument 'lag' must be a positive integer".to_string());
    }
    if differences < 1 {
        return Err("Argument 'differences' must be a positive integer".to_string());
    }

    let nrow_sel = selected_len(rows, nrow);
    let ncol_sel = selected_len(cols, ncol);
    let (nrow_ans, ncol_ans) = answer_shape(byrow, nrow_sel, ncol_sel, lag, differences);
    if nrow_ans == 0 || ncol_ans == 0 {
        return Ok(Matrix {
            values: Vec::new(),
            nrow: nrow_ans,
            ncol: ncol_ans,
        });
    }

    let full = matches!(rows, Subset::All) && matches!(cols, Subset::All);
    if full && differences == 1 {
        return Ok(full_once(x, order, nrow, ncol, lag, byrow));
    }

    if order == Order::RowMajor {
        let owned = to_column_major(x, nrow, ncol);
        return Ok(general(
            &owned, nrow, ncol, rows, cols, lag, differences, byrow, nrow_ans, ncol_ans,
        ));
    }
    Ok(general(
        x, nrow, ncol, rows, cols, lag, differences, byrow, nrow_ans, ncol_ans,
    ))
}

fn general<T: DiffValue>(
    x: &[T],
    nrow: usize,
    ncol: usize,
    rows: &Subset,
    cols: &Subset,
    lag: usize,
    differences: usize,
    byrow: bool,
    nrow_ans: usize,
    ncol_ans: usize,
) -> Matrix<T> {
    let row_pos = positions(rows, nrow);
    let col_pos = positions(cols, ncol);
    if differences == 1 {
        let tmp = first_order(x, nrow, &row_pos, &col_pos, lag, byrow, nrow_ans, ncol_ans);
        return Matrix {
            values: to_row_major(&tmp, nrow_ans, ncol_ans),
            nrow: nrow_ans,
            ncol: ncol_ans,
        };
    }

    let (mut nrow_tmp, mut ncol_tmp) = if byrow {
        (row_pos.len(), col_pos.len() - lag)
    } else {
        (row_pos.len() - lag, col_pos.len())
    };
    let mut tmp = first_order(
        x, nrow, &row_pos, &col_pos, lag, byrow, nrow_tmp, ncol_tmp,
    );
    for _ in 1..differences {
        let (nrow_y, ncol_y) = if byrow {
            (nrow_tmp, ncol_tmp - lag)
        } else {
            (nrow_tmp - lag, ncol_tmp)
        };
        let mut next = vec![T::missing(); nrow_y.saturating_mul(ncol_y)];
        dense_diff(&tmp, nrow_tmp, byrow, lag, &mut next, nrow_y, ncol_y);
        tmp = next;
        nrow_tmp = nrow_y;
        ncol_tmp = ncol_y;
    }
    Matrix {
        values: to_row_major(&tmp, nrow_tmp, ncol_tmp),
        nrow: nrow_tmp,
        ncol: ncol_tmp,
    }
}

fn full_once<T: DiffValue>(
    x: &[T],
    order: Order,
    nrow: usize,
    ncol: usize,
    lag: usize,
    byrow: bool,
) -> Matrix<T> {
    let (nrow_ans, ncol_ans) = answer_shape(byrow, nrow, ncol, lag, 1);
    let mut values = vec![T::missing(); nrow_ans.saturating_mul(ncol_ans)];
    if byrow {
        for row in 0..nrow_ans {
            for col in 0..ncol_ans {
                let later = x[at(order, nrow, ncol, row, col + lag)];
                let earlier = x[at(order, nrow, ncol, row, col)];
                values[row * ncol_ans + col] = T::diff(later, earlier);
            }
        }
    } else {
        for col in 0..ncol_ans {
            for row in 0..nrow_ans {
                let later = x[at(order, nrow, ncol, row + lag, col)];
                let earlier = x[at(order, nrow, ncol, row, col)];
                values[row * ncol_ans + col] = T::diff(later, earlier);
            }
        }
    }
    Matrix {
        values,
        nrow: nrow_ans,
        ncol: ncol_ans,
    }
}

fn at(order: Order, nrow: usize, ncol: usize, row: usize, col: usize) -> usize {
    match order {
        Order::ColumnMajor => col * nrow + row,
        Order::RowMajor => row * ncol + col,
    }
}

fn to_column_major<T: Copy>(x: &[T], nrow: usize, ncol: usize) -> Vec<T> {
    let mut out = Vec::with_capacity(x.len());
    for col in 0..ncol {
        for row in 0..nrow {
            out.push(x[row * ncol + col]);
        }
    }
    out
}

fn selected_len(subset: &Subset, n: usize) -> usize {
    match subset {
        Subset::All => n,
        Subset::At(idx) => idx.len(),
    }
}

fn answer_shape(
    byrow: bool,
    nrows: usize,
    ncols: usize,
    lag: usize,
    differences: usize,
) -> (usize, usize) {
    let span = (lag as u128).saturating_mul(differences as u128);
    if byrow {
        let ncol_ans = if span > ncols as u128 {
            0
        } else {
            ncols - span as usize
        };
        (nrows, ncol_ans)
    } else {
        let nrow_ans = if span > nrows as u128 {
            0
        } else {
            nrows - span as usize
        };
        (nrow_ans, ncols)
    }
}

fn positions(subset: &Subset, n: usize) -> Vec<Option<usize>> {
    match subset {
        Subset::All => (0..n).map(Some).collect(),
        Subset::At(idx) => idx.clone(),
    }
}

fn check_len(len: usize, nrow: usize, ncol: usize) -> Result<(), String> {
    let n = nrow
        .checked_mul(ncol)
        .ok_or_else(|| "dimension overflow".to_string())?;
    if len != n {
        return Err("x length does not match nrow * ncol".to_string());
    }
    Ok(())
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
    Ok(finish_drop(drop, kept))
}

fn exclude_negative_reals(idxs: &[f64], max_idx: usize) -> Result<Subset, String> {
    let mut drop = vec![false; max_idx];
    let mut kept = max_idx;
    for &idx in idxs {
        // C casts the negated value to an integer before the bounds check.
        let excl_f = (-idx).trunc();
        if !(excl_f >= 1.0) || excl_f >= (u64::MAX as f64) {
            continue;
        }
        let excl = excl_f as u64;
        if excl >= 1 && (excl as usize) <= max_idx {
            let pos = (excl as usize) - 1;
            if !drop[pos] {
                drop[pos] = true;
                kept -= 1;
            }
        }
    }
    Ok(finish_drop(drop, kept))
}

fn finish_drop(drop: Vec<bool>, kept: usize) -> Subset {
    if kept == 0 {
        return Subset::At(Vec::new());
    }
    let mut ans = Vec::with_capacity(kept);
    for (pos, dropped) in drop.into_iter().enumerate() {
        if !dropped {
            ans.push(Some(pos));
        }
    }
    Subset::At(ans)
}

fn cell_at<T: DiffValue>(x: &[T], nrow: usize, row: Option<usize>, col: Option<usize>) -> T {
    match (row, col) {
        (Some(row), Some(col)) => x[col * nrow + row],
        _ => T::missing(),
    }
}

fn first_order<T: DiffValue>(
    x: &[T],
    nrow: usize,
    rows: &[Option<usize>],
    cols: &[Option<usize>],
    lag: usize,
    byrow: bool,
    nrow_y: usize,
    ncol_y: usize,
) -> Vec<T> {
    let mut y = vec![T::missing(); nrow_y.saturating_mul(ncol_y)];
    if byrow {
        for jj in 0..ncol_y {
            let earlier_col = cols[jj];
            let later_col = cols[jj + lag];
            for ii in 0..nrow_y {
                let earlier = cell_at(x, nrow, rows[ii], earlier_col);
                let later = cell_at(x, nrow, rows[ii], later_col);
                y[jj * nrow_y + ii] = T::diff(later, earlier);
            }
        }
    } else {
        for jj in 0..ncol_y {
            let col = cols[jj];
            for ii in 0..nrow_y {
                let earlier = cell_at(x, nrow, rows[ii], col);
                let later = cell_at(x, nrow, rows[ii + lag], col);
                y[jj * nrow_y + ii] = T::diff(later, earlier);
            }
        }
    }
    y
}

fn dense_diff<T: DiffValue>(
    x: &[T],
    nrow_x: usize,
    byrow: bool,
    lag: usize,
    y: &mut [T],
    nrow_y: usize,
    ncol_y: usize,
) {
    if byrow {
        let mut uu = lag * nrow_x;
        let mut tt = 0_usize;
        let mut ss = 0_usize;
        for _ in 0..ncol_y {
            for _ in 0..nrow_y {
                y[ss] = T::diff(x[uu], x[tt]);
                ss += 1;
                uu += 1;
                tt += 1;
            }
        }
    } else {
        let mut uu = lag;
        let mut tt = 0_usize;
        let mut ss = 0_usize;
        for _ in 0..ncol_y {
            for _ in 0..nrow_y {
                y[ss] = T::diff(x[uu], x[tt]);
                ss += 1;
                uu += 1;
                tt += 1;
            }
            tt += lag;
            uu += lag;
        }
    }
}

fn to_row_major<T: DiffValue>(col_major: &[T], nrow: usize, ncol: usize) -> Vec<T> {
    let mut out = vec![T::missing(); nrow.saturating_mul(ncol)];
    if nrow == 0 || ncol == 0 {
        return Vec::new();
    }
    for col in 0..ncol {
        for row in 0..nrow {
            out[row * ncol + col] = col_major[col * nrow + row];
        }
    }
    out
}

#[cfg(feature = "python")]
mod py {
    use numpy::ndarray::Array2;
    use numpy::{IntoPyArray, PyReadonlyArray1, PyReadonlyArray2};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::{diffs, validate_int, validate_logical, validate_real, Order, Subset};

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

    fn subset_from(
        obj: Option<&Bound<'_, PyAny>>,
        kind: &str,
        max_idx: usize,
        what: &str,
    ) -> PyResult<Subset> {
        match kind {
            "none" => Ok(Subset::All),
            "integer" => {
                let arr = extract_array::<i64>(obj, what)?;
                let slice = arr
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                validate_int(slice, max_idx).map_err(PyValueError::new_err)
            }
            "double" => {
                let arr = extract_array::<f64>(obj, what)?;
                let slice = arr
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                validate_real(slice, max_idx).map_err(PyValueError::new_err)
            }
            "logical" => {
                let arr = extract_array::<i8>(obj, what)?;
                let slice = arr
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                validate_logical(slice, max_idx).map_err(PyValueError::new_err)
            }
            _ => Err(PyValueError::new_err(
                "idxs can only be integer, numeric, or logical",
            )),
        }
    }

    fn extract_array<'py, T: numpy::Element>(
        obj: Option<&Bound<'py, PyAny>>,
        what: &str,
    ) -> PyResult<PyReadonlyArray1<'py, T>> {
        let Some(obj) = obj else {
            return Err(PyValueError::new_err(
                "idxs can only be integer, numeric, or logical",
            ));
        };
        obj.extract::<PyReadonlyArray1<'py, T>>().map_err(|_| {
            PyValueError::new_err(format!(
                "Argument '{what}' can only be integer, numeric, or logical"
            ))
        })
    }

    fn to_array2<'py, T: numpy::Element>(
        py: Python<'py>,
        values: Vec<T>,
        nrow: usize,
        ncol: usize,
    ) -> PyResult<Bound<'py, numpy::PyArray2<T>>> {
        let arr = Array2::from_shape_vec((nrow, ncol), values)
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        Ok(arr.into_pyarray(py))
    }

    fn run_f64<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        rows: Option<Bound<'py, PyAny>>,
        cols: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols_kind: &str,
        lag: usize,
        differences: usize,
        byrow: bool,
    ) -> PyResult<Bound<'py, numpy::PyArray2<f64>>> {
        let view = x.as_array();
        let (nrow, ncol) = view.dim();
        let row_subset = subset_from(rows.as_ref(), rows_kind, nrow, "rows")?;
        let col_subset = subset_from(cols.as_ref(), cols_kind, ncol, "cols")?;
        let got = dispatch(view, &row_subset, &col_subset, lag, differences, byrow)
            .map_err(PyValueError::new_err)?;
        to_array2(py, got.values, got.nrow, got.ncol)
    }

    fn run_i32<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, i32>,
        rows: Option<Bound<'py, PyAny>>,
        cols: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols_kind: &str,
        lag: usize,
        differences: usize,
        byrow: bool,
    ) -> PyResult<Bound<'py, numpy::PyArray2<i32>>> {
        let view = x.as_array();
        let (nrow, ncol) = view.dim();
        let row_subset = subset_from(rows.as_ref(), rows_kind, nrow, "rows")?;
        let col_subset = subset_from(cols.as_ref(), cols_kind, ncol, "cols")?;
        let got = dispatch(view, &row_subset, &col_subset, lag, differences, byrow)
            .map_err(PyValueError::new_err)?;
        to_array2(py, got.values, got.nrow, got.ncol)
    }

    fn dispatch<T: crate::DiffValue>(
        view: numpy::ndarray::ArrayView2<'_, T>,
        rows: &Subset,
        cols: &Subset,
        lag: usize,
        differences: usize,
        byrow: bool,
    ) -> Result<crate::Matrix<T>, String> {
        let (nrow, ncol) = view.dim();
        let n = nrow.saturating_mul(ncol);
        if let Some(slice) = view.as_slice_memory_order() {
            if slice.len() == n {
                let (stride_row, stride_col) = (view.strides()[0], view.strides()[1]);
                if stride_row == ncol as isize && stride_col == 1 {
                    return diffs(
                        slice,
                        Order::RowMajor,
                        nrow,
                        ncol,
                        rows,
                        cols,
                        lag,
                        differences,
                        byrow,
                    );
                }
                if stride_row == 1 && stride_col == nrow as isize {
                    return diffs(
                        slice,
                        Order::ColumnMajor,
                        nrow,
                        ncol,
                        rows,
                        cols,
                        lag,
                        differences,
                        byrow,
                    );
                }
            }
        }
        let flat = owned_column_major(view);
        diffs(
            &flat,
            Order::ColumnMajor,
            nrow,
            ncol,
            rows,
            cols,
            lag,
            differences,
            byrow,
        )
    }

    #[pyfunction]
    #[pyo3(
        name = "row_diffs_f64",
        signature = (x, rows=None, cols=None, rows_kind="none", cols_kind="none", lag=1, differences=1)
    )]
    fn row_diffs_f64_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        rows: Option<Bound<'py, PyAny>>,
        cols: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols_kind: &str,
        lag: usize,
        differences: usize,
    ) -> PyResult<Bound<'py, numpy::PyArray2<f64>>> {
        run_f64(
            py,
            x,
            rows,
            cols,
            rows_kind,
            cols_kind,
            lag,
            differences,
            true,
        )
    }

    #[pyfunction]
    #[pyo3(
        name = "col_diffs_f64",
        signature = (x, rows=None, cols=None, rows_kind="none", cols_kind="none", lag=1, differences=1)
    )]
    fn col_diffs_f64_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        rows: Option<Bound<'py, PyAny>>,
        cols: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols_kind: &str,
        lag: usize,
        differences: usize,
    ) -> PyResult<Bound<'py, numpy::PyArray2<f64>>> {
        run_f64(
            py,
            x,
            rows,
            cols,
            rows_kind,
            cols_kind,
            lag,
            differences,
            false,
        )
    }

    #[pyfunction]
    #[pyo3(
        name = "row_diffs_i32",
        signature = (x, rows=None, cols=None, rows_kind="none", cols_kind="none", lag=1, differences=1)
    )]
    fn row_diffs_i32_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, i32>,
        rows: Option<Bound<'py, PyAny>>,
        cols: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols_kind: &str,
        lag: usize,
        differences: usize,
    ) -> PyResult<Bound<'py, numpy::PyArray2<i32>>> {
        run_i32(
            py,
            x,
            rows,
            cols,
            rows_kind,
            cols_kind,
            lag,
            differences,
            true,
        )
    }

    #[pyfunction]
    #[pyo3(
        name = "col_diffs_i32",
        signature = (x, rows=None, cols=None, rows_kind="none", cols_kind="none", lag=1, differences=1)
    )]
    fn col_diffs_i32_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, i32>,
        rows: Option<Bound<'py, PyAny>>,
        cols: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols_kind: &str,
        lag: usize,
        differences: usize,
    ) -> PyResult<Bound<'py, numpy::PyArray2<i32>>> {
        run_i32(
            py,
            x,
            rows,
            cols,
            rows_kind,
            cols_kind,
            lag,
            differences,
            false,
        )
    }

    #[pymodule]
    fn rowdiffs(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(row_diffs_f64_py, m)?)?;
        m.add_function(wrap_pyfunction!(col_diffs_f64_py, m)?)?;
        m.add_function(wrap_pyfunction!(row_diffs_i32_py, m)?)?;
        m.add_function(wrap_pyfunction!(col_diffs_i32_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{
        col_diffs_i32, row_diffs_f64, row_diffs_i32, validate_int, validate_logical,
        validate_real, Subset, NA_INTEGER,
    };

    fn matrix_i() -> Vec<i32> {
        vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    }

    #[test]
    fn full_integer_diffs_match_the_printed_matrix() {
        let x = matrix_i();
        let rows = row_diffs_i32(&x, 4, 3, &Subset::All, &Subset::All, 1, 1).unwrap();
        assert_eq!((rows.nrow, rows.ncol), (4, 2));
        assert_eq!(rows.values, vec![4, 4, 4, 4, 4, 4, 4, 4]);
        let cols = col_diffs_i32(&x, 4, 3, &Subset::All, &Subset::All, 1, 1).unwrap();
        assert_eq!((cols.nrow, cols.ncol), (3, 3));
        assert_eq!(cols.values, vec![1, 1, 1, 1, 1, 1, 1, 1, 1]);
    }

    #[test]
    fn higher_order_and_subset_follow_the_c_walk() {
        let x = vec![1, 4, 9, 16, 10, 30, 60, 100];
        let cols = col_diffs_i32(&x, 4, 2, &Subset::All, &Subset::All, 1, 2).unwrap();
        assert_eq!(cols.values, vec![2, 10, 2, 10]);
        let rows = validate_int(&[1, 2, 4], 4).unwrap();
        let cols = col_diffs_i32(&x, 4, 2, &rows, &Subset::All, 1, 2).unwrap();
        assert_eq!(cols.values, vec![9, 50]);
        let empty = row_diffs_i32(&x, 4, 2, &Subset::All, &Subset::All, 2, 2).unwrap();
        assert_eq!((empty.nrow, empty.ncol), (4, 0));
        assert!(empty.values.is_empty());
    }

    #[test]
    fn integer_na_propagates_and_overflow_wraps() {
        let mut x = matrix_i();
        x[1] = NA_INTEGER;
        let rows = row_diffs_i32(&x, 4, 3, &Subset::All, &Subset::All, 1, 1).unwrap();
        assert_eq!(rows.values[2], NA_INTEGER);
        assert_eq!(rows.values[3], 4);
        assert_eq!(rows.values[0], 4);
        let wrapped = row_diffs_i32(&[2_147_483_647, -1], 1, 2, &Subset::All, &Subset::All, 1, 1)
            .unwrap();
        assert_eq!(wrapped.values, vec![NA_INTEGER]);
        let other = row_diffs_i32(
            &[-2_000_000_000, 2_000_000_000],
            1,
            2,
            &Subset::All,
            &Subset::All,
            1,
            1,
        )
        .unwrap();
        assert_eq!(other.values, vec![-294_967_296]);
    }

    #[test]
    fn double_na_is_nan_and_row_major_values_match() {
        let x: Vec<f64> = matrix_i().into_iter().map(f64::from).collect();
        let rows = row_diffs_f64(&x, 4, 3, &Subset::All, &Subset::All, 1, 1).unwrap();
        assert_eq!(rows.values, vec![4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0]);
        let mut dirty = x.clone();
        dirty[5] = f64::NAN;
        let rows = row_diffs_f64(&dirty, 4, 3, &Subset::All, &Subset::All, 1, 1).unwrap();
        assert!(rows.values[2].is_nan() && rows.values[3].is_nan());
        assert_eq!(rows.values[0], 4.0);
    }

    #[test]
    fn index_rules_match_validate_indices() {
        assert_eq!(
            validate_int(&[0, 2, 0], 4).unwrap(),
            Subset::At(vec![Some(1)])
        );
        assert_eq!(
            validate_int(&[-2], 4).unwrap(),
            Subset::At(vec![Some(0), Some(2), Some(3)])
        );
        assert!(validate_int(&[1, 9], 4).is_err());
        assert!(validate_int(&[-1, 1], 4).is_err());
        assert_eq!(validate_real(&[1.9], 4).unwrap(), Subset::At(vec![Some(0)]));
        assert_eq!(
            validate_real(&[-1.2], 4).unwrap(),
            Subset::At(vec![Some(1), Some(2), Some(3)])
        );
        assert_eq!(
            validate_real(&[-0.4], 3).unwrap(),
            Subset::At(vec![Some(0), Some(1), Some(2)])
        );
        assert_eq!(
            validate_real(&[-4.9], 5).unwrap(),
            Subset::At(vec![Some(0), Some(1), Some(2), Some(4)])
        );
        assert!(validate_real(&[-4.9], 3).unwrap() == Subset::At(vec![Some(0), Some(1), Some(2)]));
        assert_eq!(validate_logical(&[1], 3).unwrap(), Subset::All);
        assert_eq!(
            validate_logical(&[0, 1], 4).unwrap(),
            Subset::At(vec![Some(1), Some(3)])
        );
        assert!(validate_logical(&[1, 0, 1], 2).is_err());
        let logical_na = validate_logical(&[1, -1, 0], 4).unwrap();
        assert_eq!(
            logical_na,
            Subset::At(vec![Some(0), None, Some(3)])
        );
    }
}
