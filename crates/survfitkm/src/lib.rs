//! Kaplan–Meier / Nelson–Aalen / Fleming–Harrington curves from survival 3.8-12
//! `src/survfitkm.c` (`Csurvfitkm`).
//!
//! `y` is column-major with `nrows` rows and `ny` columns (2 = time, status;
//! 3 = start, stop, status). `sort1` and `sort2` are 0-based indexes into
//! that matrix, ordered by start and stop (or time). `id` is 0-based and is
//! read only when `nid > 0`. `position` is the `survflag` bit field:
//! 1 = first interval, 2 = last interval, 3 = both.
//!
//! `n` is column-major with `ntime` rows. Columns are unweighted risk, events,
//! and censors, then the weighted versions, then (when `entry == 1`) unweighted
//! and weighted entries. `estimate` is column-major survival and cumulative
//! hazard. `std_err` is column-major se(survival or log survival) and se(cumhaz).
//! Influence matrices are column-major `nid` by `ntime`, empty when not requested.

#[cfg(feature = "python")]
use pyo3::prelude::*;

/// Counts, estimates, and optional influence from [`survfitkm`].
#[derive(Clone, Debug, PartialEq)]
pub struct SurvfitKm {
    pub time: Vec<f64>,
    pub n: Vec<f64>,
    pub n_cols: usize,
    pub estimate: Vec<f64>,
    pub std_err: Vec<f64>,
    pub influence1: Vec<f64>,
    pub influence2: Vec<f64>,
}

