//! Aalen–Johansen estimates from survival 3.8-12 `src/survfitaj.c` (`survfitaj`).
//!
//! `y` is column-major with `n` rows and 3 columns: time1, time2, state.
//! State 0 is censoring; an event code `s` moves to 0-based state `s - 1`.
//! `sort1` and `sort2` are 0-based indexes into `y`, ordered by time1 and
//! time2 for one curve. `cstate` and `grp` are 0-based. `hindx` is column-major
//! `nstate` by `nstate`: `hindx[from + nstate * to]` is the 0-based transition,
//! or -1 when that transition was not observed. `trmat` is column-major with
//! `nhaz` rows: the first column is the from-state and the second is the to-state.
//!
//! Counts are column-major with `ntime` rows. `n_risk` and `n_censor` have
//! `2 * nstate` columns (weighted, then unweighted). `n_event` and `pstate`
//! have `nstate` columns. `n_transition` has `2 * nhaz` columns and `cumhaz`
//! has `nhaz`. Standard errors follow the same row order. The influence matrix,
//! when requested, is column-major `(ngrp * nstate)` by `ntime`, group within
//! state.

#[cfg(feature = "python")]
use pyo3::prelude::*;

/// Counts, probabilities, hazards, and optional influence from [`survfitaj`].
#[derive(Clone, Debug, PartialEq)]
pub struct SurvfitAj {
    pub n_risk: Vec<f64>,
    pub n_event: Vec<f64>,
    pub n_censor: Vec<f64>,
    pub pstate: Vec<f64>,
    pub cumhaz: Vec<f64>,
    pub std_err: Vec<f64>,
    pub std_chaz: Vec<f64>,
    pub std_auc: Vec<f64>,
    pub influence: Vec<f64>,
    pub n_enter: Vec<f64>,
    pub n_transition: Vec<f64>,
}

