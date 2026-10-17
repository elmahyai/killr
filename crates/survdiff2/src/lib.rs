//! Log-rank and G-rho statistics from survival 3.8-12 `src/survdiff2.c`.
//!
//! `group` is 1-based. `strata` is 1 on the last row of each stratum.
//! Rows are ordered by stratum, then time. Observed and expected counts are
//! column-major, one column per stratum. The variance is column-major
//! `ngroup` by `ngroup` and is summed across strata.

#[cfg(feature = "python")]
use pyo3::prelude::*;

/// Weighted observed counts, expected counts, and the variance matrix.
#[derive(Clone, Debug, PartialEq)]
pub struct Survdiff2 {
    pub observed: Vec<f64>,
    pub expected: Vec<f64>,
    pub variance: Vec<f64>,
}

/// Fill the G-rho observed, expected, and variance arrays.
///
/// `rho == 0` is the log-rank test. Any other `rho` weights each death by the
/// left-continuous Kaplan–Meier estimate raised to `rho`.
pub fn survdiff2(
    rho: f64,
    time: &[f64],
    status: &[i32],
    group: &[i32],
    strata: &[i32],
    ngroup: usize,
    nstrat: usize,
) -> Result<Survdiff2, String> {
    let ntot = time.len();
    if status.len() != ntot || group.len() != ntot || strata.len() != ntot {
        return Err("time, status, group, and strata must have the same length".to_string());
    }
    let n_obs = ngroup
        .checked_mul(nstrat)
        .ok_or_else(|| "ngroup * nstrat overflows".to_string())?;
    let n_var = ngroup
        .checked_mul(ngroup)
        .ok_or_else(|| "ngroup * ngroup overflows".to_string())?;
    let mut observed = vec![0.0; n_obs];
    let mut expected = vec![0.0; n_obs];
    let mut variance = vec![0.0; n_var];
    if ntot == 0 {
        if nstrat != 0 {
            return Err("nstrat must be 0 when there are no rows".to_string());
        }
        return Ok(Survdiff2 {
            observed,
            expected,
            variance,
        });
    }
    if ngroup == 0 || nstrat == 0 {
        return Err("ngroup and nstrat must be positive".to_string());
    }

    let mut risk = vec![0.0; ngroup];
    let mut kaplan = vec![0.0; ntot];
    let mut istart: usize = 0;
    let mut koff: usize = 0;
    let mut seen: usize = 0;

    while istart < ntot {
        if seen == nstrat {
            return Err("more strata markers than nstrat".to_string());
        }
        risk.fill(0.0);

        let mut end = istart;
        while end < ntot && strata[end] != 1 {
            end += 1;
        }
        if end == ntot {
            return Err("a stratum must end with strata == 1".to_string());
        }
        let n = end + 1;

        if rho != 0.0 {
            let mut km = 1.0;
            let mut i = istart;
            while i < n {
                kaplan[i] = km;
                let nrisk = (n - i) as f64;
                let mut deaths = status[i] as f64;
                let mut j = i + 1;
                while j < n && time[j] == time[i] {
                    kaplan[j] = km;
                    deaths += status[j] as f64;
                    j += 1;
                }
                km = km * (nrisk - deaths) / nrisk;
                i = j;
            }
        }

        let mut i = n as isize - 1;
        let istart_i = istart as isize;
        while i >= istart_i {
            let i_us = i as usize;
            let wt = if rho == 0.0 {
                1.0
            } else {
                kaplan[i_us].powf(rho)
            };
            let mut deaths = 0.0;
            let mut j = i;
            while j >= istart_i && time[j as usize] == time[i_us] {
                let g = group[j as usize];
                if g < 1 || g as usize > ngroup {
                    return Err("group must be in 1..=ngroup".to_string());
                }
                let k = g as usize - 1;
                deaths += status[j as usize] as f64;
                risk[k] += 1.0;
                observed[k + koff] += status[j as usize] as f64 * wt;
                j -= 1;
            }
            i = j + 1;
            let nrisk = (n as isize - i) as f64;
            if deaths > 0.0 {
                for k in 0..ngroup {
                    expected[k + koff] += wt * deaths * risk[k] / nrisk;
                }
                if nrisk != 1.0 {
                    let wt = wt * wt;
                    let mut kk = 0;
                    for jg in 0..ngroup {
                        let tmp =
                            wt * deaths * risk[jg] * (nrisk - deaths) / (nrisk * (nrisk - 1.0));
                        variance[kk + jg] += tmp;
                        for k in 0..ngroup {
                            variance[kk] -= tmp * risk[k] / nrisk;
                            kk += 1;
                        }
                    }
                }
            }
            i -= 1;
        }

        istart = n;
        koff += ngroup;
        seen += 1;
    }
    if seen != nstrat {
        return Err("strata markers do not match nstrat".to_string());
    }
    Ok(Survdiff2 {
        observed,
        expected,
        variance,
    })
}