/// Port of `Csurvfitkm`.
///
/// `type_ == 1` is Kaplan–Meier survival and Nelson–Aalen hazard, `2` is
/// Kaplan–Meier and Fleming–Harrington, `3` is exp(−Nelson–Aalen), and `4` is
/// exp(−Fleming–Harrington). `reverse == 1` estimates the censoring curve in
/// the ordinary (non-robust) pass. `influence` is `1` (survival), `2`
/// (cumulative hazard), `3` (both), or `0`.
pub fn survfitkm(
    y: &[f64],
    nrows: usize,
    ny: usize,
    weight: &[f64],
    sort1: &[i32],
    sort2: &[i32],
    type_: i32,
    id: &[i32],
    nid: usize,
    position: &[i32],
    influence: i32,
    reverse: i32,
    entry: i32,
    utime: &[f64],
) -> Result<SurvfitKm, String> {
    if ny != 2 && ny != 3 {
        return Err("ny must be 2 or 3".to_string());
    }
    if y.len() != nrows.saturating_mul(ny) {
        return Err("y length must be nrows * ny".to_string());
    }
    if weight.len() != nrows || position.len() != nrows {
        return Err("weight and position must have nrows elements".to_string());
    }
    if ny == 3 && sort1.len() != sort2.len() {
        return Err("sort1 and sort2 must have the same length".to_string());
    }
    check_index(sort2, nrows, "sort2")?;
    if ny == 3 {
        check_index(sort1, nrows, "sort1")?;
    }
    if nid > 0 {
        if id.len() != nrows {
            return Err("id must have nrows elements when nid > 0".to_string());
        }
        for &idx in sort2 {
            check_id(id, idx as usize, nid)?;
        }
        if ny == 3 {
            for &idx in sort1 {
                check_id(id, idx as usize, nid)?;
            }
        }
    }

    let nused = sort2.len();
    let ntime = utime.len();
    let n_cols = if entry == 0 { 6 } else { 8 };
    let time2_col = if ny == 3 { 1 } else { 0 };
    let status_col = ny - 1;

    let mut n = vec![0.0; ntime * n_cols];
    let mut estimate = vec![0.0; ntime * 2];
    let mut std_err = vec![0.0; ntime * 2];

    // Walk stop times from the right, matching the C backward scan.
    let mut person1: isize = nused as isize - 1;
    let mut person2: isize = nused as isize - 1;
    let mut n1: i32 = 0;
    let mut wt1 = 0.0;
    for k in (0..ntime).rev() {
        let mut n2: i32 = 0;
        let mut n3: i32 = 0;
        let mut wt2 = 0.0;
        let mut wt3 = 0.0;
        while person2 >= 0 {
            let i2 = sort2[person2 as usize] as usize;
            if col(y, nrows, time2_col, i2) < utime[k] {
                break;
            }
            n1 += 1;
            wt1 += weight[i2];
            if col(y, nrows, status_col, i2) == 1.0 {
                n2 += 1;
                wt2 += weight[i2];
            } else if position[i2] & 2 != 0 {
                n3 += 1;
                wt3 += weight[i2];
            }
            person2 -= 1;
        }
        if ny == 3 {
            let mut n4: i32 = 0;
            let mut wt4 = 0.0;
            while person1 >= 0 {
                let i1 = sort1[person1 as usize] as usize;
                if col(y, nrows, 0, i1) < utime[k] {
                    break;
                }
                n1 -= 1;
                wt1 -= weight[i1];
                if entry == 1 && position[i1] & 1 != 0 && col(y, nrows, 0, i1) == utime[k] {
                    n4 += 1;
                    wt4 += weight[i1];
                }
                person1 -= 1;
            }
            if entry == 1 {
                n[6 * ntime + k] = f64::from(n4);
                n[7 * ntime + k] = wt4;
            }
        }
        n[k] = f64::from(n1);
        n[ntime + k] = f64::from(n2);
        n[2 * ntime + k] = f64::from(n3);
        n[3 * ntime + k] = wt1;
        n[4 * ntime + k] = wt2;
        n[5 * ntime + k] = wt3;
    }

    let mut nelson = 0.0;
    let mut km = 1.0;
    let mut v1 = 0.0;
    let mut v2 = 0.0;
    for i in 0..ntime {
        let (d0, d1, nrisk) = if reverse == 1 {
            (n[2 * ntime + i], n[5 * ntime + i], n[3 * ntime + i] - n[4 * ntime + i])
        } else {
            (n[ntime + i], n[4 * ntime + i], n[3 * ntime + i])
        };
        if type_ == 1 || type_ == 3 {
            if d0 > 0.0 && d1 > 0.0 {
                nelson += d1 / nrisk;
                v2 += d1 / (nrisk * nrisk);
            }
            estimate[ntime + i] = nelson;
            std_err[ntime + i] = v2.sqrt();
        } else {
            let mut j = 0i32;
            while f64::from(j) < d0 {
                let dtemp = nrisk - f64::from(j) * d1 / d0;
                nelson += d1 / (d0 * dtemp);
                v2 += d1 / (d0 * dtemp * dtemp);
                j += 1;
            }
            estimate[i] = (-nelson).exp();
            estimate[ntime + i] = nelson;
            std_err[ntime + i] = v2.sqrt();
        }
        if type_ < 3 {
            if d0 > 0.0 && d1 > 0.0 {
                km *= (nrisk - d1) / nrisk;
                v1 += d1 / (nrisk * (nrisk - d1));
            }
            estimate[i] = km;
            std_err[i] = v1.sqrt();
        } else {
            estimate[i] = (-estimate[ntime + i]).exp();
            std_err[i] = std_err[ntime + i];
        }
    }

    let want1 = nid > 0 && type_ < 3 && (influence == 1 || influence == 3);
    let want2 = nid > 0
        && ((type_ < 3 && (influence == 2 || influence == 3))
            || (type_ >= 3 && influence != 0));
    let mut influence1 = if want1 {
        vec![0.0; nid * ntime]
    } else {
        Vec::new()
    };
    let mut influence2 = if want2 {
        vec![0.0; nid * ntime]
    } else {
        Vec::new()
    };

    if nid > 0 {
        let mut gcount = vec![0i32; nid];
        let mut gwt = vec![0.0; nid];
        let mut inf1 = vec![0.0; nid];
        let mut inf2 = vec![0.0; nid];
        let mut person2: usize = 0;
        let mut person1: usize = 0;
        if ny != 3 {
            for &idx in sort2 {
                let row = idx as usize;
                let cid = id[row] as usize;
                gcount[cid] += 1;
                gwt[cid] += weight[row];
            }
        }
        let mut v1 = 0.0;
        let mut v2 = 0.0;
        let mut km = 1.0;

        if type_ == 1 {
            for i in 0..ntime {
                toss_outdated(
                    &mut person2, sort2, y, nrows, time2_col, utime[i], id, weight, &mut gcount,
                    &mut gwt,
                );
                if ny == 3 {
                    add_entries(
                        &mut person1, sort1, y, nrows, utime[i], id, weight, &mut gcount, &mut gwt,
                    );
                }
                if n[ntime + i] > 0.0 && n[4 * ntime + i] > 0.0 {
                    let haz = n[4 * ntime + i] / n[3 * ntime + i];
                    let nrisk = n[3 * ntime + i];
                    for k in 0..nid {
                        inf1[k] = inf1[k] * (1.0 - haz) + gwt[k] * km * haz / nrisk;
                        inf2[k] -= gwt[k] * haz / nrisk;
                    }
                    while person2 < nused {
                        let i2 = sort2[person2] as usize;
                        if col(y, nrows, time2_col, i2) > utime[i] {
                            break;
                        }
                        if col(y, nrows, status_col, i2) == 1.0 {
                            let cid = id[i2] as usize;
                            inf1[cid] -= km * weight[i2] / nrisk;
                            inf2[cid] += weight[i2] / nrisk;
                        }
                        leave_risk(&mut gcount, &mut gwt, id[i2] as usize, weight[i2]);
                        person2 += 1;
                    }
                    km *= 1.0 - haz;
                    v1 = 0.0;
                    v2 = 0.0;
                    for k in 0..nid {
                        v1 += inf1[k] * inf1[k];
                        v2 += inf2[k] * inf2[k];
                    }
                }
                std_err[i] = v1.sqrt();
                std_err[ntime + i] = v2.sqrt();
                if want1 {
                    for k in 0..nid {
                        influence1[k + i * nid] = inf1[k];
                    }
                }
                if want2 {
                    for k in 0..nid {
                        influence2[k + i * nid] = inf2[k];
                    }
                }
            }
        } else if type_ == 2 {
            for i in 0..ntime {
                toss_outdated(
                    &mut person2, sort2, y, nrows, time2_col, utime[i], id, weight, &mut gcount,
                    &mut gwt,
                );
                if ny == 3 {
                    add_entries(
                        &mut person1, sort1, y, nrows, utime[i], id, weight, &mut gcount, &mut gwt,
                    );
                }
                if n[ntime + i] > 0.0 && n[4 * ntime + i] > 0.0 {
                    let n_event = n[ntime + i];
                    let w_event = n[4 * ntime + i];
                    let nrisk = n[3 * ntime + i];
                    let mut dtemp = 0.0;
                    let mut dtemp2 = 0.0;
                    let mut dtemp3 = 0.0;
                    let temp = nrisk - w_event;
                    let mut k = n_event as i32;
                    while k > 0 {
                        let frac = f64::from(k) / n_event;
                        let btemp = 1.0 / (temp + frac * w_event);
                        dtemp += btemp;
                        dtemp2 += btemp * btemp * frac;
                        dtemp3 += btemp * btemp;
                        k -= 1;
                    }
                    dtemp /= n_event;
                    if w_event != n_event {
                        dtemp2 *= w_event / n_event;
                        dtemp3 *= w_event / n_event;
                    }
                    let haz = w_event / nrisk;
                    for k in 0..nid {
                        inf1[k] = inf1[k] * (1.0 - haz) + gwt[k] * km * haz / nrisk;
                        if gcount[k] > 0 {
                            inf2[k] -= gwt[k] * dtemp3;
                        }
                    }
                    while person2 < nused {
                        let i2 = sort2[person2] as usize;
                        if col(y, nrows, time2_col, i2) > utime[i] {
                            break;
                        }
                        if col(y, nrows, status_col, i2) == 1.0 {
                            let cid = id[i2] as usize;
                            inf1[cid] -= km * weight[i2] / nrisk;
                            inf2[cid] += weight[i2] * (dtemp + dtemp3 - dtemp2);
                        }
                        leave_risk(&mut gcount, &mut gwt, id[i2] as usize, weight[i2]);
                        person2 += 1;
                    }
                    km *= 1.0 - haz;
                    v1 = 0.0;
                    v2 = 0.0;
                    for k in 0..nid {
                        v1 += inf1[k] * inf1[k];
                        v2 += inf2[k] * inf2[k];
                    }
                }
                std_err[i] = v1.sqrt();
                std_err[ntime + i] = v2.sqrt();
                if want1 {
                    for k in 0..nid {
                        influence1[k + i * nid] = inf1[k];
                    }
                }
                if want2 {
                    for k in 0..nid {
                        influence2[k + i * nid] = inf2[k];
                    }
                }
            }
        } else if type_ == 3 {
            for i in 0..ntime {
                toss_outdated(
                    &mut person2, sort2, y, nrows, time2_col, utime[i], id, weight, &mut gcount,
                    &mut gwt,
                );
                if ny == 3 {
                    add_entries(
                        &mut person1, sort1, y, nrows, utime[i], id, weight, &mut gcount, &mut gwt,
                    );
                }
                if n[ntime + i] > 0.0 && n[4 * ntime + i] > 0.0 {
                    let haz = n[4 * ntime + i] / n[3 * ntime + i];
                    let nrisk = n[3 * ntime + i];
                    for k in 0..nid {
                        inf2[k] -= gwt[k] * haz / nrisk;
                    }
                    while person2 < nused {
                        let i2 = sort2[person2] as usize;
                        if col(y, nrows, time2_col, i2) > utime[i] {
                            break;
                        }
                        if col(y, nrows, status_col, i2) == 1.0 {
                            inf2[id[i2] as usize] += weight[i2] / nrisk;
                        }
                        leave_risk(&mut gcount, &mut gwt, id[i2] as usize, weight[i2]);
                        person2 += 1;
                    }
                    v2 = 0.0;
                    for k in 0..nid {
                        v2 += inf2[k] * inf2[k];
                    }
                }
                std_err[ntime + i] = v2.sqrt();
                std_err[i] = v2.sqrt();
                if want2 {
                    for k in 0..nid {
                        influence2[k + i * nid] = inf2[k];
                    }
                }
            }
        } else {
            for i in 0..ntime {
                toss_outdated(
                    &mut person2, sort2, y, nrows, time2_col, utime[i], id, weight, &mut gcount,
                    &mut gwt,
                );
                if ny == 3 {
                    add_entries(
                        &mut person1, sort1, y, nrows, utime[i], id, weight, &mut gcount, &mut gwt,
                    );
                }
                if n[ntime + i] > 0.0 && n[4 * ntime + i] > 0.0 {
                    let n_event = n[ntime + i];
                    let w_event = n[4 * ntime + i];
                    let nrisk = n[3 * ntime + i];
                    let mut dtemp = 0.0;
                    let mut dtemp2 = 0.0;
                    let mut dtemp3 = 0.0;
                    let temp = nrisk - w_event;
                    let mut k = n_event as i32;
                    while k > 0 {
                        let frac = f64::from(k) / n_event;
                        let btemp = 1.0 / (temp + frac * w_event);
                        dtemp += btemp;
                        dtemp2 += btemp * btemp * frac;
                        dtemp3 += btemp * btemp;
                        k -= 1;
                    }
                    dtemp /= n_event;
                    if w_event != n_event {
                        dtemp2 *= w_event / n_event;
                        dtemp3 *= w_event / n_event;
                    }
                    for k in 0..nid {
                        if gcount[k] > 0 {
                            inf2[k] -= gwt[k] * dtemp3;
                        }
                    }
                    while person2 < nused {
                        let i2 = sort2[person2] as usize;
                        if col(y, nrows, time2_col, i2) > utime[i] {
                            break;
                        }
                        if col(y, nrows, status_col, i2) == 1.0 {
                            inf2[id[i2] as usize] += weight[i2] * (dtemp + dtemp3 - dtemp2);
                        }
                        leave_risk(&mut gcount, &mut gwt, id[i2] as usize, weight[i2]);
                        person2 += 1;
                    }
                    v2 = 0.0;
                    for k in 0..nid {
                        v2 += inf2[k] * inf2[k];
                    }
                }
                std_err[ntime + i] = v2.sqrt();
                std_err[i] = v2.sqrt();
                if want2 {
                    for k in 0..nid {
                        influence2[k + i * nid] = inf2[k];
                    }
                }
            }
        }
    }

    Ok(SurvfitKm {
        time: utime.to_vec(),
        n,
        n_cols,
        estimate,
        std_err,
        influence1,
        influence2,
    })
}

