//! Row-major indexes to column-major indexes, from matrixStats `src/indexByRow.c`.
//!
//! `indexByRow` does not call `validateIndices`. `idxs = NULL` visits every
//! cell in row-major order and returns the 1-based column-major position.
//! A supplied `idxs` is the same row-major numbering. Zero and negative
//! values are errors. The C routine subtracts one in a 32-bit int, so the
//! integer NA (`i32::MIN`) wraps; the installed function then reports that
//! original value on the "larger than" path.

/// Translate row-major indexes into column-major indexes.
///
/// `nrow` and `ncol` are the template matrix, stored column-major as in R.
/// `idxs` is 1-based and row-major. `None` selects every cell.
pub fn index_by_row(nrow: i32, ncol: i32, idxs: Option<&[i32]>) -> Result<Vec<i32>, String> {
    let n_max = matrix_length(nrow, ncol)?;
    match idxs {
        None => Ok(every_cell(nrow, ncol, n_max)),
        Some(idxs) => map_idxs(nrow, ncol, n_max, idxs),
    }
}

/// Element count, or the C error for a negative dimension or a product past
/// `2^31 - 1`. The product is a double, matching `indexByRow`.
fn matrix_length(nrow: i32, ncol: i32) -> Result<usize, String> {
    let mut n_max = 1.0_f64;
    for dim in [nrow, ncol] {
        if dim < 0 {
            return Err(format!("Argument 'dim' specifies a negative value: {dim}"));
        }
        n_max *= f64::from(dim);
        if n_max > 2_147_483_647.0 {
            return Err(format!(
                "Argument 'dim' ({nrow},{ncol}) specifies a matrix that has more than 2^31-1 elements: {n_max:.0}"
            ));
        }
    }
    Ok((i64::from(nrow) * i64::from(ncol)) as usize)
}

/// `idxs == NULL` branch of `indexByRow_i`.
fn every_cell(nrow: i32, ncol: i32, n: usize) -> Vec<i32> {
    let mut ans = vec![0_i32; n];
    let mut row: i64 = 1;
    let mut col: i64 = 0;
    let nrow_i = i64::from(nrow);
    let ncol_i = i64::from(ncol);
    for slot in &mut ans {
        *slot = (row + col * nrow_i) as i32;
        col += 1;
        if col == ncol_i {
            row += 1;
            col = 0;
        }
    }
    ans
}

/// Supplied `idxs` branch of `indexByRow_i`.
fn map_idxs(nrow: i32, ncol: i32, n_max: usize, idxs: &[i32]) -> Result<Vec<i32>, String> {
    let n_max = n_max as i64;
    let nrow_i = i64::from(nrow);
    let ncol_i = i64::from(ncol);
    let mut ans = Vec::with_capacity(idxs.len());
    for &raw in idxs {
        // `idxs_ptr[i] - 1` is a C int subtraction. Only `NA_integer_` wraps.
        let idx = i64::from(raw.wrapping_sub(1));
        if idx < 0 {
            return Err(format!(
                "Argument 'idxs' may only contain positive indices: {raw}"
            ));
        }
        if idx >= n_max {
            return Err(format!(
                "Argument 'idxs' contains indices larger than {n_max}: {raw}"
            ));
        }
        let col = idx / ncol_i;
        let row = idx % ncol_i;
        ans.push((col + nrow_i * row + 1) as i32);
    }
    Ok(ans)
}

