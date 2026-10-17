//! Row and column cumulative products, ported from matrixStats `src/rowCumprods.c`.
//!
//! `rowCumprods` calls the C routine with `byrow = TRUE` and `colCumprods`
//! with `byrow = FALSE`. The matrix is stored column-major, as in R, when
//! the strides are `(1, nrow)`. `rows` and `cols` follow `validateIndices`:
//! missing means every position, values are 1-based, zeros are dropped, and
//! negatives exclude. A missing index reads R's NA.
//!
//! Double products are IEEE multiplies. The row form copies the first
//! selected column; the column form starts from 1 and multiplies, which is
//! how a leading NA becomes a quiet NA only on the column path. Integer and
//! logical input return `i32`. Logical values are 1 and 0. `i32::MIN` is
//! R's NA. A running product outside [-2147483647, 2147483647] becomes NA
//! for the rest of that row or column.

/// Positions along one margin.
///
/// `All` is R's `NULL`. `At` is a validated list of 0-based positions;
/// `None` is an NA index.
#[derive(Clone, Debug, PartialEq)]
pub enum Subset {
    All,
    At(Vec<Option<usize>>),
}

/// Row-major cumulative products.
#[derive(Clone, Debug, PartialEq)]
pub struct CumprodF64 {
    pub values: Vec<f64>,
    pub nrow: usize,
    pub ncol: usize,
}

/// Row-major integer cumulative products.
///
/// `overflow` is true when any product left the R integer range. Those
/// entries, and every later entry on the same row or column, are
/// `NA_INTEGER` (`i32::MIN`).
#[derive(Clone, Debug, PartialEq)]
pub struct CumprodI32 {
    pub values: Vec<i32>,
    pub nrow: usize,
    pub ncol: usize,
    pub overflow: bool,
}

const NA_INTEGER: i32 = i32::MIN;
const R_INT_MIN: i64 = -2_147_483_647;
const R_INT_MAX: i64 = 2_147_483_647;
const NA_REAL_BITS: u64 = 0x7ff00000000007a2;

/// Cumulative product of each row. `x` is addressed with the given strides.
pub fn row_cumprods_f64(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    row_stride: usize,
    col_stride: usize,
    rows: &Subset,
    cols: &Subset,
) -> Result<CumprodF64, String> {
    cumprods_f64(x, row_stride, col_stride, nrow, ncol, rows, cols, true)
}

/// Cumulative product of each column. `x` is addressed with the given strides.
pub fn col_cumprods_f64(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    row_stride: usize,
    col_stride: usize,
    rows: &Subset,
    cols: &Subset,
) -> Result<CumprodF64, String> {
    cumprods_f64(x, row_stride, col_stride, nrow, ncol, rows, cols, false)
}

/// Integer cumulative product of each row. Column-major when `col_stride == nrow`.
pub fn row_cumprods_i32(
    x: &[i32],
    nrow: usize,
    ncol: usize,
    row_stride: usize,
    col_stride: usize,
    rows: &Subset,
    cols: &Subset,
) -> Result<CumprodI32, String> {
    cumprods_i32(x, row_stride, col_stride, nrow, ncol, rows, cols, true)
}