/// Port of `survfitaj`.
///
/// `sefit` is 0 (no standard error), 1 (standard errors), or greater than 1
/// (standard errors and the influence matrix). `entry == 1` records entry
/// counts; `utime` must then contain the entry times and must be increasing.
pub fn survfitaj(
    y: &[f64],
    n: usize,
    sort1: &[i32],
    sort2: &[i32],
    utime: &[f64],
    cstate: &[i32],
    wt: &[f64],
    grp: &[i32],
    ngrp: usize,
    p0: &[f64],
    i0: &[f64],
    sefit: i32,
    entry: i32,
    position: &[i32],
    hindx: &[i32],
    trmat: &[i32],
    t0: f64,
) -> Result<SurvfitAj, String> {
    if n > 0 && y.len() != n.saturating_mul(3) {
        return Err("y length must be n * 3".to_string());
    }
    if cstate.len() != n || wt.len() != n || grp.len() != n || position.len() != n {
        return Err("cstate, wt, grp, and position must have n elements".to_string());
    }
    if sort1.len() != sort2.len() {
        return Err("sort1 and sort2 must have the same length".to_string());
    }
    let nstate = p0.len();
    if hindx.len() != nstate.saturating_mul(nstate) {
        return Err("hindx length must be nstate * nstate".to_string());
    }
    if trmat.len() % 2 != 0 {
        return Err("trmat must have two columns".to_string());
    }
    let nhaz = trmat.len() / 2;
    if sefit > 0 && i0.len() < ngrp.saturating_mul(nstate) {
        return Err("i0 length must be at least ngrp * nstate".to_string());
    }
    check_index(sort1, n, "sort1")?;
    check_index(sort2, n, "sort2")?;
    for &idx in sort1.iter().chain(sort2.iter()) {
        let row = idx as usize;
        let state = cstate[row];
        if state < 0 || state as usize >= nstate {
            return Err(format!("cstate[{row}] = {state} is outside 0..{nstate}"));
        }
        if sefit > 0 {
            let g = grp[row];
            if g < 0 || g as usize >= ngrp {
                return Err(format!("grp[{row}] = {g} is outside 0..{ngrp}"));
            }
        }
    }
    for jk in 0..nhaz {
        let from = trmat[jk];
        let to = trmat[jk + nhaz];
        if from < 0 || to < 0 || from as usize >= nstate || to as usize >= nstate {
            return Err(format!("trmat row {jk} is outside 0..{nstate}"));
        }
    }

    let nused = sort1.len();
    let ntime = utime.len();
    let mut n_risk = vec![0.0; ntime * 2 * nstate];
    let mut n_event = vec![0.0; ntime * nstate];
    let mut n_censor = vec![0.0; ntime * 2 * nstate];
    let mut n_enter = if entry == 1 {
        vec![0.0; ntime * 2 * nstate]
    } else {
        Vec::new()
    };
    let mut n_transition = vec![0.0; ntime * 2 * nhaz];
    let mut pstate = vec![0.0; ntime * nstate];
    let mut cumhaz = vec![0.0; ntime * nhaz];
    let want_se = sefit > 0;
    let want_influence = sefit > 1;
    let mut std_err = if want_se {
        vec![0.0; ntime * nstate]
    } else {
        Vec::new()
    };
    let mut std_chaz = if want_se {
        vec![0.0; ntime * nhaz]
    } else {
        Vec::new()
    };
    let mut std_auc = if want_se {
        vec![0.0; ntime * nstate]
    } else {
        Vec::new()
    };
    let mut influence = if want_influence {
        vec![0.0; ngrp * nstate * ntime]
    } else {
        Vec::new()
    };

    // ntemp is weighted risk, unweighted risk, then scratch reused as phat.
    let mut ntemp = vec![0.0; 2 * nstate];
    let mut phat = p0.to_vec();
    let mut chaz = vec![0.0; nhaz];

    // Backward pass: risk sets shrink toward later times, so walking from the
    // right does more additions than subtractions.
    let mut person1: isize = nused as isize - 1;
    let mut person2: isize = nused as isize - 1;
    for i in (0..ntime).rev() {
        let ctime = utime[i];
        while person1 >= 0 {
            let i1 = sort1[person1 as usize] as usize;
            if col(y, n, 0, i1) < ctime {
                break;
            }
            let j = cstate[i1] as usize;
            ntemp[j] -= wt[i1];
            ntemp[j + nstate] -= 1.0;
            if position[i1] & 1 & entry != 0 {
                add(&mut n_enter, ntime, j, i, wt[i1]);
                add(&mut n_enter, ntime, j + nstate, i, 1.0);
            }
            person1 -= 1;
        }
        while person2 >= 0 {
            let i2 = sort2[person2 as usize] as usize;
            if col(y, n, 1, i2) < ctime {
                break;
            }
            let j = cstate[i2] as usize;
            ntemp[j] += wt[i2];
            ntemp[j + nstate] += 1.0;
            let event = col(y, n, 2, i2);
            if event > 0.0 {
                let k = (event as i32 - 1) as usize;
                let jk = transition(hindx, nstate, j, k)?;
                add(&mut n_transition, ntime, jk, i, wt[i2]);
                add(&mut n_transition, ntime, jk + nhaz, i, 1.0);
                add(&mut n_event, ntime, k, i, wt[i2]);
            } else if position[i2] > 1 {
                add(&mut n_censor, ntime, j, i, wt[i2]);
                add(&mut n_censor, ntime, j + nstate, i, 1.0);
            }
            person2 -= 1;
        }
        for j in 0..(2 * nstate) {
            set(&mut n_risk, ntime, j, i, ntemp[j]);
        }
    }

    let mut u = vec![vec![0.0; ngrp]; nstate];
    let mut ucopy = vec![vec![0.0; ngrp]; nstate];
    let mut ua = vec![vec![0.0; ngrp]; nstate];
    let mut c_mat = vec![vec![0.0; ngrp]; nhaz];
    let mut wg = vec![vec![0.0; ngrp]; nstate];
    let mut se1 = vec![0.0; nstate];
    let mut se2 = vec![0.0; nhaz];
    let mut se3 = vec![0.0; nstate];
    if want_se {
        for j in 0..nstate {
            let mut temp = 0.0;
            for g in 0..ngrp {
                u[j][g] = i0[g + j * ngrp];
                temp += u[j][g] * u[j][g];
            }
            se1[j] = temp.sqrt();
        }
    }

    let mut person1: usize = 0;
    let mut person2: usize = 0;
    for i in 0..ntime {
        let mut update_phat = !want_se;
        if want_se {
            let delta = if i > 0 {
                utime[i] - utime[i - 1]
            } else {
                utime[i] - t0
            };
            for j in 0..nstate {
                let mut temp = 0.0;
                for g in 0..ngrp {
                    ua[j][g] += delta * u[j][g];
                    temp += ua[j][g] * ua[j][g];
                }
                se3[j] = temp.sqrt();
            }
            while person1 < nused {
                let i1 = sort1[person1] as usize;
                if col(y, n, 0, i1) < utime[i] {
                    let j = cstate[i1] as usize;
                    wg[j][grp[i1] as usize] += wt[i1];
                    person1 += 1;
                } else {
                    break;
                }
            }
            while person2 < nused {
                let i2 = sort2[person2] as usize;
                if col(y, n, 1, i2) < utime[i] {
                    let j = cstate[i2] as usize;
                    wg[j][grp[i2] as usize] -= wt[i2];
                    person2 += 1;
                } else {
                    break;
                }
            }

            let mut h = vec![vec![0.0; nstate]; nstate];
            let mut hcopy = vec![0u8; nstate];
            let mut tdeath = 0i32;
            let mut p = person2;
            while p < nused {
                let i2 = sort2[p] as usize;
                let stop = col(y, n, 1, i2);
                if stop > utime[i] {
                    break;
                }
                let event = col(y, n, 2, i2);
                if stop == utime[i] && event > 0.0 {
                    tdeath += 1;
                    let j = cstate[i2] as usize;
                    let k = (event as i32 - 1) as usize;
                    let jk = transition(hindx, nstate, j, k)?;
                    let g = grp[i2] as usize;
                    let risk = at(&n_risk, ntime, j, i);
                    c_mat[jk][g] += wt[i2] / risk;
                    if j != k {
                        h[j][j] -= wt[i2] / risk;
                        h[j][k] += wt[i2] / risk;
                    }
                }
                p += 1;
            }
            if tdeath != 0 {
                // U = U + U H. H is stored as H[from][to], and a zero diagonal
                // means that whole from-state row is zero.
                for j in 0..nstate {
                    if h[j][j] != 0.0 {
                        for k in 0..nstate {
                            if k != j && h[j][k] != 0.0 {
                                if h[k][k] != 0.0 && k > j && hcopy[k] == 0 {
                                    hcopy[k] = 1;
                                    ucopy[k].copy_from_slice(&u[k]);
                                }
                                if hcopy[j] == 0 {
                                    for g in 0..ngrp {
                                        u[k][g] += u[j][g] * h[j][k];
                                    }
                                } else {
                                    for g in 0..ngrp {
                                        u[k][g] += ucopy[j][g] * h[j][k];
                                    }
                                }
                            }
                        }
                        if hcopy[j] == 0 {
                            for g in 0..ngrp {
                                u[j][g] += u[j][g] * h[j][j];
                            }
                        } else {
                            for g in 0..ngrp {
                                u[j][g] += ucopy[j][g] * h[j][j];
                            }
                        }
                    }
                }
                p = person2;
                while p < nused {
                    let i2 = sort2[p] as usize;
                    let stop = col(y, n, 1, i2);
                    if stop > utime[i] {
                        break;
                    }
                    let event = col(y, n, 2, i2);
                    if stop == utime[i] && event > 0.0 {
                        let j = cstate[i2] as usize;
                        let k = (event as i32 - 1) as usize;
                        let g = grp[i2] as usize;
                        if j != k {
                            let bump = wt[i2] * phat[j] / at(&n_risk, ntime, j, i);
                            u[j][g] -= bump;
                            u[k][g] += bump;
                        }
                    }
                    p += 1;
                }
                for jk in 0..nhaz {
                    if at(&n_transition, ntime, jk, i) > 0.0 {
                        let j = trmat[jk] as usize;
                        let k = trmat[jk + nhaz] as usize;
                        let haz = at(&n_transition, ntime, jk, i) / at(&n_risk, ntime, j, i);
                        let htemp = haz / at(&n_risk, ntime, j, i);
                        for g in 0..ngrp {
                            if wg[j][g] > 0.0 {
                                c_mat[jk][g] -= wg[j][g] * htemp;
                            }
                        }
                        if j != k {
                            for g in 0..ngrp {
                                if wg[j][g] > 0.0 {
                                    let bump = wg[j][g] * phat[j] * htemp;
                                    u[j][g] += bump;
                                    u[k][g] -= bump;
                                }
                            }
                        }
                    }
                }
                if tdeath > 0 || i == 0 {
                    for j in 0..nstate {
                        let mut temp = 0.0;
                        for g in 0..ngrp {
                            temp += u[j][g] * u[j][g];
                        }
                        se1[j] = temp.sqrt();
                    }
                    for jk in 0..nhaz {
                        let mut temp = 0.0;
                        for g in 0..ngrp {
                            temp += c_mat[jk][g] * c_mat[jk][g];
                        }
                        se2[jk] = temp.sqrt();
                    }
                }
                update_phat = true;
            }
        }

        if update_phat {
            let prev = phat.clone();
            for jk in 0..nhaz {
                let count = at(&n_transition, ntime, jk, i);
                if count > 0.0 {
                    let j = trmat[jk] as usize;
                    let k = trmat[jk + nhaz] as usize;
                    let haz = count / at(&n_risk, ntime, j, i);
                    chaz[jk] += haz;
                    phat[j] -= prev[j] * haz;
                    phat[k] += prev[j] * haz;
                }
            }
        }

        for j in 0..nstate {
            set(&mut pstate, ntime, j, i, phat[j]);
            if want_se {
                set(&mut std_err, ntime, j, i, se1[j]);
                set(&mut std_auc, ntime, j, i, se3[j]);
            }
        }
        for jk in 0..nhaz {
            set(&mut cumhaz, ntime, jk, i, chaz[jk]);
            if want_se {
                set(&mut std_chaz, ntime, jk, i, se2[jk]);
            }
        }
        if want_influence {
            let mut offset = i * ngrp * nstate;
            for j in 0..nstate {
                for g in 0..ngrp {
                    influence[offset] = u[j][g];
                    offset += 1;
                }
            }
        }
    }

    Ok(SurvfitAj {
        n_risk,
        n_event,
        n_censor,
        pstate,
        cumhaz,
        std_err,
        std_chaz,
        std_auc,
        influence,
        n_enter,
        n_transition,
    })
}

