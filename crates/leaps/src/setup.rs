//! Orthogonal reduction and tolerance setup, ported from leaps 3.2 `src/leaps.f`:
//! `INCLUD` (AS 274 update), `MAKEQR`, `TOLSET`, `SSLEAPS`, `SING` and `INITR`.
//!
//! Vectors are 1-based (index 0 unused). `RBAR` is packed by rows, as in the
//! Fortran.

use crate::{nrbar_for, Mat};

const LARGE: f64 = 1.0e35;

/// Update the reduction by one weighted row. `xrow` is overwritten, as in
/// the Fortran. Returns `IER`.
#[allow(clippy::too_many_arguments)]
pub fn includ(
    np: usize,
    nrbar: usize,
    weight: f64,
    xrow: &mut [f64],
    yelem: f64,
    d: &mut [f64],
    rbar: &mut [f64],
    thetab: &mut [f64],
    sserr: &mut f64,
) -> i32 {
    if np < 1 {
        return 1;
    }
    if nrbar < nrbar_for(np) {
        return 2;
    }

    let mut w = weight;
    let mut y = yelem;
    let mut nextr = 1usize;
    for i in 1..=np {
        if w == 0.0 {
            return 0;
        }
        let xi = xrow[i];
        if xi == 0.0 {
            nextr += np - i;
            continue;
        }
        let di = d[i];
        let wxi = w * xi;
        let dpi = di + wxi * xi;
        let cbar = di / dpi;
        let sbar = wxi / dpi;
        w = cbar * w;
        d[i] = dpi;
        if i != np {
            for k in (i + 1)..=np {
                let xk = xrow[k];
                xrow[k] = xk - xi * rbar[nextr];
                rbar[nextr] = cbar * rbar[nextr] + sbar * xk;
                nextr += 1;
            }
        }
        let xk = y;
        y = xk - xi * thetab[i];
        thetab[i] = cbar * thetab[i] + sbar * xk;
    }
    *sserr += w * y * y;
    0
}

/// Build the orthogonal reduction from the rows of `x` (row-major, `nn` x `np`).
#[allow(clippy::too_many_arguments)]
pub fn makeqr(
    np: usize,
    x: &[f64],
    y: &[f64],
    wt: &[f64],
    d: &mut [f64],
    rbar: &mut [f64],
    thetab: &mut [f64],
    sserr: &mut f64,
) -> i32 {
    let nn = y.len();
    let nrbar = nrbar_for(np);
    for i in 0..nn {
        let mut xrow = vec![0.0; np + 1];
        xrow[1..].copy_from_slice(&x[i * np..(i + 1) * np]);
        let ier = includ(np, nrbar, wt[i], &mut xrow, y[i], d, rbar, thetab, sserr);
        if ier != 0 {
            return ier;
        }
    }
    0
}

/// Tolerances for testing zero columns of the reduction. Returns `IER`.
pub fn tolset(np: usize, nrbar: usize, d: &[f64], rbar: &[f64], tol: &mut [f64]) -> i32 {
    if np < 1 {
        return 1;
    }
    if nrbar < nrbar_for(np) {
        return 2;
    }
    const EPS: f64 = 5.0e-10;
    let mut work = vec![0.0; np + 1];
    for row in 1..=np {
        work[row] = d[row].sqrt();
    }
    for col in 1..=np {
        let mut pos = col - 1;
        let mut sum = work[col];
        for row in 1..col {
            sum += rbar[pos].abs() * work[row];
            pos = pos + np - row - 1;
        }
        tol[col] = EPS * sum;
    }
    0
}

/// Partial residual sums of squares for positions `1..=np`. Returns `IER`.
pub fn ssleaps(np: usize, d: &[f64], thetab: &[f64], sserr: f64, rss: &mut [f64]) -> i32 {
    if np < 1 {
        return 1;
    }
    let mut sum = sserr;
    rss[np] = sserr;
    for i in (2..=np).rev() {
        sum += d[i] * (thetab[i] * thetab[i]);
        rss[i - 1] = sum;
    }
    0
}

