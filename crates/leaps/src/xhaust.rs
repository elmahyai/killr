//! Leaps-and-bounds exhaustive search, ported from leaps 3.2 `src/leaps.f`.
//!
//! Ported routines: `XHAUST` with its callees `ADD1`, `EXADD1`, `REPORT`
//! and `VMOVE`. Indices follow the Fortran source: vectors are 1-based
//! (index 0 is unused), and [`Mat`] is column-major with 1-based
//! `(row, col)` access. Expressions keep the Fortran evaluation order, so
//! `X**2` is `x * x` and `A * B**2` is `A * (B * B)`.

use crate::{nrbar_for, Mat};

const UNDER1: f64 = 0.9999;
const OVER1: f64 = 1.0001;

/// Reduction in residual sum of squares for each candidate in `first..=last`.
///
/// Returns `(smax, jmax, ier)`. `ss`, `sxx` and `sxy` need indices up to `last`.
#[allow(clippy::too_many_arguments)]
pub fn add1(
    np: usize,
    nrbar: usize,
    d: &[f64],
    rbar: &[f64],
    thetab: &[f64],
    first: usize,
    last: usize,
    tol: &[f64],
    ss: &mut [f64],
    sxx: &mut [f64],
    sxy: &mut [f64],
) -> (f64, usize, i32) {
    let mut jmax = 0usize;
    let mut smax = 0.0;
    let mut ier = 0;
    if first > np {
        ier = 1;
    }
    if last < first {
        ier += 2;
    }
    if first < 1 {
        ier += 4;
    }
    if last > np {
        ier += 8;
    }
    if nrbar < nrbar_for(np) {
        ier += 16;
    }
    if ier != 0 {
        return (smax, jmax, ier);
    }

    for j in first..=last {
        sxx[j] = 0.0;
        sxy[j] = 0.0;
    }
    let inc = np - last;
    let mut pos = (first - 1) * (np + np - first) / 2 + 1;
    for row in first..=last {
        let diag = d[row];
        let dy = diag * thetab[row];
        sxx[row] += diag;
        sxy[row] += dy;
        for col in (row + 1)..=last {
            sxx[col] += diag * (rbar[pos] * rbar[pos]);
            sxy[col] += dy * rbar[pos];
            pos += 1;
        }
        pos += inc;
    }

    for j in first..=last {
        let ssqx = sxx[j];
        if ssqx.sqrt() > tol[j] {
            ss[j] = (sxy[j] * sxy[j]) / sxx[j];
            if ss[j] > smax {
                smax = ss[j];
                jmax = j;
            }
        } else {
            ss[j] = 0.0;
        }
    }
    (smax, jmax, ier)
}

/// Record the candidate found by `ADD1` in the best-`NBEST` table, and
/// walk the next best candidates for the same position.
#[allow(clippy::too_many_arguments)]
pub fn exadd1(
    ivar: usize,
    rss: &[f64],
    bound: &mut [f64],
    nvmax: usize,
    ress: &mut Mat<f64>,
    lopt: &mut Mat<usize>,
    vorder: &mut [usize],
    smax: f64,
    jmax: usize,
    ss: &[f64],
    last: usize,
) {
    if jmax == 0 || ivar == 0 || ivar > nvmax {
        return;
    }
    let nbest = ress.ncol;
    let ltemp = vorder[ivar];
    let mut jm = jmax;
    let mut sm = smax;
    let ssbase = if ivar > 1 {
        rss[ivar - 1]
    } else {
        rss[ivar] + ss[1]
    };

    let mut wk = vec![0.0; last + 1];
    for j in ivar..=last {
        wk[j] = ss[j];
    }

    for i in 1..=nbest {
        let temp = ssbase - sm;
        if temp >= bound[ivar] {
            break;
        }
        vorder[ivar] = vorder[jm];
        if jm == ivar {
            vorder[ivar] = ltemp;
        }
        report(ivar, temp, bound, nvmax, ress, lopt, vorder);
        if i >= nbest {
            break;
        }
        wk[jm] = 0.0;
        sm = 0.0;
        jm = 0;
        for j in ivar..=last {
            if wk[j] <= sm {
                continue;
            }
            jm = j;
            sm = wk[j];
        }
        if jm == 0 {
            break;
        }
    }
    vorder[ivar] = ltemp;
}