fn col(y: &[f64], nrows: usize, column: usize, row: usize) -> f64 {
    y[row + column * nrows]
}

fn at(flat: &[f64], nrow: usize, column: usize, row: usize) -> f64 {
    flat[row + column * nrow]
}

fn set(flat: &mut [f64], nrow: usize, column: usize, row: usize, value: f64) {
    flat[row + column * nrow] = value;
}

fn add(flat: &mut [f64], nrow: usize, column: usize, row: usize, value: f64) {
    flat[row + column * nrow] += value;
}

fn transition(hindx: &[i32], nstate: usize, from: usize, to: usize) -> Result<usize, String> {
    if from >= nstate || to >= nstate {
        return Err(format!("state pair {from}->{to} is outside 0..{nstate}"));
    }
    let jk = hindx[from + to * nstate];
    if jk < 0 {
        return Err(format!("no transition from state {from} to state {to}"));
    }
    Ok(jk as usize)
}

fn check_index(sort: &[i32], nrows: usize, what: &str) -> Result<(), String> {
    for &idx in sort {
        if idx < 0 || idx as usize >= nrows {
            return Err(format!("{what} index {idx} is outside 0..{nrows}"));
        }
    }
    Ok(())
}

#[cfg(feature = "python")]
#[pymodule(name = "survfitaj")]
fn survfitaj_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(survfitaj_py, m)?)?;
    Ok(())
}

