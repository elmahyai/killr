//! Elementwise `x OP y` and `t(t(x) OP y)`, ported from matrixStats
//! `src/x_OP_y.c` and `src/x_OP_y_lowlevel_template.h`.
//!
//! `OP` is addition, subtraction, multiplication, or division. `by_row` is
//! false for `x_OP_y` and true for `t_tx_OP_y`. `commute` swaps the operands.
//! `na.rm` changes only addition and multiplication: a missing operand is
//! replaced by the other one. Subtraction and division ignore `na.rm`.
//!
//! Integer missing values are `i32::MIN`. The template's `R_INT_MIN` is
//! `-INT_MAX` (`-2147483647`), so a result of `-2147483648` is overflow:
//! that element becomes `NA_integer_` and the call warns. Casting an integer
//! `NA` to double yields `-2147483648`, which is what `na.rm` returns when
//! the kept operand is an integer `NA` and the result is double.
//!
//! `xrows` and `xcols` reject a positive index past the matrix. `yidxs`
//! allows it and reads that element as missing. Indices are 1-based.

/// R's integer NA. `NA_LOGICAL` equals `NA_INTEGER`.
const NA_INTEGER: i32 = i32::MIN;

/// R's `NA_real_`: a NaN whose low 32 bits are 1954 (`0x7A2`).
const NA_REAL_BITS: u64 = 0x7ff0_0000_0000_07a2;

/// `R_INT_MIN` in matrixStats `000.types.h` is `-INT_MAX`, not `INT_MIN`.
const R_INT_MIN_F: f64 = -2_147_483_647.0;
const R_INT_MAX_F: f64 = 2_147_483_647.0;

/// Operator codes used by `x_OP_y.R`: 1 add, 2 subtract, 3 multiply, 4 divide.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Op {
    Add = 1,
    Sub = 2,
    Mul = 3,
    Div = 4,
}

impl Op {
    pub fn from_i32(op: i32) -> Result<Self, String> {
        match op {
            1 => Ok(Op::Add),
            2 => Ok(Op::Sub),
            3 => Ok(Op::Mul),
            4 => Ok(Op::Div),
            _ => Err(format!("Unknown value on argument 'OP': {op}L")),
        }
    }

    fn drops_na(self) -> bool {
        matches!(self, Op::Add | Op::Mul)
    }
}

/// 1-based subscript vector. `All` is R's `NULL`.
#[derive(Clone, Debug, PartialEq)]
pub enum Subset {
    All,
    /// 0-based positions. `None` is an NA index.
    At(Vec<Option<usize>>),
}

/// Column-major result stored row-major, so axis 0 is rows.
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

trait Num: Copy {
    const IS_INT: bool;
    fn is_missing(self) -> bool;
    fn early_na(self) -> bool;
    fn as_f64(self) -> f64;
    fn missing() -> Self;
}

impl Num for i32 {
    const IS_INT: bool = true;

    fn is_missing(self) -> bool {
        self == NA_INTEGER
    }

    fn early_na(self) -> bool {
        self == NA_INTEGER
    }

    fn as_f64(self) -> f64 {
        self as f64
    }

    fn missing() -> Self {
        NA_INTEGER
    }
}

impl Num for f64 {
    const IS_INT: bool = false;

    fn is_missing(self) -> bool {
        self.is_nan()
    }

    fn early_na(self) -> bool {
        false
    }

    fn as_f64(self) -> f64 {
        self
    }

    fn missing() -> Self {
        f64::from_bits(NA_REAL_BITS)
    }
}

fn na_real() -> f64 {
    f64::from_bits(NA_REAL_BITS)
}

#[inline]
fn apply_op(op: Op, left: f64, right: f64) -> f64 {
    match op {
        Op::Add => left + right,
        Op::Sub => left - right,
        Op::Mul => left * right,
        Op::Div => left / right,
    }
}

/// `FUN_no_NA` or `FUN_narm` from the lowlevel template.
///
/// `drop_na` is true only for addition and multiplication when `na.rm` is set.
/// Integer `NA` returns `NA_real_` before the arithmetic. Double `NA` and
/// `NaN` go through IEEE arithmetic unless `drop_na` substitutes the other
/// operand. That substitution casts an integer `NA` to `-2147483648`.
#[inline]
fn combine<X: Num, Y: Num>(op: Op, drop_na: bool, x: X, y: Y) -> f64 {
    if drop_na {
        if x.is_missing() {
            return y.as_f64();
        }
        if y.is_missing() {
            return x.as_f64();
        }
        return apply_op(op, x.as_f64(), y.as_f64());
    }
    if x.early_na() || y.early_na() {
        return na_real();
    }
    apply_op(op, x.as_f64(), y.as_f64())
}

