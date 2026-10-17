//! Binned local polynomial fit, ported from KernSmooth `src/locpoly.f`.
//!
//! The linear solve uses the `linpack` crate. The returned curve is the raw
//! coefficient. The R wrapper multiplies it by `gamma(drv + 1)` afterwards.

use linpack::{dgefa, dgesl};

/// Fit a local polynomial of `degree` to binned counts.
///
/// `indic` is one-based, as produced by the R bandwidth discretisation.
/// `lvec[i]` is the half-width, in bins, of bandwidth `hdisc[i]`.
pub fn locpol(
    xcounts: &[f64],
    ycounts: &[f64],
    drv: i32,
    delta: f64,
    hdisc: &[f64],
    lvec: &[i32],
    indic: &[i32],
    degree: i32,
) -> Result<Vec<f64>, String> {
    let m = xcounts.len();
    if ycounts.len() != m || indic.len() != m {
        return Err("xcounts, ycounts, and indic must have the same length".into());
    }
    if hdisc.len() != lvec.len() {
        return Err("hdisc and lvec must have the same length".into());
    }
    if degree < 0 || drv < 0 || drv > degree {
        return Err("degree must be at least drv, and both must be non-negative".into());
    }
    let q = hdisc.len();
    if q == 0 || m == 0 {
        return Err("the bandwidth grid and the bin grid must be non-empty".into());
    }

    let ipp = (degree as usize) + 1;
    let ippp = (2 * degree as usize) + 1;
    let mut fkap = vec![0.0; 2 * lvec.iter().map(|value| *value as usize).sum::<usize>() + q];
    let mut midpts = vec![0_i32; q];
    let mut ss = vec![0.0; m * ippp];
    let mut tt = vec![0.0; m * ipp];

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
                let yterm = ycounts[k - 1] * weight;
                ss[j - 1] += xterm;
                tt[j - 1] += yterm;
                let mut factor = 1.0;
                for power in 2..=ippp {
                    factor *= delta * (k as f64 - j as f64);
                    ss[(power - 1) * m + (j - 1)] += xterm * factor;
                    if power <= ipp {
                        tt[(power - 1) * m + (j - 1)] += yterm * factor;
                    }
                }
            }
        }
    }

    let mut curve = vec![0.0; m];
    let mut matrix = vec![0.0; ipp * ipp];
    let mut pivots = vec![0_usize; ipp];
    let mut right = vec![0.0; ipp];
    for k in 0..m {
        for row in 0..ipp {
            for col in 0..ipp {
                let moment = row + col;
                matrix[col * ipp + row] = ss[moment * m + k];
            }
            right[row] = tt[row * m + k];
        }
        dgefa(&mut matrix, ipp, ipp, &mut pivots);
        dgesl(&matrix, ipp, ipp, &pivots, &mut right, 0);
        curve[k] = right[drv as usize];
    }
    Ok(curve)
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
    #[pyo3(name = "locpol")]
    fn locpol_py<'py>(
        py: Python<'py>,
        xcounts: PyReadonlyArray1<'py, f64>,
        ycounts: PyReadonlyArray1<'py, f64>,
        drv: i32,
        delta: f64,
        hdisc: PyReadonlyArray1<'py, f64>,
        lvec: PyReadonlyArray1<'py, i32>,
        indic: PyReadonlyArray1<'py, i32>,
        degree: i32,
    ) -> PyResult<Bound<'py, numpy::PyArray1<f64>>> {
        let curve = crate::locpol(
            slice_f64(&xcounts)?,
            slice_f64(&ycounts)?,
            drv,
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
    fn locpol(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(locpol_py, m)?)?;
        Ok(())
    }
}
