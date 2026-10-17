//! Bin means, ported from matrixStats `src/binMeans.c` and
//! `src/binMeans_lowlevel_template.h`.
//!
//! `right` selects right-closed, left-open bins `(bx[j], bx[j + 1]]`.
//! Otherwise the bins are left-closed and right-open, `[bx[j], bx[j + 1])`.
//! Pairs are ordered by `x`. Missing `x` is always dropped. Missing `y` is
//! dropped when `na_rm` is set. An empty bin has a missing mean and a zero count.

mod indices;

use indices::{positions, Subscripts};

const INT_MAX: u64 = i32::MAX as u64;

/// Mean of `y` in each bin of `x`, and the integer count of each bin.
pub fn bin_means(
    y: &[f64],
    x: &[f64],
    idxs: &Subscripts,
    bx: &[f64],
    na_rm: bool,
    y_is_double: bool,
    right: bool,
) -> Result<(Vec<f64>, Vec<i32>), String> {
    if y_is_double && y.iter().any(|value| value.is_infinite()) {
        return Err("Argument 'y' must not contain infinite values".to_string());
    }
    if y.len() != x.len() {
        return Err(format!(
            "Argument 'y' and 'x' have different lengths: {} != {}",
            y.len(),
            x.len()
        ));
    }
    validate_bx(bx)?;

    let index = positions(x.len(), idxs)?;
    let mut pairs: Vec<(f64, f64)> = index.into_iter().map(|i| (x[i], y[i])).collect();
    pairs.retain(|(position, _)| !position.is_nan());
    if na_rm {
        pairs.retain(|(_, value)| !value.is_nan());
    }
    pairs.sort_unstable_by(|a, b| a.0.total_cmp(&b.0));
    let positions: Vec<f64> = pairs.iter().map(|pair| pair.0).collect();
    let values: Vec<f64> = pairs.iter().map(|pair| pair.1).collect();
    Ok(means_sorted(&values, &positions, bx, right))
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

fn store(means: &mut [f64], count: &mut [i32], bin: usize, n: u64, sum: f64) {
    count[bin] = if n > INT_MAX { i32::MAX } else { n as i32 };
    means[bin] = if n > 0 { sum / (n as f64) } else { f64::NAN };
}

fn means_sorted(y: &[f64], x: &[f64], bx: &[f64], right: bool) -> (Vec<f64>, Vec<i32>) {
    let nbins = bx.len() - 1;
    let mut means = vec![f64::NAN; nbins];
    let mut count = vec![0i32; nbins];
    if nbins == 0 {
        return (means, count);
    }

    let mut ii = 0usize;
    while ii < x.len() && in_first(x[ii], bx[0], right) {
        ii += 1;
    }

    let mut jj = 0usize;
    let mut n = 0u64;
    let mut sum = 0.0f64;
    while ii < x.len() {
        if jj >= nbins {
            break;
        }
        while jj < nbins && in_next(x[ii], bx[jj + 1], right) {
            store(&mut means, &mut count, jj, n, sum);
            sum = 0.0;
            n = 0;
            jj += 1;
        }
        if jj >= nbins {
            break;
        }
        sum += y[ii];
        n += 1;
        if n % 1_048_576 == 0 && !sum.is_finite() {
            break;
        }
        ii += 1;
    }
    if jj < nbins {
        store(&mut means, &mut count, jj, n, sum);
    }
    (means, count)
}

#[cfg(feature = "python")]
mod py {
    use numpy::{IntoPyArray, PyReadonlyArray1};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::bin_means;
    use crate::indices::{parse_subscripts, Subscripts};

    #[pyfunction]
    #[pyo3(name = "bin_means", signature = (y, x, bx, idxs=None, na_rm=true, right=true, y_is_double=true))]
    fn bin_means_py<'py>(
        py: Python<'py>,
        y: PyReadonlyArray1<'py, f64>,
        x: PyReadonlyArray1<'py, f64>,
        bx: PyReadonlyArray1<'py, f64>,
        idxs: Option<Bound<'py, PyAny>>,
        na_rm: bool,
        right: bool,
        y_is_double: bool,
    ) -> PyResult<(
        Bound<'py, numpy::PyArray1<f64>>,
        Bound<'py, numpy::PyArray1<i32>>,
    )> {
        let y = owned_f64(&y)?;
        let x = owned_f64(&x)?;
        let bx = owned_f64(&bx)?;
        let sub = match idxs {
            Some(obj) => parse_subscripts(&obj)?,
            None => Subscripts::All,
        };
        let (means, counts) =
            bin_means(&y, &x, &sub, &bx, na_rm, y_is_double, right).map_err(PyValueError::new_err)?;
        Ok((means.into_pyarray(py), counts.into_pyarray(py)))
    }

    fn owned_f64(array: &PyReadonlyArray1<'_, f64>) -> PyResult<Vec<f64>> {
        if let Ok(slice) = array.as_slice() {
            return Ok(slice.to_vec());
        }
        Ok(array.as_array().iter().copied().collect())
    }

    #[pymodule]
    fn binmeans(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(bin_means_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::bin_means;
    use crate::indices::Subscripts;

    fn means(y: &[f64], x: &[f64], bx: &[f64], right: bool) -> (Vec<f64>, Vec<i32>) {
        bin_means(y, x, &Subscripts::All, bx, true, true, right).unwrap()
    }

    #[test]
    fn break_lands_in_the_closed_side() {
        let (left, left_n) = means(&[10.0, 20.0, 30.0], &[1.0, 1.0, 2.0], &[0.0, 1.0, 2.0], false);
        assert!(left[0].is_nan());
        assert_eq!(left[1], 15.0);
        assert_eq!(left_n, vec![0, 2]);

        let (right, right_n) = means(&[10.0, 20.0, 30.0], &[1.0, 1.0, 2.0], &[0.0, 1.0, 2.0], true);
        assert_eq!(right, vec![15.0, 30.0]);
        assert_eq!(right_n, vec![2, 1]);
    }

    #[test]
    fn missing_y_follows_na_rm_and_missing_x_is_always_dropped() {
        let y = [1.0, f64::NAN, 3.0, 4.0];
        let x = [1.0, 2.0, 3.0, 4.0];
        let bx = [0.5, 2.5, 4.5];
        let (dropped, dropped_n) = bin_means(&y, &x, &Subscripts::All, &bx, true, true, false).unwrap();
        assert_eq!(dropped, vec![1.0, 3.5]);
        assert_eq!(dropped_n, vec![1, 2]);

        let (kept, kept_n) = bin_means(&y, &x, &Subscripts::All, &bx, false, true, false).unwrap();
        assert!(kept[0].is_nan());
        assert_eq!(kept[1], 3.5);
        assert_eq!(kept_n, vec![2, 2]);

        let (no_x, no_x_n) = bin_means(
            &[10.0, 20.0],
            &[f64::NAN, 1.0],
            &Subscripts::All,
            &[0.0, 2.0],
            false,
            true,
            true,
        )
        .unwrap();
        assert_eq!(no_x, vec![20.0]);
        assert_eq!(no_x_n, vec![1]);
    }

    #[test]
    fn empty_bins_and_infinite_y() {
        let (means, counts) = means(&[1.0, 2.0], &[6.0, 7.0], &[0.0, 5.0, 10.0], false);
        assert!(means[0].is_nan());
        assert_eq!(means[1], 1.5);
        assert_eq!(counts, vec![0, 2]);
        assert!(bin_means(
            &[1.0, f64::INFINITY],
            &[1.0, 2.0],
            &Subscripts::All,
            &[0.0, 3.0],
            true,
            true,
            true
        )
        .is_err());
        assert!(bin_means(&[1.0], &[1.0, 2.0], &Subscripts::All, &[0.0, 3.0], true, true, true).is_err());
    }
}
