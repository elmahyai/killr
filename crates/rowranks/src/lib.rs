//! Row and column ranks, ported from matrixStats `src/rowRanksWithTies.c`.
//!
//! `ties` follows the C codes: 1 average, 2 first, 3 last, 4 random, 5 max,
//! 6 min, 7 dense. Missing doubles are every NaN, including R's NA, and they
//! are written back as `NA_real_`. Missing integers are `i32::MIN`. Signed
//! zeros compare equal, so they share a tie. `rows` and `cols` follow
//! `validateIndices`: missing means every position, values are 1-based, zeros
//! are dropped, and negatives exclude. A missing index reads as R's NA.
//!
//! The result has one row per selected row and one column per selected
//! column. `by_row` ranks along columns. Otherwise each column is ranked and
//! the matrix keeps that shape; the R wrapper transposes it when
//! `preserveShape` is false.

use std::cmp::Ordering;

/// R's integer NA. `NA_LOGICAL` equals `NA_INTEGER`.
const NA_INTEGER: i32 = i32::MIN;

/// R's `NA_real_`: a NaN whose low 32 bits are 1954 (`0x7A2`).
const NA_REAL_BITS: u64 = 0x7ff0_0000_0000_07a2;

/// How ties are ranked. The numeric values match `rowRanksWithTies.c`.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Ties {
    /// `tiesMethod = 1`. Identical values share the mean of their ranks.
    Average = 1,
    /// `tiesMethod = 2`. Earlier positions receive the smaller ranks.
    First = 2,
    /// `tiesMethod = 3`. Earlier positions receive the larger ranks.
    Last = 3,
    /// `tiesMethod = 4`. Ranks inside a tie are shuffled.
    Random = 4,
    /// `tiesMethod = 5`. Identical values share the maximum rank.
    Max = 5,
    /// `tiesMethod = 6`. Identical values share the minimum rank.
    Min = 6,
    /// `tiesMethod = 7`. Identical values share one rank and the next value
    /// continues at the following integer.
    Dense = 7,
}

impl Ties {
    pub fn from_i32(ties: i32) -> Result<Self, String> {
        match ties {
            1 => Ok(Ties::Average),
            2 => Ok(Ties::First),
            3 => Ok(Ties::Last),
            4 => Ok(Ties::Random),
            5 => Ok(Ties::Max),
            6 => Ok(Ties::Min),
            7 => Ok(Ties::Dense),
            _ => Err(format!(
                "Argument 'tiesMethod' is out of range [1,7]: {ties}"
            )),
        }
    }

    fn average(self) -> bool {
        matches!(self, Ties::Average)
    }
}

/// 1-based subscript vector. `All` selects every position in order.
#[derive(Clone, Debug, PartialEq)]
pub enum Subset {
    All,
    /// 0-based positions. `None` is an NA index.
    At(Vec<Option<usize>>),
}

/// Ranks of the selected matrix. Average ties are [`Answer::F64`].
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

enum Slot {
    Missing,
    Int(i32),
    Real(f64),
}

trait RankNum: Copy {
    fn is_missing(self) -> bool;
    fn ties_less(self, other: Self) -> bool;
    fn ties_eq(self, other: Self) -> bool;
}

impl RankNum for f64 {
    fn is_missing(self) -> bool {
        self.is_nan()
    }

    fn ties_less(self, other: Self) -> bool {
        self < other
    }

    fn ties_eq(self, other: Self) -> bool {
        self == other
    }
}

impl RankNum for i32 {
    fn is_missing(self) -> bool {
        self == NA_INTEGER
    }

    fn ties_less(self, other: Self) -> bool {
        self < other
    }

    fn ties_eq(self, other: Self) -> bool {
        self == other
    }
}

/// Ranks of each row, or of each column when `by_row` is false.
///
/// `x` is addressed with the given strides. Column-major storage, matching
/// R, uses `row_stride == 1` and `col_stride == nrow`. The result is
/// row-major with one row per selected row. `rng` is advanced only for
/// [`Ties::Random`].
pub fn row_ranks_f64(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    row_stride: usize,
    col_stride: usize,
    rows: &Subset,
    cols: &Subset,
    method: Ties,
    by_row: bool,
    rng: &mut u64,
) -> Result<Answer, String> {
    rank_matrix(
        x,
        nrow,
        ncol,
        row_stride,
        col_stride,
        rows,
        cols,
        method,
        by_row,
        rng,
        load_f64,
    )
}

