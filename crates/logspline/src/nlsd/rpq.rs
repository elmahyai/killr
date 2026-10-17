//! Density, distribution function and quantiles of a fitted log-spline:
//! `rpqlsd` in `src/nlsd.c` and its helpers (`getp0`..`getq2`, `z1int`,
//! `z2int`, `z3int`, `pqexpi`).

use super::base::{mat, mylog, myexp};
use crate::lsdall::tables::{GL12_W, GL12_Y, GL3_W, GL3_Y};

/// `getf`: exp of the cubic `cf` at x.
fn getf(c: &[f64], x: f64) -> f64 {
    (c[0] + x * (c[1] + x * (c[2] + x * c[3]))).exp()
}

/// `z1int`: integral from -inf to t1 (`j == 1`) or from t1 to inf (`j == -1`)
/// of exp(polynomial(c0)).
fn z1int(t1: f64, c0: &[f64], j: i32) -> f64 {
    let mut j = j;
    if c0[1] < 0.0 {
        j = -j;
    }
    let mut f1 = mylog((1.0 / c0[1]).abs()) + c0[1] * t1 + c0[0];
    if f1 > 600.0 {
        f1 = 600.0;
    }
    (j as f64) * myexp(f1)
}

/// `z2int`: integral from t1 to t2 of exp(polynomial(c0)).
fn z2int(t1: f64, t2: f64, c0: &[f64]) -> f64 {
    let mut i1: i32 = 1;
    if t2 == t1 {
        return 0.0;
    }
    if c0[1] != 0.0 {
        if c0[1] < 0.0 {
            i1 = -1;
        }
        let mut f1 = mylog((1.0 / c0[1]).abs()) + c0[1] * t1 + c0[0];
        let mut f2 = f1 + c0[1] * (t2 - t1);
        if f1 > 600.0 {
            f1 = 600.0;
        }
        if f2 > 600.0 {
            f2 = 600.0;
        }
        (i1 as f64) * myexp(f2) - (i1 as f64) * myexp(f1)
    } else {
        (t2 - t1) * myexp(c0[0])
    }
}

/// `z3int`: integral from k1 to k2 of exp(polynomial(coef)) by Gauss-Legendre
/// quadrature (3-point when `accuracy == 1`, otherwise 32-point).
fn z3int(k1: f64, k2: f64, coef: &[f64], accuracy: i32) -> f64 {
    let mut vv = 0.0f64;
    if k2 == k1 {
        return 0.0;
    }
    let r1 = (k2 - k1) / 2.0;
    let r2 = (k2 + k1) / 2.0;
    if accuracy == 1 {
        for i1 in 1..4 {
            let y = GL3_Y[i1] * r1;
            let v = r1 * GL3_W[i1];
            let mut x = r2 - y;
            vv += v * myexp(coef[0] + x * (coef[1] + x * (coef[2] + x * coef[3])));
            x = r2 + y;
            vv += v * myexp(coef[0] + x * (coef[1] + x * (coef[2] + x * coef[3])));
        }
    } else {
        for i1 in 1..33 {
            let y = GL12_Y[i1] * r1;
            let v = r1 * GL12_W[i1];
            let mut x = r2 - y;
            vv += v * myexp(coef[0] + x * (coef[1] + x * (coef[2] + x * coef[3])));
            x = r2 + y;
            vv += v * myexp(coef[0] + x * (coef[1] + x * (coef[2] + x * coef[3])));
        }
    }
    vv
}

/// `pqexpi`: invert the distribution function on one interval.
/// `version`: 1 = -inf -> x, 2 = t -> x, 3 = x -> inf, 4 = x -> t.
fn pqexpi(version: i32, t: f64, p: f64, cf: &[f64]) -> f64 {
    let mut t = t;
    let mut p = p;
    if cf[1] != 0.0 || version == 1 || version == 3 {
        p *= cf[1];
        if version == 1 && p < 0.0 {
            return myexp(600.0);
        }
        if version == 3 && p > 0.0 {
            return -myexp(600.0);
        }
        if version == 2 || version == 4 {
            t = myexp(t * cf[1] + cf[0]);
        }
        if version == 2 && t + p < 0.0 {
            return myexp(600.0);
        }
        if version == 4 && t - p < 0.0 {
            return -myexp(600.0);
        }
        if version == 1 {
            return (mylog(p) - cf[0]) / cf[1];
        }
        if version == 2 {
            return (mylog(t + p) - cf[0]) / cf[1];
        }
        if version == 3 {
            return (mylog(-p) - cf[0]) / cf[1];
        }
        return (mylog(t - p) - cf[0]) / cf[1];
    }
    if version == 2 {
        return t + p / myexp(cf[0]);
    }
    t - p / myexp(cf[0])
}