fn col(y: &[f64], nrows: usize, column: usize, row: usize) -> f64 {
    y[column * nrows + row]
}

fn check_index(sort: &[i32], nrows: usize, what: &str) -> Result<(), String> {
    for &idx in sort {
        if idx < 0 || idx as usize >= nrows {
            return Err(format!("{what} index {idx} is outside 0..{nrows}"));
        }
    }
    Ok(())
}

fn check_id(id: &[i32], row: usize, nid: usize) -> Result<(), String> {
    let cid = id[row];
    if cid < 0 || cid as usize >= nid {
        return Err(format!("id[{row}] = {cid} is outside 0..{nid}"));
    }
    Ok(())
}

fn leave_risk(gcount: &mut [i32], gwt: &mut [f64], cid: usize, w: f64) {
    gcount[cid] -= 1;
    if gcount[cid] == 0 {
        gwt[cid] = 0.0;
    } else {
        gwt[cid] -= w;
    }
}

fn toss_outdated(
    person2: &mut usize,
    sort2: &[i32],
    y: &[f64],
    nrows: usize,
    time2_col: usize,
    dtime: f64,
    id: &[i32],
    weight: &[f64],
    gcount: &mut [i32],
    gwt: &mut [f64],
) {
    let nused = sort2.len();
    while *person2 < nused {
        let i2 = sort2[*person2] as usize;
        if col(y, nrows, time2_col, i2) >= dtime {
            break;
        }
        leave_risk(gcount, gwt, id[i2] as usize, weight[i2]);
        *person2 += 1;
    }
}

