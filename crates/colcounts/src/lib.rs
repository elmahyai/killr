//! Column counts and `count()`, ported from matrixStats `src/colCounts.c`.
//!
//! `what` is 0 for "all", 1 for "any", and 2 for "count". Column routines
//! keep the tally in `f64` because `count()` must return a value above
//! `.Machine$integer.max`. A missing tally is `(double) NA_R_XLEN_T`, which
//! is `-2^63`. `colCounts` then casts that vector to integer, mapping the
//! sentinel to `NA_INTEGER`.
//!
//! `count()` treats `x` as one column and passes `idxs` with out-of-bounds
//! allowed. Row and column margins reject a positive index past the end.

mod indices;

use indices::{Subset, margin_at, margin_len, validate_int, validate_logical, validate_real};

/// R's integer NA. `NA_LOGICAL` equals `NA_INTEGER`.
const NA_INTEGER: i32 = i32::MIN;

/// `(double) NA_R_XLEN_T` on a long-vector build. Exactly `-2^63`.
const NA_COUNT: f64 = i64::MIN as f64;

/// Which question `colCounts.c` answers.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum What {
    /// `what = 0`. One means every selected element equals `value`.
    All,
    /// `what = 1`. One means some selected element equals `value`.
    Any,
    /// `what = 2`. How many selected elements equal `value`.
    Count,
}

impl What {
    pub fn from_i32(what: i32) -> Result<Self, String> {
        match what {
            0 => Ok(What::All),
            1 => Ok(What::Any),
            2 => Ok(What::Count),
            other => Err(format!(
                "INTERNAL ERROR: Unknown value of 'what' for rowCounts: {other}"
            )),
        }
    }
}

trait Element: Copy {
    fn is_missing(self) -> bool;
    fn same(self, other: Self) -> bool;
    fn missing_value() -> Self;
}

impl Element for f64 {
    fn is_missing(self) -> bool {
        self.is_nan()
    }

    fn same(self, other: Self) -> bool {
        self == other
    }

    fn missing_value() -> Self {
        f64::NAN
    }
}

impl Element for i32 {
    fn is_missing(self) -> bool {
        self == NA_INTEGER
    }

    fn same(self, other: Self) -> bool {
        self == other
    }

    fn missing_value() -> Self {
        NA_INTEGER
    }
}

/// Column-wise all, any, or count for a double matrix.
///
/// The result is one `i32` per selected column. `i32::MIN` is R's NA.
/// Counts that do not fit in a 32-bit integer become NA, matching the C cast.
pub fn col_counts_f64(
    x: &[f64],
    nrow: usize,
    ncol: usize,
    row_stride: usize,
    col_stride: usize,
    rows: &Subset,
    cols: &Subset,
    value: f64,
    what: What,
    na_rm: bool,
) -> Result<Vec<i32>, String> {
    Ok(col_counts(x, nrow, ncol, row_stride, col_stride, rows, cols, value, what, na_rm)?
        .into_iter()
        .map(f64_count_to_i32)
        .collect())
}

/// Column-wise all, any, or count for an integer or logical matrix.
pub fn col_counts_i32(
    x: &[i32],
    nrow: usize,
    ncol: usize,
    row_stride: usize,
    col_stride: usize,
    rows: &Subset,
    cols: &Subset,
    value: i32,
    what: What,
    na_rm: bool,
) -> Result<Vec<i32>, String> {
    Ok(col_counts(x, nrow, ncol, row_stride, col_stride, rows, cols, value, what, na_rm)?
        .into_iter()
        .map(f64_count_to_i32)
        .collect())
}

/// `count()` for a double vector.
///
/// The result is the raw tally. [`NA_COUNT`] means R's NA. A finite value
/// above `i32::MAX` is returned as a double by the R wrapper; smaller
/// tallies, including a tally equal to `.Machine$integer.max`, stay integer.
pub fn count_f64(x: &[f64], idxs: &Subset, value: f64, what: What, na_rm: bool) -> Result<f64, String> {
    let tallies = col_counts(x, x.len(), 1, 1, 1, idxs, &Subset::All, value, what, na_rm)?;
    Ok(tallies[0])
}

/// `count()` for an integer or logical vector. See [`count_f64`].
pub fn count_i32(x: &[i32], idxs: &Subset, value: i32, what: What, na_rm: bool) -> Result<f64, String> {
    let tallies = col_counts(x, x.len(), 1, 1, 1, idxs, &Subset::All, value, what, na_rm)?;
    Ok(tallies[0])
}