fn store_i32(value: f64, overflow: &mut bool) -> i32 {
    if value.is_nan() {
        return NA_INTEGER;
    }
    if value < R_INT_MIN_F || value > R_INT_MAX_F {
        *overflow = true;
        return NA_INTEGER;
    }
    value as i32
}

/// Apply `op` to a matrix and a recycled vector.
///
/// `x` is addressed with the given strides. Column-major storage, matching
/// R, uses `row_stride == 1` and `col_stride == nrow`. The boolean in the
/// result is true when an integer result overflowed.
pub(crate) fn operate<X: Num, Y: Num>(
    x: &[X],
    nrow: usize,
    ncol: usize,
    row_stride: usize,
    col_stride: usize,
    y: &[Y],
    rows: &Subset,
    cols: &Subset,
    yidxs: &Subset,
    op: Op,
    by_row: bool,
    commute: bool,
    na_rm: bool,
) -> Result<(Answer, bool), String> {
    ensure_span(x.len(), nrow, ncol, row_stride, col_stride)?;
    let row_pos = positions(rows, nrow);
    let col_pos = positions(cols, ncol);
    let nxrows = row_pos.len();
    let nxcols = col_pos.len();
    let n_out = nxrows
        .checked_mul(nxcols)
        .ok_or_else(|| "result dimensions overflow".to_string())?;
    let (y_direct, y_at, nyidxs) = match yidxs {
        Subset::All => (true, &[][..], y.len()),
        Subset::At(idx) => (false, idx.as_slice(), idx.len()),
    };
    if n_out > 0 && nyidxs == 0 {
        return Err("argument 'y' has length zero".to_string());
    }

    let drop_na = na_rm && op.drops_na();
    let integer_answer = X::IS_INT && Y::IS_INT && !matches!(op, Op::Div);
    let mut overflow = false;

    if integer_answer {
        let mut out = vec![0_i32; n_out];
        for jj in 0..nxcols {
            for ii in 0..nxrows {
                let value = cell(
                    x,
                    row_stride,
                    col_stride,
                    y,
                    &row_pos,
                    &col_pos,
                    y_direct,
                    y_at,
                    nyidxs,
                    ii,
                    jj,
                    nxrows,
                    nxcols,
                    op,
                    by_row,
                    commute,
                    drop_na,
                )?;
                out[ii * nxcols + jj] = store_i32(value, &mut overflow);
            }
        }
        return Ok((
            Answer::I32 {
                values: out,
                nrow: nxrows,
                ncol: nxcols,
            },
            overflow,
        ));
    }

    let mut out = vec![0.0_f64; n_out];
    for jj in 0..nxcols {
        for ii in 0..nxrows {
            out[ii * nxcols + jj] = cell(
                x,
                row_stride,
                col_stride,
                y,
                &row_pos,
                &col_pos,
                y_direct,
                y_at,
                nyidxs,
                ii,
                jj,
                nxrows,
                nxcols,
                op,
                by_row,
                commute,
                drop_na,
            )?;
        }
    }
    Ok((
        Answer::F64 {
            values: out,
            nrow: nxrows,
            ncol: nxcols,
        },
        false,
    ))
}

