//! Row and column means, ported from matrixStats `src/rowMeans2.c`.
//!
//! The C routine sums in `LDOUBLE` and, when `refine` is set, adds a second
//! pass of residuals. This build of matrixStats 1.5.0 behaves as double
//! precision, so both passes use `f64`. Index rules follow `validateIndices`.

/// Missing subscript. Valid data indices are non-negative.
const NA_INDEX: i64 = i64::MIN;

/// Same cadence as the C `jj % 1048576 == 0` NA check.
const CHECK_EVERY: usize = 1_048_576;

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

/// Mean of each row. `x` is length `nrow * ncol`.
///
/// `column_major` means element `(r, c)` lives at `r + c * nrow`, which is
/// how R stores a matrix. Otherwise element `(r, c)` lives at `r * ncol + c`.
pub fn row_means2(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    column_major: bool,
    rows: Index<'_>,
    cols: Index<'_>,
    na_rm: bool,
    refine: bool,
) -> Result<Vec<f64>, String> {
    means2(x, nrow, ncol, column_major, rows, cols, na_rm, refine, true)
}

/// Mean of each column. Layout and subscripts match [`row_means2`].
pub fn col_means2(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    column_major: bool,
    rows: Index<'_>,
    cols: Index<'_>,
    na_rm: bool,
    refine: bool,
) -> Result<Vec<f64>, String> {
    means2(x, nrow, ncol, column_major, rows, cols, na_rm, refine, false)
}

fn means2(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    column_major: bool,
    rows: Index<'_>,
    cols: Index<'_>,
    na_rm: bool,
    refine: bool,
    by_row: bool,
) -> Result<Vec<f64>, String> {
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
    if row_sub.all && col_sub.all {
        return Ok(means_all(
            x,
            nrow,
            ncol,
            column_major,
            na_rm,
            refine,
            by_row,
        ));
    }
    let row_stride: i64 = if column_major { 1 } else { ncol as i64 };
    let col_stride: i64 = if column_major { nrow as i64 } else { 1 };

    // After the C `byrow` swap, the outer margin is the one being returned.
    let (outer, inner, outer_is_row) = if by_row {
        (row_sub, col_sub, true)
    } else {
        (col_sub, row_sub, false)
    };

    let mut ans = vec![0.0; outer.len];
    for ii in 0..outer.len {
        let outer_at = if outer.all {
            ii as i64
        } else {
            outer.index[ii]
        };
        let mut sum = 0.0;
        let mut count: u64 = 0;
        for jj in 0..inner.len {
            let value = value_at(
                x,
                outer_at,
                inner_at(&inner, jj),
                outer_is_row,
                row_stride,
                col_stride,
            );
            if !na_rm {
                sum += value;
                count += 1;
                if jj % CHECK_EVERY == 0 && sum.is_nan() {
                    break;
                }
            } else if !value.is_nan() {
                sum += value;
                count += 1;
            }
        }

        let avg = if sum > f64::MAX {
            f64::INFINITY
        } else if sum < -f64::MAX {
            f64::NEG_INFINITY
        } else {
            let mut avg = sum / count as f64;
            if refine {
                let mut residual = 0.0;
                for jj in 0..inner.len {
                    let value = value_at(
                        x,
                        outer_at,
                        inner_at(&inner, jj),
                        outer_is_row,
                        row_stride,
                        col_stride,
                    );
                    if !na_rm {
                        residual += value - avg;
                        if jj % CHECK_EVERY == 0 && residual.is_nan() {
                            break;
                        }
                    } else if !value.is_nan() {
                        residual += value - avg;
                    }
                }
                avg += residual / count as f64;
            }
            avg
        };
        ans[ii] = avg;
    }
    Ok(ans)
}

/// Full-margin means. Element order matches the general loop.
fn means_all(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    column_major: bool,
    na_rm: bool,
    refine: bool,
    by_row: bool,
) -> Vec<f64> {
    if by_row {
        let mut ans = vec![0.0; nrow];
        for i in 0..nrow {
            ans[i] = if column_major {
                mean_strided(x, i, nrow, ncol, na_rm, refine)
            } else {
                let start = i * ncol;
                mean_contiguous(&x[start..start + ncol], na_rm, refine)
            };
        }
        ans
    } else {
        let mut ans = vec![0.0; ncol];
        for j in 0..ncol {
            ans[j] = if column_major {
                let start = j * nrow;
                mean_contiguous(&x[start..start + nrow], na_rm, refine)
            } else {
                mean_strided(x, j, ncol, nrow, na_rm, refine)
            };
        }
        ans
    }
}

