//! Cumulative minima, ported from matrixStats `src/rowCummins.c`.
//!
//! `rowCummins` calls the C routine with `byrow = TRUE` and `colCummins`
//! with `byrow = FALSE`. The result is a matrix. Along the chosen margin,
//! each value is the minimum of the values seen so far. R's NA (integer
//! `NA_INTEGER`, or a double NaN) ends that run: the current cell and every
//! cell after it on that run are missing. Index rules follow
//! `validateIndices` with out-of-bounds indexes rejected.

/// Missing subscript. Valid data indices are non-negative.
const NA_INDEX: i64 = i64::MIN;

/// R's integer and logical NA. `NA_LOGICAL` equals `NA_INTEGER`.
const NA_INTEGER: i32 = i32::MIN;

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

trait CumValue: Copy {
    fn missing() -> Self;
    fn zero() -> Self;
    fn is_missing(self) -> bool;
    fn is_less(self, other: Self) -> bool;
}

impl CumValue for f64 {
    fn missing() -> Self {
        f64::NAN
    }

    fn zero() -> Self {
        0.0
    }

    fn is_missing(self) -> bool {
        self.is_nan()
    }

    fn is_less(self, other: Self) -> bool {
        self < other
    }
}

impl CumValue for i32 {
    fn missing() -> Self {
        NA_INTEGER
    }

    fn zero() -> Self {
        0
    }

    fn is_missing(self) -> bool {
        self == NA_INTEGER
    }

    fn is_less(self, other: Self) -> bool {
        self < other
    }
}

/// Cumulative minimum of each row. `x` has length `nrow * ncol`.
///
/// `column_major` means element `(r, c)` lives at `r + c * nrow`, which is
/// how R stores a matrix. Otherwise element `(r, c)` lives at `r * ncol + c`.
/// The returned vector is row-major with shape `(selected rows, selected cols)`.
pub fn row_cummins(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    column_major: bool,
    rows: Index<'_>,
    cols: Index<'_>,
) -> Result<(Vec<f64>, usize, usize), String> {
    cummins(x, nrow, ncol, column_major, rows, cols, true)
}

/// Cumulative minimum of each column. Layout and subscripts match [`row_cummins`].
pub fn col_cummins(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    column_major: bool,
    rows: Index<'_>,
    cols: Index<'_>,
) -> Result<(Vec<f64>, usize, usize), String> {
    cummins(x, nrow, ncol, column_major, rows, cols, false)
}

/// Integer cumulative minimum of each row.
///
/// Logical input uses this path too: the C dispatcher calls `rowCummins_int`
/// for both, and a logical value is 0 or 1. `i32::MIN` is R's NA.
pub fn row_cummins_i32(
    x: &[i32],
    nrow: usize,
    ncol: usize,
    column_major: bool,
    rows: Index<'_>,
    cols: Index<'_>,
) -> Result<(Vec<i32>, usize, usize), String> {
    cummins(x, nrow, ncol, column_major, rows, cols, true)
}

/// Integer cumulative minimum of each column. See [`row_cummins_i32`].
pub fn col_cummins_i32(
    x: &[i32],
    nrow: usize,
    ncol: usize,
    column_major: bool,
    rows: Index<'_>,
    cols: Index<'_>,
) -> Result<(Vec<i32>, usize, usize), String> {
    cummins(x, nrow, ncol, column_major, rows, cols, false)
}

fn cummins<T: CumValue>(
    x: &[T],
    nrow: usize,
    ncol: usize,
    column_major: bool,
    rows: Index<'_>,
    cols: Index<'_>,
    by_row: bool,
) -> Result<(Vec<T>, usize, usize), String> {
    let Some(len) = nrow.checked_mul(ncol) else {
        return Err("Argument 'dim.' does not match length of argument 'x'".to_string());
    };
    if len != x.len() {
        return Err(format!(
            "Argument 'dim.' does not match length of argument 'x': {nrow} * {ncol} != {}",
            x.len()
        ));
    }

    let row_sub = resolve(rows, nrow)?;
    let col_sub = resolve(cols, ncol)?;
    let out_nrow = row_sub.len;
    let out_ncol = col_sub.len;
    let Some(n_out) = out_nrow.checked_mul(out_ncol) else {
        return Err("result dimensions overflow".to_string());
    };
    // `allocMatrix` zero-fills. An empty margin returns before any write.
    let mut ans = vec![T::zero(); n_out];
    if out_nrow == 0 || out_ncol == 0 {
        return Ok((ans, out_nrow, out_ncol));
    }

    if by_row {
        let col0 = at(&col_sub, 0);
        let mut ok = vec![false; out_nrow];
        let mut running = vec![T::missing(); out_nrow];
        for r in 0..out_nrow {
            let value = load(x, at(&row_sub, r), col0, nrow, ncol, column_major);
            if value.is_missing() {
                ans[r * out_ncol] = T::missing();
            } else {
                ok[r] = true;
                running[r] = value;
                ans[r * out_ncol] = value;
            }
        }
        for c in 1..out_ncol {
            let col = at(&col_sub, c);
            for r in 0..out_nrow {
                let dest = r * out_ncol + c;
                if !ok[r] {
                    ans[dest] = T::missing();
                    continue;
                }
                let value = load(x, at(&row_sub, r), col, nrow, ncol, column_major);
                if value.is_missing() {
                    ok[r] = false;
                    ans[dest] = T::missing();
                } else if value.is_less(running[r]) {
                    running[r] = value;
                    ans[dest] = value;
                } else {
                    ans[dest] = running[r];
                }
            }
        }
    } else {
        for c in 0..out_ncol {
            let col = at(&col_sub, c);
            let first = load(x, at(&row_sub, 0), col, nrow, ncol, column_major);
            let mut ok = !first.is_missing();
            let mut running = if ok { first } else { T::missing() };
            ans[c] = running;
            for r in 1..out_nrow {
                let dest = r * out_ncol + c;
                if !ok {
                    ans[dest] = T::missing();
                    continue;
                }
                let value = load(x, at(&row_sub, r), col, nrow, ncol, column_major);
                if value.is_missing() {
                    ok = false;
                    ans[dest] = T::missing();
                } else if value.is_less(running) {
                    running = value;
                    ans[dest] = value;
                } else {
                    ans[dest] = running;
                }
            }
        }
    }
    Ok((ans, out_nrow, out_ncol))
}