fn cell<X: Num, Y: Num>(
    x: &[X],
    row_stride: usize,
    col_stride: usize,
    y: &[Y],
    row_pos: &[Option<usize>],
    col_pos: &[Option<usize>],
    y_direct: bool,
    y_at: &[Option<usize>],
    nyidxs: usize,
    ii: usize,
    jj: usize,
    nxrows: usize,
    nxcols: usize,
    op: Op,
    by_row: bool,
    commute: bool,
    drop_na: bool,
) -> Result<f64, String> {
    let x_value = match (row_pos[ii], col_pos[jj]) {
        (Some(row), Some(col)) => x[row * row_stride + col * col_stride],
        _ => X::missing(),
    };
    let linear = if by_row {
        ii.checked_mul(nxcols).and_then(|value| value.checked_add(jj))
    } else {
        jj.checked_mul(nxrows).and_then(|value| value.checked_add(ii))
    }
    .ok_or_else(|| "index overflow".to_string())?;
    let y_pos = linear % nyidxs;
    let y_value = if y_direct {
        y[y_pos]
    } else {
        match y_at[y_pos] {
            Some(index) => y[index],
            None => Y::missing(),
        }
    };
    if commute {
        Ok(combine(op, drop_na, y_value, x_value))
    } else {
        Ok(combine(op, drop_na, x_value, y_value))
    }
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

/// 1-based integer indices. `i32::MIN` is R's integer NA.
///
/// `allow_oob` is false for `xrows` and `xcols`, and true for `yidxs`.
pub fn validate_int(idxs: &[i64], max_idx: usize, allow_oob: bool) -> Result<Subset, String> {
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
            if !is_int_na(idx) && idx > max_idx as i64 {
                if !allow_oob {
                    return Err("subscript out of bounds".to_string());
                }
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

/// 1-based real indices. NaN and both infinities are NA indices.
pub fn validate_real(idxs: &[f64], max_idx: usize, allow_oob: bool) -> Result<Subset, String> {
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
            if idx.is_finite() && idx > max_idx as f64 && !allow_oob {
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
            ans.push(real_to_zero_based(idx, max_idx));
        }
        return Ok(Subset::At(ans));
    }

    if state >= 0 {
        let mut ans = Vec::with_capacity(count);
        for &idx in idxs {
            if idx != 0.0 {
                ans.push(real_to_zero_based(idx, max_idx));
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
///
/// A pattern longer than `max_idx` is an error unless `allow_oob` is set,
/// in which case the extra true and missing entries become missing indices.
pub fn validate_logical(idxs: &[i8], max_idx: usize, allow_oob: bool) -> Result<Subset, String> {
    let nidxs = idxs.len();
    if nidxs == 0 {
        return Ok(Subset::At(Vec::new()));
    }
    if nidxs > max_idx {
        if !allow_oob {
            return Err("logical subscript too long".to_string());
        }
        let mut ans = Vec::new();
        for (ii, &flag) in idxs.iter().enumerate() {
            if flag == 0 {
                continue;
            }
            if ii < max_idx && flag > 0 {
                ans.push(Some(ii));
            } else {
                ans.push(None);
            }
        }
        return Ok(Subset::At(ans));
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

fn is_int_na(idx: i64) -> bool {
    idx == i32::MIN as i64
}

fn int_to_zero_based(idx: i64, max_idx: usize) -> Option<usize> {
    if is_int_na(idx) || idx < 1 || idx > max_idx as i64 {
        None
    } else {
        Some((idx as usize) - 1)
    }
}

fn real_to_zero_based(idx: f64, max_idx: usize) -> Option<usize> {
    if !idx.is_finite() || idx > max_idx as f64 {
        return None;
    }
    let zero_based = (idx - 1.0).trunc();
    if zero_based <= 0.0 {
        Some(0)
    } else {
        Some(zero_based as usize)
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
    use numpy::ndarray::{Array2, ArrayView1, ArrayView2};
    use numpy::{IntoPyArray, PyReadonlyArray1, PyReadonlyArray2};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::{
        validate_int, validate_logical, validate_real, Answer, Num, Op, Subset, operate,
    };

    fn parse_subset(
        obj: Option<&Bound<'_, PyAny>>,
        kind: &str,
        max_idx: usize,
        allow_oob: bool,
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
                validate_int(slice, max_idx, allow_oob)
            }
            "real" => {
                let arr = obj.extract::<PyReadonlyArray1<f64>>()?;
                let slice = arr
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                validate_real(slice, max_idx, allow_oob)
            }
            "logical" => {
                let arr = obj.extract::<PyReadonlyArray1<i8>>()?;
                let slice = arr
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                validate_logical(slice, max_idx, allow_oob)
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

    fn vector_slice<'a, T: Copy>(view: &'a ArrayView1<'a, T>, owned: &'a mut Option<Vec<T>>) -> &'a [T] {
        if let Some(slice) = view.as_slice() {
            return slice;
        }
        *owned = Some(view.iter().copied().collect());
        owned.as_deref().unwrap()
    }

    fn answer_to_py(py: Python<'_>, answer: Answer) -> PyResult<Py<PyAny>> {
        match answer {
            Answer::F64 {
                values,
                nrow,
                ncol,
            } => {
                let arr = Array2::from_shape_vec((nrow, ncol), values)
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                Ok(arr.into_pyarray(py).into_any().unbind())
            }
            Answer::I32 {
                values,
                nrow,
                ncol,
            } => {
                let arr = Array2::from_shape_vec((nrow, ncol), values)
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                Ok(arr.into_pyarray(py).into_any().unbind())
            }
        }
    }

    fn run<X: Num, Y: Num>(
        py: Python<'_>,
        x: &[X],
        nrow: usize,
        ncol: usize,
        row_stride: usize,
        col_stride: usize,
        y: &[Y],
        op: i32,
        by_row: bool,
        commute: bool,
        na_rm: bool,
        rows: &Subset,
        cols: &Subset,
        yidxs: &Subset,
    ) -> PyResult<(Py<PyAny>, bool)> {
        let op = Op::from_i32(op).map_err(PyValueError::new_err)?;
        let (answer, overflow) = operate(
            x,
            nrow,
            ncol,
            row_stride,
            col_stride,
            y,
            rows,
            cols,
            yidxs,
            op,
            by_row,
            commute,
            na_rm,
        )
        .map_err(PyValueError::new_err)?;
        Ok((answer_to_py(py, answer)?, overflow))
    }

    fn subsets<'py>(
        xrows: Option<Bound<'py, PyAny>>,
        xrows_kind: &str,
        xcols: Option<Bound<'py, PyAny>>,
        xcols_kind: &str,
        yidxs: Option<Bound<'py, PyAny>>,
        yidxs_kind: &str,
        nrow: usize,
        ncol: usize,
        ny: usize,
    ) -> PyResult<(Subset, Subset, Subset)> {
        let rows = parse_subset(xrows.as_ref(), xrows_kind, nrow, false)?;
        let cols = parse_subset(xcols.as_ref(), xcols_kind, ncol, false)?;
        let y_index = parse_subset(yidxs.as_ref(), yidxs_kind, ny, true)?;
        Ok((rows, cols, y_index))
    }

    fn apply_f64<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        y_slice: &[f64],
        op: i32,
        by_row: bool,
        commute: bool,
        na_rm: bool,
        rows: &Subset,
        cols: &Subset,
        y_index: &Subset,
    ) -> PyResult<(Py<PyAny>, bool)> {
        let view = x.as_array();
        let (nrow, ncol) = view.dim();
        if nrow == 0 || ncol == 0 {
            return run(
                py,
                &[] as &[f64],
                nrow,
                ncol,
                1,
                0,
                y_slice,
                op,
                by_row,
                commute,
                na_rm,
                rows,
                cols,
                y_index,
            );
        }
        if let Some((slice, row_stride, col_stride)) = contiguous(&view) {
            return run(
                py,
                slice,
                nrow,
                ncol,
                row_stride,
                col_stride,
                y_slice,
                op,
                by_row,
                commute,
                na_rm,
                rows,
                cols,
                y_index,
            );
        }
        let owned = owned_column_major(view);
        run(
            py,
            &owned,
            nrow,
            ncol,
            1,
            nrow,
            y_slice,
            op,
            by_row,
            commute,
            na_rm,
            rows,
            cols,
            y_index,
        )
    }

    fn apply_i32<'py, Y: Num>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, i32>,
        y_slice: &[Y],
        op: i32,
        by_row: bool,
        commute: bool,
        na_rm: bool,
        rows: &Subset,
        cols: &Subset,
        y_index: &Subset,
    ) -> PyResult<(Py<PyAny>, bool)> {
        let view = x.as_array();
        let (nrow, ncol) = view.dim();
        if nrow == 0 || ncol == 0 {
            return run(
                py,
                &[] as &[i32],
                nrow,
                ncol,
                1,
                0,
                y_slice,
                op,
                by_row,
                commute,
                na_rm,
                rows,
                cols,
                y_index,
            );
        }
        if let Some((slice, row_stride, col_stride)) = contiguous(&view) {
            return run(
                py,
                slice,
                nrow,
                ncol,
                row_stride,
                col_stride,
                y_slice,
                op,
                by_row,
                commute,
                na_rm,
                rows,
                cols,
                y_index,
            );
        }
        let owned = owned_column_major(view);
        run(
            py,
            &owned,
            nrow,
            ncol,
            1,
            nrow,
            y_slice,
            op,
            by_row,
            commute,
            na_rm,
            rows,
            cols,
            y_index,
        )
    }

    #[pyfunction]
    #[pyo3(
        name = "apply_f64_f64",
        signature = (x, y, op, by_row, commute, na_rm, xrows=None, xrows_kind="all", xcols=None, xcols_kind="all", yidxs=None, yidxs_kind="all")
    )]
    fn apply_f64_f64<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        y: PyReadonlyArray1<'py, f64>,
        op: i32,
        by_row: bool,
        commute: bool,
        na_rm: bool,
        xrows: Option<Bound<'py, PyAny>>,
        xrows_kind: &str,
        xcols: Option<Bound<'py, PyAny>>,
        xcols_kind: &str,
        yidxs: Option<Bound<'py, PyAny>>,
        yidxs_kind: &str,
    ) -> PyResult<(Py<PyAny>, bool)> {
        let (nrow, ncol) = x.as_array().dim();
        let mut y_owned = None;
        let y_view = y.as_array();
        let y_slice = vector_slice(&y_view, &mut y_owned);
        let (rows, cols, y_index) = subsets(
            xrows,
            xrows_kind,
            xcols,
            xcols_kind,
            yidxs,
            yidxs_kind,
            nrow,
            ncol,
            y_slice.len(),
        )?;
        apply_f64(
            py, x, y_slice, op, by_row, commute, na_rm, &rows, &cols, &y_index,
        )
    }

    #[pyfunction]
    #[pyo3(
        name = "apply_f64_i32",
        signature = (x, y, op, by_row, commute, na_rm, xrows=None, xrows_kind="all", xcols=None, xcols_kind="all", yidxs=None, yidxs_kind="all")
    )]
    fn apply_f64_i32<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        y: PyReadonlyArray1<'py, i32>,
        op: i32,
        by_row: bool,
        commute: bool,
        na_rm: bool,
        xrows: Option<Bound<'py, PyAny>>,
        xrows_kind: &str,
        xcols: Option<Bound<'py, PyAny>>,
        xcols_kind: &str,
        yidxs: Option<Bound<'py, PyAny>>,
        yidxs_kind: &str,
    ) -> PyResult<(Py<PyAny>, bool)> {
        let (nrow, ncol) = x.as_array().dim();
        let mut y_owned = None;
        let y_view = y.as_array();
        let y_slice = vector_slice(&y_view, &mut y_owned);
        let (rows, cols, y_index) = subsets(
            xrows,
            xrows_kind,
            xcols,
            xcols_kind,
            yidxs,
            yidxs_kind,
            nrow,
            ncol,
            y_slice.len(),
        )?;
        let view = x.as_array();
        if nrow == 0 || ncol == 0 {
            return run(
                py,
                &[] as &[f64],
                nrow,
                ncol,
                1,
                0,
                y_slice,
                op,
                by_row,
                commute,
                na_rm,
                &rows,
                &cols,
                &y_index,
            );
        }
        if let Some((slice, row_stride, col_stride)) = contiguous(&view) {
            return run(
                py,
                slice,
                nrow,
                ncol,
                row_stride,
                col_stride,
                y_slice,
                op,
                by_row,
                commute,
                na_rm,
                &rows,
                &cols,
                &y_index,
            );
        }
        let owned = owned_column_major(view);
        run(
            py,
            &owned,
            nrow,
            ncol,
            1,
            nrow,
            y_slice,
            op,
            by_row,
            commute,
            na_rm,
            &rows,
            &cols,
            &y_index,
        )
    }

    #[pyfunction]
    #[pyo3(
        name = "apply_i32_f64",
        signature = (x, y, op, by_row, commute, na_rm, xrows=None, xrows_kind="all", xcols=None, xcols_kind="all", yidxs=None, yidxs_kind="all")
    )]
    fn apply_i32_f64<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, i32>,
        y: PyReadonlyArray1<'py, f64>,
        op: i32,
        by_row: bool,
        commute: bool,
        na_rm: bool,
        xrows: Option<Bound<'py, PyAny>>,
        xrows_kind: &str,
        xcols: Option<Bound<'py, PyAny>>,
        xcols_kind: &str,
        yidxs: Option<Bound<'py, PyAny>>,
        yidxs_kind: &str,
    ) -> PyResult<(Py<PyAny>, bool)> {
        let (nrow, ncol) = x.as_array().dim();
        let mut y_owned = None;
        let y_view = y.as_array();
        let y_slice = vector_slice(&y_view, &mut y_owned);
        let (rows, cols, y_index) = subsets(
            xrows,
            xrows_kind,
            xcols,
            xcols_kind,
            yidxs,
            yidxs_kind,
            nrow,
            ncol,
            y_slice.len(),
        )?;
        apply_i32(
            py, x, y_slice, op, by_row, commute, na_rm, &rows, &cols, &y_index,
        )
    }

    #[pyfunction]
    #[pyo3(
        name = "apply_i32_i32",
        signature = (x, y, op, by_row, commute, na_rm, xrows=None, xrows_kind="all", xcols=None, xcols_kind="all", yidxs=None, yidxs_kind="all")
    )]
    fn apply_i32_i32<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, i32>,
        y: PyReadonlyArray1<'py, i32>,
        op: i32,
        by_row: bool,
        commute: bool,
        na_rm: bool,
        xrows: Option<Bound<'py, PyAny>>,
        xrows_kind: &str,
        xcols: Option<Bound<'py, PyAny>>,
        xcols_kind: &str,
        yidxs: Option<Bound<'py, PyAny>>,
        yidxs_kind: &str,
    ) -> PyResult<(Py<PyAny>, bool)> {
        let (nrow, ncol) = x.as_array().dim();
        let mut y_owned = None;
        let y_view = y.as_array();
        let y_slice = vector_slice(&y_view, &mut y_owned);
        let (rows, cols, y_index) = subsets(
            xrows,
            xrows_kind,
            xcols,
            xcols_kind,
            yidxs,
            yidxs_kind,
            nrow,
            ncol,
            y_slice.len(),
        )?;
        apply_i32(
            py, x, y_slice, op, by_row, commute, na_rm, &rows, &cols, &y_index,
        )
    }

    #[pymodule]
    fn xopy(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(apply_f64_f64, m)?)?;
        m.add_function(wrap_pyfunction!(apply_f64_i32, m)?)?;
        m.add_function(wrap_pyfunction!(apply_i32_f64, m)?)?;
        m.add_function(wrap_pyfunction!(apply_i32_i32, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{
        Answer, Op, Subset, na_real, operate, validate_int, validate_logical, NA_INTEGER,
        NA_REAL_BITS,
    };

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

    #[test]
    fn column_recycle_matches_the_manual_layout() {
        let x = vec![1.0, 2.0, 3.0, 4.0];
        let y = vec![10.0, 20.0];
        let (answer, overflow) = operate(
            &x,
            2,
            2,
            1,
            2,
            &y,
            &Subset::All,
            &Subset::All,
            &Subset::All,
            Op::Add,
            false,
            false,
            false,
        )
        .unwrap();
        assert!(!overflow);
        assert_eq!(f64_of(answer), vec![11.0, 13.0, 22.0, 24.0]);

        let (by_row, _) = operate(
            &x,
            2,
            2,
            1,
            2,
            &y,
            &Subset::All,
            &Subset::All,
            &Subset::All,
            Op::Add,
            true,
            false,
            false,
        )
        .unwrap();
        assert_eq!(f64_of(by_row), vec![11.0, 23.0, 12.0, 24.0]);
    }

    #[test]
    fn manual_example_keeps_the_missing_sum() {
        let x = vec![1.0, 2.0, 3.0, na_real(), 5.0, 6.0];
        let y = vec![1_i32, 2];
        let (answer, _) = operate(
            &x,
            3,
            2,
            1,
            3,
            &y,
            &Subset::All,
            &Subset::All,
            &Subset::All,
            Op::Add,
            false,
            false,
            false,
        )
        .unwrap();
        let values = f64_of(answer);
        assert_eq!(values[0], 2.0);
        assert!(values[1].is_nan());
        assert_eq!(&values[2..], &[4.0, 6.0, 4.0, 8.0]);

        let y_row = vec![1_i32, 2, 3];
        let (by_row, _) = operate(
            &x,
            3,
            2,
            1,
            3,
            &y_row,
            &Subset::All,
            &Subset::All,
            &Subset::All,
            Op::Add,
            true,
            false,
            false,
        )
        .unwrap();
        let values = f64_of(by_row);
        assert_eq!(values[0], 2.0);
        assert!(values[1].is_nan());
        assert_eq!(&values[2..], &[5.0, 6.0, 5.0, 9.0]);
    }

    #[test]
    fn na_rm_substitutes_and_integer_na_casts_to_the_int_min_double() {
        let x = vec![na_real(), 2.0];
        let y = vec![NA_INTEGER, 3];
        let (answer, overflow) = operate(
            &x,
            2,
            1,
            1,
            2,
            &y,
            &Subset::All,
            &Subset::All,
            &Subset::All,
            Op::Add,
            false,
            false,
            true,
        )
        .unwrap();
        assert!(!overflow);
        let values = f64_of(answer);
        assert_eq!(values[0], -2_147_483_648.0);
        assert_eq!(values[1], 5.0);

        let both = vec![NA_INTEGER];
        let (answer, overflow) = operate(
            &both,
            1,
            1,
            1,
            1,
            &both,
            &Subset::All,
            &Subset::All,
            &Subset::All,
            Op::Add,
            false,
            false,
            true,
        )
        .unwrap();
        assert!(overflow);
        assert_eq!(i32_of(answer), vec![NA_INTEGER]);

        let (quiet, overflow) = operate(
            &both,
            1,
            1,
            1,
            1,
            &both,
            &Subset::All,
            &Subset::All,
            &Subset::All,
            Op::Add,
            false,
            false,
            false,
        )
        .unwrap();
        assert!(!overflow);
        assert_eq!(i32_of(quiet), vec![NA_INTEGER]);
    }

    #[test]
    fn integer_overflow_uses_negative_int_max_as_the_limit() {
        let x = vec![2_000_000_000, 1];
        let y = vec![2_000_000_000];
        let (answer, overflow) = operate(
            &x,
            2,
            1,
            1,
            2,
            &y,
            &Subset::All,
            &Subset::All,
            &Subset::All,
            Op::Add,
            false,
            false,
            false,
        )
        .unwrap();
        assert!(overflow);
        assert_eq!(i32_of(answer), vec![NA_INTEGER, 2_000_000_001]);

        let exact = vec![-2_147_483_647];
        let step = vec![-1];
        let (answer, overflow) = operate(
            &exact,
            1,
            1,
            1,
            1,
            &step,
            &Subset::All,
            &Subset::All,
            &Subset::All,
            Op::Add,
            false,
            false,
            false,
        )
        .unwrap();
        assert!(overflow);
        assert_eq!(i32_of(answer), vec![NA_INTEGER]);
    }

    #[test]
    fn subtraction_ignores_na_rm_and_division_is_double() {
        let x = vec![1_i32, NA_INTEGER];
        let y = vec![0_i32];
        let (answer, _) = operate(
            &x,
            2,
            1,
            1,
            2,
            &y,
            &Subset::All,
            &Subset::All,
            &Subset::All,
            Op::Sub,
            false,
            false,
            true,
        )
        .unwrap();
        assert_eq!(i32_of(answer), vec![1, NA_INTEGER]);

        let (answer, overflow) = operate(
            &x,
            2,
            1,
            1,
            2,
            &y,
            &Subset::All,
            &Subset::All,
            &Subset::All,
            Op::Div,
            false,
            false,
            false,
        )
        .unwrap();
        assert!(!overflow);
        let values = f64_of(answer);
        assert!(values[0].is_infinite() && values[0].is_sign_positive());
        assert!(values[1].is_nan());
        assert_eq!(values[1].to_bits(), NA_REAL_BITS);
    }

    #[test]
    fn yidxs_may_pass_the_end_and_rows_may_not() {
        assert!(validate_int(&[1, 9], 2, false).is_err());
        assert_eq!(
            validate_int(&[1, 9], 2, true).unwrap(),
            Subset::At(vec![Some(0), None])
        );
        assert_eq!(
            validate_logical(&[1, 0, 1], 1, true).unwrap(),
            Subset::At(vec![Some(0), None])
        );
    }
}