fn col_counts<T: Element>(
    x: &[T],
    nrow: usize,
    ncol: usize,
    row_stride: usize,
    col_stride: usize,
    rows: &Subset,
    cols: &Subset,
    value: T,
    what: What,
    na_rm: bool,
) -> Result<Vec<f64>, String> {
    ensure_span(x.len(), nrow, ncol, row_stride, col_stride)?;
    let nrows = margin_len(rows, nrow);
    let ncols = margin_len(cols, ncol);
    let mut ans = Vec::with_capacity(ncols);
    for jj in 0..ncols {
        let col = margin_at(cols, jj);
        ans.push(scan_column(
            x, row_stride, col_stride, rows, nrows, col, value, what, na_rm,
        ));
    }
    Ok(ans)
}

fn scan_column<T: Element>(
    x: &[T],
    row_stride: usize,
    col_stride: usize,
    rows: &Subset,
    nrows: usize,
    col: Option<usize>,
    value: T,
    what: What,
    na_rm: bool,
) -> f64 {
    if value.is_missing() {
        return scan_missing(x, row_stride, col_stride, rows, nrows, col, what);
    }
    match what {
        What::All => {
            let mut na = false;
            for ii in 0..nrows {
                let xvalue = load(x, row_stride, col_stride, margin_at(rows, ii), col);
                if xvalue.same(value) {
                } else if na_rm && xvalue.is_missing() {
                } else if !na_rm && xvalue.is_missing() {
                    na = true;
                } else {
                    return 0.0;
                }
            }
            if na { NA_COUNT } else { 1.0 }
        }
        What::Any => {
            let mut na = false;
            for ii in 0..nrows {
                let xvalue = load(x, row_stride, col_stride, margin_at(rows, ii), col);
                if xvalue.same(value) {
                    return 1.0;
                } else if na_rm && xvalue.is_missing() {
                } else if !na_rm && xvalue.is_missing() {
                    na = true;
                }
            }
            if na { NA_COUNT } else { 0.0 }
        }
        What::Count => {
            let mut count = 0_i64;
            for ii in 0..nrows {
                let xvalue = load(x, row_stride, col_stride, margin_at(rows, ii), col);
                if xvalue.same(value) {
                    count += 1;
                } else if !na_rm && xvalue.is_missing() {
                    return NA_COUNT;
                }
            }
            count as f64
        }
    }
}

fn scan_missing<T: Element>(
    x: &[T],
    row_stride: usize,
    col_stride: usize,
    rows: &Subset,
    nrows: usize,
    col: Option<usize>,
    what: What,
) -> f64 {
    match what {
        What::All => {
            for ii in 0..nrows {
                let xvalue = load(x, row_stride, col_stride, margin_at(rows, ii), col);
                if !xvalue.is_missing() {
                    return 0.0;
                }
            }
            1.0
        }
        What::Any => {
            for ii in 0..nrows {
                let xvalue = load(x, row_stride, col_stride, margin_at(rows, ii), col);
                if xvalue.is_missing() {
                    return 1.0;
                }
            }
            0.0
        }
        What::Count => {
            let mut count = 0_i64;
            for ii in 0..nrows {
                let xvalue = load(x, row_stride, col_stride, margin_at(rows, ii), col);
                if xvalue.is_missing() {
                    count += 1;
                }
            }
            count as f64
        }
    }
}

fn f64_count_to_i32(count: f64) -> i32 {
    if count == NA_COUNT || !count.is_finite() {
        return NA_INTEGER;
    }
    if count > i32::MAX as f64 || count < i32::MIN as f64 {
        return NA_INTEGER;
    }
    count as i32
}

