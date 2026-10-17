//! `srqfnc` and `slpfnc` from quantreg 6.1 `src/srqfnc.f`: the constrained
//! sparse Frisch-Newton interior point behind `rq.fit.sfnc`, which `rqss.fit`
//! runs with method "sfnc" when the constraint is not "N".
//!
//! The primal has two blocks: the design `A1` (n1 x m) with the box `0 <= x1 <= u`,
//! and the constraint block `A2` (n2 x m) with `x2 >= 0`. The normal matrix is
//! `E = A1' Q1^(-1) A1 + A2' Q2^(-1) A2`, which is the `h = e + g` of the
//! Fortran. `E` is formed from the CSR rows and factored by a dense Cholesky
//! with the same tiny-pivot rule as `srqfn` in `crates/quantreg/src/sfn.rs`:
//! a pivot at or below `tiny * max(diag E)` is replaced by `large`, and the
//! iteration stops with `ierr = 16 + count`. The Fortran `chlfct` (Ng-Peyton
//! supernodal) is not ported; the iteration, the Mehrotra corrector, the step
//! bound `beta` and the stopping rule follow `slpfnc` line for line.
//!
//! The Fortran 1-based indices are 0-based here. The argument `c1` of
//! `srqfnc` is the negated response; the loop never reads it, so it is not
//! passed. `c2` is the negated constraint right-hand side.

#![allow(clippy::too_many_arguments, clippy::needless_range_loop)]

#[cfg(feature = "python")]
mod python;

/// `beta` in `srqfnc`: the fraction of the distance to the boundary taken per step.
pub const BETA: f64 = 0.9995;
/// `big` in `boundc`: the starting value of the step lengths.
const BIG: f64 = 1.0e20;

/// A design in compressed sparse row form. Row `i` holds the entries
/// `indices[indptr[i]..indptr[i + 1]]` with values `data[...]`, and each row
/// has no repeated column.
pub struct Csr<'a> {
    pub n: usize,
    pub m: usize,
    pub indptr: &'a [usize],
    pub indices: &'a [usize],
    pub data: &'a [f64],
}

/// The result of `srqfnc`: the dual `y` (length m), the iteration count `it`
/// (the Fortran `maxit` on return), and the error code `ierr` (0 when converged).
pub struct SfncOut {
    pub y: Vec<f64>,
    pub it: usize,
    pub ierr: i32,
}

/// The starting point and the tolerances of `srqfnc`.
pub struct SfncStart<'a> {
    /// The right-hand side of the equality constraint `b` (length m).
    pub b: &'a [f64],
    /// The negated constraint right-hand side `c2` (length n2).
    pub c2: &'a [f64],
    /// Primal slacks x1 (length n1), x2 (length n2), and s (length n1).
    pub x1: &'a [f64],
    pub x2: &'a [f64],
    pub s: &'a [f64],
    /// Dual slacks z1 (length n1), z2 (length n2), and w (length n1).
    pub z1: &'a [f64],
    pub z2: &'a [f64],
    pub w: &'a [f64],
    /// The starting dual `y` (length m).
    pub y0: &'a [f64],
    /// Gap tolerance `small`, pivot rule `tiny` and `large`, and the iteration cap.
    pub small: f64,
    pub tiny: f64,
    pub large: f64,
    pub maxit: usize,
}

fn dot(a: &[f64], b: &[f64]) -> f64 {
    a.iter().zip(b).map(|(p, q)| p * q).sum()
}

/// `A v` for a length-m vector `v`: the n-vector `amux(n, v, ., a)`.
fn a_times(a: &Csr, v: &[f64]) -> Vec<f64> {
    (0..a.n)
        .map(|i| {
            (a.indptr[i]..a.indptr[i + 1])
                .map(|p| a.data[p] * v[a.indices[p]])
                .sum()
        })
        .collect()
}

/// `A' v` for a length-n vector `v`: the m-vector `amux(m, v, ., ao)`.
fn at_times(a: &Csr, v: &[f64]) -> Vec<f64> {
    let mut out = vec![0.0; a.m];
    for i in 0..a.n {
        for p in a.indptr[i]..a.indptr[i + 1] {
            out[a.indices[p]] += a.data[p] * v[i];
        }
    }
    out
}

/// Adds `A' diag(q) A` into the dense m x m row-major matrix `e`.
fn add_normal(a: &Csr, q: &[f64], e: &mut [f64]) {
    let m = a.m;
    for i in 0..a.n {
        let (lo, hi) = (a.indptr[i], a.indptr[i + 1]);
        for p in lo..hi {
            let j = a.indices[p];
            let vj = a.data[p] * q[i];
            for t in lo..hi {
                e[j * m + a.indices[t]] += vj * a.data[t];
            }
        }
    }
}

/// `E = A1' Q1^(-1) A1 + A2' Q2^(-1) A2` as a dense m x m row-major matrix,
/// and the largest diagonal entry, which `chlfct` calls `mxdiag`.
fn normal_matrix(a1: &Csr, q1: &[f64], a2: &Csr, q2: &[f64]) -> (Vec<f64>, f64) {
    let m = a1.m;
    let mut e = vec![0.0; m * m];
    add_normal(a1, q1, &mut e);
    add_normal(a2, q2, &mut e);
    let mut mxdiag = 0.0_f64;
    for j in 0..m {
        mxdiag = mxdiag.max(e[j * m + j]);
    }
    (e, mxdiag)
}