/// Milliseconds for one [`survdiff2`] call, measured with [`std::time::Instant`].
pub fn survdiff2_ms(
    rho: f64,
    time: &[f64],
    status: &[i32],
    group: &[i32],
    strata: &[i32],
    ngroup: usize,
    nstrat: usize,
) -> Result<f64, String> {
    let started = std::time::Instant::now();
    let _fit = survdiff2(rho, time, status, group, strata, ngroup, nstrat)?;
    Ok(started.elapsed().as_secs_f64() * 1000.0)
}

#[cfg(feature = "python")]
#[pymodule(name = "survdiff2")]
fn survdiff2_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(survdiff2_py, m)?)?;
    m.add_function(wrap_pyfunction!(survdiff2_ms_py, m)?)?;
    Ok(())
}

#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(name = "survdiff2")]
fn survdiff2_py(
    rho: f64,
    time: Vec<f64>,
    status: Vec<i32>,
    group: Vec<i32>,
    strata: Vec<i32>,
    ngroup: usize,
    nstrat: usize,
) -> PyResult<(Vec<f64>, Vec<f64>, Vec<f64>)> {
    let fit = survdiff2(rho, &time, &status, &group, &strata, ngroup, nstrat)
        .map_err(pyo3::exceptions::PyValueError::new_err)?;
    Ok((fit.observed, fit.expected, fit.variance))
}

#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(name = "survdiff2_ms")]
fn survdiff2_ms_py(
    rho: f64,
    time: Vec<f64>,
    status: Vec<i32>,
    group: Vec<i32>,
    strata: Vec<i32>,
    ngroup: usize,
    nstrat: usize,
) -> PyResult<f64> {
    survdiff2_ms(rho, &time, &status, &group, &strata, ngroup, nstrat)
        .map_err(pyo3::exceptions::PyValueError::new_err)
}

#[cfg(test)]
mod tests {
    use super::survdiff2;

    #[test]
    fn logrank_four_subjects() {
        let fit = survdiff2(
            0.0,
            &[1.0, 2.0, 3.0, 4.0],
            &[1, 1, 0, 1],
            &[1, 2, 1, 2],
            &[0, 0, 0, 1],
            2,
            1,
        )
        .unwrap();
        assert!((fit.observed[0] - 1.0).abs() < 1e-15);
        assert!((fit.observed[1] - 2.0).abs() < 1e-15);
        assert!((fit.expected[0] - 5.0 / 6.0).abs() < 1e-15);
        assert!((fit.expected[1] - 13.0 / 6.0).abs() < 1e-15);
        let v = 17.0 / 36.0;
        assert!((fit.variance[0] - v).abs() < 1e-12);
        assert!((fit.variance[1] + v).abs() < 1e-12);
        assert!((fit.variance[2] + v).abs() < 1e-12);
        assert!((fit.variance[3] - v).abs() < 1e-12);
    }
}
