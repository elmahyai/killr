//! Column minima, maxima, and ranges, ported from matrixStats `src/colRanges.c`.
//!
//! The R wrappers call this routine with `what` 0 for minima, 1 for maxima,
//! and 2 for ranges, and they always pass `hasNA = TRUE`. `rows` and `cols`
//! follow `validateIndices`: missing means every position, values are
//! 1-based, zeros are dropped, and negatives exclude. A missing index reads
//! as R's NA.
//!
//! Each selected column is scanned in row order. For doubles, R's NA is a
//! NaN whose low 32 bits are 1954. That value is copied and the rest of the
//! column is skipped when `na.rm` is false. A plain NaN is stored and does
//! not stop the column, but later finite values do not replace it because
//! NaN comparisons are false. A later NaN overwrites both ends with its own
//! payload. A column with no counted value has minimum `+Inf` and maximum
//! `-Inf`.
//!
//! Integer NA is `i32::MIN`. It stops the column when `na.rm` is false. If
//! any selected column counts no value, the whole integer result is promoted
//! to double: counted columns are cast with a C `(double)` conversion, and
//! an empty column is `+Inf` or `-Inf`. Logical input is rejected by the R
//! wrapper and is not accepted here.

/// R's integer NA. `NA_LOGICAL` equals `NA_INTEGER`.
const NA_INTEGER: i32 = i32::MIN;

/// R's `NA_real_`: a NaN whose low 32 bits are 1954 (`0x7A2`).
const NA_REAL_BITS: u64 = 0x7ff0_0000_0000_07a2;

/// Which summary `colRanges.c` computes.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum What {
    /// `what = 0`, one minimum per column.
    Min,
    /// `what = 1`, one maximum per column.
    Max,
    /// `what = 2`, minimum and maximum as two columns.
    Range,
}

impl What {
    pub fn from_i32(what: i32) -> Result<Self, String> {
        match what {
            0 => Ok(What::Min),
            1 => Ok(What::Max),
            2 => Ok(What::Range),
            _ => Err(format!("Invalid value of 'what': {what}")),
        }
    }

    fn columns(self) -> usize {
        match self {
            What::Range => 2,
            What::Min | What::Max => 1,
        }
    }
}

/// 1-based subscript vector. `All` selects every position in order.
#[derive(Clone, Debug, PartialEq)]
pub enum Subset {
    All,
    /// 0-based positions. `None` is an NA index.
    At(Vec<Option<usize>>),
}

/// A column summary. Integer input stays `I32` when every column counted a value.
#[derive(Clone, Debug, PartialEq)]
pub enum Answer {
    F64 {
        values: Vec<f64>,
        nrow: usize,
        ncol: usize,
    },
    I32 {
        values: Vec<i32>,
        nrow: usize,
        ncol: usize,
    },
}

impl Answer {
    pub fn nrow(&self) -> usize {
        match self {
            Answer::F64 { nrow, .. } | Answer::I32 { nrow, .. } => *nrow,
        }
    }

    pub fn ncol(&self) -> usize {
        match self {
            Answer::F64 { ncol, .. } | Answer::I32 { ncol, .. } => *ncol,
        }
    }
}

