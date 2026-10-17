//! Row order statistics, ported from matrixStats `src/rowOrderStats.c`.
//!
//! Each selected row is copied and partially sorted with R's `rPsort` or
//! `iPsort` (`X_PSORT` in the template). `psortKM.c` is a different export
//! and is not used here. `which` is the 1-based order after `asInteger`.
//! `rows` and `cols` follow `validateIndices`: missing means every position,
//! values are 1-based, zeros are dropped, and negatives exclude.
//!
//! The R wrapper rejects missing values in `x` before this routine runs.
//! An NA row or column index is an error when the other margin is non-empty.

/// R's integer NA.
const NA_INTEGER: i32 = i32::MIN;

/// 1-based subscript vector. `All` selects every position in order.
#[derive(Clone, Debug, PartialEq)]
pub enum Subset {
    All,
    /// 0-based positions. `None` is an NA index.
    At(Vec<Option<usize>>),
}

/// Order statistic of each row of a double matrix.
///
/// `x` is addressed with the given strides. Column-major storage, matching
/// R, uses `row_stride == 1` and `col_stride == nrow`. `which` is R's
/// `asInteger` result: the returned value is the `which`-th smallest in each
/// selected row, with `which` counted from 1.
pub fn row_order_stats_f64(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    row_stride: usize,
    col_stride: usize,
    rows: &Subset,
    cols: &Subset,
    which: i32,
) -> Result<Vec<f64>, String> {
    ensure_span(x.len(), nrow, ncol, row_stride, col_stride)?;
    let row_pos = positions(rows, nrow);
    let col_pos = positions(cols, ncol);
    let nrows = row_pos.len();
    let ncols = col_pos.len();
    if row_pos.iter().any(Option::is_none) && ncols > 0 {
        return Err("Argument 'rows' must not contain missing value".to_string());
    }
    if col_pos.iter().any(Option::is_none) && nrows > 0 {
        return Err("Argument 'cols' must not contain missing value".to_string());
    }
    let qq = order_index(which, ncols)?;
    let mut ans = vec![0.0; nrows];
    if nrows == 0 {
        return Ok(ans);
    }
    let mut values = vec![0.0; ncols];
    for (ii, row) in row_pos.iter().enumerate() {
        let row = row.expect("missing row index");
        for (jj, col) in col_pos.iter().enumerate() {
            let col = col.expect("missing column index");
            values[jj] = x[row * row_stride + col * col_stride];
        }
        r_psort(&mut values, qq);
        ans[ii] = values[qq];
    }
    Ok(ans)
}

/// Order statistic of each row of an integer matrix.
///
/// `i32::MIN` is R's NA. The R wrapper rejects it before this routine. The
/// result stays `i32`, matching the installed integer implementation.
pub fn row_order_stats_i32(
    x: &[i32],
    nrow: usize,
    ncol: usize,
    row_stride: usize,
    col_stride: usize,
    rows: &Subset,
    cols: &Subset,
    which: i32,
) -> Result<Vec<i32>, String> {
    ensure_span(x.len(), nrow, ncol, row_stride, col_stride)?;
    let row_pos = positions(rows, nrow);
    let col_pos = positions(cols, ncol);
    let nrows = row_pos.len();
    let ncols = col_pos.len();
    if row_pos.iter().any(Option::is_none) && ncols > 0 {
        return Err("Argument 'rows' must not contain missing value".to_string());
    }
    if col_pos.iter().any(Option::is_none) && nrows > 0 {
        return Err("Argument 'cols' must not contain missing value".to_string());
    }
    let qq = order_index(which, ncols)?;
    let mut ans = vec![0; nrows];
    if nrows == 0 {
        return Ok(ans);
    }
    let mut values = vec![0; ncols];
    for (ii, row) in row_pos.iter().enumerate() {
        let row = row.expect("missing row index");
        for (jj, col) in col_pos.iter().enumerate() {
            let col = col.expect("missing column index");
            values[jj] = x[row * row_stride + col * col_stride];
        }
        i_psort(&mut values, qq);
        ans[ii] = values[qq];
    }
    Ok(ans)
}