/// Integer ranks. `i32::MIN` is R's NA. See [`row_ranks_f64`].
pub fn row_ranks_i32(
    x: &[i32],
    nrow: usize,
    ncol: usize,
    row_stride: usize,
    col_stride: usize,
    rows: &Subset,
    cols: &Subset,
    method: Ties,
    by_row: bool,
    rng: &mut u64,
) -> Result<Answer, String> {
    rank_matrix(
        x,
        nrow,
        ncol,
        row_stride,
        col_stride,
        rows,
        cols,
        method,
        by_row,
        rng,
        load_i32,
    )
}

fn rank_matrix<T, F>(
    x: &[T],
    nrow: usize,
    ncol: usize,
    row_stride: usize,
    col_stride: usize,
    rows: &Subset,
    cols: &Subset,
    method: Ties,
    by_row: bool,
    rng: &mut u64,
    load: F,
) -> Result<Answer, String>
where
    T: RankNum,
    F: Fn(&[T], usize, usize, Option<usize>, Option<usize>) -> T,
{
    ensure_span(x.len(), nrow, ncol, row_stride, col_stride)?;
    let row_pos = positions(rows, nrow);
    let col_pos = positions(cols, ncol);
    let nrows = row_pos.len();
    let ncols = col_pos.len();
    let n_out = nrows
        .checked_mul(ncols)
        .ok_or_else(|| "result dimensions overflow".to_string())?;
    let margin = if by_row { ncols } else { nrows };
    if margin > i32::MAX as usize {
        return Err("margin is longer than R's integer maximum".to_string());
    }

    let mut finite_pos = Vec::new();
    let mut group = Vec::new();
    let mut buf = Vec::with_capacity(margin);

    if method.average() {
        let mut ans = vec![f64::from_bits(NA_REAL_BITS); n_out];
        for ii in 0..if by_row { nrows } else { ncols } {
            fill_margin(
                &mut buf,
                x,
                row_stride,
                col_stride,
                &row_pos,
                &col_pos,
                ii,
                by_row,
                &load,
            );
            rank_values(&buf, method, rng, &mut finite_pos, &mut group, |p, slot| {
                let at = if by_row { ii * ncols + p } else { p * ncols + ii };
                ans[at] = match slot {
                    Slot::Missing => f64::from_bits(NA_REAL_BITS),
                    Slot::Real(value) => value,
                    Slot::Int(value) => f64::from(value),
                };
            });
        }
        return Ok(Answer::F64 {
            values: ans,
            nrow: nrows,
            ncol: ncols,
        });
    }

    let mut ans = vec![NA_INTEGER; n_out];
    for ii in 0..if by_row { nrows } else { ncols } {
        fill_margin(
            &mut buf,
            x,
            row_stride,
            col_stride,
            &row_pos,
            &col_pos,
            ii,
            by_row,
            &load,
        );
        rank_values(&buf, method, rng, &mut finite_pos, &mut group, |p, slot| {
            let at = if by_row { ii * ncols + p } else { p * ncols + ii };
            ans[at] = match slot {
                Slot::Missing => NA_INTEGER,
                Slot::Int(value) => value,
                Slot::Real(value) => value as i32,
            };
        });
    }
    Ok(Answer::I32 {
        values: ans,
        nrow: nrows,
        ncol: ncols,
    })
}

fn fill_margin<T, F>(
    buf: &mut Vec<T>,
    x: &[T],
    row_stride: usize,
    col_stride: usize,
    row_pos: &[Option<usize>],
    col_pos: &[Option<usize>],
    ii: usize,
    by_row: bool,
    load: &F,
) where
    T: Copy,
    F: Fn(&[T], usize, usize, Option<usize>, Option<usize>) -> T,
{
    buf.clear();
    if by_row {
        let row = row_pos[ii];
        for &col in col_pos {
            buf.push(load(x, row_stride, col_stride, row, col));
        }
    } else {
        let col = col_pos[ii];
        for &row in row_pos {
            buf.push(load(x, row_stride, col_stride, row, col));
        }
    }
}