/// Upper Cholesky factor `U` (row-major, `E = U'U`) with the `blkfct` tiny-pivot
/// rule. Returns the factor and the number of pivots replaced by `large`.
fn cholesky(e: &[f64], m: usize, mxdiag: f64, tiny: f64, large: f64) -> (Vec<f64>, usize) {
    let mut u = vec![0.0; m * m];
    let mut ntiny = 0usize;
    for j in 0..m {
        let mut d = e[j * m + j];
        for k in 0..j {
            d -= u[k * m + j] * u[k * m + j];
        }
        if d <= tiny * mxdiag {
            d = large;
            ntiny += 1;
        }
        let ujj = d.sqrt();
        u[j * m + j] = ujj;
        for i in j + 1..m {
            let mut t = e[j * m + i];
            for k in 0..j {
                t -= u[k * m + j] * u[k * m + i];
            }
            u[j * m + i] = t / ujj;
        }
    }
    (u, ntiny)
}

/// Solves `U'U x = c` with the factor from `cholesky`.
fn solve(u: &[f64], m: usize, c: &[f64]) -> Vec<f64> {
    let mut z = vec![0.0; m];
    for j in 0..m {
        let mut t = c[j];
        for k in 0..j {
            t -= u[k * m + j] * z[k];
        }
        z[j] = t / u[j * m + j];
    }
    let mut x = vec![0.0; m];
    for j in (0..m).rev() {
        let mut t = z[j];
        for k in j + 1..m {
            t -= u[j * m + k] * x[k];
        }
        x[j] = t / u[j * m + j];
    }
    x
}

/// `boundc`: the largest step lengths (primal, dual) that keep x1, x2, s, z1,
/// z2 and w positive, scaled by `beta` and capped at one.
fn bound(p: &[&[f64]], d: &[&[f64]], zdual: &[&[f64]], ddual: &[&[f64]]) -> (f64, f64) {
    // p = [x1, s, x2], d = [dx1, ds, dx2]; zdual = [z1, w, z2], ddual = [dz1, dw, dz2].
    let mut deltap = BIG;
    let mut deltad = BIG;
    for k in 0..p.len() {
        for i in 0..p[k].len() {
            if d[k][i] < 0.0 {
                deltap = deltap.min(-p[k][i] / d[k][i]);
            }
        }
    }
    for k in 0..zdual.len() {
        for i in 0..zdual[k].len() {
            if ddual[k][i] < 0.0 {
                deltad = deltad.min(-zdual[k][i] / ddual[k][i]);
            }
        }
    }
    ((BETA * deltap).min(1.0), (BETA * deltad).min(1.0))
}