#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(name = "survfitaj")]
fn survfitaj_py(
    y: Vec<f64>,
    n: usize,
    sort1: Vec<i32>,
    sort2: Vec<i32>,
    utime: Vec<f64>,
    cstate: Vec<i32>,
    wt: Vec<f64>,
    grp: Vec<i32>,
    ngrp: usize,
    p0: Vec<f64>,
    i0: Vec<f64>,
    sefit: i32,
    entry: i32,
    position: Vec<i32>,
    hindx: Vec<i32>,
    trmat: Vec<i32>,
    t0: f64,
) -> PyResult<(
    Vec<f64>,
    Vec<f64>,
    Vec<f64>,
    Vec<f64>,
    Vec<f64>,
    Vec<f64>,
    Vec<f64>,
    Vec<f64>,
    Vec<f64>,
    Vec<f64>,
    Vec<f64>,
)> {
    let fit = survfitaj(
        &y, n, &sort1, &sort2, &utime, &cstate, &wt, &grp, ngrp, &p0, &i0, sefit, entry,
        &position, &hindx, &trmat, t0,
    )
    .map_err(pyo3::exceptions::PyValueError::new_err)?;
    Ok((
        fit.n_risk,
        fit.n_event,
        fit.n_censor,
        fit.pstate,
        fit.cumhaz,
        fit.std_err,
        fit.std_chaz,
        fit.std_auc,
        fit.influence,
        fit.n_enter,
        fit.n_transition,
    ))
}