/// 1-based `which` after `asInteger`, checked against the selected length.
fn order_index(which: i32, n_selected: usize) -> Result<usize, String> {
    let qq = i64::from(which) - 1;
    if qq < 0 || qq as usize >= n_selected {
        return Err(format!("Argument 'which' is out of range: {}", qq + 1));
    }
    Ok(qq as usize)
}

/// R 4.5 `rcmp` with `nalast = true`. NaN sorts after every finite value.
fn rcmp(x: f64, y: f64) -> i32 {
    let nax = x.is_nan();
    let nay = y.is_nan();
    if nax && nay {
        return 0;
    }
    if nax {
        return 1;
    }
    if nay {
        return -1;
    }
    if x < y {
        return -1;
    }
    if x > y {
        return 1;
    }
    0
}

/// R 4.5 `icmp` with `nalast = true`. Integer NA sorts after every other int.
fn icmp(x: i32, y: i32) -> i32 {
    if x == NA_INTEGER && y == NA_INTEGER {
        return 0;
    }
    if x == NA_INTEGER {
        return 1;
    }
    if y == NA_INTEGER {
        return -1;
    }
    if x < y {
        return -1;
    }
    if x > y {
        return 1;
    }
    0
}

/// R's `rPsort`: `x[k]` ends in place, smaller values to the left.
fn r_psort(x: &mut [f64], k: usize) {
    let n = x.len();
    if n == 0 {
        return;
    }
    r_psort2(x, 0, (n - 1) as isize, k as isize);
}

fn r_psort2(x: &mut [f64], mut lo: isize, mut hi: isize, k: isize) {
    while lo < hi {
        let v = x[k as usize];
        let mut i = lo;
        let mut j = hi;
        while i <= j {
            while rcmp(x[i as usize], v) < 0 {
                i += 1;
            }
            while rcmp(v, x[j as usize]) < 0 {
                j -= 1;
            }
            if i <= j {
                x.swap(i as usize, j as usize);
                i += 1;
                j -= 1;
            }
        }
        if j < k {
            lo = i;
        }
        if k < i {
            hi = j;
        }
    }
}

/// R's `iPsort`.
fn i_psort(x: &mut [i32], k: usize) {
    let n = x.len();
    if n == 0 {
        return;
    }
    i_psort2(x, 0, (n - 1) as isize, k as isize);
}