#[cfg(feature = "python")]
mod py {
    use numpy::{IntoPyArray, PyArray1, PyReadonlyArray1};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    #[pyfunction]
    #[pyo3(name = "index_by_row")]
    #[pyo3(signature = (nrow, ncol, idxs=None))]
    fn index_by_row_py<'py>(
        py: Python<'py>,
        nrow: i32,
        ncol: i32,
        idxs: Option<PyReadonlyArray1<'py, i32>>,
    ) -> PyResult<Bound<'py, PyArray1<i32>>> {
        let result = match idxs {
            None => crate::index_by_row(nrow, ncol, None),
            Some(arr) => {
                let slice = arr
                    .as_slice()
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                crate::index_by_row(nrow, ncol, Some(slice))
            }
        };
        let values = result.map_err(PyValueError::new_err)?;
        Ok(values.into_pyarray(py))
    }

    #[pymodule]
    fn indexbyrow(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(index_by_row_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::index_by_row;

    #[test]
    fn null_walks_the_template_by_rows() {
        assert_eq!(
            index_by_row(5, 4, None).unwrap(),
            vec![1, 6, 11, 16, 2, 7, 12, 17, 3, 8, 13, 18, 4, 9, 14, 19, 5, 10, 15, 20]
        );
        assert_eq!(index_by_row(2, 3, None).unwrap(), vec![1, 3, 5, 2, 4, 6]);
        assert_eq!(index_by_row(1, 1, None).unwrap(), vec![1]);
        assert_eq!(index_by_row(4, 1, None).unwrap(), vec![1, 2, 3, 4]);
        assert_eq!(index_by_row(1, 4, None).unwrap(), vec![1, 2, 3, 4]);
    }

    #[test]
    fn supplied_indexes_keep_order_and_duplicates() {
        assert_eq!(index_by_row(5, 4, Some(&[1, 3, 7])).unwrap(), vec![1, 11, 12]);
        assert_eq!(index_by_row(2, 3, Some(&[2, 2, 1])).unwrap(), vec![3, 3, 1]);
        assert_eq!(index_by_row(2, 3, Some(&[6, 1, 4])).unwrap(), vec![6, 1, 2]);
        assert!(index_by_row(2, 3, Some(&[])).unwrap().is_empty());
    }

    #[test]
    fn zero_and_negative_indexes_are_errors() {
        let err = index_by_row(5, 4, Some(&[-1, -2])).unwrap_err();
        assert_eq!(err, "Argument 'idxs' may only contain positive indices: -1");
        let err = index_by_row(1, 1, Some(&[0])).unwrap_err();
        assert_eq!(err, "Argument 'idxs' may only contain positive indices: 0");
        let err = index_by_row(2, 2, Some(&[1, -3])).unwrap_err();
        assert_eq!(err, "Argument 'idxs' may only contain positive indices: -3");
    }

    #[test]
    fn integer_na_is_reported_as_larger_than_the_matrix() {
        let na = i32::MIN;
        let err = index_by_row(2, 3, Some(&[na])).unwrap_err();
        assert_eq!(
            err,
            "Argument 'idxs' contains indices larger than 6: -2147483648"
        );
        let err = index_by_row(2, 3, Some(&[7])).unwrap_err();
        assert_eq!(err, "Argument 'idxs' contains indices larger than 6: 7");
        let err = index_by_row(2, 3, Some(&[i32::MAX])).unwrap_err();
        assert_eq!(
            err,
            "Argument 'idxs' contains indices larger than 6: 2147483647"
        );
    }

    #[test]
    fn empty_and_negative_dimensions() {
        assert!(index_by_row(0, 4, None).unwrap().is_empty());
        assert!(index_by_row(3, 0, None).unwrap().is_empty());
        let err = index_by_row(0, 4, Some(&[1])).unwrap_err();
        assert_eq!(err, "Argument 'idxs' contains indices larger than 0: 1");
        let err = index_by_row(-1, 2, None).unwrap_err();
        assert_eq!(err, "Argument 'dim' specifies a negative value: -1");
        let err = index_by_row(i32::MIN, 2, None).unwrap_err();
        assert_eq!(
            err,
            "Argument 'dim' specifies a negative value: -2147483648"
        );
    }

    #[test]
    fn product_past_integer_max_uses_the_double_text() {
        let err = index_by_row(2_147_483_647, 2, Some(&[1])).unwrap_err();
        assert_eq!(
            err,
            "Argument 'dim' (2147483647,2) specifies a matrix that has more than 2^31-1 elements: 4294967294"
        );
        let err = index_by_row(100_000_001, 100_000_001, Some(&[1])).unwrap_err();
        assert_eq!(
            err,
            "Argument 'dim' (100000001,100000001) specifies a matrix that has more than 2^31-1 elements: 10000000200000000"
        );
        assert_eq!(index_by_row(2_147_483_647, 1, Some(&[1])).unwrap(), vec![1]);
    }
}