#[inline]
fn at(sub: &Subset, i: usize) -> i64 {
    if sub.all { i as i64 } else { sub.index[i] }
}

#[inline]
fn load<T: CumValue>(
    x: &[T],
    row: i64,
    col: i64,
    nrow: usize,
    ncol: usize,
    column_major: bool,
) -> T {
    if row < 0 || col < 0 {
        return T::missing();
    }
    let row = row as usize;
    let col = col as usize;
    if row >= nrow || col >= ncol {
        return T::missing();
    }
    let idx = if column_major {
        row + col * nrow
    } else {
        row * ncol + col
    };
    x[idx]
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
    use numpy::ndarray::Array2;
    use numpy::{IntoPyArray, PyArray2, PyReadonlyArray1};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::{Index, col_cummins, col_cummins_i32, row_cummins, row_cummins_i32};

    fn slice_of<'a>(
        values: &'a Option<PyReadonlyArray1<'a, f64>>,
    ) -> PyResult<Option<&'a [f64]>> {
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

    fn indexes<'a>(
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
    fn cummins_f64<'py>(
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
    ) -> PyResult<Bound<'py, PyArray2<f64>>> {
        let x_slice = x
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        let (rows_index, cols_index) = indexes(&rows, rows_logical, &cols, cols_logical)?;
        let (values, out_nrow, out_ncol) = if by_row {
            row_cummins(
                x_slice,
                nrow,
                ncol,
                column_major,
                rows_index,
                cols_index,
            )
        } else {
            col_cummins(
                x_slice,
                nrow,
                ncol,
                column_major,
                rows_index,
                cols_index,
            )
        }
        .map_err(PyValueError::new_err)?;
        let matrix = Array2::from_shape_vec((out_nrow, out_ncol), values)
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        Ok(matrix.into_pyarray(py))
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
    fn cummins_i32<'py>(
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
    ) -> PyResult<Bound<'py, PyArray2<i32>>> {
        let x_slice = x
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        let (rows_index, cols_index) = indexes(&rows, rows_logical, &cols, cols_logical)?;
        let (values, out_nrow, out_ncol) = if by_row {
            row_cummins_i32(
                x_slice,
                nrow,
                ncol,
                column_major,
                rows_index,
                cols_index,
            )
        } else {
            col_cummins_i32(
                x_slice,
                nrow,
                ncol,
                column_major,
                rows_index,
                cols_index,
            )
        }
        .map_err(PyValueError::new_err)?;
        let matrix = Array2::from_shape_vec((out_nrow, out_ncol), values)
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        Ok(matrix.into_pyarray(py))
    }

    #[pymodule]
    fn rowcummins(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(cummins_f64, m)?)?;
        m.add_function(wrap_pyfunction!(cummins_i32, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{Index, col_cummins, row_cummins, row_cummins_i32};

    fn col_major_1_to_12() -> Vec<f64> {
        (1..=12).map(|v| v as f64).collect()
    }

    #[test]
    fn row_and_column_mins_of_a_small_matrix() {
        let x = col_major_1_to_12();
        let (rows, nrow, ncol) =
            row_cummins(&x, 4, 3, true, Index::All, Index::All).unwrap();
        assert_eq!((nrow, ncol), (4, 3));
        assert_eq!(
            rows,
            vec![1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 3.0, 3.0, 3.0, 4.0, 4.0, 4.0]
        );
        let (cols, _, _) = col_cummins(&x, 4, 3, true, Index::All, Index::All).unwrap();
        assert_eq!(
            cols,
            vec![1.0, 5.0, 9.0, 1.0, 5.0, 9.0, 1.0, 5.0, 9.0, 1.0, 5.0, 9.0]
        );
    }

    #[test]
    fn row_major_layout_reads_the_printed_matrix() {
        let x = vec![
            1.0, 5.0, 9.0, 2.0, 6.0, 10.0, 3.0, 7.0, 11.0, 4.0, 8.0, 12.0,
        ];
        let (rows, _, _) = row_cummins(&x, 4, 3, false, Index::All, Index::All).unwrap();
        assert_eq!(
            rows,
            vec![1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 3.0, 3.0, 3.0, 4.0, 4.0, 4.0]
        );
    }

    #[test]
    fn missing_double_stops_the_run() {
        // Column-major:
        // 1 NA 9
        // 2  6 10
        // 4  1  5
        let x = vec![1.0, 2.0, 4.0, f64::NAN, 6.0, 1.0, 9.0, 10.0, 5.0];
        let (rows, _, _) = row_cummins(&x, 3, 3, true, Index::All, Index::All).unwrap();
        assert_eq!(rows[0], 1.0);
        assert!(rows[1].is_nan() && rows[2].is_nan());
        assert_eq!(&rows[3..6], &[2.0, 2.0, 2.0]);
        assert_eq!(&rows[6..9], &[4.0, 1.0, 1.0]);

        let (cols, _, _) = col_cummins(&x, 3, 3, true, Index::All, Index::All).unwrap();
        // Row-major result:
        // 1 NA 9
        // 1 NA 9
        // 1 NA 5
        assert_eq!(cols[0], 1.0);
        assert!(cols[1].is_nan());
        assert_eq!(cols[2], 9.0);
        assert_eq!(cols[3], 1.0);
        assert!(cols[4].is_nan());
        assert_eq!(cols[5], 9.0);
        assert_eq!(cols[6], 1.0);
        assert!(cols[7].is_nan());
        assert_eq!(cols[8], 5.0);
    }

    #[test]
    fn integer_na_stops_the_run_and_logical_values_are_ints() {
        let na = i32::MIN;
        let x = vec![1, 0, 1, na, 1, 0];
        let (rows, _, _) = row_cummins_i32(&x, 2, 3, true, Index::All, Index::All).unwrap();
        assert_eq!(&rows[..3], &[1, 1, 1]);
        assert_eq!(rows[3], 0);
        assert_eq!(rows[4], na);
        assert_eq!(rows[5], na);
    }

    #[test]
    fn rows_subset_keeps_index_order() {
        let x = col_major_1_to_12();
        let rows = [3.0, 0.0, 1.0];
        let (got, nrow, ncol) = row_cummins(
            &x,
            4,
            3,
            true,
            Index::Numeric(&rows),
            Index::All,
        )
        .unwrap();
        assert_eq!((nrow, ncol), (2, 3));
        assert_eq!(got, vec![3.0, 3.0, 3.0, 1.0, 1.0, 1.0]);

        let (down, _, _) = col_cummins(
            &x,
            4,
            3,
            true,
            Index::Numeric(&rows),
            Index::All,
        )
        .unwrap();
        assert_eq!(down, vec![3.0, 7.0, 11.0, 1.0, 5.0, 9.0]);
    }

    #[test]
    fn strict_less_keeps_the_earlier_zero_sign() {
        let (kept, _, _) = row_cummins(&[0.0, -0.0], 1, 2, true, Index::All, Index::All).unwrap();
        assert_eq!(kept[0].to_bits(), 0.0f64.to_bits());
        assert_eq!(kept[1].to_bits(), 0.0f64.to_bits());
        let (kept, _, _) = row_cummins(&[-0.0, 0.0], 1, 2, true, Index::All, Index::All).unwrap();
        assert_eq!(kept[0].to_bits(), (-0.0f64).to_bits());
        assert_eq!(kept[1].to_bits(), (-0.0f64).to_bits());
    }

    #[test]
    fn infinities_compare_and_an_empty_margin_is_empty() {
        let x = [f64::INFINITY, 1.0, f64::NEG_INFINITY];
        let (got, _, _) = row_cummins(&x, 1, 3, true, Index::All, Index::All).unwrap();
        assert_eq!(got, vec![f64::INFINITY, 1.0, f64::NEG_INFINITY]);

        let (empty, nrow, ncol) = row_cummins(&[], 0, 3, true, Index::All, Index::All).unwrap();
        assert!(empty.is_empty());
        assert_eq!((nrow, ncol), (0, 3));
    }

    #[test]
    fn out_of_bounds_and_mixed_signs_error() {
        let x = col_major_1_to_12();
        let oob = [5.0];
        let err = row_cummins(&x, 4, 3, true, Index::Numeric(&oob), Index::All).unwrap_err();
        assert_eq!(err, "subscript out of bounds");
        let mixed = [-1.0, 1.0];
        let err = col_cummins(&x, 4, 3, true, Index::All, Index::Numeric(&mixed)).unwrap_err();
        assert_eq!(err, "only 0's may be mixed with negative subscripts");
    }
}
