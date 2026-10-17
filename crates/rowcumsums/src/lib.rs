//! Cumulative row and column sums, ported from matrixStats `src/rowCumsums.c`.
//!
//! `rowCumsums` calls the C routine with `byrow = TRUE` and `colCumsums` with
//! `byrow = FALSE`. The slice API stores `x` column-major, as in R. `rows`
//! and `cols` follow `validateIndices`: missing means every position, values
//! are 1-based, zeros are dropped, and negatives exclude. A missing index
//! contributes a missing value.
//!
//! Logical data uses the integer routine. Integer NA is `i32::MIN`. A running
//! integer sum outside [-2147483647, 2147483647] becomes NA and sets
//! `overflow`. Double NA is NaN, and it propagates through later sums.
//!
//! matrixStats 1.5.0 passes `rowsHasNA` as the double routine's `colsHasNA`
//! argument. An NA column index on a double matrix is then an invalid read.
//! This port uses the column flag, so that index is missing data.

/// Positions along one margin.
///
/// `All` is R's `NULL`. `At` is a validated list of 0-based positions;
/// `None` is an NA index.
#[derive(Clone, Debug, PartialEq)]
pub enum Subset {
    All,
    At(Vec<Option<usize>>),
}

/// Row-major cumulative sums. `values[row * ncol + col]` is one cell.
#[derive(Clone, Debug, PartialEq)]
pub struct RealCumsums {
    pub values: Vec<f64>,
    pub nrow: usize,
    pub ncol: usize,
}

/// Row-major integer cumulative sums. `i32::MIN` is R's integer NA.
#[derive(Clone, Debug, PartialEq)]
pub struct IntegerCumsums {
    pub values: Vec<i32>,
    pub nrow: usize,
    pub ncol: usize,
    pub overflow: bool,
}

const R_INT_MIN: i64 = -2_147_483_647;
const R_INT_MAX: i64 = 2_147_483_647;
const NA_INTEGER: i32 = i32::MIN;

/// Cumulative sum of each row. `x` is column-major with `nrow * ncol` values.
pub fn row_cumsums_f64(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    rows: &Subset,
    cols: &Subset,
) -> Result<RealCumsums, String> {
    cumsums_f64(x, nrow, ncol, rows, cols, true)
}

/// Cumulative sum of each column. `x` is column-major with `nrow * ncol` values.
pub fn col_cumsums_f64(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    rows: &Subset,
    cols: &Subset,
) -> Result<RealCumsums, String> {
    cumsums_f64(x, nrow, ncol, rows, cols, false)
}

/// Cumulative integer sum of each row. `x` is column-major.
pub fn row_cumsums_i32(
    x: &[i32],
    nrow: usize,
    ncol: usize,
    rows: &Subset,
    cols: &Subset,
) -> Result<IntegerCumsums, String> {
    cumsums_i32(x, nrow, ncol, rows, cols, true)
}