fn rank_values<T, E>(
    values: &[T],
    method: Ties,
    rng: &mut u64,
    finite_pos: &mut Vec<usize>,
    group: &mut Vec<usize>,
    mut emit: E,
) where
    T: RankNum,
    E: FnMut(usize, Slot),
{
    finite_pos.clear();
    for (j, &value) in values.iter().enumerate() {
        if value.is_missing() {
            emit(j, Slot::Missing);
        } else {
            finite_pos.push(j);
        }
    }
    finite_pos.sort_by(|&left, &right| {
        let a = values[left];
        let b = values[right];
        if a.ties_less(b) {
            Ordering::Less
        } else if b.ties_less(a) {
            Ordering::Greater
        } else {
            Ordering::Equal
        }
    });

    let mut pos = 0usize;
    let mut dense = 0i32;
    while pos < finite_pos.len() {
        let start = pos;
        let current = values[finite_pos[pos]];
        pos += 1;
        while pos < finite_pos.len() && values[finite_pos[pos]].ties_eq(current) {
            pos += 1;
        }
        let end = pos;
        let first_tie = start as i32;
        let above_tie = end as i32;
        match method {
            Ties::Max => {
                for &p in &finite_pos[start..end] {
                    emit(p, Slot::Int(above_tie));
                }
            }
            Ties::Min => {
                for &p in &finite_pos[start..end] {
                    emit(p, Slot::Int(first_tie + 1));
                }
            }
            Ties::Average => {
                let rank = (f64::from(first_tie) + f64::from(above_tie) + 1.0) / 2.0;
                for &p in &finite_pos[start..end] {
                    emit(p, Slot::Real(rank));
                }
            }
            Ties::Dense => {
                dense += 1;
                for &p in &finite_pos[start..end] {
                    emit(p, Slot::Int(dense));
                }
            }
            Ties::First => {
                group.clear();
                group.extend_from_slice(&finite_pos[start..end]);
                group.sort_unstable();
                for (k, &p) in group.iter().enumerate() {
                    emit(p, Slot::Int(first_tie + 1 + k as i32));
                }
            }
            Ties::Last => {
                group.clear();
                group.extend_from_slice(&finite_pos[start..end]);
                group.sort_unstable();
                for (k, &p) in group.iter().enumerate() {
                    emit(p, Slot::Int(above_tie - k as i32));
                }
            }
            Ties::Random => {
                group.clear();
                group.extend_from_slice(&finite_pos[start..end]);
                shuffle(group, rng);
                for (k, &p) in group.iter().enumerate() {
                    emit(p, Slot::Int(first_tie + 1 + k as i32));
                }
            }
        }
    }
}

/// Fisher-Yates over `idxs[0..=last]`, matching `SHUFFLE_INT`.
fn shuffle(idxs: &mut [usize], rng: &mut u64) {
    let n = idxs.len();
    if n <= 1 {
        return;
    }
    let last = n - 1;
    for k in 0..last {
        let span = (last - k + 1) as f64;
        let offset = (unif(rng) * span) as usize;
        idxs.swap(k, k + offset);
    }
}

