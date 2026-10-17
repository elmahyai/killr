//! Row counts, ported from matrixStats `src/rowCounts.c`.
//!
//! `what` is 0 for "all", 1 for "any", and 2 for "count". The R wrappers
//! pass `hasNA = TRUE`; that flag is unused in the C template. `rows` and
//! `cols` follow `validateIndicesCheckNA` with out-of-bounds rejected.
//!
//! A missing index reads as R's NA. For doubles, every NaN is missing,
//! including R's NA. For integers and logicals, missing is `i32::MIN`.
//! Logical data is stored as 0, 1, and `i32::MIN`. When `na.rm` is false, a
//! missing value makes a count `NA` and an all/any result stay undecided
//! until a definite false or true is seen.

mod indices;

use indices::{Subset, margin_at, margin_len, validate_int, validate_logical, validate_real};

/// R's integer NA. `NA_LOGICAL` equals `NA_INTEGER`.
const NA_INTEGER: i32 = i32::MIN;

/// Which question `rowCounts.c` answers.
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

/// Row-wise all, any, or count for a double matrix.
///
/// `x` is addressed with the given strides. Column-major storage, matching
/// R, uses `row_stride == 1` and `col_stride == nrow`. The result is one
/// `i32` per selected row. `i32::MIN` is R's NA.
pub fn row_counts_f64(
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
    row_counts(x, nrow, ncol, row_stride, col_stride, rows, cols, value, what, na_rm)
}

/// Row-wise all, any, or count for an integer or logical matrix.
///
/// Logical values are `0`, `1`, and [`NA_INTEGER`]. See [`row_counts_f64`].
pub fn row_counts_i32(
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
    row_counts(x, nrow, ncol, row_stride, col_stride, rows, cols, value, what, na_rm)
}

fn row_counts<T: Element>(
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
) -> Result<Vec<i32>, String> {
    ensure_span(x.len(), nrow, ncol, row_stride, col_stride)?;
    let nrows = margin_len(rows, nrow);
    let ncols = margin_len(cols, ncol);
    let mut ans = vec![
        match what {
            What::All => 1,
            What::Any | What::Count => 0,
        };
        nrows
    ];
    let value_missing = value.is_missing();

    for jj in 0..ncols {
        let col = margin_at(cols, jj);
        for ii in 0..nrows {
            if skip_row(ans[ii], what, value_missing) {
                continue;
            }
            let row = margin_at(rows, ii);
            let xvalue = load(x, row_stride, col_stride, row, col);
            if value_missing {
                apply_missing(&mut ans[ii], what, xvalue);
            } else {
                apply_value(&mut ans[ii], what, xvalue, value, na_rm);
            }
        }
    }
    Ok(ans)
}

fn skip_row(current: i32, what: What, value_missing: bool) -> bool {
    match what {
        What::All => current == 0,
        What::Any => {
            if value_missing {
                current != 0
            } else {
                current != 0 && current != NA_INTEGER
            }
        }
        What::Count => !value_missing && current == NA_INTEGER,
    }
}

fn apply_missing<T: Element>(ans: &mut i32, what: What, xvalue: T) {
    match what {
        What::All => {
            if !xvalue.is_missing() {
                *ans = 0;
            }
        }
        What::Any => {
            if xvalue.is_missing() {
                *ans = 1;
            }
        }
        What::Count => {
            if xvalue.is_missing() {
                *ans = ans.wrapping_add(1);
            }
        }
    }
}

fn apply_value<T: Element>(ans: &mut i32, what: What, xvalue: T, value: T, na_rm: bool) {
    let matches = xvalue.same(value);
    let missing = xvalue.is_missing();
    match what {
        What::All => {
            if matches {
            } else if na_rm && missing {
            } else if !na_rm && missing {
                *ans = NA_INTEGER;
            } else {
                *ans = 0;
            }
        }
        What::Any => {
            if matches {
                *ans = 1;
            } else if na_rm && missing {
            } else if !na_rm && missing {
                *ans = NA_INTEGER;
            }
        }
        What::Count => {
            if matches {
                *ans = ans.wrapping_add(1);
            } else if !na_rm && missing {
                *ans = NA_INTEGER;
            }
        }
    }
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
) -> Result<Subset, String> {
    match kind {
        "all" => Ok(Subset::All),
        "int" => validate_int(int_idxs.unwrap_or(&[]), max_idx, false),
        "real" => validate_real(real_idxs.unwrap_or(&[]), max_idx, false),
        "logical" => validate_logical(logical_idxs.unwrap_or(&[]), max_idx, false),
        _ => Err("idxs can only be integer, numeric, or logical".to_string()),
    }
}