/// `srqfnc`: the constrained sparse Frisch-Newton iteration. Returns the dual
/// `y`, the iteration count, and `ierr` (0 when the gap falls below `small`).
pub fn srqfnc(a1: &Csr, a2: &Csr, st: &SfncStart) -> SfncOut {
    let (n1, n2, m) = (a1.n, a2.n, a1.m);
    let mut x1 = st.x1.to_vec();
    let mut x2 = st.x2.to_vec();
    let mut s = st.s.to_vec();
    let mut z1 = st.z1.to_vec();
    let mut z2 = st.z2.to_vec();
    let mut w = st.w.to_vec();
    let mut y = st.y0.to_vec();
    let mut gap = dot(&z1, &x1) + dot(&z2, &x2) + dot(&w, &s);
    let mut it = 0usize;
    let mut ierr = 0;
    while !(gap < st.small || it > st.maxit) {
        it += 1;
        // Q1^(-1), Q2^(-1), the slack ds = z1 - w, and the constraint residual r2 = c2 - A2 y.
        let q1: Vec<f64> = (0..n1).map(|i| 1.0 / (z1[i] / x1[i] + w[i] / s[i])).collect();
        let q2: Vec<f64> = (0..n2).map(|i| x2[i] / z2[i]).collect();
        let ds: Vec<f64> = (0..n1).map(|i| z1[i] - w[i]).collect();
        let ay = a_times(a2, &y);
        let r2: Vec<f64> = (0..n2).map(|i| st.c2[i] - ay[i]).collect();
        // dy = b - A1'x1 - A2'x2, then rhs = dy + A1'Q1^(-1) ds + A2'Q2^(-1) r2.
        let ax1 = at_times(a1, &x1);
        let ax2 = at_times(a2, &x2);
        let q1ds: Vec<f64> = (0..n1).map(|i| q1[i] * ds[i]).collect();
        let q2r2: Vec<f64> = (0..n2).map(|i| q2[i] * r2[i]).collect();
        let w2 = at_times(a1, &q1ds);
        let w3 = at_times(a2, &q2r2);
        let mut rhs: Vec<f64> = (0..m).map(|j| (st.b[j] - ax1[j] - ax2[j]) + w2[j] + w3[j]).collect();
        let (e, mxdiag) = normal_matrix(a1, &q1, a2, &q2);
        let (u, ntiny) = cholesky(&e, m, mxdiag, st.tiny, st.large);
        if ntiny > 0 {
            ierr = 16 + ntiny as i32;
            break;
        }
        let mut dy = solve(&u, m, &rhs);
        let adx1 = a_times(a1, &dy);
        let adx2 = a_times(a2, &dy);
        let mut dx1: Vec<f64> = (0..n1).map(|i| q1[i] * (adx1[i] - ds[i])).collect();
        let mut dsv: Vec<f64> = dx1.iter().map(|v| -v).collect();
        let mut dz1: Vec<f64> = (0..n1).map(|i| -z1[i] * (1.0 + dx1[i] / x1[i])).collect();
        let mut dw: Vec<f64> = (0..n1).map(|i| -w[i] * (1.0 + dsv[i] / s[i])).collect();
        let mut dx2: Vec<f64> = (0..n2).map(|i| q2[i] * (adx2[i] - r2[i])).collect();
        let mut dz2: Vec<f64> = (0..n2).map(|i| -z2[i] * (1.0 + dx2[i] / x2[i])).collect();
        let (mut deltap, mut deltad) = bound(
            &[&x1, &s, &x2],
            &[&dx1, &dsv, &dx2],
            &[&z1, &w, &z2],
            &[&dz1, &dw, &dz2],
        );
        if deltap * deltad < 1.0 {
            // Mehrotra centring parameter mu, from the predictor steps.
            let mut mu = dot(&z1, &x1) + dot(&z2, &x2) + dot(&w, &s);
            let g1 = mu
                + deltap * dot(&z1, &dx1)
                + deltad * dot(&dz1, &x1)
                + deltad * deltap * dot(&dz1, &dx1)
                + deltap * dot(&z2, &dx2)
                + deltad * dot(&dz2, &x2)
                + deltad * deltap * dot(&dz2, &dx2)
                + deltap * dot(&w, &dsv)
                + deltad * dot(&dw, &s)
                + deltad * deltap * dot(&dw, &dsv);
            let ratio = g1 / mu;
            mu = mu * (ratio * ratio * ratio) / (2.0 * n1 as f64 + n2 as f64);
            let mut dxdz1 = vec![0.0; n1];
            let mut dsdw = vec![0.0; n1];
            let mut xi1 = vec![0.0; n1];
            let mut ww1 = vec![0.0; n1];
            for i in 0..n1 {
                dxdz1[i] = dx1[i] * dz1[i];
                dsdw[i] = dsv[i] * dw[i];
                xi1[i] = dxdz1[i] / x1[i] - dsdw[i] / s[i] - mu * (1.0 / x1[i] - 1.0 / s[i]);
                ww1[i] = q1[i] * xi1[i];
            }
            let mut xi2 = vec![0.0; n2];
            let mut dxdz2 = vec![0.0; n2];
            let mut ww1b = vec![0.0; n2];
            for i in 0..n2 {
                dxdz2[i] = dx2[i] * dz2[i];
                xi2[i] = (dxdz2[i] - mu) / x2[i];
                ww1b[i] = q2[i] * xi2[i];
            }
            let c2w = at_times(a1, &ww1);
            let c3w = at_times(a2, &ww1b);
            for j in 0..m {
                rhs[j] += c2w[j] + c3w[j];
            }
            dy = solve(&u, m, &rhs);
            let adx1 = a_times(a1, &dy);
            let adx2 = a_times(a2, &dy);
            for i in 0..n1 {
                dx1[i] = q1[i] * (adx1[i] - xi1[i] - z1[i] + w[i]);
                dsv[i] = -dx1[i];
                dz1[i] = -z1[i] + (mu - z1[i] * dx1[i] - dxdz1[i]) / x1[i];
                dw[i] = -w[i] + (mu - w[i] * dsv[i] - dsdw[i]) / s[i];
            }
            for i in 0..n2 {
                dx2[i] = q2[i] * (adx2[i] - xi2[i] - r2[i]);
                dz2[i] = -z2[i] + (mu - z2[i] * dx2[i] - dxdz2[i]) / x2[i];
            }
            let step = bound(
                &[&x1, &s, &x2],
                &[&dx1, &dsv, &dx2],
                &[&z1, &w, &z2],
                &[&dz1, &dw, &dz2],
            );
            deltap = step.0;
            deltad = step.1;
        }
        for i in 0..n1 {
            x1[i] += deltap * dx1[i];
            s[i] += deltap * dsv[i];
            w[i] += deltad * dw[i];
            z1[i] += deltad * dz1[i];
        }
        for i in 0..n2 {
            x2[i] += deltap * dx2[i];
            z2[i] += deltad * dz2[i];
        }
        for j in 0..m {
            y[j] += deltad * dy[j];
        }
        gap = dot(&z1, &x1) + dot(&z2, &x2) + dot(&w, &s);
    }
    SfncOut { y, it, ierr }
}
