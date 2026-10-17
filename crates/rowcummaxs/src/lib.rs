//! Row and column cumulative maxima, ported from matrixStats `src/rowCummaxs.c`.
//!
//! The C template walks one margin and keeps the greater value (`>`), so a tie
//! leaves the earlier bits in place. A missing value (IEEE NaN, or integer
//! `NA_INTEGER`) ends that line: every later cell on it is missing too.
//! Index rules follow `validateIndices`.

/// Missing subscript. Valid data indices are non-negative.
const NA_INDEX: i64 = i64::MIN;

/// R's `NA_INTEGER` / `NA_LOGICAL`.
const NA_INTEGER: i32 = i32::MIN;

/// Column-major matrix. `values` has length `nrow * ncol`.
#[derive(Clone, Debug)]
pub struct Matrix<T> {
    pub values: Vec<T>,
    pub nrow: usize,
    pub ncol: usize,
}

/// 1-based subscript vector. `All` selects every position in order.
#[derive(Clone, Copy)]
pub enum Index<'a> {
    All,
    /// Numeric subscripts. Zeros are dropped. Negatives exclude.
    Numeric(&'a [f64]),
    /// Logical subscripts recycled to the margin length. Nonzero is TRUE.
    Logical(&'a [f64]),
}

#[derive(Clone)]
struct Subset {
    all: bool,
    index: Vec<i64>,
    len: usize,
}

impl Subset {
    fn all(n: usize) -> Self {
        Self {
            all: true,
            index: Vec::new(),
            len: n,
        }
    }

    fn empty() -> Self {
        Self {
            all: false,
            index: Vec::new(),
            len: 0,
        }
    }
}

/// Cumulative maximum of each row. `x` is length `nrow * ncol`.
///
/// `column_major` means element `(r, c)` lives at `r + c * nrow`, which is
/// how R stores a matrix. Otherwise element `(r, c)` lives at `r * ncol + c`.
/// The result is column-major with one row per selected row.
pub fn row_cummaxs_f64(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    column_major: bool,
    rows: Index<'_>,
    cols: Index<'_>,
) -> Result<Matrix<f64>, String> {
    cummaxs(
        x,
        nrow,
        ncol,
        column_major,
        rows,
        cols,
        true,
        |v| v.is_nan(),
        f64::NAN,
        |a, b| a > b,
    )
}

/// Cumulative maximum of each column. Layout and subscripts match [`row_cummaxs_f64`].
pub fn col_cummaxs_f64(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    column_major: bool,
    rows: Index<'_>,
    cols: Index<'_>,
) -> Result<Matrix<f64>, String> {
    cummaxs(
        x,
        nrow,
        ncol,
        column_major,
        rows,
        cols,
        false,
        |v| v.is_nan(),
        f64::NAN,
        |a, b| a > b,
    )
}

/// Integer cumulative maximum of each row. `NA_INTEGER` (`i32::MIN`) is missing.
pub fn row_cummaxs_i32(
    x: &[i32],
    nrow: usize,
    ncol: usize,
    column_major: bool,
    rows: Index<'_>,
    cols: Index<'_>,
) -> Result<Matrix<i32>, String> {
    cummaxs(
        x,
        nrow,
        ncol,
        column_major,
        rows,
        cols,
        true,
        |v| v == NA_INTEGER,
        NA_INTEGER,
        |a, b| a > b,
    )
}

/// Integer cumulative maximum of each column. Missing values match [`row_cummaxs_i32`].
pub fn col_cummaxs_i32(
    x: &[i32],
    nrow: usize,
    ncol: usize,
    column_major: bool,
    rows: Index<'_>,
    cols: Index<'_>,
) -> Result<Matrix<i32>, String> {
    cummaxs(
        x,
        nrow,
        ncol,
        column_major,
        rows,
        cols,
        false,
        |v| v == NA_INTEGER,
        NA_INTEGER,
        |a, b| a > b,
    )
}

fn cummaxs<T, F, G>(
    x: &[T],
    nrow: usize,
    ncol: usize,
    column_major: bool,
    rows: Index<'_>,
    cols: Index<'_>,
    by_row: bool,
    is_missing: F,
    missing: T,
    greater: G,
) -> Result<Matrix<T>, String>
where
    T: Copy,
    F: Fn(T) -> bool,
    G: Fn(T, T) -> bool,
{
    let Some(need) = nrow.checked_mul(ncol) else {
        return Err("Argument 'dim.' does not match length of argument 'x'".to_string());
    };
    if need != x.len() {
        return Err(format!(
            "Argument 'dim.' does not match length of argument 'x': {nrow} * {ncol} != {}",
            x.len()
        ));
    }

    let row_sub = resolve(rows, nrow)?;
    let col_sub = resolve(cols, ncol)?;
    let out_nrow = row_sub.len;
    let out_ncol = col_sub.len;
    let Some(n) = out_nrow.checked_mul(out_ncol) else {
        return Err("Argument 'dim.' does not match length of argument 'x'".to_string());
    };
    if out_nrow == 0 || out_ncol == 0 {
        return Ok(Matrix {
            values: Vec::new(),
            nrow: out_nrow,
            ncol: out_ncol,
        });
    }

    let mut ans = vec![missing; n];
    if row_sub.all && col_sub.all {
        if column_major {
            if by_row {
                fill_all::<_, _, _, true, true>(x, nrow, ncol, missing, &is_missing, &greater, &mut ans);
            } else {
                fill_all::<_, _, _, true, false>(x, nrow, ncol, missing, &is_missing, &greater, &mut ans);
            }
        } else if by_row {
            fill_all::<_, _, _, false, true>(x, nrow, ncol, missing, &is_missing, &greater, &mut ans);
        } else {
            fill_all::<_, _, _, false, false>(x, nrow, ncol, missing, &is_missing, &greater, &mut ans);
        }
    } else if by_row {
        for r in 0..out_nrow {
            let row_at = index_at(&row_sub, r);
            let mut dead = false;
            let mut prev = missing;
            let mut started = false;
            for c in 0..out_ncol {
                let dst = r + c * out_nrow;
                if dead {
                    ans[dst] = missing;
                    continue;
                }
                let value = load(x, nrow, ncol, column_major, row_at, index_at(&col_sub, c), missing);
                if is_missing(value) {
                    dead = true;
                    ans[dst] = missing;
                } else if !started || greater(value, prev) {
                    prev = value;
                    started = true;
                    ans[dst] = value;
                } else {
                    ans[dst] = prev;
                }
            }
        }
    } else {
        for c in 0..out_ncol {
            let col_at = index_at(&col_sub, c);
            let mut dead = false;
            let mut prev = missing;
            let mut started = false;
            for r in 0..out_nrow {
                let dst = r + c * out_nrow;
                if dead {
                    ans[dst] = missing;
                    continue;
                }
                let value = load(x, nrow, ncol, column_major, index_at(&row_sub, r), col_at, missing);
                if is_missing(value) {
                    dead = true;
                    ans[dst] = missing;
                } else if !started || greater(value, prev) {
                    prev = value;
                    started = true;
                    ans[dst] = value;
                } else {
                    ans[dst] = prev;
                }
            }
        }
    }

    Ok(Matrix {
        values: ans,
        nrow: out_nrow,
        ncol: out_ncol,
    })
}

fn fill_all<T, F, G, const COL_MAJOR: bool, const BY_ROW: bool>(
    x: &[T],
    nrow: usize,
    ncol: usize,
    missing: T,
    is_missing: &F,
    greater: &G,
    ans: &mut [T],
) where
    T: Copy,
    F: Fn(T) -> bool,
    G: Fn(T, T) -> bool,
{
    if BY_ROW {
        for r in 0..nrow {
            let mut dead = false;
            let mut prev = missing;
            let mut started = false;
            for c in 0..ncol {
                let dst = r + c * nrow;
                if dead {
                    ans[dst] = missing;
                    continue;
                }
                let value = x[offset::<COL_MAJOR>(r, c, nrow, ncol)];
                if is_missing(value) {
                    dead = true;
                    ans[dst] = missing;
                } else if !started || greater(value, prev) {
                    prev = value;
                    started = true;
                    ans[dst] = value;
                } else {
                    ans[dst] = prev;
                }
            }
        }
    } else {
        for c in 0..ncol {
            let mut dead = false;
            let mut prev = missing;
            let mut started = false;
            for r in 0..nrow {
                let dst = r + c * nrow;
                if dead {
                    ans[dst] = missing;
                    continue;
                }
                let value = x[offset::<COL_MAJOR>(r, c, nrow, ncol)];
                if is_missing(value) {
                    dead = true;
                    ans[dst] = missing;
                } else if !started || greater(value, prev) {
                    prev = value;
                    started = true;
                    ans[dst] = value;
                } else {
                    ans[dst] = prev;
                }
            }
        }
    }
}

#[inline(always)]
fn offset<const COL_MAJOR: bool>(row: usize, col: usize, nrow: usize, ncol: usize) -> usize {
    if COL_MAJOR {
        row + col * nrow
    } else {
        row * ncol + col
    }
}

#[inline(always)]
fn index_at(sub: &Subset, i: usize) -> i64 {
    if sub.all {
        i as i64
    } else {
        sub.index[i]
    }
}

fn load<T: Copy>(
    x: &[T],
    nrow: usize,
    ncol: usize,
    column_major: bool,
    row: i64,
    col: i64,
    missing: T,
) -> T {
    if row < 0 || col < 0 {
        return missing;
    }
    let row_u = row as usize;
    let col_u = col as usize;
    if row_u >= nrow || col_u >= ncol {
        return missing;
    }
    let idx = if column_major {
        col_u.checked_mul(nrow).and_then(|base| base.checked_add(row_u))
    } else {
        row_u.checked_mul(ncol).and_then(|base| base.checked_add(col_u))
    };
    match idx {
        Some(i) if i < x.len() => x[i],
        _ => missing,
    }
}

fn resolve(index: Index<'_>, n: usize) -> Result<Subset, String> {
    match index {
        Index::All => Ok(Subset::all(n)),
        Index::Numeric(idxs) => validate_numeric(idxs, n),
        Index::Logical(idxs) => validate_logical(idxs, n),
    }
}

fn from_idx(idx: f64, max_idx: f64) -> i64 {
    if idx.is_nan() || idx.is_infinite() || idx > max_idx {
        NA_INDEX
    } else {
        (idx - 1.0).trunc() as i64
    }
}

fn validate_numeric(idxs: &[f64], max_idx: usize) -> Result<Subset, String> {
    let max_f = max_idx as f64;
    let mut state = 0i32;
    let mut count = 0usize;
    for &idx in idxs {
        if idx > 0.0 || idx.is_nan() || idx.is_infinite() {
            if state < 0 {
                return Err("only 0's may be mixed with negative subscripts".to_string());
            }
            if !(idx.is_nan() || idx.is_infinite()) && idx > max_f {
                return Err("subscript out of bounds".to_string());
            }
            state = 1;
            count += 1;
        } else if idx < 0.0 {
            if state > 0 {
                return Err("only 0's may be mixed with negative subscripts".to_string());
            }
            state = -1;
        }
    }

    if state >= 0 {
        let mut index = Vec::with_capacity(count);
        for &idx in idxs {
            if idx > 0.0 || idx.is_nan() || idx.is_infinite() {
                index.push(from_idx(idx, max_f));
            }
        }
        return Ok(Subset {
            all: false,
            index,
            len: count,
        });
    }

    let mut excluded = vec![false; max_idx];
    let mut keep = max_idx;
    for &idx in idxs {
        if idx >= 0.0 || idx.is_nan() || idx.is_infinite() {
            continue;
        }
        let excl = (-idx).trunc();
        if !excl.is_finite() {
            continue;
        }
        // C converts to an integer subscript before the bounds check.
        let excl_i = excl as i64;
        if excl_i <= 0 || (excl_i as usize) > max_idx {
            continue;
        }
        let pos = (excl_i as usize) - 1;
        if !excluded[pos] {
            excluded[pos] = true;
            keep -= 1;
        }
    }
    if keep == 0 {
        return Ok(Subset::empty());
    }
    let mut index = Vec::with_capacity(keep);
    for (i, drop) in excluded.iter().enumerate() {
        if !*drop {
            index.push(i as i64);
        }
    }
    Ok(Subset {
        all: false,
        index,
        len: keep,
    })
}

fn logical_on(flag: f64) -> i8 {
    if flag.is_nan() {
        -1
    } else if flag == 0.0 {
        0
    } else {
        1
    }
}

fn validate_logical(idxs: &[f64], max_idx: usize) -> Result<Subset, String> {
    let nidxs = idxs.len();
    if nidxs == 0 {
        return Ok(Subset::empty());
    }
    if nidxs > max_idx {
        return Err("logical subscript too long".to_string());
    }

    let max_i = max_idx as i64;
    let nidxs_i = nidxs as i64;
    let last_part = (max_i % nidxs_i) as usize;
    let mut na_count = 0i64;
    let mut count1 = 0i64;
    let mut count2 = 0i64;
    for (ii, &flag) in idxs.iter().enumerate() {
        let on = logical_on(flag);
        if on == 0 {
            continue;
        }
        if on < 0 {
            na_count += 1;
        }
        if ii < last_part {
            count1 += 1;
        } else {
            count2 += 1;
        }
    }
    let count = count1 + count2;
    if na_count == 0 && count == nidxs_i {
        return Ok(Subset::all(max_idx));
    }

    let ans_len = (max_i / nidxs_i) * count + count1;
    if ans_len == 0 {
        return Ok(Subset::empty());
    }
    let mut ans = vec![0i64; ans_len as usize];
    let mut jj = 0usize;
    for (ii, &flag) in idxs.iter().enumerate() {
        let on = logical_on(flag);
        if on == 0 {
            continue;
        }
        ans[jj] = if on < 0 { NA_INDEX } else { ii as i64 };
        jj += 1;
    }
    let count_us = count as usize;
    let mut ii = count_us;
    let mut kk = nidxs_i;
    while kk + nidxs_i <= max_i {
        for j in 0..count_us {
            ans[ii + j] = if ans[j] == NA_INDEX {
                NA_INDEX
            } else {
                ans[j] + kk
            };
        }
        kk += nidxs_i;
        ii += count_us;
    }
    for j in 0..count1 as usize {
        ans[ii + j] = if ans[j] == NA_INDEX {
            NA_INDEX
        } else {
            ans[j] + kk
        };
    }
    Ok(Subset {
        all: false,
        index: ans,
        len: ans_len as usize,
    })
}

#[cfg(feature = "python")]
mod py {
    use numpy::{IntoPyArray, PyReadonlyArray1};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::{Index, col_cummaxs_f64, col_cummaxs_i32, row_cummaxs_f64, row_cummaxs_i32};

    fn slice_of<'a>(values: &'a Option<PyReadonlyArray1<'a, f64>>) -> PyResult<Option<&'a [f64]>> {
        match values {
            None => Ok(None),
            Some(array) => array
                .as_slice()
                .map(Some)
                .map_err(|err| PyValueError::new_err(err.to_string())),
        }
    }

    fn index_of<'a>(values: Option<&'a [f64]>, logical: bool) -> PyResult<Index<'a>> {
        match values {
            None => Ok(Index::All),
            Some(vals) if logical => Ok(Index::Logical(vals)),
            Some(vals) => Ok(Index::Numeric(vals)),
        }
    }

    fn rows_cols<'a>(
        rows: &'a Option<PyReadonlyArray1<'a, f64>>,
        rows_logical: bool,
        cols: &'a Option<PyReadonlyArray1<'a, f64>>,
        cols_logical: bool,
    ) -> PyResult<(Index<'a>, Index<'a>)> {
        let rows_slice = slice_of(rows)?;
        let cols_slice = slice_of(cols)?;
        Ok((
            index_of(rows_slice, rows_logical)?,
            index_of(cols_slice, cols_logical)?,
        ))
    }

    #[pyfunction]
    #[pyo3(signature = (
        x,
        nrow,
        ncol,
        column_major,
        rows=None,
        rows_logical=false,
        cols=None,
        cols_logical=false,
        by_row=true
    ))]
    fn cummaxs_f64<'py>(
        py: Python<'py>,
        x: PyReadonlyArray1<'py, f64>,
        nrow: usize,
        ncol: usize,
        column_major: bool,
        rows: Option<PyReadonlyArray1<'py, f64>>,
        rows_logical: bool,
        cols: Option<PyReadonlyArray1<'py, f64>>,
        cols_logical: bool,
        by_row: bool,
    ) -> PyResult<(Bound<'py, numpy::PyArray1<f64>>, usize, usize)> {
        let x_slice = x
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        let (rows_index, cols_index) = rows_cols(&rows, rows_logical, &cols, cols_logical)?;
        let ans = if by_row {
            row_cummaxs_f64(x_slice, nrow, ncol, column_major, rows_index, cols_index)
        } else {
            col_cummaxs_f64(x_slice, nrow, ncol, column_major, rows_index, cols_index)
        }
        .map_err(PyValueError::new_err)?;
        let nrow_out = ans.nrow;
        let ncol_out = ans.ncol;
        Ok((ans.values.into_pyarray(py), nrow_out, ncol_out))
    }

    #[pyfunction]
    #[pyo3(signature = (
        x,
        nrow,
        ncol,
        column_major,
        rows=None,
        rows_logical=false,
        cols=None,
        cols_logical=false,
        by_row=true
    ))]
    fn cummaxs_i32<'py>(
        py: Python<'py>,
        x: PyReadonlyArray1<'py, i32>,
        nrow: usize,
        ncol: usize,
        column_major: bool,
        rows: Option<PyReadonlyArray1<'py, f64>>,
        rows_logical: bool,
        cols: Option<PyReadonlyArray1<'py, f64>>,
        cols_logical: bool,
        by_row: bool,
    ) -> PyResult<(Bound<'py, numpy::PyArray1<i32>>, usize, usize)> {
        let x_slice = x
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        let (rows_index, cols_index) = rows_cols(&rows, rows_logical, &cols, cols_logical)?;
        let ans = if by_row {
            row_cummaxs_i32(x_slice, nrow, ncol, column_major, rows_index, cols_index)
        } else {
            col_cummaxs_i32(x_slice, nrow, ncol, column_major, rows_index, cols_index)
        }
        .map_err(PyValueError::new_err)?;
        let nrow_out = ans.nrow;
        let ncol_out = ans.ncol;
        Ok((ans.values.into_pyarray(py), nrow_out, ncol_out))
    }

    #[pymodule]
    fn rowcummaxs(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(cummaxs_f64, m)?)?;
        m.add_function(wrap_pyfunction!(cummaxs_i32, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{Index, col_cummaxs_f64, col_cummaxs_i32, row_cummaxs_f64, row_cummaxs_i32};

    fn assert_f64(actual: &[f64], expected: &[f64]) {
        assert_eq!(actual.len(), expected.len());
        for (got, want) in actual.iter().zip(expected) {
            if want.is_nan() {
                assert!(got.is_nan());
            } else {
                assert_eq!(got.to_bits(), want.to_bits());
            }
        }
    }

    #[test]
    fn row_and_column_cummax_of_a_small_matrix() {
        // Printed:
        // 3 4 5
        // 1 2 0
        let x = vec![3.0, 1.0, 4.0, 2.0, 5.0, 0.0];
        let rows = row_cummaxs_f64(&x, 2, 3, true, Index::All, Index::All).unwrap();
        assert_eq!((rows.nrow, rows.ncol), (2, 3));
        assert_f64(&rows.values, &[3.0, 1.0, 4.0, 2.0, 5.0, 2.0]);
        let cols = col_cummaxs_f64(&x, 2, 3, true, Index::All, Index::All).unwrap();
        assert_f64(&cols.values, &[3.0, 3.0, 4.0, 4.0, 5.0, 5.0]);
    }

    #[test]
    fn row_major_layout_reads_the_printed_matrix() {
        let x = vec![3.0, 4.0, 5.0, 1.0, 2.0, 0.0];
        let rows = row_cummaxs_f64(&x, 2, 3, false, Index::All, Index::All).unwrap();
        assert_f64(&rows.values, &[3.0, 1.0, 4.0, 2.0, 5.0, 2.0]);
    }

    #[test]
    fn nan_ends_the_rest_of_the_line() {
        // 1 NaN 0
        // 2  4  5
        let x = vec![1.0, 2.0, f64::NAN, 4.0, 0.0, 5.0];
        let rows = row_cummaxs_f64(&x, 2, 3, true, Index::All, Index::All).unwrap();
        assert_f64(&rows.values, &[1.0, 2.0, f64::NAN, 4.0, f64::NAN, 5.0]);
        let cols = col_cummaxs_f64(&x, 2, 3, true, Index::All, Index::All).unwrap();
        assert_f64(&cols.values, &[1.0, 2.0, f64::NAN, f64::NAN, 0.0, 5.0]);
    }

    #[test]
    fn tie_keeps_a_negative_zero() {
        let x = vec![-0.0, 0.0];
        let rows = row_cummaxs_f64(&x, 1, 2, true, Index::All, Index::All).unwrap();
        assert!(rows.values[0].is_sign_negative());
        assert!(rows.values[1].is_sign_negative());
    }

    #[test]
    fn column_subset_and_a_missing_subscript() {
        let x = vec![3.0, 1.0, 4.0, 2.0, 5.0, 0.0];
        let cols = [2.0, f64::NAN, 1.0];
        let rows = row_cummaxs_f64(&x, 2, 3, true, Index::All, Index::Numeric(&cols)).unwrap();
        assert_eq!((rows.nrow, rows.ncol), (2, 3));
        assert_f64(
            &rows.values,
            &[4.0, 2.0, f64::NAN, f64::NAN, f64::NAN, f64::NAN],
        );
    }

    #[test]
    fn integer_missing_propagates_and_logical_values_fit() {
        let na = i32::MIN;
        // 1 NA
        // 3  2
        let x = vec![1, 3, na, 2];
        let rows = row_cummaxs_i32(&x, 2, 2, true, Index::All, Index::All).unwrap();
        assert_eq!(rows.values, vec![1, 3, na, 3]);
        let cols = col_cummaxs_i32(&x, 2, 2, true, Index::All, Index::All).unwrap();
        assert_eq!(cols.values, vec![1, 3, na, na]);
    }

    #[test]
    fn empty_margin_is_an_empty_matrix() {
        let rows = row_cummaxs_f64(&[], 0, 0, true, Index::All, Index::All).unwrap();
        assert_eq!((rows.nrow, rows.ncol, rows.values.len()), (0, 0, 0));
        let cols = col_cummaxs_f64(&[0.0; 0], 0, 4, true, Index::All, Index::All).unwrap();
        assert_eq!((cols.nrow, cols.ncol), (0, 4));
    }

    #[test]
    fn subscript_errors_match_validate_indices() {
        let x = vec![1.0, 2.0, 3.0, 4.0];
        let err = row_cummaxs_f64(&x, 2, 2, true, Index::Numeric(&[5.0]), Index::All).unwrap_err();
        assert!(err.contains("subscript out of bounds"));
        let err = row_cummaxs_f64(&x, 2, 2, true, Index::Numeric(&[1.0, -1.0]), Index::All)
            .unwrap_err();
        assert!(err.contains("only 0's may be mixed"));
    }
}