/// Integer cumulative product of each column.
pub fn col_cumprods_i32(
    x: &[i32],
    nrow: usize,
    ncol: usize,
    row_stride: usize,
    col_stride: usize,
    rows: &Subset,
    cols: &Subset,
) -> Result<CumprodI32, String> {
    cumprods_i32(x, row_stride, col_stride, nrow, ncol, rows, cols, false)
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

fn cumprods_f64(
    x: &[f64],
    row_stride: usize,
    col_stride: usize,
    nrow: usize,
    ncol: usize,
    rows: &Subset,
    cols: &Subset,
    byrow: bool,
) -> Result<CumprodF64, String> {
    ensure_span(x.len(), nrow, ncol, row_stride, col_stride)?;
    let row_pos = positions(rows, nrow);
    let col_pos = positions(cols, ncol);
    let nrows = row_pos.len();
    let ncols = col_pos.len();
    let mut ans = vec![0.0; nrows.saturating_mul(ncols)];
    if nrows == 0 || ncols == 0 {
        return Ok(CumprodF64 {
            values: ans,
            nrow: nrows,
            ncol: ncols,
        });
    }

    if byrow {
        let col0 = col_pos[0];
        for (r_i, &row) in row_pos.iter().enumerate() {
            ans[r_i * ncols] = load_f64(x, row_stride, col_stride, row, col0);
        }
        for (c_i, &col) in col_pos.iter().enumerate().skip(1) {
            for (r_i, &row) in row_pos.iter().enumerate() {
                let xvalue = load_f64(x, row_stride, col_stride, row, col);
                let prev = ans[r_i * ncols + (c_i - 1)];
                ans[r_i * ncols + c_i] = prev * xvalue;
            }
        }
    } else {
        for (c_i, &col) in col_pos.iter().enumerate() {
            // A real multiply by 1, not a copy. LLVM would otherwise fold
            // `1.0 * x` and keep a signaling NA payload that R quiets.
            let mut value = std::hint::black_box(1.0);
            for (r_i, &row) in row_pos.iter().enumerate() {
                let xvalue = load_f64(x, row_stride, col_stride, row, col);
                value *= xvalue;
                ans[r_i * ncols + c_i] = value;
            }
        }
    }

    Ok(CumprodF64 {
        values: ans,
        nrow: nrows,
        ncol: ncols,
    })
}

fn cumprods_i32(
    x: &[i32],
    row_stride: usize,
    col_stride: usize,
    nrow: usize,
    ncol: usize,
    rows: &Subset,
    cols: &Subset,
    byrow: bool,
) -> Result<CumprodI32, String> {
    ensure_span(x.len(), nrow, ncol, row_stride, col_stride)?;
    let row_pos = positions(rows, nrow);
    let col_pos = positions(cols, ncol);
    let nrows = row_pos.len();
    let ncols = col_pos.len();
    let mut ans = vec![0_i32; nrows.saturating_mul(ncols)];
    let mut overflow = false;
    if nrows == 0 || ncols == 0 {
        return Ok(CumprodI32 {
            values: ans,
            nrow: nrows,
            ncol: ncols,
            overflow,
        });
    }

    if byrow {
        let mut oks = vec![false; nrows];
        let col0 = col_pos[0];
        for (r_i, &row) in row_pos.iter().enumerate() {
            let xvalue = load_i32(x, row_stride, col_stride, row, col0);
            ans[r_i * ncols] = xvalue;
            oks[r_i] = xvalue != NA_INTEGER;
        }
        for (c_i, &col) in col_pos.iter().enumerate().skip(1) {
            for (r_i, &row) in row_pos.iter().enumerate() {
                let dest = r_i * ncols + c_i;
                let xvalue = load_i32(x, row_stride, col_stride, row, col);
                if oks[r_i] {
                    if xvalue == NA_INTEGER {
                        oks[r_i] = false;
                        ans[dest] = NA_INTEGER;
                    } else {
                        let prev = ans[r_i * ncols + (c_i - 1)] as i64;
                        let value = prev * i64::from(xvalue);
                        if value < R_INT_MIN || value > R_INT_MAX {
                            oks[r_i] = false;
                            overflow = true;
                            ans[dest] = NA_INTEGER;
                        } else {
                            ans[dest] = value as i32;
                        }
                    }
                } else {
                    ans[dest] = NA_INTEGER;
                }
            }
        }
    } else {
        for (c_i, &col) in col_pos.iter().enumerate() {
            let mut value: i64 = 1;
            let mut ok = true;
            for (r_i, &row) in row_pos.iter().enumerate() {
                let dest = r_i * ncols + c_i;
                let xvalue = load_i32(x, row_stride, col_stride, row, col);
                if ok {
                    if xvalue == NA_INTEGER {
                        ok = false;
                        ans[dest] = NA_INTEGER;
                    } else {
                        value *= i64::from(xvalue);
                        if value < R_INT_MIN || value > R_INT_MAX {
                            ok = false;
                            overflow = true;
                            ans[dest] = NA_INTEGER;
                        } else {
                            ans[dest] = value as i32;
                        }
                    }
                } else {
                    ans[dest] = NA_INTEGER;
                }
            }
        }
    }

    Ok(CumprodI32 {
        values: ans,
        nrow: nrows,
        ncol: ncols,
        overflow,
    })
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
        _ => f64::from_bits(NA_REAL_BITS),
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
        Err("x length does not match the matrix shape".to_string())
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
    use numpy::ndarray::{Array2, ArrayView2};
    use numpy::{IntoPyArray, PyArray2, PyReadonlyArray1, PyReadonlyArray2};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::{
        col_cumprods_f64, col_cumprods_i32, row_cumprods_f64, row_cumprods_i32, validate_int,
        validate_logical, validate_real, Subset,
    };

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

    fn array2_f64<'py>(
        py: Python<'py>,
        values: Vec<f64>,
        nrow: usize,
        ncol: usize,
    ) -> PyResult<Bound<'py, PyArray2<f64>>> {
        let arr = Array2::from_shape_vec((nrow, ncol), values)
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        Ok(arr.into_pyarray(py))
    }

    fn array2_i32<'py>(
        py: Python<'py>,
        values: Vec<i32>,
        nrow: usize,
        ncol: usize,
    ) -> PyResult<Bound<'py, PyArray2<i32>>> {
        let arr = Array2::from_shape_vec((nrow, ncol), values)
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        Ok(arr.into_pyarray(py))
    }

    fn cumprods_f64_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
        byrow: bool,
    ) -> PyResult<Bound<'py, PyArray2<f64>>> {
        let view = x.as_array();
        let (nrow, ncol) = view.dim();
        let row_subset = parse_subset(rows.as_ref(), rows_kind, nrow)?;
        let col_subset = parse_subset(cols.as_ref(), cols_kind, ncol)?;
        let result = if nrow == 0 || ncol == 0 {
            if byrow {
                row_cumprods_f64(&[], nrow, ncol, 1, 0, &row_subset, &col_subset)
            } else {
                col_cumprods_f64(&[], nrow, ncol, 1, 0, &row_subset, &col_subset)
            }
        } else if let Some((slice, row_stride, col_stride)) = contiguous(&view) {
            if byrow {
                row_cumprods_f64(
                    slice,
                    nrow,
                    ncol,
                    row_stride,
                    col_stride,
                    &row_subset,
                    &col_subset,
                )
            } else {
                col_cumprods_f64(
                    slice,
                    nrow,
                    ncol,
                    row_stride,
                    col_stride,
                    &row_subset,
                    &col_subset,
                )
            }
        } else {
            let owned = owned_column_major(view);
            if byrow {
                row_cumprods_f64(&owned, nrow, ncol, 1, nrow, &row_subset, &col_subset)
            } else {
                col_cumprods_f64(&owned, nrow, ncol, 1, nrow, &row_subset, &col_subset)
            }
        }
        .map_err(PyValueError::new_err)?;
        array2_f64(py, result.values, result.nrow, result.ncol)
    }

    fn cumprods_i32_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, i32>,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
        byrow: bool,
    ) -> PyResult<(Bound<'py, PyArray2<i32>>, bool)> {
        let view = x.as_array();
        let (nrow, ncol) = view.dim();
        let row_subset = parse_subset(rows.as_ref(), rows_kind, nrow)?;
        let col_subset = parse_subset(cols.as_ref(), cols_kind, ncol)?;
        let result = if nrow == 0 || ncol == 0 {
            if byrow {
                row_cumprods_i32(&[], nrow, ncol, 1, 0, &row_subset, &col_subset)
            } else {
                col_cumprods_i32(&[], nrow, ncol, 1, 0, &row_subset, &col_subset)
            }
        } else if let Some((slice, row_stride, col_stride)) = contiguous(&view) {
            if byrow {
                row_cumprods_i32(
                    slice,
                    nrow,
                    ncol,
                    row_stride,
                    col_stride,
                    &row_subset,
                    &col_subset,
                )
            } else {
                col_cumprods_i32(
                    slice,
                    nrow,
                    ncol,
                    row_stride,
                    col_stride,
                    &row_subset,
                    &col_subset,
                )
            }
        } else {
            let owned = owned_column_major(view);
            if byrow {
                row_cumprods_i32(&owned, nrow, ncol, 1, nrow, &row_subset, &col_subset)
            } else {
                col_cumprods_i32(&owned, nrow, ncol, 1, nrow, &row_subset, &col_subset)
            }
        }
        .map_err(PyValueError::new_err)?;
        let overflow = result.overflow;
        let arr = array2_i32(py, result.values, result.nrow, result.ncol)?;
        Ok((arr, overflow))
    }

    #[pyfunction]
    #[pyo3(name = "row_cumprods_f64", signature = (x, rows=None, rows_kind="all", cols=None, cols_kind="all"))]
    fn row_cumprods_f64_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
    ) -> PyResult<Bound<'py, PyArray2<f64>>> {
        cumprods_f64_py(py, x, rows, rows_kind, cols, cols_kind, true)
    }

    #[pyfunction]
    #[pyo3(name = "col_cumprods_f64", signature = (x, rows=None, rows_kind="all", cols=None, cols_kind="all"))]
    fn col_cumprods_f64_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
    ) -> PyResult<Bound<'py, PyArray2<f64>>> {
        cumprods_f64_py(py, x, rows, rows_kind, cols, cols_kind, false)
    }

    #[pyfunction]
    #[pyo3(name = "row_cumprods_i32", signature = (x, rows=None, rows_kind="all", cols=None, cols_kind="all"))]
    fn row_cumprods_i32_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, i32>,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
    ) -> PyResult<(Bound<'py, PyArray2<i32>>, bool)> {
        cumprods_i32_py(py, x, rows, rows_kind, cols, cols_kind, true)
    }

    #[pyfunction]
    #[pyo3(name = "col_cumprods_i32", signature = (x, rows=None, rows_kind="all", cols=None, cols_kind="all"))]
    fn col_cumprods_i32_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, i32>,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
    ) -> PyResult<(Bound<'py, PyArray2<i32>>, bool)> {
        cumprods_i32_py(py, x, rows, rows_kind, cols, cols_kind, false)
    }

    #[pymodule]
    fn rowcumprods(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(row_cumprods_f64_py, m)?)?;
        m.add_function(wrap_pyfunction!(col_cumprods_f64_py, m)?)?;
        m.add_function(wrap_pyfunction!(row_cumprods_i32_py, m)?)?;
        m.add_function(wrap_pyfunction!(col_cumprods_i32_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{
        col_cumprods_f64, col_cumprods_i32, row_cumprods_f64, row_cumprods_i32, validate_int,
        validate_logical, validate_real, Subset, NA_INTEGER, NA_REAL_BITS,
    };

    fn na_real() -> f64 {
        f64::from_bits(NA_REAL_BITS)
    }

    fn row_f64(x: &[f64], nrow: usize, ncol: usize, rows: &Subset, cols: &Subset) -> Vec<f64> {
        row_cumprods_f64(x, nrow, ncol, 1, nrow, rows, cols)
            .unwrap()
            .values
    }

    fn col_f64(x: &[f64], nrow: usize, ncol: usize, rows: &Subset, cols: &Subset) -> Vec<f64> {
        col_cumprods_f64(x, nrow, ncol, 1, nrow, rows, cols)
            .unwrap()
            .values
    }

    #[test]
    fn integer_matrix_matches_the_manual_example() {
        let x: Vec<i32> = (1..=12).collect();
        let rows = row_cumprods_i32(&x, 4, 3, 1, 4, &Subset::All, &Subset::All).unwrap();
        let cols = col_cumprods_i32(&x, 4, 3, 1, 4, &Subset::All, &Subset::All).unwrap();
        assert!(!rows.overflow);
        assert_eq!(
            rows.values,
            vec![1, 5, 45, 2, 12, 120, 3, 21, 231, 4, 32, 384]
        );
        assert_eq!(
            cols.values,
            vec![1, 5, 9, 2, 30, 90, 6, 210, 990, 24, 1680, 11880]
        );
    }

    #[test]
    fn zeros_negatives_and_integer_na() {
        let na = NA_INTEGER;
        let x = vec![2, na, -2, 0, 4, -2, -3, 5, 3];
        let rows = row_cumprods_i32(&x, 3, 3, 1, 3, &Subset::All, &Subset::All).unwrap();
        assert_eq!(rows.values, vec![2, 0, 0, na, na, na, -2, 4, 12]);
        let cols = col_cumprods_i32(&x, 3, 3, 1, 3, &Subset::All, &Subset::All).unwrap();
        assert_eq!(cols.values, vec![2, 0, -3, na, 0, -15, na, 0, -45]);
    }

    #[test]
    fn integer_overflow_sticks_for_the_rest_of_the_margin() {
        let x = vec![46_341, 46_341, 1];
        let rows = row_cumprods_i32(&x, 1, 3, 1, 1, &Subset::All, &Subset::All).unwrap();
        assert!(rows.overflow);
        assert_eq!(rows.values, vec![46_341, NA_INTEGER, NA_INTEGER]);

        let edge = vec![46_340, 46_340];
        let kept = row_cumprods_i32(&edge, 1, 2, 1, 1, &Subset::All, &Subset::All).unwrap();
        assert!(!kept.overflow);
        assert_eq!(kept.values, vec![46_340, 2_147_395_600]);

        let wide = vec![1_073_741_824, -2];
        let over = row_cumprods_i32(&wide, 1, 2, 1, 1, &Subset::All, &Subset::All).unwrap();
        assert!(over.overflow);
        assert_eq!(over.values[1], NA_INTEGER);

        let down = vec![46_341, 46_341];
        let cols = col_cumprods_i32(&down, 2, 1, 1, 2, &Subset::All, &Subset::All).unwrap();
        assert!(cols.overflow);
        assert_eq!(cols.values, vec![46_341, NA_INTEGER]);
    }

    #[test]
    fn double_na_is_copied_on_rows_and_multiplied_on_columns() {
        let x = vec![na_real(), 2.0, 3.0];
        let rows = row_f64(&x, 1, 3, &Subset::All, &Subset::All);
        assert_eq!(rows[0].to_bits(), NA_REAL_BITS);
        assert_eq!(rows[1].to_bits(), 0x7ff80000000007a2);
        assert_eq!(rows[2].to_bits(), 0x7ff80000000007a2);

        let col_x = vec![na_real(), 2.0];
        let cols = col_f64(&col_x, 2, 1, &Subset::All, &Subset::All);
        assert_eq!(cols[0].to_bits(), 0x7ff80000000007a2);
        assert!(cols[1].is_nan());
    }

    #[test]
    fn signed_zero_inf_and_nan_follow_ieee() {
        let x = vec![0.0, -1.0, -2.0, 3.0];
        let rows = row_f64(&x, 1, 4, &Subset::All, &Subset::All);
        assert_eq!(rows[0].to_bits(), 0.0_f64.to_bits());
        assert_eq!(rows[1].to_bits(), (-0.0_f64).to_bits());
        assert_eq!(rows[2].to_bits(), 0.0_f64.to_bits());
        assert_eq!(rows[3], 0.0);

        let inf = vec![f64::INFINITY, -2.0, 0.0];
        let got = row_f64(&inf, 1, 3, &Subset::All, &Subset::All);
        assert!(got[0].is_infinite() && got[0].is_sign_positive());
        assert!(got[1].is_infinite() && got[1].is_sign_negative());
        assert!(got[2].is_nan());
    }

    #[test]
    fn subsets_keep_order_and_repeat_rows() {
        let x = vec![1.0, 2.0, 3.0, 4.0, 5.0, 6.0];
        let rows = validate_int(&[2, 2], 2).unwrap();
        let cols = validate_int(&[3, 1], 3).unwrap();
        let got = row_f64(&x, 2, 3, &rows, &cols);
        assert_eq!(got, vec![6.0, 12.0, 6.0, 12.0]);
    }

    #[test]
    fn index_rules_match_validate_indices() {
        assert_eq!(
            validate_int(&[0, 2, 0], 2).unwrap(),
            Subset::At(vec![Some(1)])
        );
        assert_eq!(validate_int(&[-2], 2).unwrap(), Subset::At(vec![Some(0)]));
        assert!(validate_int(&[1, 9], 2).is_err());
        assert!(validate_int(&[-1, 1], 2).is_err());
        assert_eq!(validate_real(&[1.9], 2).unwrap(), Subset::At(vec![Some(0)]));
        assert_eq!(
            validate_real(&[f64::INFINITY], 2).unwrap(),
            Subset::At(vec![None])
        );
        assert_eq!(validate_logical(&[1], 3).unwrap(), Subset::All);
        assert_eq!(
            validate_logical(&[0, 1, -1], 5).unwrap(),
            Subset::At(vec![Some(1), None, Some(4)])
        );
    }
}