fn add_entries(
    person1: &mut usize,
    sort1: &[i32],
    y: &[f64],
    nrows: usize,
    dtime: f64,
    id: &[i32],
    weight: &[f64],
    gcount: &mut [i32],
    gwt: &mut [f64],
) {
    let nused = sort1.len();
    while *person1 < nused {
        let i1 = sort1[*person1] as usize;
        if col(y, nrows, 0, i1) >= dtime {
            break;
        }
        let cid = id[i1] as usize;
        gcount[cid] += 1;
        gwt[cid] += weight[i1];
        *person1 += 1;
    }
}

#[cfg(feature = "python")]
#[pymodule(name = "survfitkm")]
fn survfitkm_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(survfitkm_py, m)?)?;
    Ok(())
}

#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(name = "survfitkm")]
fn survfitkm_py(
    y: Vec<f64>,
    nrows: usize,
    ny: usize,
    weight: Vec<f64>,
    sort1: Vec<i32>,
    sort2: Vec<i32>,
    type_: i32,
    id: Vec<i32>,
    nid: usize,
    position: Vec<i32>,
    influence: i32,
    reverse: i32,
    entry: i32,
    utime: Vec<f64>,
) -> PyResult<(Vec<f64>, Vec<f64>, usize, Vec<f64>, Vec<f64>, Vec<f64>, Vec<f64>)> {
    let fit = survfitkm(
        &y, nrows, ny, &weight, &sort1, &sort2, type_, &id, nid, &position, influence, reverse,
        entry, &utime,
    )
    .map_err(pyo3::exceptions::PyValueError::new_err)?;
    Ok((
        fit.time,
        fit.n,
        fit.n_cols,
        fit.estimate,
        fit.std_err,
        fit.influence1,
        fit.influence2,
    ))
}

