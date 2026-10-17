//! Regression linear binning, ported from KernSmooth `src/rlbin.f`.
//!
//! A point exactly equal to `b` is placed on the last bin. That correction is
//! part of `rlbin` and is not part of `linbin`.

/// Bin regression pairs onto `m` equally spaced grid points from `a` to `b`.
///
/// Returns `(xcounts, ycounts)`. `truncate` drops pairs outside `[a, b]`.
/// Otherwise those pairs contribute their full weight to the nearest end bin.
pub fn rlbin(x: &[f64], y: &[f64], a: f64, b: f64, m: usize, truncate: bool) -> (Vec<f64>, Vec<f64>) {
    let mut xcounts = vec![0.0; m];
    let mut ycounts = vec![0.0; m];
    if m < 2 {
        return (xcounts, ycounts);
    }

    let delta = (b - a) / (m as f64 - 1.0);
    let count = x.len().min(y.len());
    for index in 0..count {
        let xi = x[index];
        let yi = y[index];
        let lxi = ((xi - a) / delta) + 1.0;
        let mut li = fortran_int(lxi);
        let mut rem = lxi - li as f64;
        if xi == b {
            li = m as i64 - 1;
            rem = 1.0;
        }

        if li >= 1 && (li as usize) < m {
            let slot = (li as usize) - 1;
            let stay = 1.0 - rem;
            xcounts[slot] += stay;
            xcounts[slot + 1] += rem;
            ycounts[slot] += stay * yi;
            ycounts[slot + 1] += rem * yi;
        }
        if li < 1 && !truncate {
            xcounts[0] += 1.0;
            ycounts[0] += yi;
        }
        if li >= m as i64 && !truncate {
            xcounts[m - 1] += 1.0;
            ycounts[m - 1] += yi;
        }
    }
    (xcounts, ycounts)
}

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
    #[pyo3(name = "rlbin")]
    fn rlbin_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray1<'py, f64>,
        y: PyReadonlyArray1<'py, f64>,
        a: f64,
        b: f64,
        m: usize,
        truncate: bool,
    ) -> PyResult<(Bound<'py, numpy::PyArray1<f64>>, Bound<'py, numpy::PyArray1<f64>>)> {
        let xs = x
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        let ys = y
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        if xs.len() != ys.len() {
            return Err(PyValueError::new_err("x and y must have the same length"));
        }
        let (xcounts, ycounts) = crate::rlbin(xs, ys, a, b, m, truncate);
        Ok((xcounts.into_pyarray(py), ycounts.into_pyarray(py)))
    }

    #[pymodule]
    fn rlbin(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(rlbin_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::rlbin;

    #[test]
    fn splits_an_interior_pair() {
        let (xcounts, ycounts) = rlbin(&[0.25], &[10.0], 0.0, 1.0, 3, true);
        assert!((xcounts[0] - 0.5).abs() < 1e-12);
        assert!((xcounts[1] - 0.5).abs() < 1e-12);
        assert!((ycounts[0] - 5.0).abs() < 1e-12);
        assert!((ycounts[1] - 5.0).abs() < 1e-12);
    }

    #[test]
    fn exact_right_endpoint_lands_on_the_last_bin() {
        let (xcounts, ycounts) = rlbin(&[1.0], &[30.0], 0.0, 1.0, 3, true);
        assert_eq!(xcounts, vec![0.0, 0.0, 1.0]);
        assert_eq!(ycounts, vec![0.0, 0.0, 30.0]);
    }

    #[test]
    fn truncation_drops_points_outside_the_grid() {
        let (xcounts, ycounts) = rlbin(&[-0.2], &[4.0], 0.0, 1.0, 3, true);
        assert!(xcounts.iter().all(|value| *value == 0.0));
        assert!(ycounts.iter().all(|value| *value == 0.0));
    }
}