fn unif(state: &mut u64) -> f64 {
    let mut x = *state;
    x ^= x << 13;
    x ^= x >> 7;
    x ^= x << 17;
    if x == 0 {
        x = 0x9E37_79B9_7F4A_7C15;
    }
    *state = x;
    let mant = (x >> 11) | 1;
    (mant as f64) / ((1u64 << 53) as f64)
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
    use std::sync::atomic::{AtomicU64, Ordering};

    use numpy::ndarray::Array2;
    use numpy::{IntoPyArray, PyReadonlyArray1, PyReadonlyArray2};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::{
        validate_int, validate_logical, validate_real, Answer, Subset, Ties, row_ranks_f64,
        row_ranks_i32,
    };

    static RNG: AtomicU64 = AtomicU64::new(0xA24B_AED4_963E_E407);

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

    fn contiguous<'a, T: Copy>(view: &'a numpy::ndarray::ArrayView2<'a, T>) -> Option<(&'a [T], usize, usize)> {
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

    fn with_rng<T>(ties: i32, body: impl FnOnce(&mut u64) -> T) -> T {
        if ties == 4 {
            let mut state = RNG.load(Ordering::Relaxed);
            let result = body(&mut state);
            RNG.store(state, Ordering::Relaxed);
            result
        } else {
            let mut state = 0_u64;
            body(&mut state)
        }
    }

    fn ranks_f64_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        ties: i32,
        by_row: bool,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
    ) -> PyResult<Py<PyAny>> {
        let method = Ties::from_i32(ties).map_err(PyValueError::new_err)?;
        let view = x.as_array();
        let (nrow, ncol) = view.dim();
        let row_subset = parse_subset(rows.as_ref(), rows_kind, nrow)?;
        let col_subset = parse_subset(cols.as_ref(), cols_kind, ncol)?;
        let result = with_rng(ties, |rng| {
            if nrow == 0 || ncol == 0 {
                row_ranks_f64(&[], nrow, ncol, 1, 0, &row_subset, &col_subset, method, by_row, rng)
            } else if let Some((slice, row_stride, col_stride)) = contiguous(&view) {
                row_ranks_f64(
                    slice,
                    nrow,
                    ncol,
                    row_stride,
                    col_stride,
                    &row_subset,
                    &col_subset,
                    method,
                    by_row,
                    rng,
                )
            } else {
                let owned = owned_column_major(view);
                row_ranks_f64(
                    &owned,
                    nrow,
                    ncol,
                    1,
                    nrow,
                    &row_subset,
                    &col_subset,
                    method,
                    by_row,
                    rng,
                )
            }
        })
        .map_err(PyValueError::new_err)?;
        answer_to_py(py, result)
    }

    fn ranks_i32_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, i32>,
        ties: i32,
        by_row: bool,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
    ) -> PyResult<Py<PyAny>> {
        let method = Ties::from_i32(ties).map_err(PyValueError::new_err)?;
        let view = x.as_array();
        let (nrow, ncol) = view.dim();
        let row_subset = parse_subset(rows.as_ref(), rows_kind, nrow)?;
        let col_subset = parse_subset(cols.as_ref(), cols_kind, ncol)?;
        let result = with_rng(ties, |rng| {
            if nrow == 0 || ncol == 0 {
                row_ranks_i32(&[], nrow, ncol, 1, 0, &row_subset, &col_subset, method, by_row, rng)
            } else if let Some((slice, row_stride, col_stride)) = contiguous(&view) {
                row_ranks_i32(
                    slice,
                    nrow,
                    ncol,
                    row_stride,
                    col_stride,
                    &row_subset,
                    &col_subset,
                    method,
                    by_row,
                    rng,
                )
            } else {
                let owned = owned_column_major(view);
                row_ranks_i32(
                    &owned,
                    nrow,
                    ncol,
                    1,
                    nrow,
                    &row_subset,
                    &col_subset,
                    method,
                    by_row,
                    rng,
                )
            }
        })
        .map_err(PyValueError::new_err)?;
        answer_to_py(py, result)
    }

    #[pyfunction]
    #[pyo3(
        name = "row_ranks_f64",
        signature = (x, ties, by_row, rows=None, rows_kind="all", cols=None, cols_kind="all")
    )]
    fn row_ranks_f64_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        ties: i32,
        by_row: bool,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
    ) -> PyResult<Py<PyAny>> {
        ranks_f64_py(py, x, ties, by_row, rows, rows_kind, cols, cols_kind)
    }

    #[pyfunction]
    #[pyo3(
        name = "row_ranks_i32",
        signature = (x, ties, by_row, rows=None, rows_kind="all", cols=None, cols_kind="all")
    )]
    fn row_ranks_i32_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, i32>,
        ties: i32,
        by_row: bool,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
    ) -> PyResult<Py<PyAny>> {
        ranks_i32_py(py, x, ties, by_row, rows, rows_kind, cols, cols_kind)
    }

    #[pymodule]
    fn rowranks(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(row_ranks_f64_py, m)?)?;
        m.add_function(wrap_pyfunction!(row_ranks_i32_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{
        Answer, Subset, Ties, row_ranks_f64, row_ranks_i32, validate_int, NA_INTEGER, NA_REAL_BITS,
    };

    fn i32_of(answer: Answer) -> Vec<i32> {
        match answer {
            Answer::I32 { values, .. } => values,
            Answer::F64 { .. } => panic!("expected int32"),
        }
    }

    fn f64_of(answer: Answer) -> Vec<f64> {
        match answer {
            Answer::F64 { values, .. } => values,
            Answer::I32 { .. } => panic!("expected float64"),
        }
    }

    fn ranks_i32(x: &[i32], nrow: usize, ncol: usize, method: Ties, by_row: bool) -> Vec<i32> {
        let mut rng = 1_u64;
        i32_of(
            row_ranks_i32(
                x,
                nrow,
                ncol,
                1,
                nrow,
                &Subset::All,
                &Subset::All,
                method,
                by_row,
                &mut rng,
            )
            .unwrap(),
        )
    }

    #[test]
    fn ties_on_the_printed_integer_matrix() {
        // Column-major 3, 1, 3, 2 prints as
        // 3 3
        // 1 2
        let x = [3, 1, 3, 2];
        assert_eq!(ranks_i32(&x, 2, 2, Ties::Max, true), vec![2, 2, 1, 2]);
        assert_eq!(ranks_i32(&x, 2, 2, Ties::Min, true), vec![1, 1, 1, 2]);
        assert_eq!(ranks_i32(&x, 2, 2, Ties::First, true), vec![1, 2, 1, 2]);
        assert_eq!(ranks_i32(&x, 2, 2, Ties::Last, true), vec![2, 1, 1, 2]);
        assert_eq!(ranks_i32(&x, 2, 2, Ties::Dense, true), vec![1, 1, 1, 2]);
        let mut rng = 1_u64;
        let avg = row_ranks_f64(
            &[3.0, 1.0, 3.0, 2.0],
            2,
            2,
            1,
            2,
            &Subset::All,
            &Subset::All,
            Ties::Average,
            true,
            &mut rng,
        )
        .unwrap();
        assert_eq!(f64_of(avg), vec![1.5, 1.5, 1.0, 2.0]);
    }

    #[test]
    fn column_ranks_keep_the_selected_shape() {
        let x = [3, 1, 3, 2];
        assert_eq!(ranks_i32(&x, 2, 2, Ties::Max, false), vec![2, 2, 1, 1]);
    }

    #[test]
    fn signed_zeros_tie_and_nan_is_missing() {
        let mut rng = 1_u64;
        let zeros = row_ranks_f64(
            &[-0.0, 0.0, 1.0, -0.0],
            1,
            4,
            1,
            1,
            &Subset::All,
            &Subset::All,
            Ties::First,
            true,
            &mut rng,
        )
        .unwrap();
        assert_eq!(i32_of(zeros), vec![1, 2, 4, 3]);
        let maxed = row_ranks_f64(
            &[-0.0, 0.0, 1.0, -0.0],
            1,
            4,
            1,
            1,
            &Subset::All,
            &Subset::All,
            Ties::Max,
            true,
            &mut rng,
        )
        .unwrap();
        assert_eq!(i32_of(maxed), vec![3, 3, 4, 3]);

        let na = f64::from_bits(NA_REAL_BITS);
        let mixed = row_ranks_f64(
            &[3.0, na, f64::NAN, 3.0],
            1,
            4,
            1,
            1,
            &Subset::All,
            &Subset::All,
            Ties::First,
            true,
            &mut rng,
        )
        .unwrap();
        let values = i32_of(mixed);
        assert_eq!(values[0], 1);
        assert_eq!(values[1], NA_INTEGER);
        assert_eq!(values[2], NA_INTEGER);
        assert_eq!(values[3], 2);
    }

    #[test]
    fn random_permutes_only_the_tie() {
        let mut rng = 99_u64;
        let ranks = row_ranks_i32(
            &[1, 5, 1, 1],
            1,
            4,
            1,
            1,
            &Subset::All,
            &Subset::All,
            Ties::Random,
            true,
            &mut rng,
        )
        .unwrap();
        let values = i32_of(ranks);
        assert_eq!(values[1], 4);
        let mut tied = vec![values[0], values[2], values[3]];
        tied.sort_unstable();
        assert_eq!(tied, vec![1, 2, 3]);
    }

    #[test]
    fn index_rules_match_validate_indices() {
        assert_eq!(validate_int(&[0, 2, 0], 2).unwrap(), Subset::At(vec![Some(1)]));
        assert_eq!(validate_int(&[-2], 2).unwrap(), Subset::At(vec![Some(0)]));
        assert!(validate_int(&[1, 9], 2).is_err());
        let rows = validate_int(&[1, i32::MIN as i64], 2).unwrap();
        let mut rng = 1_u64;
        let ranks = row_ranks_i32(
            &[3, 1, 3, 2],
            2,
            2,
            1,
            2,
            &rows,
            &Subset::All,
            Ties::Max,
            true,
            &mut rng,
        )
        .unwrap();
        assert_eq!(i32_of(ranks), vec![2, 2, NA_INTEGER, NA_INTEGER]);
    }
}
