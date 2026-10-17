//! Bin counts, ported from matrixStats `src/binCounts.c` and
//! `src/binCounts_lowlevel_template.h`.
//!
//! `right` selects right-closed, left-open bins `(bx[j], bx[j + 1]]`.
//! Otherwise the bins are left-closed and right-open, `[bx[j], bx[j + 1])`.
//! `x` is sorted before counting. Missing `x` values are dropped.

mod indices;

use indices::{take, Subscripts};

const INT_MAX: i32 = i32::MAX;

/// Count finite `x` values into the bins defined by ordered break points `bx`.
pub fn bin_counts(
    x: &[f64],
    idxs: &Subscripts,
    bx: &[f64],
    right: bool,
) -> Result<Vec<i32>, String> {
    validate_bx(bx)?;
    let mut values = take(x, idxs)?;
    values.retain(|value| !value.is_nan());
    values.sort_unstable_by(|a, b| a.total_cmp(b));
    Ok(count_sorted(&values, bx, right))
}

pub fn validate_bx(bx: &[f64]) -> Result<(), String> {
    if bx.iter().any(|value| value.is_infinite()) {
        return Err("Argument 'bx' must not contain infinite values".to_string());
    }
    if bx.iter().any(|value| value.is_nan()) {
        return Err("Argument 'bx' must not contain missing values".to_string());
    }
    if bx.len() < 2 {
        return Err(format!(
            "Argument 'bx' must specify at least two bin boundaries (= one bin): {}",
            bx.len()
        ));
    }
    if bx.windows(2).any(|pair| pair[0] > pair[1]) {
        return Err("Argument 'bx' is not ordered".to_string());
    }
    Ok(())
}

fn in_first(x: f64, left: f64, right: bool) -> bool {
    if right {
        x <= left
    } else {
        x < left
    }
}

fn in_next(x: f64, edge: f64, right: bool) -> bool {
    if right {
        x > edge
    } else {
        x >= edge
    }
}

fn count_sorted(x: &[f64], bx: &[f64], right: bool) -> Vec<i32> {
    let nbins = bx.len() - 1;
    let mut count = vec![0i32; nbins];
    if nbins == 0 {
        return count;
    }

    let mut ii = 0usize;
    while ii < x.len() && in_first(x[ii], bx[0], right) {
        ii += 1;
    }

    let mut jj = 0usize;
    let mut n = 0i32;
    while ii < x.len() {
        if jj >= nbins {
            break;
        }
        while jj < nbins && in_next(x[ii], bx[jj + 1], right) {
            count[jj] = n;
            jj += 1;
            n = 0;
        }
        if jj >= nbins {
            break;
        }
        if n == INT_MAX {
            break;
        }
        n += 1;
        ii += 1;
    }
    if jj < nbins {
        count[jj] = n;
    }
    count
}

#[cfg(feature = "python")]
mod py {
    use numpy::{IntoPyArray, PyReadonlyArray1};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::indices::{parse_subscripts, Subscripts};
    use crate::bin_counts;

    #[pyfunction]
    #[pyo3(name = "bin_counts", signature = (x, bx, idxs=None, right=true))]
    fn bin_counts_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray1<'py, f64>,
        bx: PyReadonlyArray1<'py, f64>,
        idxs: Option<Bound<'py, PyAny>>,
        right: bool,
    ) -> PyResult<Bound<'py, numpy::PyArray1<i32>>> {
        let x = owned_f64(&x)?;
        let bx = owned_f64(&bx)?;
        let sub = match idxs {
            Some(obj) => parse_subscripts(&obj)?,
            None => Subscripts::All,
        };
        let counts = bin_counts(&x, &sub, &bx, right).map_err(PyValueError::new_err)?;
        Ok(counts.into_pyarray(py))
    }

    fn owned_f64(array: &PyReadonlyArray1<'_, f64>) -> PyResult<Vec<f64>> {
        if let Ok(slice) = array.as_slice() {
            return Ok(slice.to_vec());
        }
        Ok(array.as_array().iter().copied().collect())
    }

    #[pymodule]
    fn bincounts(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(bin_counts_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::bin_counts;
    use crate::indices::Subscripts;

    fn counts(x: &[f64], bx: &[f64], right: bool) -> Vec<i32> {
        bin_counts(x, &Subscripts::All, bx, right).unwrap()
    }

    #[test]
    fn right_closed_and_left_closed_keep_the_break() {
        let x = [0.0, 1.0, 2.0, 5.0, 10.0];
        let bx: Vec<f64> = (0..=10).map(|v| v as f64).collect();
        assert_eq!(
            counts(&x, &bx, true),
            vec![1, 1, 0, 0, 1, 0, 0, 0, 0, 1]
        );
        assert_eq!(
            counts(&x, &bx, false),
            vec![1, 1, 1, 0, 0, 1, 0, 0, 0, 0]
        );
    }

    #[test]
    fn missing_x_is_dropped_and_empty_input_is_zero() {
        assert_eq!(
            counts(&[1.0, f64::NAN, 2.0, f64::NAN, 3.0], &[0.5, 1.5, 2.5, 3.5], false),
            vec![1, 1, 1]
        );
        assert_eq!(counts(&[], &[0.0, 1.0, 2.0], true), vec![0, 0]);
    }

    #[test]
    fn duplicate_breaks_alternate_empty_bins() {
        let x: Vec<f64> = (1..=10).map(|v| v as f64).collect();
        let bx: Vec<f64> = (1..=10).flat_map(|v| [v as f64, v as f64]).collect();
        let expected: Vec<i32> = (0..19).map(|i| i32::from(i % 2 == 1)).collect();
        assert_eq!(counts(&x, &bx, false), expected);
    }

    #[test]
    fn points_outside_and_unsorted_input() {
        assert_eq!(counts(&[1.0, 2.0, 3.0], &[-9.0, 0.0], true), vec![0]);
        assert_eq!(counts(&[3.0, 1.0, 2.0, 2.0], &[1.0, 2.0, 3.0], true), vec![2, 1]);
    }

    #[test]
    fn bx_errors() {
        assert!(bin_counts(&[1.0], &Subscripts::All, &[1.0, f64::INFINITY], true).is_err());
        assert!(bin_counts(&[1.0], &Subscripts::All, &[1.0, f64::NAN], true).is_err());
        assert!(bin_counts(&[1.0], &Subscripts::All, &[3.0, 1.0], true).is_err());
        assert!(bin_counts(&[1.0], &Subscripts::All, &[1.0], true).is_err());
    }

    #[test]
    fn subset_is_applied_before_counting() {
        let x = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0];
        let idxs = Subscripts::Int(vec![Some(3), Some(0), Some(5), Some(1), Some(5)]);
        let counts = bin_counts(&x, &idxs, &[0.0, 2.0, 4.0, 7.0], false).unwrap();
        assert_eq!(counts, vec![1, 1, 2]);
    }
}