#[cfg(test)]
mod tests {
    use super::survfitkm;

    fn plain(time: &[f64], status: &[f64], weight: &[f64], type_: i32) -> super::SurvfitKm {
        let n = time.len();
        let mut y = vec![0.0; n * 2];
        y[..n].copy_from_slice(time);
        y[n..].copy_from_slice(status);
        let sort2: Vec<i32> = (0..n as i32).collect();
        let position = vec![3; n];
        let mut utime = time.to_vec();
        utime.sort_by(|a, b| a.partial_cmp(b).unwrap());
        utime.dedup();
        survfitkm(
            &y, n, 2, weight, &[], &sort2, type_, &[], 0, &position, 0, 0, 0, &utime,
        )
        .unwrap()
    }

    #[test]
    fn kaplan_meier_four_subjects() {
        let fit = plain(&[1.0, 2.0, 3.0, 4.0], &[1.0, 0.0, 1.0, 1.0], &[1.0; 4], 1);
        assert_eq!(fit.time, vec![1.0, 2.0, 3.0, 4.0]);
        assert_eq!(&fit.n[..4], &[4.0, 3.0, 2.0, 1.0]);
        assert_eq!(&fit.n[4..8], &[1.0, 0.0, 1.0, 1.0]);
        assert_eq!(&fit.n[8..12], &[0.0, 1.0, 0.0, 0.0]);
        let surv = &fit.estimate[..4];
        assert!((surv[0] - 0.75).abs() < 1e-12);
        assert!((surv[1] - 0.75).abs() < 1e-12);
        assert!((surv[2] - 0.375).abs() < 1e-12);
        assert!((surv[3] - 0.0).abs() < 1e-12);
        let haz = &fit.estimate[4..];
        assert!((haz[0] - 0.25).abs() < 1e-12);
        assert!((haz[1] - 0.25).abs() < 1e-12);
        assert!((haz[2] - 0.75).abs() < 1e-12);
        assert!((haz[3] - 1.75).abs() < 1e-12);
        assert!((fit.std_err[0] - (1.0 / 12.0_f64).sqrt()).abs() < 1e-12);
        assert!((fit.std_err[2] - (7.0 / 12.0_f64).sqrt()).abs() < 1e-12);
        assert!(fit.std_err[3].is_infinite());
        assert!((fit.std_err[4] - 0.25).abs() < 1e-12);
        assert!((fit.std_err[6] - (5.0 / 16.0_f64).sqrt()).abs() < 1e-12);
    }

    #[test]
    fn fleming_harrington_tie_differs_from_nelson() {
        let fit = plain(&[1.0, 1.0, 2.0], &[1.0, 1.0, 0.0], &[1.0; 3], 2);
        assert!((fit.estimate[0] - 1.0 / 3.0).abs() < 1e-12);
        assert!((fit.estimate[1] - 1.0 / 3.0).abs() < 1e-12);
        assert!((fit.estimate[2] - 5.0 / 6.0).abs() < 1e-12);
        assert!((fit.estimate[3] - 5.0 / 6.0).abs() < 1e-12);
        assert!((fit.std_err[0] - (2.0 / 3.0_f64).sqrt()).abs() < 1e-12);
        assert!((fit.std_err[2] - (13.0 / 36.0_f64).sqrt()).abs() < 1e-12);
    }
}
