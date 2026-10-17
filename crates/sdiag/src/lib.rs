//! Diagonal of a binned local-polynomial smoother, ported from KernSmooth `src/sdiag.f`.
//!
//! The inverse of each local moment matrix comes from the `linpack` crate.
//! `indic` is one-based, as produced by the R bandwidth discretisation.

use linpack::{dgefa, dgedi};

/// Diagonal entries of the binned smoother matrix.
///
/// `degree` is the local polynomial degree. KernSmooth's `dpill` uses `1`.
pub fn sdiag(
    xcounts: &[f64],
    delta: f64,
    hdisc: &[f64],
    lvec: &[i32],
    indic: &[i32],
    degree: i32,
) -> Result<Vec<f64>, String> {
    let prepared = prepare(xcounts, delta, hdisc, lvec, indic, degree)?;
    let mut curve = vec![0.0; prepared.m];
    let mut matrix = vec![0.0; prepared.ipp * prepared.ipp];
    let mut pivots = vec![0_usize; prepared.ipp];
    for k in 0..prepared.m {
        fill_moment(&mut matrix, &prepared.ss, prepared.m, prepared.ipp, k);
        dgefa(&mut matrix, prepared.ipp, prepared.ipp, &mut pivots);
        dgedi(&mut matrix, prepared.ipp, prepared.ipp, &pivots, 1);
        curve[k] = matrix[0];
    }
    Ok(curve)
}

struct Prepared {
    m: usize,
    ipp: usize,
    ss: Vec<f64>,
}

fn prepare(
    xcounts: &[f64],
    delta: f64,
    hdisc: &[f64],
    lvec: &[i32],
    indic: &[i32],
    degree: i32,
) -> Result<Prepared, String> {
    let m = xcounts.len();
    if indic.len() != m {
        return Err("xcounts and indic must have the same length".into());
    }
    if hdisc.len() != lvec.len() {
        return Err("hdisc and lvec must have the same length".into());
    }
    if degree < 0 {
        return Err("degree must be non-negative".into());
    }
    let q = hdisc.len();
    if q == 0 || m == 0 {
        return Err("the bandwidth grid and the bin grid must be non-empty".into());
    }
    if lvec.iter().any(|value| *value < 0) {
        return Err("lvec must be non-negative".into());
    }

    let ipp = (degree as usize) + 1;
    let ippp = (2 * degree as usize) + 1;
    let mut fkap = vec![0.0; 2 * lvec.iter().map(|value| *value as usize).sum::<usize>() + q];
    let mut midpts = vec![0_i32; q];
    let mut ss = vec![0.0; m * ippp];

    let mut mid = lvec[0] + 1;
    for index in 0..(q - 1) {
        midpts[index] = mid;
        fill_weights(&mut fkap, mid, lvec[index], delta, hdisc[index]);
        mid += lvec[index] + lvec[index + 1] + 1;
    }
    midpts[q - 1] = mid;
    fill_weights(&mut fkap, mid, lvec[q - 1], delta, hdisc[q - 1]);

    for k in 1..=m {
        if xcounts[k - 1] == 0.0 {
            continue;
        }
        for band in 1..=q {
            let half = lvec[band - 1] as i64;
            let lower = (k as i64 - half).max(1) as usize;
            let upper = (k as i64 + half).min(m as i64) as usize;
            for j in lower..=upper {
                if indic[j - 1] != band as i32 {
                    continue;
                }
                let weight = fkap[(k as i32 - j as i32 + midpts[band - 1]) as usize - 1];
                let xterm = xcounts[k - 1] * weight;
                ss[j - 1] += xterm;
                let mut factor = 1.0;
                for power in 2..=ippp {
                    factor *= delta * (k as f64 - j as f64);
                    ss[(power - 1) * m + (j - 1)] += xterm * factor;
                }
            }
        }
    }
    Ok(Prepared { m, ipp, ss })
}

fn fill_moment(matrix: &mut [f64], ss: &[f64], m: usize, ipp: usize, k: usize) {
    for row in 0..ipp {
        for col in 0..ipp {
            matrix[col * ipp + row] = ss[(row + col) * m + k];
        }
    }
}

fn fill_weights(fkap: &mut [f64], mid: i32, half: i32, delta: f64, bandwidth: f64) {
    let center = (mid as usize) - 1;
    fkap[center] = 1.0;
    for step in 1..=half {
        let distance = delta * f64::from(step) / bandwidth;
        let weight = (-distance * distance / 2.0).exp();
        fkap[center + step as usize] = weight;
        fkap[center - step as usize] = weight;
    }
}

#[cfg(feature = "python")]
mod py {
    use numpy::{IntoPyArray, PyReadonlyArray1};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    #[pyfunction]
    #[pyo3(name = "sdiag")]
    fn sdiag_py<'py>(
        py: Python<'py>,
        xcounts: PyReadonlyArray1<'py, f64>,
        delta: f64,
        hdisc: PyReadonlyArray1<'py, f64>,
        lvec: PyReadonlyArray1<'py, i32>,
        indic: PyReadonlyArray1<'py, i32>,
        degree: i32,
    ) -> PyResult<Bound<'py, numpy::PyArray1<f64>>> {
        let curve = crate::sdiag(
            slice_f64(&xcounts)?,
            delta,
            slice_f64(&hdisc)?,
            slice_i32(&lvec)?,
            slice_i32(&indic)?,
            degree,
        )
        .map_err(PyValueError::new_err)?;
        Ok(curve.into_pyarray(py))
    }

    fn slice_f64<'a>(array: &'a PyReadonlyArray1<'a, f64>) -> PyResult<&'a [f64]> {
        array
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))
    }

    fn slice_i32<'a>(array: &'a PyReadonlyArray1<'a, i32>) -> PyResult<&'a [i32]> {
        array
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))
    }

    #[pymodule]
    fn sdiag(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(sdiag_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::sdiag;

    #[test]
    fn local_constant_diagonal_is_the_reciprocal_weight() {
        let curve = sdiag(&[2.0], 1.0, &[1.0], &[0], &[1], 0).unwrap();
        assert!((curve[0] - 0.5).abs() < 1e-12);
    }
}
