//! Row and column sums, ported from matrixStats `src/rowSums2.c`.
//!
//! `rowSums2` calls the C routine with `byrow = TRUE` and `colSums2` with
//! `byrow = FALSE`. Both pass `hasNA = TRUE`. The matrix is stored
//! column-major, as in R. `rows` and `cols` follow `validateIndices`:
//! missing means every position, values are 1-based, zeros are dropped,
//! and negatives exclude. A missing index contributes a quiet NaN, which
//! is this port's double NA.

/// Positions along one margin.
///
/// `All` is R's `NULL`. `At` is a validated list of 0-based positions;
/// `None` is an NA index.
#[derive(Clone, Debug, PartialEq)]
pub enum Subset {
    All,
    At(Vec<Option<usize>>),
}

/// Sum each row. `x` is column-major with `nrow * ncol` values.
pub fn row_sums2(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    rows: &Subset,
    cols: &Subset,
    na_rm: bool,
) -> Result<Vec<f64>, String> {
    sums2(x, nrow, ncol, rows, cols, na_rm, true)
}

/// Sum each column. `x` is column-major with `nrow * ncol` values.
pub fn col_sums2(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    rows: &Subset,
    cols: &Subset,
    na_rm: bool,
) -> Result<Vec<f64>, String> {
    sums2(x, nrow, ncol, rows, cols, na_rm, false)
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

/// 1-based real indices. NaN is an NA index. Both infinities are NA indices
/// and are flagged as missing, so the sum reads a NaN instead of walking
/// off the matrix.
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

fn sums2(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    rows: &Subset,
    cols: &Subset,
    na_rm: bool,
    byrow: bool,
) -> Result<Vec<f64>, String> {
    let Some(n) = nrow.checked_mul(ncol) else {
        return Err("dimension overflow".to_string());
    };
    if x.len() != n {
        return Err("x length does not match nrow * ncol".to_string());
    }

    if matches!(rows, Subset::All) && matches!(cols, Subset::All) {
        return Ok(sums_full(x, nrow, ncol, na_rm, byrow));
    }

    let row_pos = expand(rows, nrow);
    let col_pos = expand(cols, ncol);
    let nrows = row_pos.len();
    let ncols = col_pos.len();

    if byrow {
        let mut row_sum = vec![0.0; nrows];
        for &col in &col_pos {
            let offset = col.map(|c| c * nrow);
            for (ii, &row) in row_pos.iter().enumerate() {
                let value = value_at(x, offset, row);
                add_value(&mut row_sum[ii], value, na_rm);
            }
        }
        Ok(row_sum)
    } else {
        let mut ans = Vec::with_capacity(ncols);
        for &col in &col_pos {
            let mut col_sum = 0.0;
            let offset = col.map(|c| c * nrow);
            for &row in &row_pos {
                let value = value_at(x, offset, row);
                add_value(&mut col_sum, value, na_rm);
            }
            ans.push(col_sum);
        }
        Ok(ans)
    }
}

/// `x` is row-major: element `(row, col)` is at `row * ncol + col`.
fn sums_row_major(x: &[f64], nrow: usize, ncol: usize, na_rm: bool, byrow: bool) -> Vec<f64> {
    if byrow {
        let mut ans = Vec::with_capacity(nrow);
        for row in 0..nrow {
            let offset = row * ncol;
            ans.push(sum_column(&x[offset..offset + ncol], na_rm));
        }
        ans
    } else {
        let mut ans = vec![0.0; ncol];
        for row in 0..nrow {
            let offset = row * ncol;
            if na_rm {
                for col in 0..ncol {
                    let value = x[offset + col];
                    if !value.is_nan() {
                        ans[col] += value;
                    }
                }
            } else {
                for col in 0..ncol {
                    ans[col] += x[offset + col];
                }
            }
        }
        ans
    }
}

fn sums_full(x: &[f64], nrow: usize, ncol: usize, na_rm: bool, byrow: bool) -> Vec<f64> {
    if byrow {
        let mut row_sum = vec![0.0; nrow];
        for col in 0..ncol {
            let offset = col * nrow;
            if na_rm {
                for row in 0..nrow {
                    let value = x[offset + row];
                    if !value.is_nan() {
                        row_sum[row] += value;
                    }
                }
            } else {
                for row in 0..nrow {
                    row_sum[row] += x[offset + row];
                }
            }
        }
        row_sum
    } else {
        let mut ans = Vec::with_capacity(ncol);
        for col in 0..ncol {
            let offset = col * nrow;
            ans.push(sum_column(&x[offset..offset + nrow], na_rm));
        }
        ans
    }
}

/// Several partial sums, then one total. A single running total is limited by
/// add latency; the split still drops NaN when `na_rm` is set.
fn sum_column(col: &[f64], na_rm: bool) -> f64 {
    const LANES: usize = 8;
    let mut lanes = [0.0; LANES];
    let mut chunks = col.chunks_exact(LANES);
    for chunk in chunks.by_ref() {
        for (lane, &value) in lanes.iter_mut().zip(chunk.iter()) {
            if !na_rm || !value.is_nan() {
                *lane += value;
            }
        }
    }
    let mut total = 0.0;
    for lane in lanes {
        total += lane;
    }
    for &value in chunks.remainder() {
        if !na_rm || !value.is_nan() {
            total += value;
        }
    }
    total
}

fn expand(subset: &Subset, n: usize) -> Vec<Option<usize>> {
    match subset {
        Subset::All => (0..n).map(Some).collect(),
        Subset::At(idx) => idx.clone(),
    }
}

fn value_at(x: &[f64], col_offset: Option<usize>, row: Option<usize>) -> f64 {
    match (col_offset, row) {
        (Some(offset), Some(row)) => x[offset + row],
        _ => f64::NAN,
    }
}

fn add_value(sum: &mut f64, value: f64, na_rm: bool) {
    if !na_rm {
        *sum += value;
    } else if !value.is_nan() {
        *sum += value;
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

    use crate::{validate_int, validate_logical, validate_real, Subset};

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

    fn subset_from_py(obj: Option<&Bound<'_, PyAny>>, max_idx: usize, what: &str) -> PyResult<Subset> {
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
        Err(PyValueError::new_err(format!(
            "{what} can only be integer, numeric, or logical"
        )))
    }

    fn sums_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        rows: Option<Bound<'py, PyAny>>,
        cols: Option<Bound<'py, PyAny>>,
        na_rm: bool,
        byrow: bool,
    ) -> PyResult<Bound<'py, numpy::PyArray1<f64>>> {
        let view = x.as_array();
        let (nrow, ncol) = view.dim();
        let row_subset = subset_from_py(rows.as_ref(), nrow, "rows")?;
        let col_subset = subset_from_py(cols.as_ref(), ncol, "cols")?;
        let (stride_row, stride_col) = if view.strides().len() == 2 {
            (view.strides()[0], view.strides()[1])
        } else {
            (0, 0)
        };
        let full = matches!(row_subset, Subset::All) && matches!(col_subset, Subset::All);
        let ans = if full {
            if let Some(slice) = view.as_slice_memory_order() {
                if slice.len() == nrow * ncol && stride_row == 1 && stride_col == nrow as isize {
                    Ok(crate::sums_full(slice, nrow, ncol, na_rm, byrow))
                } else if slice.len() == nrow * ncol
                    && stride_row == ncol as isize
                    && stride_col == 1
                {
                    Ok(crate::sums_row_major(slice, nrow, ncol, na_rm, byrow))
                } else {
                    let flat = owned_column_major(view);
                    crate::sums2(&flat, nrow, ncol, &row_subset, &col_subset, na_rm, byrow)
                }
            } else {
                let flat = owned_column_major(view);
                crate::sums2(&flat, nrow, ncol, &row_subset, &col_subset, na_rm, byrow)
            }
        } else {
            let flat = owned_column_major(view);
            crate::sums2(&flat, nrow, ncol, &row_subset, &col_subset, na_rm, byrow)
        }
        .map_err(PyValueError::new_err)?;
        Ok(ans.into_pyarray(py))
    }

    #[pyfunction]
    #[pyo3(name = "row_sums2", signature = (x, rows=None, cols=None, na_rm=false))]
    fn row_sums2_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        rows: Option<Bound<'py, PyAny>>,
        cols: Option<Bound<'py, PyAny>>,
        na_rm: bool,
    ) -> PyResult<Bound<'py, numpy::PyArray1<f64>>> {
        sums_py(py, x, rows, cols, na_rm, true)
    }

    #[pyfunction]
    #[pyo3(name = "col_sums2", signature = (x, rows=None, cols=None, na_rm=false))]
    fn col_sums2_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        rows: Option<Bound<'py, PyAny>>,
        cols: Option<Bound<'py, PyAny>>,
        na_rm: bool,
    ) -> PyResult<Bound<'py, numpy::PyArray1<f64>>> {
        sums_py(py, x, rows, cols, na_rm, false)
    }

    #[pymodule]
    fn rowsums2(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(row_sums2_py, m)?)?;
        m.add_function(wrap_pyfunction!(col_sums2_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{col_sums2, row_sums2, validate_int, validate_logical, validate_real, Subset};

    fn matrix() -> Vec<f64> {
        // Printed layout:
        // 1 3 5
        // 2 4 6
        vec![1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    }

    #[test]
    fn full_sums_match_the_printed_matrix() {
        let x = matrix();
        let rows = row_sums2(&x, 2, 3, &Subset::All, &Subset::All, false).unwrap();
        let cols = col_sums2(&x, 2, 3, &Subset::All, &Subset::All, false).unwrap();
        assert_eq!(rows, vec![9.0, 12.0]);
        assert_eq!(cols, vec![3.0, 7.0, 11.0]);
    }

    #[test]
    fn na_rm_skips_nan_and_all_nan_margins_stay_zero() {
        let mut x = matrix();
        x[0] = f64::NAN;
        x[2] = f64::NAN;
        x[4] = f64::NAN;
        let kept = row_sums2(&x, 2, 3, &Subset::All, &Subset::All, true).unwrap();
        let dropped = row_sums2(&x, 2, 3, &Subset::All, &Subset::All, false).unwrap();
        assert_eq!(kept, vec![0.0, 12.0]);
        assert!(dropped[0].is_nan());
        assert_eq!(dropped[1], 12.0);

        let all_nan = vec![f64::NAN; 6];
        let rows = row_sums2(&all_nan, 2, 3, &Subset::All, &Subset::All, true).unwrap();
        let cols = col_sums2(&all_nan, 2, 3, &Subset::All, &Subset::All, true).unwrap();
        assert_eq!(rows, vec![0.0, 0.0]);
        assert_eq!(cols, vec![0.0, 0.0, 0.0]);
    }

    #[test]
    fn empty_margins_match_r() {
        let x = matrix();
        let no_rows = Subset::At(Vec::new());
        let no_cols = Subset::At(Vec::new());
        assert!(row_sums2(&x, 2, 3, &no_rows, &Subset::All, false)
            .unwrap()
            .is_empty());
        assert_eq!(
            row_sums2(&x, 2, 3, &Subset::All, &no_cols, false).unwrap(),
            vec![0.0, 0.0]
        );
        assert_eq!(
            col_sums2(&x, 2, 3, &no_rows, &Subset::All, false).unwrap(),
            vec![0.0, 0.0, 0.0]
        );
        assert!(col_sums2(&x, 2, 3, &Subset::All, &no_cols, false)
            .unwrap()
            .is_empty());

        let empty = col_sums2(&[], 0, 3, &Subset::All, &Subset::All, false).unwrap();
        assert_eq!(empty, vec![0.0, 0.0, 0.0]);
        let empty_rows = row_sums2(&[], 4, 0, &Subset::All, &Subset::All, false).unwrap();
        assert_eq!(empty_rows, vec![0.0, 0.0, 0.0, 0.0]);
    }

    #[test]
    fn subsets_are_one_based_and_keep_duplicates() {
        let x = matrix();
        let rows = validate_int(&[1, 1], 2).unwrap();
        let cols = validate_int(&[1, 3], 3).unwrap();
        assert_eq!(
            row_sums2(&x, 2, 3, &rows, &Subset::All, false).unwrap(),
            vec![9.0, 9.0]
        );
        assert_eq!(
            row_sums2(&x, 2, 3, &Subset::All, &cols, false).unwrap(),
            vec![6.0, 8.0]
        );
        assert_eq!(
            col_sums2(&x, 2, 3, &Subset::All, &cols, false).unwrap(),
            vec![3.0, 11.0]
        );
    }

    #[test]
    fn zeros_negatives_and_na_indices() {
        let x = matrix();
        let rows = validate_int(&[0, 2, 0], 2).unwrap();
        assert_eq!(
            row_sums2(&x, 2, 3, &rows, &Subset::All, false).unwrap(),
            vec![12.0]
        );
        let excluded = validate_int(&[-2], 2).unwrap();
        assert_eq!(
            row_sums2(&x, 2, 3, &excluded, &Subset::All, false).unwrap(),
            vec![9.0]
        );
        let missing = validate_int(&[i32::MIN as i64, 2], 2).unwrap();
        let sums = row_sums2(&x, 2, 3, &missing, &Subset::All, false).unwrap();
        assert!(sums[0].is_nan());
        assert_eq!(sums[1], 12.0);
        assert!(validate_int(&[1, 9], 2).is_err());
        assert!(validate_int(&[-1, 1], 2).is_err());
    }

    #[test]
    fn real_indices_truncate_toward_zero() {
        let rows = validate_real(&[1.9], 2).unwrap();
        assert_eq!(rows, Subset::At(vec![Some(0)]));
        assert!(validate_real(&[2.1], 2).is_err());
        let excluded = validate_real(&[-1.2], 2).unwrap();
        assert_eq!(excluded, Subset::At(vec![Some(1)]));
        let missing = validate_real(&[f64::NAN, 2.0], 2).unwrap();
        assert_eq!(missing, Subset::At(vec![None, Some(1)]));
    }

    #[test]
    fn logical_indices_recycle() {
        assert_eq!(validate_logical(&[1], 2).unwrap(), Subset::All);
        assert_eq!(validate_logical(&[0], 2).unwrap(), Subset::At(vec![]));
        assert_eq!(
            validate_logical(&[0, 1], 2).unwrap(),
            Subset::At(vec![Some(1)])
        );
        assert_eq!(
            validate_logical(&[1, 0], 5).unwrap(),
            Subset::At(vec![Some(0), Some(2), Some(4)])
        );
        assert_eq!(
            validate_logical(&[0, 1, -1], 5).unwrap(),
            Subset::At(vec![Some(1), None, Some(4)])
        );
        assert!(validate_logical(&[1, 0, 1], 2).is_err());
    }
}