/// Minimum, maximum, or range of each column of a double matrix.
///
/// `x` is addressed with the given strides. Column-major storage, matching
/// R, uses `row_stride == 1` and `col_stride == nrow`. The result is
/// row-major: one value per selected column, or `[min, max]` pairs when
/// `what` is [`What::Range`]. That pair layout is the printed K by 2 matrix.
/// The C buffer stores every minimum, then every maximum.
pub fn col_stat_f64(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    row_stride: usize,
    col_stride: usize,
    rows: &Subset,
    cols: &Subset,
    what: What,
    na_rm: bool,
) -> Result<Answer, String> {
    ensure_span(x.len(), nrow, ncol, row_stride, col_stride)?;
    let row_pos = positions(rows, nrow);
    let col_pos = positions(cols, ncol);
    let ncols = col_pos.len();
    let out_cols = what.columns();
    let n_out = ncols
        .checked_mul(out_cols)
        .ok_or_else(|| "result dimensions overflow".to_string())?;
    let mut ans = vec![0.0; n_out];
    if ncols == 0 {
        return Ok(Answer::F64 {
            values: ans,
            nrow: ncols,
            ncol: out_cols,
        });
    }

    let mut counted = vec![false; ncols];
    for (jj, &col) in col_pos.iter().enumerate() {
        for &row in &row_pos {
            let value = load_f64(x, row_stride, col_stride, row, col);
            if value.is_nan() {
                if !na_rm {
                    write_f64(&mut ans, jj, what, value);
                    counted[jj] = true;
                    // R's NA stops this column. A plain NaN does not.
                    if is_r_na(value) {
                        break;
                    }
                }
            } else if !counted[jj] {
                write_f64(&mut ans, jj, what, value);
                counted[jj] = true;
            } else {
                update_f64(&mut ans, jj, what, value);
            }
        }
    }
    for jj in 0..ncols {
        if !counted[jj] {
            match what {
                What::Min => ans[jj] = f64::INFINITY,
                What::Max => ans[jj] = f64::NEG_INFINITY,
                What::Range => {
                    ans[jj * 2] = f64::INFINITY;
                    ans[jj * 2 + 1] = f64::NEG_INFINITY;
                }
            }
        }
    }
    Ok(Answer::F64 {
        values: ans,
        nrow: ncols,
        ncol: out_cols,
    })
}