/// `getp0`: probabilities for the first interval (from kpl[0] to the knot).
fn getp0(q: &[f64], p: &mut [f64], f: usize, l: usize, cf: &[f64], k: f64, b: f64, cr: f64) {
    if b > 0.5 {
        for i in f..=l {
            p[i] = z2int(k, q[i], cf) / cr;
        }
    } else {
        for i in f..=l {
            p[i] = z1int(q[i], cf, 1) / cr;
        }
    }
}

/// `getq0`: quantiles for the first interval.
fn getq0(p: &[f64], q: &mut [f64], f: usize, l: usize, cf: &[f64], k: f64, b: f64, cr: f64) {
    if b > 0.5 {
        for i in f..=l {
            q[i] = pqexpi(2, k, p[i] / cr, cf);
        }
    } else {
        for i in f..=l {
            q[i] = pqexpi(1, k, p[i] / cr, cf);
        }
    }
}

/// `getp2`: probabilities beyond the last knot.
fn getp2(q: &[f64], p: &mut [f64], f: usize, l: usize, cf: &[f64], k: f64, b: f64, cr: f64) {
    if b > 0.5 {
        for i in f..=l {
            p[i] = 1.0 - z2int(q[i], k, cf) / cr;
        }
    } else {
        for i in f..=l {
            p[i] = 1.0 - z1int(q[i], cf, -1) / cr;
        }
    }
}

/// `getq2`: quantiles beyond the last knot.
fn getq2(p: &[f64], q: &mut [f64], f: usize, l: usize, cf: &[f64], k: f64, b: f64, cr: f64) {
    if b > 0.5 {
        for i in f..=l {
            q[i] = pqexpi(4, k, 1.0 - p[i] / cr, cf);
        }
    } else {
        for i in f..=l {
            q[i] = pqexpi(3, k, 1.0 - p[i] / cr, cf);
        }
    }
}

/// `getp1`: probabilities inside an interval (k0, k1), scaled to (p0, p1).
#[allow(clippy::too_many_arguments)]
fn getp1(q: &[f64], p: &mut [f64], f: usize, l: usize, cf: &[f64], k0: f64, k1: f64, p0: f64, p1: f64) {
    let j = if l - f > 5 { 1 } else { 0 };
    p[f] = z3int(k0, q[f], cf, j);
    for i in f + 1..=l {
        p[i] = z3int(q[i - 1], q[i], cf, j) + p[i - 1];
    }
    let r = p[l] + z3int(q[l], k1, cf, j);
    let r = (p1 - p0) / r;
    for i in f..=l {
        p[i] = p0 + p[i] * r;
    }
}

/// `getq1`: quantiles inside an interval (k0, k1), from a 100-step table.
#[allow(clippy::too_many_arguments)]
fn getq1(p: &[f64], q: &mut [f64], f: usize, l: usize, cf: &[f64], k0: f64, k1: f64, p0: f64, p1: f64) {
    // y is one element longer than C's to keep the out-of-range read defined
    let mut y = [0.0f64; 60];
    let mut f1 = [0.0f64; 101];
    let r = (k1 - k0) / 100.0;
    for i in 0..101 {
        f1[i] = getf(cf, k0 + r * (i as f64));
    }
    y[0] = 0.0;
    for i in 1..=50 {
        y[i] = y[i - 1] + r * (f1[2 * (i - 1)] + 4.0 * f1[2 * i - 1] + f1[2 * i]) / 3.0;
    }
    let mut s = (p1 - p0) / y[50];
    for i in 0..=50 {
        y[i] = p0 + y[i] * s;
    }
    y[0] = p0;
    y[50] = p1;
    let mut i: usize = 0;
    s = 2.0 * r;
    for j in f..=l {
        q[j] = k0 - 1.0;
        loop {
            if p[j] >= y[i] && p[j] <= y[i + 1] {
                q[j] = k0 + s * (i as f64) + s * (p[j] - y[i]) / (y[i + 1] - y[i]);
            } else {
                i += 1;
            }
            if !(q[j] < k0 && i < 50) {
                break;
            }
        }
    }
}