fn mean_contiguous(values: &[f64], na_rm: bool, refine: bool) -> f64 {
    let mut sum = 0.0;
    let mut count = 0u64;
    if !na_rm {
        for (j, &value) in values.iter().enumerate() {
            sum += value;
            count += 1;
            if j % CHECK_EVERY == 0 && sum.is_nan() {
                break;
            }
        }
    } else {
        for &value in values {
            if !value.is_nan() {
                sum += value;
                count += 1;
            }
        }
    }
    if sum > f64::MAX {
        return f64::INFINITY;
    }
    if sum < -f64::MAX {
        return f64::NEG_INFINITY;
    }
    let mut avg = sum / count as f64;
    if refine {
        let mut residual = 0.0;
        if !na_rm {
            for (j, &value) in values.iter().enumerate() {
                residual += value - avg;
                if j % CHECK_EVERY == 0 && residual.is_nan() {
                    break;
                }
            }
        } else {
            for &value in values {
                if !value.is_nan() {
                    residual += value - avg;
                }
            }
        }
        avg += residual / count as f64;
    }
    avg
}

fn mean_strided(
    x: &[f64],
    start: usize,
    step: usize,
    n: usize,
    na_rm: bool,
    refine: bool,
) -> f64 {
    let mut sum = 0.0;
    let mut count = 0u64;
    if !na_rm {
        for j in 0..n {
            sum += x[start + j * step];
            count += 1;
            if j % CHECK_EVERY == 0 && sum.is_nan() {
                break;
            }
        }
    } else {
        for j in 0..n {
            let value = x[start + j * step];
            if !value.is_nan() {
                sum += value;
                count += 1;
            }
        }
    }
    if sum > f64::MAX {
        return f64::INFINITY;
    }
    if sum < -f64::MAX {
        return f64::NEG_INFINITY;
    }
    let mut avg = sum / count as f64;
    if refine {
        let mut residual = 0.0;
        if !na_rm {
            for j in 0..n {
                residual += x[start + j * step] - avg;
                if j % CHECK_EVERY == 0 && residual.is_nan() {
                    break;
                }
            }
        } else {
            for j in 0..n {
                let value = x[start + j * step];
                if !value.is_nan() {
                    residual += value - avg;
                }
            }
        }
        avg += residual / count as f64;
    }
    avg
}

fn inner_at(inner: &Subset, jj: usize) -> i64 {
    if inner.all {
        jj as i64
    } else {
        inner.index[jj]
    }
}