/// Minimum, maximum, or range of each column of an integer matrix.
///
/// `i32::MIN` is R's NA. See [`col_stat_f64`] for layout. The result is
/// [`Answer::I32`] when every column counted a value, and [`Answer::F64`]
/// otherwise. An empty column selection stays integer, matching the C
/// wrapper: `all_counted` starts true and the promotion loop does not run.
pub fn col_stat_i32(
    x: &[i32],
    nrow: usize,
    ncol: usize,
    row_stride: usize,
    col_stride: usize,
    rows: &Subset,
    cols: &Subset,
    what: What,
    na_rm: bool,
) -> Result<Answer, String> {
    ensure_span(x.len(), nrow, ncol, row_stride, col_stride)?;
    let row_pos = positions(rows, nrow);
    let col_pos = positions(cols, ncol);
    let ncols = col_pos.len();
    let out_cols = what.columns();
    let n_out = ncols
        .checked_mul(out_cols)
        .ok_or_else(|| "result dimensions overflow".to_string())?;
    let mut ans = vec![0_i32; n_out];
    if ncols == 0 {
        return Ok(Answer::I32 {
            values: ans,
            nrow: ncols,
            ncol: out_cols,
        });
    }

    let mut counted = vec![false; ncols];
    for (jj, &col) in col_pos.iter().enumerate() {
        for &row in &row_pos {
            let value = load_i32(x, row_stride, col_stride, row, col);
            if value == NA_INTEGER {
                if !na_rm {
                    write_i32(&mut ans, jj, what, value);
                    counted[jj] = true;
                    break;
                }
            } else if !counted[jj] {
                write_i32(&mut ans, jj, what, value);
                counted[jj] = true;
            } else {
                update_i32(&mut ans, jj, what, value);
            }
        }
    }

    if counted.iter().any(|flag| !flag) {
        let mut promoted = Vec::with_capacity(n_out);
        for jj in 0..ncols {
            if counted[jj] {
                match what {
                    What::Range => {
                        promoted.push(ans[jj * 2] as f64);
                        promoted.push(ans[jj * 2 + 1] as f64);
                    }
                    What::Min | What::Max => promoted.push(ans[jj] as f64),
                }
            } else {
                match what {
                    What::Min => promoted.push(f64::INFINITY),
                    What::Max => promoted.push(f64::NEG_INFINITY),
                    What::Range => {
                        promoted.push(f64::INFINITY);
                        promoted.push(f64::NEG_INFINITY);
                    }
                }
            }
        }
        return Ok(Answer::F64 {
            values: promoted,
            nrow: ncols,
            ncol: out_cols,
        });
    }

    Ok(Answer::I32 {
        values: ans,
        nrow: ncols,
        ncol: out_cols,
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

fn write_f64(ans: &mut [f64], ii: usize, what: What, value: f64) {
    match what {
        What::Min | What::Max => ans[ii] = value,
        What::Range => {
            ans[ii * 2] = value;
            ans[ii * 2 + 1] = value;
        }
    }
}

fn update_f64(ans: &mut [f64], ii: usize, what: What, value: f64) {
    match what {
        What::Min => {
            if value < ans[ii] {
                ans[ii] = value;
            }
        }
        What::Max => {
            if value > ans[ii] {
                ans[ii] = value;
            }
        }
        What::Range => {
            let min_at = ii * 2;
            if value < ans[min_at] {
                ans[min_at] = value;
            } else if value > ans[min_at + 1] {
                ans[min_at + 1] = value;
            }
        }
    }
}

fn write_i32(ans: &mut [i32], ii: usize, what: What, value: i32) {
    match what {
        What::Min | What::Max => ans[ii] = value,
        What::Range => {
            ans[ii * 2] = value;
            ans[ii * 2 + 1] = value;
        }
    }
}

fn update_i32(ans: &mut [i32], ii: usize, what: What, value: i32) {
    match what {
        What::Min => {
            if value < ans[ii] {
                ans[ii] = value;
            }
        }
        What::Max => {
            if value > ans[ii] {
                ans[ii] = value;
            }
        }
        What::Range => {
            let min_at = ii * 2;
            if value < ans[min_at] {
                ans[min_at] = value;
            } else if value > ans[min_at + 1] {
                ans[min_at + 1] = value;
            }
        }
    }
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
        Err("Argument 'dim.' does not match length of argument 'x'".to_string())
    }
}

/// True for R's NA, including a quiet or negative NaN with payload 1954.
fn is_r_na(value: f64) -> bool {
    value.is_nan() && (value.to_bits() as u32) == 0x7A2
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
    use numpy::ndarray::{Array1, Array2, ArrayView2};
    use numpy::{IntoPyArray, PyReadonlyArray1, PyReadonlyArray2};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::{
        validate_int, validate_logical, validate_real, Answer, Subset, What, col_stat_f64,
        col_stat_i32,
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

    fn answer_to_py(py: Python<'_>, answer: Answer) -> PyResult<Py<PyAny>> {
        match answer {
            Answer::F64 {
                values,
                nrow,
                ncol,
            } => array_f64(py, values, nrow, ncol),
            Answer::I32 {
                values,
                nrow,
                ncol,
            } => array_i32(py, values, nrow, ncol),
        }
    }

    fn array_f64(py: Python<'_>, values: Vec<f64>, nrow: usize, ncol: usize) -> PyResult<Py<PyAny>> {
        if ncol == 1 {
            let arr = Array1::from_shape_vec(nrow, values)
                .map_err(|err| PyValueError::new_err(err.to_string()))?;
            Ok(arr.into_pyarray(py).into_any().unbind())
        } else {
            let arr = Array2::from_shape_vec((nrow, ncol), values)
                .map_err(|err| PyValueError::new_err(err.to_string()))?;
            Ok(arr.into_pyarray(py).into_any().unbind())
        }
    }

    fn array_i32(py: Python<'_>, values: Vec<i32>, nrow: usize, ncol: usize) -> PyResult<Py<PyAny>> {
        if ncol == 1 {
            let arr = Array1::from_shape_vec(nrow, values)
                .map_err(|err| PyValueError::new_err(err.to_string()))?;
            Ok(arr.into_pyarray(py).into_any().unbind())
        } else {
            let arr = Array2::from_shape_vec((nrow, ncol), values)
                .map_err(|err| PyValueError::new_err(err.to_string()))?;
            Ok(arr.into_pyarray(py).into_any().unbind())
        }
    }

    fn stat_f64_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        what: i32,
        na_rm: bool,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
    ) -> PyResult<Py<PyAny>> {
        let what = What::from_i32(what).map_err(PyValueError::new_err)?;
        let view = x.as_array();
        let (nrow, ncol) = view.dim();
        let row_subset = parse_subset(rows.as_ref(), rows_kind, nrow)?;
        let col_subset = parse_subset(cols.as_ref(), cols_kind, ncol)?;
        let result = if nrow == 0 || ncol == 0 {
            col_stat_f64(&[], nrow, ncol, 1, 0, &row_subset, &col_subset, what, na_rm)
        } else if let Some((slice, row_stride, col_stride)) = contiguous(&view) {
            col_stat_f64(
                slice,
                nrow,
                ncol,
                row_stride,
                col_stride,
                &row_subset,
                &col_subset,
                what,
                na_rm,
            )
        } else {
            let owned = owned_column_major(view);
            col_stat_f64(
                &owned,
                nrow,
                ncol,
                1,
                nrow,
                &row_subset,
                &col_subset,
                what,
                na_rm,
            )
        }
        .map_err(PyValueError::new_err)?;
        answer_to_py(py, result)
    }

    fn stat_i32_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, i32>,
        what: i32,
        na_rm: bool,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
    ) -> PyResult<Py<PyAny>> {
        let what = What::from_i32(what).map_err(PyValueError::new_err)?;
        let view = x.as_array();
        let (nrow, ncol) = view.dim();
        let row_subset = parse_subset(rows.as_ref(), rows_kind, nrow)?;
        let col_subset = parse_subset(cols.as_ref(), cols_kind, ncol)?;
        let result = if nrow == 0 || ncol == 0 {
            col_stat_i32(&[], nrow, ncol, 1, 0, &row_subset, &col_subset, what, na_rm)
        } else if let Some((slice, row_stride, col_stride)) = contiguous(&view) {
            col_stat_i32(
                slice,
                nrow,
                ncol,
                row_stride,
                col_stride,
                &row_subset,
                &col_subset,
                what,
                na_rm,
            )
        } else {
            let owned = owned_column_major(view);
            col_stat_i32(
                &owned,
                nrow,
                ncol,
                1,
                nrow,
                &row_subset,
                &col_subset,
                what,
                na_rm,
            )
        }
        .map_err(PyValueError::new_err)?;
        answer_to_py(py, result)
    }

    #[pyfunction]
    #[pyo3(name = "col_stat_f64", signature = (x, what, na_rm, rows=None, rows_kind="all", cols=None, cols_kind="all"))]
    fn col_stat_f64_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        what: i32,
        na_rm: bool,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
    ) -> PyResult<Py<PyAny>> {
        stat_f64_py(py, x, what, na_rm, rows, rows_kind, cols, cols_kind)
    }

    #[pyfunction]
    #[pyo3(name = "col_stat_i32", signature = (x, what, na_rm, rows=None, rows_kind="all", cols=None, cols_kind="all"))]
    fn col_stat_i32_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, i32>,
        what: i32,
        na_rm: bool,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
    ) -> PyResult<Py<PyAny>> {
        stat_i32_py(py, x, what, na_rm, rows, rows_kind, cols, cols_kind)
    }

    #[pymodule]
    fn colranges(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(col_stat_f64_py, m)?)?;
        m.add_function(wrap_pyfunction!(col_stat_i32_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{
        Answer, Subset, What, col_stat_f64, col_stat_i32, is_r_na, validate_int, validate_logical,
        validate_real, NA_INTEGER, NA_REAL_BITS,
    };

    fn na_real() -> f64 {
        f64::from_bits(NA_REAL_BITS)
    }

    fn f64_of(answer: Answer) -> Vec<f64> {
        match answer {
            Answer::F64 { values, .. } => values,
            Answer::I32 { .. } => panic!("expected float64"),
        }
    }

    fn i32_of(answer: Answer) -> Vec<i32> {
        match answer {
            Answer::I32 { values, .. } => values,
            Answer::F64 { .. } => panic!("expected int32"),
        }
    }

    fn col_major_1_to_12() -> Vec<i32> {
        (1..=12).collect()
    }

    #[test]
    fn integer_matrix_matches_the_printed_column_range() {
        let x = col_major_1_to_12();
        let mins = col_stat_i32(&x, 4, 3, 1, 4, &Subset::All, &Subset::All, What::Min, false)
            .unwrap();
        assert_eq!(i32_of(mins), vec![1, 5, 9]);
        let maxs = col_stat_i32(&x, 4, 3, 1, 4, &Subset::All, &Subset::All, What::Max, false)
            .unwrap();
        assert_eq!(i32_of(maxs), vec![4, 8, 12]);
        let ranges = col_stat_i32(
            &x,
            4,
            3,
            1,
            4,
            &Subset::All,
            &Subset::All,
            What::Range,
            false,
        )
        .unwrap();
        assert_eq!(ranges.nrow(), 3);
        assert_eq!(ranges.ncol(), 2);
        assert_eq!(i32_of(ranges), vec![1, 4, 5, 8, 9, 12]);
    }

    #[test]
    fn row_major_layout_reads_the_printed_matrix() {
        let x: Vec<f64> = vec![1.0, 5.0, 9.0, 2.0, 6.0, 10.0, 3.0, 7.0, 11.0, 4.0, 8.0, 12.0];
        let ranges = col_stat_f64(
            &x,
            4,
            3,
            3,
            1,
            &Subset::All,
            &Subset::All,
            What::Range,
            false,
        )
        .unwrap();
        assert_eq!(f64_of(ranges), vec![1.0, 4.0, 5.0, 8.0, 9.0, 12.0]);
    }

    #[test]
    fn r_na_stops_the_column_and_keeps_its_payload() {
        let quiet = f64::from_bits(0x7ff8_0000_0000_07a2);
        let negative = f64::from_bits(0xfff0_0000_0000_07a2);
        assert!(is_r_na(na_real()) && is_r_na(quiet) && is_r_na(negative));

        let mins = col_stat_f64(
            &[3.0, quiet, -9.0],
            3,
            1,
            1,
            3,
            &Subset::All,
            &Subset::All,
            What::Min,
            false,
        )
        .unwrap();
        assert_eq!(f64_of(mins)[0].to_bits(), quiet.to_bits());

        let mins = col_stat_f64(
            &[1.0, negative, -4.0],
            3,
            1,
            1,
            3,
            &Subset::All,
            &Subset::All,
            What::Min,
            false,
        )
        .unwrap();
        assert_eq!(f64_of(mins)[0].to_bits(), negative.to_bits());

        let ranges = col_stat_f64(
            &[5.0, na_real(), 9.0],
            3,
            1,
            1,
            3,
            &Subset::All,
            &Subset::All,
            What::Range,
            false,
        )
        .unwrap();
        let values = f64_of(ranges);
        assert_eq!(values[0].to_bits(), NA_REAL_BITS);
        assert_eq!(values[1].to_bits(), NA_REAL_BITS);

        let later = f64::from_bits(0x7ff8_0000_0000_0001);
        let stopped = col_stat_f64(
            &[na_real(), later],
            2,
            1,
            1,
            2,
            &Subset::All,
            &Subset::All,
            What::Min,
            false,
        )
        .unwrap();
        assert_eq!(f64_of(stopped)[0].to_bits(), NA_REAL_BITS);
    }

    #[test]
    fn plain_nan_is_stored_and_a_later_nan_overwrites_both_ends() {
        let first = f64::from_bits(0x7ff8_0000_0000_0001);
        let second = f64::from_bits(0x7ff8_0000_0000_0002);
        let ranges = col_stat_f64(
            &[8.0, first, -3.0, second, 4.0],
            5,
            1,
            1,
            5,
            &Subset::All,
            &Subset::All,
            What::Range,
            false,
        )
        .unwrap();
        let values = f64_of(ranges);
        assert_eq!(values[0].to_bits(), second.to_bits());
        assert_eq!(values[1].to_bits(), second.to_bits());

        let mins = col_stat_f64(
            &[first, -5.0],
            2,
            1,
            1,
            2,
            &Subset::All,
            &Subset::All,
            What::Min,
            false,
        )
        .unwrap();
        assert_eq!(f64_of(mins)[0].to_bits(), first.to_bits());
    }

    #[test]
    fn na_rm_drops_missing_values_and_an_empty_column_is_infinite() {
        let ranges = col_stat_f64(
            &[5.0, f64::NAN, 1.0],
            3,
            1,
            1,
            3,
            &Subset::All,
            &Subset::All,
            What::Range,
            true,
        )
        .unwrap();
        assert_eq!(f64_of(ranges), vec![1.0, 5.0]);

        let ranges = col_stat_f64(
            &[na_real(), f64::NAN],
            2,
            1,
            1,
            2,
            &Subset::All,
            &Subset::All,
            What::Range,
            true,
        )
        .unwrap();
        let values = f64_of(ranges);
        assert!(values[0].is_infinite() && values[0].is_sign_positive());
        assert!(values[1].is_infinite() && values[1].is_sign_negative());

        let no_rows = col_stat_f64(&[], 0, 2, 1, 0, &Subset::All, &Subset::All, What::Min, false)
            .unwrap();
        assert!(f64_of(no_rows)
            .iter()
            .all(|v| v.is_infinite() && v.is_sign_positive()));
        let no_cols = col_stat_f64(&[], 2, 0, 1, 0, &Subset::All, &Subset::All, What::Min, false)
            .unwrap();
        assert!(f64_of(no_cols).is_empty());
    }

    #[test]
    fn integer_na_stays_int32_until_a_column_counts_nothing() {
        let na = NA_INTEGER;
        // Column-major 3x3:
        //  1  3  NA
        // NA  2   0
        //  4  1   5
        let x = vec![1, na, 4, 3, 2, 1, na, 0, 5];
        let mins = col_stat_i32(&x, 3, 3, 1, 3, &Subset::All, &Subset::All, What::Min, false)
            .unwrap();
        assert_eq!(i32_of(mins), vec![na, 1, na]);
        let kept = col_stat_i32(&x, 3, 3, 1, 3, &Subset::All, &Subset::All, What::Min, true)
            .unwrap();
        assert_eq!(i32_of(kept), vec![1, 1, 0]);

        let mixed = vec![1, 2, na, na];
        let ranges =
            col_stat_i32(&mixed, 2, 2, 1, 2, &Subset::All, &Subset::All, What::Range, true)
                .unwrap();
        assert_eq!(
            f64_of(ranges),
            vec![1.0, 2.0, f64::INFINITY, f64::NEG_INFINITY]
        );

        let empty_cols =
            col_stat_i32(&[], 3, 0, 1, 0, &Subset::All, &Subset::All, What::Range, false).unwrap();
        assert!(matches!(empty_cols, Answer::I32 { nrow: 0, ncol: 2, .. }));
        let empty_rows =
            col_stat_i32(&[], 0, 2, 1, 0, &Subset::All, &Subset::All, What::Range, true).unwrap();
        assert_eq!(
            f64_of(empty_rows),
            vec![
                f64::INFINITY,
                f64::NEG_INFINITY,
                f64::INFINITY,
                f64::NEG_INFINITY
            ]
        );
    }

    #[test]
    fn signed_zero_keeps_the_first_sign_and_a_later_negative_zero_can_win() {
        let neg_then_pos = col_stat_f64(
            &[-0.0, 0.0],
            2,
            1,
            1,
            2,
            &Subset::All,
            &Subset::All,
            What::Range,
            false,
        )
        .unwrap();
        let values = f64_of(neg_then_pos);
        assert_eq!(values[0].to_bits(), (-0.0_f64).to_bits());
        assert_eq!(values[1].to_bits(), (-0.0_f64).to_bits());

        let one_then_neg = col_stat_f64(
            &[1.0, -0.0],
            2,
            1,
            1,
            2,
            &Subset::All,
            &Subset::All,
            What::Min,
            false,
        )
        .unwrap();
        assert_eq!(f64_of(one_then_neg)[0].to_bits(), (-0.0_f64).to_bits());
    }

    #[test]
    fn row_subset_order_stops_at_r_na_and_column_order_is_the_result_order() {
        let na = f64::NAN;
        // 1  NA  4
        // 2   3  5
        let x = vec![1.0, 2.0, na, 3.0, 4.0, 5.0];
        let cols = validate_int(&[3, 2], 3).unwrap();
        let ranges =
            col_stat_f64(&x, 2, 3, 1, 2, &Subset::All, &cols, What::Range, false).unwrap();
        let values = f64_of(ranges);
        assert_eq!(&values[0..2], &[4.0, 5.0]);
        assert!(values[2].is_nan() && values[3].is_nan());

        let dropped =
            col_stat_f64(&x, 2, 3, 1, 2, &Subset::All, &cols, What::Range, true).unwrap();
        assert_eq!(f64_of(dropped), vec![4.0, 5.0, 3.0, 3.0]);

        let late_then_early = validate_int(&[2, 1], 2).unwrap();
        let seen_first = col_stat_f64(
            &[10.0, na_real(), 1.0],
            3,
            1,
            1,
            3,
            &late_then_early,
            &Subset::All,
            What::Min,
            false,
        )
        .unwrap();
        assert_eq!(f64_of(seen_first)[0].to_bits(), NA_REAL_BITS);

        let finite_first = validate_int(&[3, 1], 3).unwrap();
        let kept = col_stat_f64(
            &[10.0, na_real(), 1.0],
            3,
            1,
            1,
            3,
            &finite_first,
            &Subset::All,
            What::Min,
            false,
        )
        .unwrap();
        assert_eq!(f64_of(kept), vec![1.0]);
    }

    #[test]
    fn missing_index_is_r_na_and_index_rules_match_validate_indices() {
        let x: Vec<i32> = (1..=12).collect();
        let cols = validate_int(&[1, i32::MIN as i64], 3).unwrap();
        let mins = col_stat_i32(&x, 4, 3, 1, 4, &Subset::All, &cols, What::Min, false).unwrap();
        assert_eq!(i32_of(mins), vec![1, NA_INTEGER]);

        assert_eq!(
            validate_int(&[0, 2, 0], 2).unwrap(),
            Subset::At(vec![Some(1)])
        );
        assert_eq!(validate_int(&[-2], 2).unwrap(), Subset::At(vec![Some(0)]));
        assert!(validate_int(&[1, 9], 2).is_err());
        assert!(validate_int(&[-1, 1], 2).is_err());
        assert_eq!(validate_real(&[1.9], 4).unwrap(), Subset::At(vec![Some(0)]));
        assert_eq!(
            validate_real(&[-1.9], 3).unwrap(),
            Subset::At(vec![Some(1), Some(2)])
        );
        assert_eq!(validate_logical(&[1], 3).unwrap(), Subset::All);
        assert_eq!(validate_logical(&[0], 3).unwrap(), Subset::At(vec![]));
        assert!(validate_logical(&[1, 0, 1, 0], 3).is_err());
    }

    #[test]
    fn infinities_compare_as_in_ieee() {
        let ranges = col_stat_f64(
            &[f64::INFINITY, 1.0, f64::NEG_INFINITY],
            3,
            1,
            1,
            3,
            &Subset::All,
            &Subset::All,
            What::Range,
            false,
        )
        .unwrap();
        assert_eq!(f64_of(ranges), vec![f64::NEG_INFINITY, f64::INFINITY]);
    }
}