/// Detect singular columns and adjust the reduction. Returns `IER`.
#[allow(clippy::too_many_arguments)]
pub fn sing(
    np: usize,
    nrbar: usize,
    d: &mut [f64],
    rbar: &mut [f64],
    thetab: &mut [f64],
    sserr: &mut f64,
    tol: &[f64],
    lindep: &mut [bool],
) -> i32 {
    let mut ier = 0;
    if np < 1 {
        ier = 1;
    }
    if nrbar < nrbar_for(np) {
        ier += 2;
    }
    if ier != 0 {
        return ier;
    }

    let mut work = vec![0.0; np + 1];
    for col in 1..=np {
        work[col] = d[col].sqrt();
    }

    for col in 1..=np {
        let temp = tol[col];
        let mut pos = col - 1;
        for row in 1..col {
            if rbar[pos].abs() * work[row] < temp {
                rbar[pos] = 0.0;
            }
            pos = pos + np - row - 1;
        }

        lindep[col] = false;
        if work[col] <= temp {
            lindep[col] = true;
            // INCLUD takes IER as an output and resets it, as in the Fortran.
            if col < np {
                let nc2 = np - col;
                let pos2 = pos + np - col + 1;
                let nr2 = nc2 * (nc2 - 1) / 2;
                // XROW = RBAR(POS+1..) and the RBAR block at POS2 share one
                // array, so both are copied out, updated, and copied back.
                let mut xrow = vec![0.0; nc2 + 1];
                for k in 1..=nc2 {
                    xrow[k] = rbar[pos + k];
                }
                let mut sub = vec![0.0; nr2 + 1];
                for k in 1..=nr2 {
                    sub[k] = rbar[pos2 + k - 1];
                }
                let weight = d[col];
                let yelem = thetab[col];
                ier = includ(
                    nc2,
                    nr2,
                    weight,
                    &mut xrow,
                    yelem,
                    &mut d[col..],
                    &mut sub,
                    &mut thetab[col..],
                    sserr,
                );
                for k in 1..=nc2 {
                    rbar[pos + k] = xrow[k];
                }
                for k in 1..=nr2 {
                    rbar[pos2 + k - 1] = sub[k];
                }
            } else {
                *sserr += d[col] * (thetab[col] * thetab[col]);
            }
            d[col] = 0.0;
            work[col] = 0.0;
            thetab[col] = 0.0;
        }
    }
    ier
}

/// Initialise the best-subset record from the initial order. Returns `IER`.
#[allow(clippy::too_many_arguments)]
pub fn initr(
    np: usize,
    nvmax: usize,
    bound: &mut [f64],
    ress: &mut Mat<f64>,
    lopt: &mut Mat<usize>,
    vorder: &[usize],
    rss: &[f64],
) -> i32 {
    let nbest = ress.ncol;
    let mut ier = 0;
    if nbest == 0 {
        ier = 1;
    }
    if nvmax == 0 {
        ier += 2;
    }
    if nvmax > np {
        ier += 4;
    }
    if ress.nrow < nvmax {
        ier += 8;
    }
    if lopt.nrow < nvmax * (nvmax + 1) / 2 {
        ier += 16;
    }
    if ier != 0 {
        return ier;
    }

    for best in 1..=nbest {
        let mut pos = 1;
        for nvar in 1..=nvmax {
            if best == 1 {
                ress.set(nvar, best, rss[nvar]);
            } else {
                ress.set(nvar, best, LARGE);
            }
            if best == nbest {
                bound[nvar] = ress.get(nvar, nbest);
            }
            for i in 1..=nvar {
                if best == 1 {
                    lopt.set(pos, best, vorder[i]);
                } else {
                    lopt.set(pos, best, 0);
                }
                pos += 1;
            }
        }
    }
    0
}
