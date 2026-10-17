//! Linear binning, ported from KernSmooth `src/linbin.f`.
//!
//! Fortran `int` truncates toward zero. A point exactly at `b` has bin index
//! `M`, so the split branch does not run: with truncation it is dropped, and
//! without truncation its full weight lands on the last bin.

/// Bin univariate points onto `m` equally spaced grid points from `a` to `b`.
///
/// `truncate` drops points outside `[a, b]`. Otherwise those points contribute
/// their full weight to the nearest end bin.
pub fn linbin(x: &[f64], a: f64, b: f64, m: usize, truncate: bool) -> Vec<f64> {
    let mut gcnts = vec![0.0; m];
    if m < 2 {
        return gcnts;
    }

    let delta = (b - a) / (m as f64 - 1.0);
    for &xi in x {
        let lxi = ((xi - a) / delta) + 1.0;
        let li = fortran_int(lxi);
        let rem = lxi - li as f64;

        if li >= 1 && li < m as i64 {
            let idx = (li as usize) - 1;
            gcnts[idx] += 1.0 - rem;
            gcnts[idx + 1] += rem;
        }
        if li < 1 && !truncate {
            gcnts[0] += 1.0;
        }
        if li >= m as i64 && !truncate {
            gcnts[m - 1] += 1.0;
        }
    }
    gcnts
}

/// Fortran `INT` for a finite value: truncate toward zero.
fn fortran_int(value: f64) -> i64 {
    if !value.is_finite() {
        return 0;
    }
    value.trunc() as i64
}

#[cfg(feature = "python")]
mod py {
    use numpy::{IntoPyArray, PyReadonlyArray1};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    #[pyfunction]
    #[pyo3(name = "linbin")]
    fn linbin_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray1<'py, f64>,
        a: f64,
        b: f64,
        m: usize,
        truncate: bool,
    ) -> PyResult<Bound<'py, numpy::PyArray1<f64>>> {
        let slice = x
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        let counts = crate::linbin(slice, a, b, m, truncate);
        Ok(counts.into_pyarray(py))
    }

    #[pymodule]
    fn linbin(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(linbin_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::linbin;

    #[test]
    fn splits_an_interior_point() {
        let counts = linbin(&[0.1], 0.0, 1.0, 5, true);
        assert_eq!(counts.len(), 5);
        assert!((counts[0] - 0.6).abs() < 1e-12);
        assert!((counts[1] - 0.4).abs() < 1e-12);
        assert_eq!(&counts[2..], &[0.0, 0.0, 0.0]);
    }

    #[test]
    fn truncation_drops_points_outside_the_grid() {
        let counts = linbin(&[-0.2, 1.2], 0.0, 1.0, 5, true);
        assert!(counts.iter().all(|c| *c == 0.0));
    }

    #[test]
    fn without_truncation_end_points_take_the_full_weight() {
        let counts = linbin(&[-0.2, 1.2], 0.0, 1.0, 5, false);
        assert!((counts[0] - 1.0).abs() < 1e-12);
        assert!((counts[4] - 1.0).abs() < 1e-12);
        assert_eq!(&counts[1..4], &[0.0, 0.0, 0.0]);
    }

    #[test]
    fn exact_right_endpoint_follows_fortran_int() {
        let dropped = linbin(&[1.0], 0.0, 1.0, 5, true);
        assert!(dropped.iter().all(|c| *c == 0.0));

        let kept = linbin(&[1.0], 0.0, 1.0, 5, false);
        assert!((kept[4] - 1.0).abs() < 1e-12);
        assert_eq!(&kept[..4], &[0.0, 0.0, 0.0, 0.0]);
    }
}
