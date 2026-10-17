//! Bivariate linear binning, ported from KernSmooth `src/linbin2D.f`.
//!
//! Fortran `int` truncates toward zero. A point exactly equal to `b1` or `b2`
//! has bin index `M` in that direction, so the split does not run and the
//! observation is ignored. Observations outside the mesh are ignored.

/// Bin paired observations onto an `m1` by `m2` grid.
///
/// The grid runs from `a1` to `b1` and from `a2` to `b2`. The returned vector
/// is row-major with `m1` rows and `m2` columns, the same layout as R's
/// `matrix(..., M1, M2)`: rows follow the first coordinate.
pub fn lbtwod(
    x1: &[f64],
    x2: &[f64],
    a1: f64,
    a2: f64,
    b1: f64,
    b2: f64,
    m1: usize,
    m2: usize,
) -> Vec<f64> {
    let mut gcnts = vec![0.0; m1.saturating_mul(m2)];
    if m1 < 2 || m2 < 2 {
        return gcnts;
    }

    let delta1 = (b1 - a1) / (m1 as f64 - 1.0);
    let delta2 = (b2 - a2) / (m2 as f64 - 1.0);
    let count = x1.len().min(x2.len());
    for index in 0..count {
        let lxi1 = ((x1[index] - a1) / delta1) + 1.0;
        let lxi2 = ((x2[index] - a2) / delta2) + 1.0;
        let li1 = fortran_int(lxi1);
        let li2 = fortran_int(lxi2);
        let rem1 = lxi1 - li1 as f64;
        let rem2 = lxi2 - li2 as f64;

        if li1 >= 1 && li2 >= 1 && li1 < m1 as i64 && li2 < m2 as i64 {
            let row = (li1 as usize) - 1;
            let col = (li2 as usize) - 1;
            let stay1 = 1.0 - rem1;
            let stay2 = 1.0 - rem2;
            gcnts[row * m2 + col] += stay1 * stay2;
            gcnts[(row + 1) * m2 + col] += rem1 * stay2;
            gcnts[row * m2 + (col + 1)] += stay1 * rem2;
            gcnts[(row + 1) * m2 + (col + 1)] += rem1 * rem2;
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
    #[pyo3(name = "lbtwod")]
    fn lbtwod_py<'py>(
        py: Python<'py>,
        x1: PyReadonlyArray1<'py, f64>,
        x2: PyReadonlyArray1<'py, f64>,
        a1: f64,
        a2: f64,
        b1: f64,
        b2: f64,
        m1: usize,
        m2: usize,
    ) -> PyResult<Bound<'py, numpy::PyArray1<f64>>> {
        let first = x1
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        let second = x2
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        if first.len() != second.len() {
            return Err(PyValueError::new_err("x1 and x2 must have the same length"));
        }
        let counts = crate::lbtwod(first, second, a1, a2, b1, b2, m1, m2);
        Ok(counts.into_pyarray(py))
    }

    #[pymodule]
    fn lbtwod(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(lbtwod_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::lbtwod;

    #[test]
    fn splits_an_interior_point_across_four_bins() {
        let counts = lbtwod(&[0.1], &[0.1], 0.0, 0.0, 1.0, 1.0, 5, 5);
        let grid = |row: usize, col: usize| counts[row * 5 + col];
        assert!((grid(0, 0) - 0.36).abs() < 1e-12);
        assert!((grid(1, 0) - 0.24).abs() < 1e-12);
        assert!((grid(0, 1) - 0.24).abs() < 1e-12);
        assert!((grid(1, 1) - 0.16).abs() < 1e-12);
        let rest: f64 = counts.iter().sum();
        assert!((rest - 1.0).abs() < 1e-12);
    }

    #[test]
    fn exact_lower_corner_lands_on_the_first_bin() {
        let counts = lbtwod(&[0.0], &[0.0], 0.0, 0.0, 1.0, 1.0, 3, 4);
        assert!((counts[0] - 1.0).abs() < 1e-12);
        assert!(counts[1..].iter().all(|value| *value == 0.0));
    }

    #[test]
    fn exact_upper_edge_is_ignored() {
        let on_b1 = lbtwod(&[1.0], &[0.25], 0.0, 0.0, 1.0, 1.0, 3, 3);
        let on_b2 = lbtwod(&[0.25], &[1.0], 0.0, 0.0, 1.0, 1.0, 3, 3);
        assert!(on_b1.iter().all(|value| *value == 0.0));
        assert!(on_b2.iter().all(|value| *value == 0.0));
    }

    #[test]
    fn points_outside_the_mesh_are_ignored() {
        let counts = lbtwod(&[-0.2, 1.2], &[0.25, -1.4], 0.0, 0.0, 1.0, 1.0, 4, 4);
        assert!(counts.iter().all(|value| *value == 0.0));
    }
}