/// Update the record of the best `NBEST` subsets of `pos` variables with `ssq`.
pub fn report(
    pos: usize,
    ssq: f64,
    bound: &mut [f64],
    nvmax: usize,
    ress: &mut Mat<f64>,
    lopt: &mut Mat<usize>,
    vorder: &[usize],
) {
    if pos > nvmax || ssq >= bound[pos] {
        return;
    }
    let nbest = ress.ncol;

    let mut rank = 1;
    while rank <= nbest {
        if ssq <= ress.get(pos, rank) {
            break;
        }
        rank += 1;
    }
    if rank > nbest {
        return;
    }

    let l0 = pos * (pos - 1) / 2;
    let mut jj = rank;
    // Fortran GO TO 50 (duplicate check) versus GO TO 90 (record).
    let mut check_duplicates;
    if ssq > UNDER1 * ress.get(pos, rank) {
        check_duplicates = true;
    } else if rank == 1 {
        check_duplicates = false;
    } else if ssq > OVER1 * ress.get(pos, rank - 1) {
        check_duplicates = false;
    } else {
        jj = rank - 1;
        check_duplicates = true;
    }

    while check_duplicates {
        // Label 50: is the subset already recorded in slot JJ?
        let mut duplicate = true;
        for j in 1..=pos {
            let listj = vorder[j];
            let mut found = false;
            for i in 1..=pos {
                if listj == lopt.get(l0 + i, jj) {
                    found = true;
                    break;
                }
            }
            if !found {
                duplicate = false;
                break;
            }
        }
        if duplicate {
            return;
        }
        // Label 80.
        jj -= 1;
        check_duplicates = jj > 0 && jj == rank - 1;
    }

    // Label 90: shift down the worse records, then store the new subset.
    if rank != nbest {
        let shift = nbest - rank;
        for i in 1..=shift {
            let jj2 = nbest - i;
            ress.set(pos, jj2 + 1, ress.get(pos, jj2));
            for k in 1..=pos {
                lopt.set(l0 + k, jj2 + 1, lopt.get(l0 + k, jj2));
            }
        }
    }
    ress.set(pos, rank, ssq);
    for k in 1..=pos {
        lopt.set(l0 + k, rank, vorder[k]);
    }
    bound[pos] = ress.get(pos, nbest);
}

/// Move the variable in position `from` to position `to`, keeping the
/// orthogonal reduction (AS 274 plane rotations).
#[allow(clippy::too_many_arguments)]
pub fn vmove(
    np: usize,
    nrbar: usize,
    vorder: &mut [usize],
    d: &mut [f64],
    rbar: &mut [f64],
    thetab: &mut [f64],
    rss: &mut [f64],
    from: usize,
    to: usize,
    tol: &mut [f64],
) -> i32 {
    let mut ier = 0;
    if np < 1 {
        ier = 1;
    }
    if nrbar < nrbar_for(np) {
        ier += 2;
    }
    if from < 1 || from > np {
        ier += 4;
    }
    if to < 1 || to > np {
        ier += 8;
    }
    if ier != 0 || from == to {
        return ier;
    }

    // Fortran DO M = FIRST, LAST, INC.
    let ms: Vec<usize> = if from < to {
        (from..=to - 1).collect()
    } else {
        (to..=from - 1).rev().collect()
    };

    for m in ms {
        let mut m1 = (m - 1) * (np + np - m) / 2 + 1;
        let mut m2 = m1 + np - m;
        let mp1 = m + 1;
        let (d1, d2) = if m <= np {
            (d[m], if mp1 <= np { d[mp1] } else { 0.0 })
        } else {
            (0.0, 0.0)
        };

        // Label 40 is reached directly when both diagonals are zero.
        if !(d1 == 0.0 && d2 == 0.0) {
            let mut x = rbar[m1];
            if x.abs() * d1.sqrt() < tol[mp1] {
                x = 0.0;
            }
            if d1 == 0.0 || x == 0.0 {
                d[m] = d2;
                d[mp1] = d1;
                rbar[m1] = 0.0;
                for _col in (m + 2)..=np {
                    m1 += 1;
                    x = rbar[m1];
                    rbar[m1] = rbar[m2];
                    rbar[m2] = x;
                    m2 += 1;
                }
                x = thetab[m];
                thetab[m] = thetab[mp1];
                thetab[mp1] = x;
            } else if d2 == 0.0 {
                d[m] = d1 * (x * x);
                rbar[m1] = 1.0 / x;
                for _col in (m + 2)..=np {
                    m1 += 1;
                    rbar[m1] /= x;
                }
                thetab[m] /= x;
            } else {
                // Planar rotation in the regular case.
                let d1new = d2 + d1 * (x * x);
                let cbar = d2 / d1new;
                let sbar = (x * d1) / d1new;
                let d2new = d1 * cbar;
                d[m] = d1new;
                d[mp1] = d2new;
                rbar[m1] = sbar;
                for _col in (m + 2)..=np {
                    m1 += 1;
                    let y = rbar[m1];
                    rbar[m1] = cbar * rbar[m2] + sbar * y;
                    rbar[m2] = y - x * rbar[m2];
                    m2 += 1;
                }
                let y = thetab[m];
                thetab[m] = cbar * thetab[mp1] + sbar * y;
                thetab[mp1] = y - x * thetab[mp1];
            }
        }

        // Label 40: swap columns M and M+1 down to row M-1.
        if m != 1 {
            let mut pos = m;
            for row in 1..m {
                let xx = rbar[pos];
                rbar[pos] = rbar[pos - 1];
                rbar[pos - 1] = xx;
                pos = pos + np - row - 1;
            }
        }

        // Label 60: variable order, tolerances and residual sums of squares.
        let t = vorder[m];
        vorder[m] = vorder[mp1];
        vorder[mp1] = t;
        let tt = tol[m];
        tol[m] = tol[mp1];
        tol[mp1] = tt;
        rss[m] = rss[mp1] + d[mp1] * (thetab[mp1] * thetab[mp1]);
    }
    ier
}