#[cfg(feature = "python")]
mod py {
    use numpy::ndarray::{Array1, ArrayView2};
    use numpy::{IntoPyArray, PyReadonlyArray1, PyReadonlyArray2};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::{What, row_counts_f64, row_counts_i32};
    use crate::indices::Subset;
    use crate::resolve_subset;

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
                resolve_subset("int", Some(slice), None, None, max_idx)
            }
            "real" => {
                let arr = obj.extract::<PyReadonlyArray1<f64>>()?;
                let slice = arr
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                resolve_subset("real", None, Some(slice), None, max_idx)
            }
            "logical" => {
                let arr = obj.extract::<PyReadonlyArray1<i8>>()?;
                let slice = arr
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                resolve_subset("logical", None, None, Some(slice), max_idx)
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

    fn counts_to_py(py: Python<'_>, values: Vec<i32>) -> PyResult<Py<PyAny>> {
        let arr = Array1::from_vec(values);
        Ok(arr.into_pyarray(py).into_any().unbind())
    }

    fn stat_f64<'py>(
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
        let row_subset = parse_subset(rows.as_ref(), rows_kind, nrow)?;
        let col_subset = parse_subset(cols.as_ref(), cols_kind, ncol)?;
        let result = if nrow == 0 || ncol == 0 {
            row_counts_f64(&[], nrow, ncol, 1, 0, &row_subset, &col_subset, value, what, na_rm)
        } else if let Some((slice, row_stride, col_stride)) = contiguous(&view) {
            row_counts_f64(
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
            row_counts_f64(
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

    fn stat_i32<'py>(
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
        let row_subset = parse_subset(rows.as_ref(), rows_kind, nrow)?;
        let col_subset = parse_subset(cols.as_ref(), cols_kind, ncol)?;
        let result = if nrow == 0 || ncol == 0 {
            row_counts_i32(&[], nrow, ncol, 1, 0, &row_subset, &col_subset, value, what, na_rm)
        } else if let Some((slice, row_stride, col_stride)) = contiguous(&view) {
            row_counts_i32(
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
            row_counts_i32(
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
        name = "row_counts_f64",
        signature = (x, what, value, na_rm, rows=None, rows_kind="all", cols=None, cols_kind="all")
    )]
    fn row_counts_f64_py<'py>(
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
        stat_f64(py, x, what, value, na_rm, rows, rows_kind, cols, cols_kind)
    }

    #[pyfunction]
    #[pyo3(
        name = "row_counts_i32",
        signature = (x, what, value, na_rm, rows=None, rows_kind="all", cols=None, cols_kind="all")
    )]
    fn row_counts_i32_py<'py>(
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
        stat_i32(py, x, what, value, na_rm, rows, rows_kind, cols, cols_kind)
    }

    #[pymodule]
    fn rowcounts(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(row_counts_f64_py, m)?)?;
        m.add_function(wrap_pyfunction!(row_counts_i32_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{What, row_counts_i32};
    use crate::indices::Subset;

    const NA: i32 = i32::MIN;

    #[test]
    fn manual_integer_matrix_counts_twos_and_stops_on_na() {
        // Printed matrix, stored column-major:
        // 0 4  8
        // 1 2  4
        // 2 3 NA
        // 3 7 11
        let x = [0, 1, 2, 3, 4, 2, 3, 7, 8, 4, NA, 11];
        let counts = row_counts_i32(&x, 4, 3, 1, 4, &Subset::All, &Subset::All, 2, What::Count, false)
            .unwrap();
        assert_eq!(counts, vec![0, 1, NA, 0]);
        let kept = row_counts_i32(&x, 4, 3, 1, 4, &Subset::All, &Subset::All, 2, What::Count, true)
            .unwrap();
        assert_eq!(kept, vec![0, 1, 1, 0]);
    }
}