/// Cumulative integer sum of each column. `x` is column-major.
pub fn col_cumsums_i32(
    x: &[i32],
    nrow: usize,
    ncol: usize,
    rows: &Subset,
    cols: &Subset,
) -> Result<IntegerCumsums, String> {
    cumsums_i32(x, nrow, ncol, rows, cols, false)
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

fn cumsums_f64(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    rows: &Subset,
    cols: &Subset,
    byrow: bool,
) -> Result<RealCumsums, String> {
    check_len(x.len(), nrow, ncol)?;
    if matches!(rows, Subset::All) && matches!(cols, Subset::All) {
        let values = if byrow {
            row_fast_column_major(x, nrow, ncol)
        } else {
            col_fast_column_major(x, nrow, ncol)
        };
        return Ok(RealCumsums { values, nrow, ncol });
    }

    let row_pos = expand(rows, nrow);
    let col_pos = expand(cols, ncol);
    let nr = row_pos.len();
    let nc = col_pos.len();
    let n_out = nr
        .checked_mul(nc)
        .ok_or_else(|| "dimension overflow".to_string())?;
    let mut values = vec![0.0; n_out];
    if nr == 0 || nc == 0 {
        return Ok(RealCumsums {
            values,
            nrow: nr,
            ncol: nc,
        });
    }

    if byrow {
        let mut acc = vec![0.0; nr];
        for ii in 0..nr {
            let value = f64_at(x, nrow, row_pos[ii], col_pos[0]);
            acc[ii] = value;
            values[ii * nc] = value;
        }
        for jj in 1..nc {
            for ii in 0..nr {
                acc[ii] += f64_at(x, nrow, row_pos[ii], col_pos[jj]);
                values[ii * nc + jj] = acc[ii];
            }
        }
    } else {
        for jj in 0..nc {
            let mut acc = 0.0;
            for ii in 0..nr {
                acc += f64_at(x, nrow, row_pos[ii], col_pos[jj]);
                values[ii * nc + jj] = acc;
            }
        }
    }
    Ok(RealCumsums {
        values,
        nrow: nr,
        ncol: nc,
    })
}

fn cumsums_i32(
    x: &[i32],
    nrow: usize,
    ncol: usize,
    rows: &Subset,
    cols: &Subset,
    byrow: bool,
) -> Result<IntegerCumsums, String> {
    check_len(x.len(), nrow, ncol)?;
    let row_pos = expand(rows, nrow);
    let col_pos = expand(cols, ncol);
    let nr = row_pos.len();
    let nc = col_pos.len();
    let n_out = nr
        .checked_mul(nc)
        .ok_or_else(|| "dimension overflow".to_string())?;
    let mut values = vec![0; n_out];
    let mut overflow = false;
    if nr == 0 || nc == 0 {
        return Ok(IntegerCumsums {
            values,
            nrow: nr,
            ncol: nc,
            overflow,
        });
    }

    if byrow {
        let mut acc = vec![0_i64; nr];
        let mut ok = vec![true; nr];
        for jj in 0..nc {
            for ii in 0..nr {
                let value = i32_at(x, nrow, row_pos[ii], col_pos[jj]);
                values[ii * nc + jj] = store_int(&mut acc[ii], &mut ok[ii], value, &mut overflow);
            }
        }
    } else {
        for jj in 0..nc {
            let mut acc = 0_i64;
            let mut ok = true;
            for ii in 0..nr {
                let value = i32_at(x, nrow, row_pos[ii], col_pos[jj]);
                values[ii * nc + jj] = store_int(&mut acc, &mut ok, value, &mut overflow);
            }
        }
    }
    Ok(IntegerCumsums {
        values,
        nrow: nr,
        ncol: nc,
        overflow,
    })
}

/// Row-major result from a C-contiguous (row-major) matrix, no subset.
pub(crate) fn row_fast_row_major(x: &[f64], nrow: usize, ncol: usize) -> Vec<f64> {
    let mut values = vec![0.0; nrow.saturating_mul(ncol)];
    if nrow == 0 || ncol == 0 {
        return values;
    }
    for row in 0..nrow {
        let start = row * ncol;
        let mut acc = x[start];
        values[start] = acc;
        for col in 1..ncol {
            acc += x[start + col];
            values[start + col] = acc;
        }
    }
    values
}

/// Row-major result from a C-contiguous matrix, cumulative down each column.
pub(crate) fn col_fast_row_major(x: &[f64], nrow: usize, ncol: usize) -> Vec<f64> {
    let mut values = vec![0.0; nrow.saturating_mul(ncol)];
    if nrow == 0 || ncol == 0 {
        return values;
    }
    for col in 0..ncol {
        let mut acc = 0.0;
        for row in 0..nrow {
            acc += x[row * ncol + col];
            values[row * ncol + col] = acc;
        }
    }
    values
}

fn row_fast_column_major(x: &[f64], nrow: usize, ncol: usize) -> Vec<f64> {
    let mut values = vec![0.0; nrow.saturating_mul(ncol)];
    if nrow == 0 || ncol == 0 {
        return values;
    }
    for row in 0..nrow {
        let mut acc = x[row];
        values[row * ncol] = acc;
        for col in 1..ncol {
            acc += x[col * nrow + row];
            values[row * ncol + col] = acc;
        }
    }
    values
}

fn col_fast_column_major(x: &[f64], nrow: usize, ncol: usize) -> Vec<f64> {
    let mut values = vec![0.0; nrow.saturating_mul(ncol)];
    if nrow == 0 || ncol == 0 {
        return values;
    }
    for col in 0..ncol {
        let mut acc = 0.0;
        let start = col * nrow;
        for row in 0..nrow {
            acc += x[start + row];
            values[row * ncol + col] = acc;
        }
    }
    values
}

fn store_int(acc: &mut i64, ok: &mut bool, value: i32, overflow: &mut bool) -> i32 {
    if !*ok {
        return NA_INTEGER;
    }
    if value == NA_INTEGER {
        *ok = false;
        return NA_INTEGER;
    }
    let Some(sum) = acc.checked_add(i64::from(value)) else {
        *ok = false;
        *overflow = true;
        return NA_INTEGER;
    };
    if sum < R_INT_MIN || sum > R_INT_MAX {
        *ok = false;
        *overflow = true;
        return NA_INTEGER;
    }
    *acc = sum;
    sum as i32
}

fn f64_at(x: &[f64], nrow: usize, row: Option<usize>, col: Option<usize>) -> f64 {
    match (row, col) {
        (Some(row), Some(col)) => x[col * nrow + row],
        _ => f64::NAN,
    }
}

fn i32_at(x: &[i32], nrow: usize, row: Option<usize>, col: Option<usize>) -> i32 {
    match (row, col) {
        (Some(row), Some(col)) => x[col * nrow + row],
        _ => NA_INTEGER,
    }
}

fn expand(subset: &Subset, n: usize) -> Vec<Option<usize>> {
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
    use numpy::ndarray::Array2;
    use numpy::{IntoPyArray, PyReadonlyArray1, PyReadonlyArray2};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::{
        col_cumsums_f64, col_cumsums_i32, col_fast_row_major, row_cumsums_f64, row_cumsums_i32,
        row_fast_row_major, validate_int, validate_logical, validate_real, Subset,
    };

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
            _ => Err(PyValueError::new_err(format!(
                "Argument '{what}' can only be integer, numeric, or logical"
            ))),
        }
    }

    fn extract_array<'py, T: numpy::Element>(
        obj: Option<&Bound<'py, PyAny>>,
        what: &str,
    ) -> PyResult<PyReadonlyArray1<'py, T>> {
        let Some(obj) = obj else {
            return Err(PyValueError::new_err(format!(
                "Argument '{what}' can only be integer, numeric, or logical"
            )));
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

    fn cumsums_f64_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        rows: Option<Bound<'py, PyAny>>,
        cols: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols_kind: &str,
        byrow: bool,
    ) -> PyResult<Bound<'py, numpy::PyArray2<f64>>> {
        let view = x.as_array();
        let (nrow, ncol) = view.dim();
        let row_subset = subset_from(rows.as_ref(), rows_kind, nrow, "rows")?;
        let col_subset = subset_from(cols.as_ref(), cols_kind, ncol, "cols")?;
        let full = matches!(row_subset, Subset::All) && matches!(col_subset, Subset::All);
        let n = nrow
            .checked_mul(ncol)
            .ok_or_else(|| PyValueError::new_err("dimension overflow"))?;
        if full {
            if let Some(slice) = view.as_slice_memory_order() {
                if slice.len() == n {
                    let (stride_row, stride_col) = (view.strides()[0], view.strides()[1]);
                    if stride_row == ncol as isize && stride_col == 1 {
                        let values = if byrow {
                            row_fast_row_major(slice, nrow, ncol)
                        } else {
                            col_fast_row_major(slice, nrow, ncol)
                        };
                        return to_array2(py, values, nrow, ncol);
                    }
                    if stride_row == 1 && stride_col == nrow as isize {
                        let result = if byrow {
                            row_cumsums_f64(slice, nrow, ncol, &row_subset, &col_subset)
                        } else {
                            col_cumsums_f64(slice, nrow, ncol, &row_subset, &col_subset)
                        }
                        .map_err(PyValueError::new_err)?;
                        return to_array2(py, result.values, result.nrow, result.ncol);
                    }
                }
            }
        }
        let flat = owned_column_major(view);
        let result = if byrow {
            row_cumsums_f64(&flat, nrow, ncol, &row_subset, &col_subset)
        } else {
            col_cumsums_f64(&flat, nrow, ncol, &row_subset, &col_subset)
        }
        .map_err(PyValueError::new_err)?;
        to_array2(py, result.values, result.nrow, result.ncol)
    }

    fn cumsums_i32_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, i32>,
        rows: Option<Bound<'py, PyAny>>,
        cols: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols_kind: &str,
        byrow: bool,
    ) -> PyResult<(Bound<'py, numpy::PyArray2<i32>>, bool)> {
        let view = x.as_array();
        let (nrow, ncol) = view.dim();
        let row_subset = subset_from(rows.as_ref(), rows_kind, nrow, "rows")?;
        let col_subset = subset_from(cols.as_ref(), cols_kind, ncol, "cols")?;
        let flat = owned_column_major(view);
        let result = if byrow {
            row_cumsums_i32(&flat, nrow, ncol, &row_subset, &col_subset)
        } else {
            col_cumsums_i32(&flat, nrow, ncol, &row_subset, &col_subset)
        }
        .map_err(PyValueError::new_err)?;
        let array = to_array2(py, result.values, result.nrow, result.ncol)?;
        Ok((array, result.overflow))
    }

    #[pyfunction]
    #[pyo3(name = "row_cumsums_f64", signature = (x, rows=None, cols=None, rows_kind="none", cols_kind="none"))]
    fn row_cumsums_f64_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        rows: Option<Bound<'py, PyAny>>,
        cols: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols_kind: &str,
    ) -> PyResult<Bound<'py, numpy::PyArray2<f64>>> {
        cumsums_f64_py(py, x, rows, cols, rows_kind, cols_kind, true)
    }

    #[pyfunction]
    #[pyo3(name = "col_cumsums_f64", signature = (x, rows=None, cols=None, rows_kind="none", cols_kind="none"))]
    fn col_cumsums_f64_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        rows: Option<Bound<'py, PyAny>>,
        cols: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols_kind: &str,
    ) -> PyResult<Bound<'py, numpy::PyArray2<f64>>> {
        cumsums_f64_py(py, x, rows, cols, rows_kind, cols_kind, false)
    }

    #[pyfunction]
    #[pyo3(name = "row_cumsums_i32", signature = (x, rows=None, cols=None, rows_kind="none", cols_kind="none"))]
    fn row_cumsums_i32_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, i32>,
        rows: Option<Bound<'py, PyAny>>,
        cols: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols_kind: &str,
    ) -> PyResult<(Bound<'py, numpy::PyArray2<i32>>, bool)> {
        cumsums_i32_py(py, x, rows, cols, rows_kind, cols_kind, true)
    }

    #[pyfunction]
    #[pyo3(name = "col_cumsums_i32", signature = (x, rows=None, cols=None, rows_kind="none", cols_kind="none"))]
    fn col_cumsums_i32_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, i32>,
        rows: Option<Bound<'py, PyAny>>,
        cols: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols_kind: &str,
    ) -> PyResult<(Bound<'py, numpy::PyArray2<i32>>, bool)> {
        cumsums_i32_py(py, x, rows, cols, rows_kind, cols_kind, false)
    }

    #[pymodule]
    fn rowcumsums(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(row_cumsums_f64_py, m)?)?;
        m.add_function(wrap_pyfunction!(col_cumsums_f64_py, m)?)?;
        m.add_function(wrap_pyfunction!(row_cumsums_i32_py, m)?)?;
        m.add_function(wrap_pyfunction!(col_cumsums_i32_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{
        col_cumsums_f64, col_cumsums_i32, col_fast_row_major, row_cumsums_f64, row_cumsums_i32,
        row_fast_row_major, validate_int, validate_logical, validate_real, Subset, NA_INTEGER,
    };

    fn matrix_i() -> Vec<i32> {
        // Printed layout, filled down each column:
        // 1 5 9
        // 2 6 10
        // 3 7 11
        // 4 8 12
        vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    }

    fn matrix_f() -> Vec<f64> {
        matrix_i().into_iter().map(f64::from).collect()
    }

    #[test]
    fn full_sums_match_the_printed_matrix() {
        let x = matrix_f();
        let rows = row_cumsums_f64(&x, 4, 3, &Subset::All, &Subset::All).unwrap();
        let cols = col_cumsums_f64(&x, 4, 3, &Subset::All, &Subset::All).unwrap();
        assert_eq!(
            rows.values,
            vec![1.0, 6.0, 15.0, 2.0, 8.0, 18.0, 3.0, 10.0, 21.0, 4.0, 12.0, 24.0]
        );
        assert_eq!(
            cols.values,
            vec![1.0, 5.0, 9.0, 3.0, 11.0, 19.0, 6.0, 18.0, 30.0, 10.0, 26.0, 42.0]
        );
        assert_eq!((rows.nrow, rows.ncol), (4, 3));
    }

    #[test]
    fn row_major_fast_path_matches_column_major() {
        let column = matrix_f();
        let row_major = vec![
            1.0, 5.0, 9.0, 2.0, 6.0, 10.0, 3.0, 7.0, 11.0, 4.0, 8.0, 12.0,
        ];
        let from_c = row_fast_row_major(&row_major, 4, 3);
        let from_f = row_cumsums_f64(&column, 4, 3, &Subset::All, &Subset::All).unwrap();
        assert_eq!(from_c, from_f.values);
        let from_c = col_fast_row_major(&row_major, 4, 3);
        let from_f = col_cumsums_f64(&column, 4, 3, &Subset::All, &Subset::All).unwrap();
        assert_eq!(from_c, from_f.values);
    }

    #[test]
    fn double_na_propagates_forward() {
        let mut x = matrix_f();
        x[1] = f64::NAN;
        let rows = row_cumsums_f64(&x, 4, 3, &Subset::All, &Subset::All).unwrap();
        assert!(rows.values[3].is_nan());
        assert!(rows.values[4].is_nan());
        assert!(rows.values[5].is_nan());
        assert_eq!(rows.values[0], 1.0);
        let cols = col_cumsums_f64(&x, 4, 3, &Subset::All, &Subset::All).unwrap();
        assert_eq!(cols.values[0], 1.0);
        assert!(cols.values[3].is_nan());
        assert!(cols.values[6].is_nan());
        assert!(cols.values[9].is_nan());
        assert_eq!(cols.values[1], 5.0);
    }

    #[test]
    fn integer_na_propagates_and_logical_values_sum() {
        let mut x = matrix_i();
        x[1] = NA_INTEGER;
        let rows = row_cumsums_i32(&x, 4, 3, &Subset::All, &Subset::All).unwrap();
        assert!(!rows.overflow);
        assert_eq!(rows.values[3], NA_INTEGER);
        assert_eq!(rows.values[4], NA_INTEGER);
        assert_eq!(rows.values[5], NA_INTEGER);
        let cols = col_cumsums_i32(&x, 4, 3, &Subset::All, &Subset::All).unwrap();
        assert_eq!(cols.values[0], 1);
        assert_eq!(cols.values[3], NA_INTEGER);
        assert_eq!(cols.values[6], NA_INTEGER);
        assert_eq!(cols.values[9], NA_INTEGER);
        assert_eq!(cols.values[1], 5);
    }

    #[test]
    fn integer_overflow_sets_na_and_the_flag() {
        let x = vec![2_000_000_000, 2_000_000_000];
        let rows = row_cumsums_i32(&x, 1, 2, &Subset::All, &Subset::All).unwrap();
        assert!(rows.overflow);
        assert_eq!(rows.values, vec![2_000_000_000, NA_INTEGER]);
        let x = vec![2_147_483_647, 1];
        let rows = row_cumsums_i32(&x, 1, 2, &Subset::All, &Subset::All).unwrap();
        assert_eq!(rows.values[0], 2_147_483_647);
        assert_eq!(rows.values[1], NA_INTEGER);
        let x = vec![-2_147_483_647, -1];
        let cols = col_cumsums_i32(&x, 2, 1, &Subset::All, &Subset::All).unwrap();
        assert!(cols.overflow);
        assert_eq!(cols.values[0], -2_147_483_647);
        assert_eq!(cols.values[1], NA_INTEGER);
    }

    #[test]
    fn subsets_keep_order_duplicates_and_na_indexes() {
        let x = matrix_f();
        let rows = validate_int(&[2, 4], 4).unwrap();
        let got = row_cumsums_f64(&x, 4, 3, &rows, &Subset::All).unwrap();
        assert_eq!(got.values, vec![2.0, 8.0, 18.0, 4.0, 12.0, 24.0]);
        let cols = validate_int(&[3, 1], 3).unwrap();
        let got = col_cumsums_f64(&x, 4, 3, &Subset::All, &cols).unwrap();
        assert_eq!(got.values, vec![9.0, 1.0, 19.0, 3.0, 30.0, 6.0, 42.0, 10.0]);
        let dup = validate_int(&[1, 1], 4).unwrap();
        let reordered = validate_int(&[3, 1, 2], 3).unwrap();
        let got = row_cumsums_f64(&x, 4, 3, &dup, &reordered).unwrap();
        assert_eq!(got.nrow, 2);
        assert_eq!(got.ncol, 3);
        assert_eq!(got.values, vec![9.0, 10.0, 15.0, 9.0, 10.0, 15.0]);

        let missing = validate_int(&[i32::MIN as i64, 2], 4).unwrap();
        let got = row_cumsums_f64(&x, 4, 3, &missing, &Subset::All).unwrap();
        assert!(got.values[0].is_nan() && got.values[1].is_nan() && got.values[2].is_nan());
        assert_eq!(&got.values[3..], &[2.0, 8.0, 18.0]);
    }

    #[test]
    fn empty_margins_keep_the_other_dimension() {
        let x = matrix_f();
        let none = Subset::At(Vec::new());
        let rows = row_cumsums_f64(&x, 4, 3, &none, &Subset::All).unwrap();
        assert_eq!((rows.nrow, rows.ncol), (0, 3));
        assert!(rows.values.is_empty());
        let cols = col_cumsums_f64(&x, 4, 3, &Subset::All, &none).unwrap();
        assert_eq!((cols.nrow, cols.ncol), (4, 0));
        assert!(cols.values.is_empty());
        let empty = col_cumsums_f64(&[], 0, 3, &Subset::All, &Subset::All).unwrap();
        assert_eq!((empty.nrow, empty.ncol), (0, 3));
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
        assert_eq!(validate_logical(&[1], 3).unwrap(), Subset::All);
        assert_eq!(
            validate_logical(&[0, 1], 4).unwrap(),
            Subset::At(vec![Some(1), Some(3)])
        );
        assert!(validate_logical(&[1, 0, 1], 2).is_err());
    }
}