fn value_at(
    x: &[f64],
    outer_at: i64,
    inner_at: i64,
    outer_is_row: bool,
    row_stride: i64,
    col_stride: i64,
) -> f64 {
    let (row, col) = if outer_is_row {
        (outer_at, inner_at)
    } else {
        (inner_at, outer_at)
    };
    if row < 0 || col < 0 {
        return f64::NAN;
    }
    let idx = (row as i128) * (row_stride as i128) + (col as i128) * (col_stride as i128);
    if idx < 0 || idx >= x.len() as i128 {
        return f64::NAN;
    }
    x[idx as usize]
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

    use crate::{Index, col_means2, row_means2};

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
        na_rm=false,
        refine=true,
        by_row=true
    ))]
    fn means2<'py>(
        py: Python<'py>,
        x: PyReadonlyArray1<'py, f64>,
        nrow: usize,
        ncol: usize,
        column_major: bool,
        rows: Option<PyReadonlyArray1<'py, f64>>,
        rows_logical: bool,
        cols: Option<PyReadonlyArray1<'py, f64>>,
        cols_logical: bool,
        na_rm: bool,
        refine: bool,
        by_row: bool,
    ) -> PyResult<Bound<'py, numpy::PyArray1<f64>>> {
        let x_slice = x
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        let rows_slice = slice_of(&rows)?;
        let cols_slice = slice_of(&cols)?;
        let rows_index = index_of(rows_slice, rows_logical)?;
        let cols_index = index_of(cols_slice, cols_logical)?;
        let ans = if by_row {
            row_means2(
                x_slice,
                nrow,
                ncol,
                column_major,
                rows_index,
                cols_index,
                na_rm,
                refine,
            )
        } else {
            col_means2(
                x_slice,
                nrow,
                ncol,
                column_major,
                rows_index,
                cols_index,
                na_rm,
                refine,
            )
        }
        .map_err(PyValueError::new_err)?;
        Ok(ans.into_pyarray(py))
    }

    #[pymodule]
    fn rowmeans2(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(means2, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{Index, col_means2, row_means2};

    fn col_major_1_to_12() -> Vec<f64> {
        (1..=12).map(|v| v as f64).collect()
    }

    #[test]
    fn row_and_column_means_of_a_small_matrix() {
        let x = col_major_1_to_12();
        let rows = row_means2(&x, 4, 3, true, Index::All, Index::All, false, true).unwrap();
        assert_eq!(rows, vec![5.0, 6.0, 7.0, 8.0]);
        let cols = col_means2(&x, 4, 3, true, Index::All, Index::All, false, true).unwrap();
        assert_eq!(cols, vec![2.5, 6.5, 10.5]);
    }

    #[test]
    fn row_major_layout_reads_the_printed_matrix() {
        // Printed matrix is the same 4 by 3, stored row by row.
        let x = vec![1.0, 5.0, 9.0, 2.0, 6.0, 10.0, 3.0, 7.0, 11.0, 4.0, 8.0, 12.0];
        let rows = row_means2(&x, 4, 3, false, Index::All, Index::All, false, true).unwrap();
        assert_eq!(rows, vec![5.0, 6.0, 7.0, 8.0]);
    }

    #[test]
    fn positive_subscripts_drop_zeros_and_keep_duplicates() {
        let x = col_major_1_to_12();
        let rows = [3.0, 0.0, 0.0, 1.0, 3.0];
        let got = row_means2(
            &x,
            4,
            3,
            true,
            Index::Numeric(&rows),
            Index::All,
            false,
            true,
        )
        .unwrap();
        assert_eq!(got, vec![7.0, 5.0, 7.0]);
    }

    #[test]
    fn negative_subscripts_exclude() {
        let x = col_major_1_to_12();
        let rows = [-4.0, 0.0, 0.0, -3.0, -1.0];
        let got = row_means2(
            &x,
            4,
            3,
            true,
            Index::Numeric(&rows),
            Index::All,
            false,
            false,
        )
        .unwrap();
        assert_eq!(got, vec![6.0]);
    }

    #[test]
    fn fractional_subscripts_truncate_after_subtracting_one() {
        let x = col_major_1_to_12();
        let rows = [1.9, 2.2];
        let got = row_means2(
            &x,
            4,
            3,
            true,
            Index::Numeric(&rows),
            Index::All,
            false,
            false,
        )
        .unwrap();
        assert_eq!(got, vec![5.0, 6.0]);
    }

    #[test]
    fn logical_subscripts_are_recycled() {
        let x = col_major_1_to_12();
        let rows = [0.0, 1.0];
        let got = row_means2(
            &x,
            4,
            3,
            true,
            Index::Logical(&rows),
            Index::All,
            false,
            false,
        )
        .unwrap();
        assert_eq!(got, vec![6.0, 8.0]);
    }

    #[test]
    fn missing_index_is_a_missing_mean() {
        let x = col_major_1_to_12();
        let rows = [f64::NAN, 0.0, 2.0];
        let got = row_means2(
            &x,
            4,
            3,
            true,
            Index::Numeric(&rows),
            Index::All,
            false,
            true,
        )
        .unwrap();
        assert!(got[0].is_nan());
        assert_eq!(got[1], 6.0);
    }

    #[test]
    fn refine_matches_the_double_residual_pass() {
        let x = [1e8, 1.0, -1e8];
        let refined = row_means2(&x, 1, 3, true, Index::All, Index::All, false, true).unwrap();
        let plain = row_means2(&x, 1, 3, true, Index::All, Index::All, false, false).unwrap();
        assert!((refined[0] - 0.33333333830038703).abs() < 1e-18);
        assert!((plain[0] - (1.0 / 3.0)).abs() < 1e-18);
    }

    #[test]
    fn na_rm_skips_nan_and_an_empty_margin_is_nan() {
        let x = [f64::NAN, 1.0, 2.0, f64::NAN];
        let kept = row_means2(&x, 2, 2, true, Index::All, Index::All, true, true).unwrap();
        assert_eq!(kept, vec![2.0, 1.0]);
        let poisoned = row_means2(&x, 2, 2, true, Index::All, Index::All, false, true).unwrap();
        assert!(poisoned.iter().all(|v| v.is_nan()));

        let empty_cols = row_means2(&[], 3, 0, true, Index::All, Index::All, false, true).unwrap();
        assert_eq!(empty_cols.len(), 3);
        assert!(empty_cols.iter().all(|v| v.is_nan()));
        let empty_rows = col_means2(&[], 0, 3, true, Index::All, Index::All, false, true).unwrap();
        assert_eq!(empty_rows.len(), 3);
        assert!(empty_rows.iter().all(|v| v.is_nan()));
    }

    #[test]
    fn out_of_bounds_and_mixed_signs_error() {
        let x = col_major_1_to_12();
        let oob = [4.0, 5.0, 6.0, 7.0, 8.0, 9.0];
        let err = row_means2(
            &x,
            4,
            3,
            true,
            Index::Numeric(&oob),
            Index::All,
            false,
            false,
        )
        .unwrap_err();
        assert_eq!(err, "subscript out of bounds");
        let mixed = [-1.0_f64, 1.0];
        let err = row_means2(
            &x,
            4,
            3,
            true,
            Index::Numeric(&mixed),
            Index::All,
            false,
            false,
        )
        .unwrap_err();
        assert_eq!(err, "only 0's may be mixed with negative subscripts");
    }
}