/// Exhaustive leaps-and-bounds search over positions `first..=last`.
///
/// `ress` (`nvmax` x `nbest`) and `lopt` (`il` x `nbest`) receive the best
/// subsets. Returns `IER` as in the Fortran; `-999` means a singular diagonal.
#[allow(clippy::too_many_arguments)]
pub fn xhaust(
    np: usize,
    nrbar: usize,
    d: &mut [f64],
    rbar: &mut [f64],
    thetab: &mut [f64],
    first: usize,
    last: usize,
    vorder: &mut [usize],
    tol: &mut [f64],
    rss: &mut [f64],
    bound: &mut [f64],
    nvmax: usize,
    ress: &mut Mat<f64>,
    lopt: &mut Mat<usize>,
) -> i32 {
    let mut ier = 0;
    if first >= np {
        ier = 1;
    }
    if last <= 1 {
        ier += 2;
    }
    if first < 1 {
        ier += 4;
    }
    if last > np {
        ier += 8;
    }
    if nrbar < nrbar_for(np) {
        ier += 16;
    }
    let nbest = ress.ncol;
    if nbest > 0 {
        let need = nvmax * (nvmax + 1) / 2;
        if ress.nrow < nvmax {
            ier += 64;
        }
        if lopt.nrow < need {
            ier += 128;
        }
    }
    if ier != 0 || nbest == 0 {
        return ier;
    }

    // Work arrays, one per Fortran WK segment (SS, SXX, SXY).
    let mut ss = vec![0.0; last + 1];
    let mut sxx = vec![0.0; last + 1];
    let mut sxy = vec![0.0; last + 1];

    // Record the subsets in the initial order.
    for row in first..=nvmax {
        if d[row] <= tol[row] {
            return -999;
        }
        report(row, rss[row], bound, nvmax, ress, lopt, vorder);
    }

    // IWK(I) is the upper limit of the simulated DO loop for position I.
    let mut iwk = vec![0isize; nvmax + 1];
    for i in first..=nvmax {
        iwk[i] = last as isize;
    }

    let mut ipt: isize = 0;
    let mut at_label_30 = true;
    loop {
        if at_label_30 {
            // Label 30: innermost loop, best variable for position NVMAX.
            at_label_30 = false;
            let lim = iwk[nvmax] as usize;
            let (smax, jmax, e) = add1(
                np,
                nrbar,
                d,
                rbar,
                thetab,
                nvmax,
                lim,
                tol,
                &mut ss,
                &mut sxx,
                &mut sxy,
            );
            ier = e;
            exadd1(
                nvmax, rss, bound, nvmax, ress, lopt, vorder, smax, jmax, &ss, lim,
            );
            ipt = nvmax as isize - 1;
        }

        // Label 40: move to the next lower loop that is not exhausted.
        if ipt >= iwk[ipt as usize] {
            ipt -= 1;
            if ipt >= first as isize {
                continue;
            }
            return ier;
        }

        let ip = ipt as usize;
        let newpos = iwk[ip] as usize;
        ier = vmove(np, nrbar, vorder, d, rbar, thetab, rss, ip, newpos, tol);
        for i in ip..=std::cmp::min(nvmax, newpos - 1) {
            report(i, rss[i], bound, nvmax, ress, lopt, vorder);
        }

        for i in ip..=nvmax {
            iwk[i] = newpos as isize - 1;
        }

        // If the RSS for the moved position already exceeds BOUND(I) for
        // some I, no better subsets of that size exist inside this loop.
        let temp = rss[newpos - 1];
        let mut cut = None;
        for i in ip..=nvmax {
            if temp > bound[i] {
                cut = Some(i);
                break;
            }
        }
        match cut {
            Some(i) => {
                ipt = i as isize - 1;
                if ipt < first as isize {
                    return ier;
                }
            }
            None => {
                if iwk[nvmax] > nvmax as isize {
                    at_label_30 = true;
                    continue;
                }
                ipt = nvmax as isize - 1;
            }
        }
    }
}