#[cfg(test)]
mod tests {
    use super::survfitaj;

    fn competing(sefit: i32) -> super::SurvfitAj {
        // Three subjects, times 1, 2, 3: death, censor, pcm.
        // States (s0)=0, death=1, pcm=2. Remapped event codes are 2 and 3.
        let n = 3usize;
        let mut y = vec![0.0; n * 3];
        y[3] = 1.0;
        y[4] = 2.0;
        y[5] = 3.0;
        y[6] = 2.0;
        y[8] = 3.0;
        let sort = vec![0, 1, 2];
        let position = vec![3, 3, 3];
        let cstate = vec![0, 0, 0];
        let wt = vec![1.0, 1.0, 1.0];
        let grp = vec![0, 1, 2];
        let p0 = vec![1.0, 0.0, 0.0];
        let i0 = vec![0.0; 9];
        let mut hindx = vec![-1; 9];
        hindx[0 + 1 * 3] = 0;
        hindx[0 + 2 * 3] = 1;
        let trmat = vec![0, 0, 1, 2];
        survfitaj(
            &y,
            n,
            &sort,
            &sort,
            &[1.0, 2.0, 3.0],
            &cstate,
            &wt,
            &grp,
            3,
            &p0,
            &i0,
            sefit,
            0,
            &position,
            &hindx,
            &trmat,
            0.0,
        )
        .unwrap()
    }

    #[test]
    fn competing_risks_three_subjects() {
        let fit = competing(0);
        assert_eq!(&fit.n_risk[..3], &[3.0, 2.0, 1.0]);
        assert_eq!(&fit.n_risk[3..6], &[0.0, 0.0, 0.0]);
        assert_eq!(&fit.n_event[..3], &[0.0, 0.0, 0.0]);
        assert_eq!(&fit.n_event[3..6], &[1.0, 0.0, 0.0]);
        assert_eq!(&fit.n_event[6..], &[0.0, 0.0, 1.0]);
        assert_eq!(&fit.n_censor[..3], &[0.0, 1.0, 0.0]);
        assert_eq!(&fit.n_transition[..3], &[1.0, 0.0, 0.0]);
        assert_eq!(&fit.n_transition[3..6], &[0.0, 0.0, 1.0]);
        let p = &fit.pstate;
        assert!((p[0] - 2.0 / 3.0).abs() < 1e-12);
        assert!((p[1] - 2.0 / 3.0).abs() < 1e-12);
        assert!(p[2].abs() < 1e-12);
        assert!((p[3] - 1.0 / 3.0).abs() < 1e-12);
        assert!((p[4] - 1.0 / 3.0).abs() < 1e-12);
        assert!((p[5] - 1.0 / 3.0).abs() < 1e-12);
        assert!(p[6].abs() < 1e-12);
        assert!(p[7].abs() < 1e-12);
        assert!((p[8] - 2.0 / 3.0).abs() < 1e-12);
        assert!((fit.cumhaz[0] - 1.0 / 3.0).abs() < 1e-12);
        assert!((fit.cumhaz[2] - 1.0 / 3.0).abs() < 1e-12);
        assert!(fit.cumhaz[3].abs() < 1e-12);
        assert!((fit.cumhaz[5] - 1.0).abs() < 1e-12);
        assert!(fit.std_err.is_empty());
        assert!(fit.n_enter.is_empty());
    }

    #[test]
    fn standard_errors_do_not_change_the_estimate() {
        let plain = competing(0);
        let with_se = competing(1);
        assert_eq!(plain.pstate, with_se.pstate);
        assert_eq!(plain.cumhaz, with_se.cumhaz);
        assert_eq!(with_se.std_err.len(), 9);
        assert!(with_se.std_err.iter().all(|v| v.is_finite()));
        assert!(with_se.influence.is_empty());
        let both = competing(2);
        assert_eq!(both.influence.len(), 3 * 3 * 3);
    }
}