fn load<T: Element>(
    x: &[T],
    row_stride: usize,
    col_stride: usize,
    row: Option<usize>,
    col: Option<usize>,
) -> T {
    match (row, col) {
        (Some(row), Some(col)) => x[row * row_stride + col * col_stride],
        _ => T::missing_value(),
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

fn resolve_subset(
    kind: &str,
    int_idxs: Option<&[i64]>,
    real_idxs: Option<&[f64]>,
    logical_idxs: Option<&[i8]>,
    max_idx: usize,
    allow_out_of_bounds: bool,
) -> Result<Subset, String> {
    match kind {
        "all" => Ok(Subset::All),
        "int" => validate_int(int_idxs.unwrap_or(&[]), max_idx, allow_out_of_bounds),
        "real" => validate_real(real_idxs.unwrap_or(&[]), max_idx, allow_out_of_bounds),
        "logical" => validate_logical(logical_idxs.unwrap_or(&[]), max_idx, allow_out_of_bounds),
        _ => Err("idxs can only be integer, numeric, or logical".to_string()),
    }
}

#[cfg(feature = "python")]
mod py {
    use numpy::ndarray::{Array1, ArrayView1, ArrayView2};
    use numpy::{IntoPyArray, PyReadonlyArray1, PyReadonlyArray2};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::indices::Subset;
    use crate::{What, col_counts_f64, col_counts_i32, count_f64, count_i32, resolve_subset};

    fn parse_subset(
        obj: Option<&Bound<'_, PyAny>>,
        kind: &str,
        max_idx: usize,
        allow_out_of_bounds: bool,
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
                resolve_subset("int", Some(slice), None, None, max_idx, allow_out_of_bounds)
            }
            "real" => {
                let arr = obj.extract::<PyReadonlyArray1<f64>>()?;
                let slice = arr
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                resolve_subset("real", None, Some(slice), None, max_idx, allow_out_of_bounds)
            }
            "logical" => {
                let arr = obj.extract::<PyReadonlyArray1<i8>>()?;
                let slice = arr
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                resolve_subset(
                    "logical",
                    None,
                    None,
                    Some(slice),
                    max_idx,
                    allow_out_of_bounds,
                )
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
        if row_stride <= 0 || col_stride <= 0 {
            return None;
        }
        Some((slice, row_stride as usize, col_stride as usize))
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

    fn vector_data<T: Copy>(view: ArrayView1<'_, T>) -> Vec<T> {
        if let Some(slice) = view.as_slice() {
            slice.to_vec()
        } else {
            view.iter().copied().collect()
        }
    }

    fn counts_to_py(py: Python<'_>, values: Vec<i32>) -> PyResult<Py<PyAny>> {
        let arr = Array1::from_vec(values);
        Ok(arr.into_pyarray(py).into_any().unbind())
    }

    #[pyfunction]
    #[pyo3(
        name = "col_counts_f64",
        signature = (x, what, value, na_rm, rows=None, rows_kind="all", cols=None, cols_kind="all")
    )]
    fn col_counts_f64_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        what: i32,
        value: f64,
        na_rm: bool,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
    ) -> PyResult<Py<PyAny>> {
        let what = What::from_i32(what).map_err(PyValueError::new_err)?;
        let view = x.as_array();
        let (nrow, ncol) = view.dim();
        let row_subset = parse_subset(rows.as_ref(), rows_kind, nrow, false)?;
        let col_subset = parse_subset(cols.as_ref(), cols_kind, ncol, false)?;
        let result = if nrow == 0 || ncol == 0 {
            col_counts_f64(&[], nrow, ncol, 1, 0, &row_subset, &col_subset, value, what, na_rm)
        } else if let Some((slice, row_stride, col_stride)) = contiguous(&view) {
            col_counts_f64(
                slice,
                nrow,
                ncol,
                row_stride,
                col_stride,
                &row_subset,
                &col_subset,
                value,
                what,
                na_rm,
            )
        } else {
            let owned = owned_column_major(view);
            col_counts_f64(
                &owned,
                nrow,
                ncol,
                1,
                nrow,
                &row_subset,
                &col_subset,
                value,
                what,
                na_rm,
            )
        }
        .map_err(PyValueError::new_err)?;
        counts_to_py(py, result)
    }

    #[pyfunction]
    #[pyo3(
        name = "col_counts_i32",
        signature = (x, what, value, na_rm, rows=None, rows_kind="all", cols=None, cols_kind="all")
    )]
    fn col_counts_i32_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, i32>,
        what: i32,
        value: i32,
        na_rm: bool,
        rows: Option<Bound<'py, PyAny>>,
        rows_kind: &str,
        cols: Option<Bound<'py, PyAny>>,
        cols_kind: &str,
    ) -> PyResult<Py<PyAny>> {
        let what = What::from_i32(what).map_err(PyValueError::new_err)?;
        let view = x.as_array();
        let (nrow, ncol) = view.dim();
        let row_subset = parse_subset(rows.as_ref(), rows_kind, nrow, false)?;
        let col_subset = parse_subset(cols.as_ref(), cols_kind, ncol, false)?;
        let result = if nrow == 0 || ncol == 0 {
            col_counts_i32(&[], nrow, ncol, 1, 0, &row_subset, &col_subset, value, what, na_rm)
        } else if let Some((slice, row_stride, col_stride)) = contiguous(&view) {
            col_counts_i32(
                slice,
                nrow,
                ncol,
                row_stride,
                col_stride,
                &row_subset,
                &col_subset,
                value,
                what,
                na_rm,
            )
        } else {
            let owned = owned_column_major(view);
            col_counts_i32(
                &owned,
                nrow,
                ncol,
                1,
                nrow,
                &row_subset,
                &col_subset,
                value,
                what,
                na_rm,
            )
        }
        .map_err(PyValueError::new_err)?;
        counts_to_py(py, result)
    }

    #[pyfunction]
    #[pyo3(
        name = "count_f64",
        signature = (x, what, value, na_rm, idxs=None, idxs_kind="all")
    )]
    fn count_f64_py<'py>(
        x: PyReadonlyArray1<'py, f64>,
        what: i32,
        value: f64,
        na_rm: bool,
        idxs: Option<Bound<'py, PyAny>>,
        idxs_kind: &str,
    ) -> PyResult<f64> {
        let what = What::from_i32(what).map_err(PyValueError::new_err)?;
        let view = x.as_array();
        let n = view.len();
        let subset = parse_subset(idxs.as_ref(), idxs_kind, n, true)?;
        let data = vector_data(view);
        count_f64(&data, &subset, value, what, na_rm).map_err(PyValueError::new_err)
    }

    #[pyfunction]
    #[pyo3(
        name = "count_i32",
        signature = (x, what, value, na_rm, idxs=None, idxs_kind="all")
    )]
    fn count_i32_py<'py>(
        x: PyReadonlyArray1<'py, i32>,
        what: i32,
        value: i32,
        na_rm: bool,
        idxs: Option<Bound<'py, PyAny>>,
        idxs_kind: &str,
    ) -> PyResult<f64> {
        let what = What::from_i32(what).map_err(PyValueError::new_err)?;
        let view = x.as_array();
        let n = view.len();
        let subset = parse_subset(idxs.as_ref(), idxs_kind, n, true)?;
        let data = vector_data(view);
        count_i32(&data, &subset, value, what, na_rm).map_err(PyValueError::new_err)
    }

    #[pymodule]
    fn colcounts(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(col_counts_f64_py, m)?)?;
        m.add_function(wrap_pyfunction!(col_counts_i32_py, m)?)?;
        m.add_function(wrap_pyfunction!(count_f64_py, m)?)?;
        m.add_function(wrap_pyfunction!(count_i32_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{NA_INTEGER, What, col_counts_i32, count_i32};
    use crate::indices::Subset;

    const NA: i32 = NA_INTEGER;

    #[test]
    fn manual_integer_matrix_counts_columns() {
        let x = [0, 1, 2, 3, 4, 2, 3, 7, 8, 4, NA, 11];
        let counts = col_counts_i32(&x, 4, 3, 1, 4, &Subset::All, &Subset::All, 2, What::Count, false)
            .unwrap();
        assert_eq!(counts, vec![1, 1, NA]);
        let nas = col_counts_i32(&x, 4, 3, 1, 4, &Subset::All, &Subset::All, NA, What::Count, false)
            .unwrap();
        assert_eq!(nas, vec![0, 0, 1]);
        let kept = col_counts_i32(&x, 4, 3, 1, 4, &Subset::All, &Subset::All, 2, What::Count, true)
            .unwrap();
        assert_eq!(kept, vec![1, 1, 0]);
    }

    #[test]
    fn count_allows_an_index_past_the_end() {
        let x = [1, 2, 3, 4, 5];
        let idxs = Subset::At(vec![Some(0), None]);
        let tally = count_i32(&x, &idxs, 1, What::Count, false).unwrap();
        assert_eq!(tally, i64::MIN as f64);
        let kept = count_i32(&x, &idxs, 1, What::Count, true).unwrap();
        assert_eq!(kept, 1.0);
    }
}