fn i_psort2(x: &mut [i32], mut lo: isize, mut hi: isize, k: isize) {
    while lo < hi {
        let v = x[k as usize];
        let mut i = lo;
        let mut j = hi;
        while i <= j {
            while icmp(x[i as usize], v) < 0 {
                i += 1;
            }
            while icmp(v, x[j as usize]) < 0 {
                j -= 1;
            }
            if i <= j {
                x.swap(i as usize, j as usize);
                i += 1;
                j -= 1;
            }
        }
        if j < k {
            lo = i;
        }
        if k < i {
            hi = j;
        }
    }
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

    use crate::{
        row_order_stats_f64, row_order_stats_i32, validate_int, validate_logical, validate_real,
        Subset,
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

    fn array_f64(py: Python<'_>, values: Vec<f64>) -> PyResult<Py<PyAny>> {
        let arr = Array1::from_vec(values);
        Ok(arr.into_pyarray(py).into_any().unbind())
    }

    fn array_i32(py: Python<'_>, values: Vec<i32>) -> PyResult<Py<PyAny>> {
        let arr = Array1::from_vec(values);
        Ok(arr.into_pyarray(py).into_any().unbind())
    }

    fn stat_f64<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        which: i32,
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
            row_order_stats_f64(&[], nrow, ncol, 1, 0, &row_subset, &col_subset, which)
        } else if let Some((slice, row_stride, col_stride)) = contiguous(&view) {
            row_order_stats_f64(
                slice,
                nrow,
                ncol,
                row_stride,
                col_stride,
                &row_subset,
                &col_subset,
                which,
            )
        } else {
            let owned = owned_column_major(view);
            row_order_stats_f64(
                &owned,
                nrow,
                ncol,
                1,
                nrow,
                &row_subset,
                &col_subset,
                which,
            )
        }
        .map_err(PyValueError::new_err)?;
        array_f64(py, result)
    }

    fn stat_i32<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, i32>,
        which: i32,
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
            row_order_stats_i32(&[], nrow, ncol, 1, 0, &row_subset, &col_subset, which)
        } else if let Some((slice, row_stride, col_stride)) = contiguous(&view) {
            row_order_stats_i32(
                slice,
                nrow,
                ncol,
                row_stride,
                col_stride,
                &row_subset,
                &col_subset,
                which,
            )
        } else {
            let owned = owned_column_major(view);
            row_order_stats_i32(
                &owned,
                nrow,
                ncol,
                1,
                nrow,
                &row_subset,
                &col_subset,
                which,
            )
        }
        .map_err(PyValueError::new_err)?;
        array_i32(py, result)
    }

    #[pyfunction]
    #[pyo3(
        name = "row_order_stats_f64",
        signature = (x, which, rows=None, rows_kind="all", cols=None, cols_kind="all")
    )]
    fn row_order_stats_f64_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        which: i32,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
    ) -> PyResult<Py<PyAny>> {
        stat_f64(py, x, which, rows, rows_kind, cols, cols_kind)
    }

    #[pyfunction]
    #[pyo3(
        name = "row_order_stats_i32",
        signature = (x, which, rows=None, rows_kind="all", cols=None, cols_kind="all")
    )]
    fn row_order_stats_i32_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, i32>,
        which: i32,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
    ) -> PyResult<Py<PyAny>> {
        stat_i32(py, x, which, rows, rows_kind, cols, cols_kind)
    }

    #[pymodule]
    fn roworderstats(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(row_order_stats_f64_py, m)?)?;
        m.add_function(wrap_pyfunction!(row_order_stats_i32_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{row_order_stats_f64, row_order_stats_i32, r_psort, Subset};

    fn col_major_1_to_12() -> Vec<i32> {
        (1..=12).collect()
    }

    #[test]
    fn integer_matrix_matches_the_printed_orders() {
        let x = col_major_1_to_12();
        let first = row_order_stats_i32(&x, 4, 3, 1, 4, &Subset::All, &Subset::All, 1).unwrap();
        assert_eq!(first, vec![1, 2, 3, 4]);
        let middle = row_order_stats_i32(&x, 4, 3, 1, 4, &Subset::All, &Subset::All, 2).unwrap();
        assert_eq!(middle, vec![5, 6, 7, 8]);
        let last = row_order_stats_i32(&x, 4, 3, 1, 4, &Subset::All, &Subset::All, 3).unwrap();
        assert_eq!(last, vec![9, 10, 11, 12]);
    }

    #[test]
    fn signed_zero_follows_r_psort() {
        let mut low = vec![-0.0, 0.0];
        r_psort(&mut low, 0);
        assert_eq!(low[0].to_bits(), 0.0_f64.to_bits());
        let mut high = vec![-0.0, 0.0];
        r_psort(&mut high, 1);
        assert_eq!(high[1].to_bits(), (-0.0_f64).to_bits());

        let x = vec![-0.0, 0.0, 0.0, -0.0];
        let first = row_order_stats_f64(&x, 2, 2, 1, 2, &Subset::All, &Subset::All, 1).unwrap();
        assert_eq!(first[0].to_bits(), 0.0_f64.to_bits());
        assert_eq!(first[1].to_bits(), (-0.0_f64).to_bits());
        let second = row_order_stats_f64(&x, 2, 2, 1, 2, &Subset::All, &Subset::All, 2).unwrap();
        assert_eq!(second[0].to_bits(), (-0.0_f64).to_bits());
        assert_eq!(second[1].to_bits(), 0.0_f64.to_bits());
    }

    #[test]
    fn which_na_prints_the_integer_missing_value() {
        let x = col_major_1_to_12();
        let err = row_order_stats_i32(&x, 4, 3, 1, 4, &Subset::All, &Subset::All, i32::MIN)
            .unwrap_err();
        assert_eq!(err, "Argument 'which' is out of range: -2147483648");
    }
}