/// `rpqlsd`: evaluate the density (`ipq == 0`, returning quantile-free
/// probabilities into `pq`) or invert the distribution function (`ipq != 0`).
/// `coef` holds the fit (`coef[0..2]` linear tail terms, then one per knot),
/// `knots` the knots, `bnd` the four bound flags and values, `pq` the
/// evaluation points (in) and results (out).
pub fn rpqlsd(
    coef: &[f64],
    knots: &[f64],
    bnd: &[f64],
    ipq: i32,
    pq: &mut [f64],
    lk: i32,
    lp: i32,
) {
    let lku = lk as usize;
    let lpu = lp as usize;
    let sz = 4 * lku + 2;
    let mut kpl = vec![0.0f64; sz];
    let mut ppl = vec![0.0f64; sz];
    let mut cpl = mat(sz, 4);
    let mut pqx = vec![0.0f64; lpu + 1];
    // get the integration points: the knots
    let mut nk = lku + 1;
    for i in 0..=nk {
        if i < nk && i > 0 {
            kpl[i] = knots[i - 1];
        }
        if i == 0 {
            kpl[0] = knots[0] - 1.0;
            if bnd[0] > 0.5 {
                kpl[0] = bnd[1];
            } else if pq[0] < kpl[0] {
                kpl[0] = pq[0] - 1.0;
            }
        }
        if i == nk {
            kpl[nk] = knots[nk - 2] + 1.0;
            if bnd[2] > 0.5 {
                kpl[nk] = bnd[3];
            } else if pq[lpu - 1] + 1.0 > kpl[nk] {
                kpl[nk] = pq[lpu - 1] + 1.0;
            }
        }
        // get the coefficients
        cpl[i][0] = coef[0];
        cpl[i][1] = coef[1];
        cpl[i][2] = 0.0;
        cpl[i][3] = 0.0;
        let mut j = 0usize;
        while i > j && j < lku {
            cpl[i][3] += coef[j + 2];
            cpl[i][2] -= 3.0 * coef[j + 2] * knots[j];
            cpl[i][1] += 3.0 * coef[j + 2] * knots[j] * knots[j];
            cpl[i][0] -= coef[j + 2] * knots[j] * knots[j] * knots[j];
            j += 1;
        }
        if i + 1 >= nk {
            cpl[i][3] = 0.0;
            cpl[i][2] = 0.0;
        }
    }
    // compute the density
    ppl[0] = 0.0;
    if bnd[0] > 0.5 {
        ppl[1] = z2int(kpl[0], kpl[1], &cpl[0]);
    } else {
        ppl[1] = z1int(kpl[1], &cpl[0], 1);
    }
    for i in 1..nk - 1 {
        ppl[i + 1] = z3int(kpl[i], kpl[i + 1], &cpl[i], 0) + ppl[i];
    }
    if bnd[2] > 0.5 {
        ppl[nk] = z2int(kpl[nk - 1], kpl[nk], &cpl[nk - 1]) + ppl[nk - 1];
    } else {
        ppl[nk] = z1int(kpl[nk - 1], &cpl[nk - 1], -1) + ppl[nk - 1];
    }
    // higher precision needed
    if ppl[nk] < 0.99999 || ppl[nk] > 1.00001 {
        // integration points: knots times four
        nk = 4 * lku - 2;
        for i in 0..=nk {
            if i < nk && i > 0 {
                let j = (((i - 1) as f64) / 4.0).floor() as usize;
                let r = (i as f64) / 4.0 - (j as f64) - 0.25;
                if r > 0.01 {
                    kpl[i] = (1.0 - r) * knots[j] + r * knots[j + 1];
                } else {
                    kpl[i] = (1.0 - r) * knots[j];
                }
            }
            if i == 0 {
                kpl[0] = knots[0] - 1.0;
                if bnd[0] > 0.5 {
                    kpl[0] = bnd[1];
                } else if pq[0] < kpl[0] {
                    kpl[0] = pq[0] - 1.0;
                }
            }
            if i == nk {
                kpl[nk] = knots[lku - 1] + 1.0;
                if bnd[2] > 0.5 {
                    kpl[nk] = bnd[3];
                } else if pq[lpu - 1] + 1.0 > kpl[nk] {
                    kpl[nk] = pq[lpu - 1] + 1.0;
                }
            }
            // get the coefficients
            cpl[i][0] = coef[0];
            cpl[i][1] = coef[1];
            cpl[i][2] = 0.0;
            cpl[i][3] = 0.0;
            let mut j = 0usize;
            while i > j * 4 && j < lku {
                cpl[i][3] += coef[j + 2];
                cpl[i][2] -= 3.0 * coef[j + 2] * knots[j];
                cpl[i][1] += 3.0 * coef[j + 2] * knots[j] * knots[j];
                cpl[i][0] -= coef[j + 2] * knots[j] * knots[j] * knots[j];
                j += 1;
            }
            if i + 1 >= nk {
                cpl[i][3] = 0.0;
                cpl[i][2] = 0.0;
            }
        }
        // compute the density
        if bnd[0] > 0.5 {
            ppl[1] = z2int(kpl[0], kpl[1], &cpl[0]);
        } else {
            ppl[1] = z1int(kpl[1], &cpl[0], 1);
        }
        for i in 1..nk - 1 {
            ppl[i + 1] = z3int(kpl[i], kpl[i + 1], &cpl[i], 0) + ppl[i];
        }
        if bnd[2] > 0.5 {
            ppl[nk] = z2int(kpl[nk - 1], kpl[nk], &cpl[nk - 1]) + ppl[nk - 1];
        } else {
            ppl[nk] = z1int(kpl[nk - 1], &cpl[nk - 1], -1) + ppl[nk - 1];
        }
    }
    // correction factor
    let cor = 1.0f64;
    // correct the density
    for i in 0..=nk {
        cpl[i][0] = cpl[i][0] + (1.0 / ppl[nk]).ln();
    }
    for i in 0..=nk {
        ppl[i] = ppl[i] / ppl[nk];
    }
    let zz: Vec<f64> = if ipq == 0 { ppl.clone() } else { kpl.clone() };

    // before the first point
    let mut j: usize = 0;
    while j < lpu && pq[j] <= zz[0] {
        if ipq == 0 {
            if bnd[0] > 0.5 {
                pqx[j] = kpl[0];
            } else {
                pqx[j] = -1.0e100;
            }
        } else {
            pqx[j] = 0.0;
        }
        j += 1;
    }
    // before the first knot
    let mut fst = j;
    let mut lst: isize = j as isize - 1;
    let jx = j;
    j = jx;
    while j < lpu && pq[j] <= zz[1] {
        lst = j as isize;
        j += 1;
    }
    if lst >= fst as isize {
        let l = lst as usize;
        if ipq == 0 {
            getq0(pq, &mut pqx, fst, l, &cpl[0], kpl[0], bnd[0], cor);
        } else {
            getp0(pq, &mut pqx, fst, l, &cpl[0], kpl[0], bnd[0], cor);
        }
    }
    // per interval between integration points
    for i in 1..nk - 1 {
        fst = j;
        lst = j as isize - 1;
        let jx = j;
        j = jx;
        while j < lpu && pq[j] <= zz[i + 1] {
            lst = j as isize;
            j += 1;
        }
        if lst >= fst as isize {
            let l = lst as usize;
            if ipq == 0 {
                getq1(pq, &mut pqx, fst, l, &cpl[i], kpl[i], kpl[i + 1], ppl[i], ppl[i + 1]);
            } else {
                getp1(pq, &mut pqx, fst, l, &cpl[i], kpl[i], kpl[i + 1], ppl[i], ppl[i + 1]);
            }
        }
    }
    // beyond the last knot
    fst = j;
    lst = j as isize - 1;
    let jx = j;
    j = jx;
    while j < lpu && pq[j] < zz[nk] {
        lst = j as isize;
        j += 1;
    }
    if lst >= fst as isize {
        let l = lst as usize;
        if ipq == 0 {
            getq2(pq, &mut pqx, fst, l, &cpl[nk - 1], kpl[nk], bnd[2], cor);
        } else {
            getp2(pq, &mut pqx, fst, l, &cpl[nk - 1], kpl[nk], bnd[2], cor);
        }
    }
    // outside the range
    let jx = j;
    for j in jx..lpu {
        if ipq == 0 {
            if bnd[2] > 0.5 {
                pqx[j] = kpl[nk];
            } else {
                pqx[j] = 1.0e100;
            }
        } else {
            pqx[j] = 1.0;
        }
    }
    for j in 0..lpu {
        pq[j] = pqx[j];
    }
}
