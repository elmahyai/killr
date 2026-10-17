//! `srqfn` and `slpfn` from quantreg 6.1 `src/srqfn.f`: the sparse
//! Frisch-Newton interior point behind `rq.fit.sfn`, `rqss.fit` and `rqss`.
//!
//! The Fortran forms E = A' Q A from the sparse design A, factors it with the
//! Ng-Peyton supernodal Cholesky (`chlfct`), and solves for the step. Here E is
//! formed from the CSR rows of A and factored by a dense Cholesky that keeps
//! the `blkfct` tiny-pivot rule: a pivot at or below `tiny * max(diag E)` is
//! replaced by `Large`, and the iteration stops with `ierr = 16 + count`, as
//! `chlfct` does. The iteration, the step bound `beta`, the Mehrotra corrector
//! and the stopping rule follow `slpfn` line for line. The sparse ordering and
//! the supernode storage are not ported; the results agree to roundoff.
//!
//! The Fortran 1-based indices are 0-based here. `x`, `s`, `z`, `w` are the
//! primal and dual slacks, `y` the dual (the coefficient is `-y`), and `rhs`
//! the right-hand side `b` of the equality constraint.

/// `beta` in `slpfn`: the fraction of the distance to the boundary taken per step.
pub const BETA: f64 = 0.9995;
/// `big` in `bound`: the starting value of the step lengths.
const BIG: f64 = 1.0e20;

/// The n x m design A in compressed sparse row form. Row `i` holds the entries
/// `indices[indptr[i]..indptr[i + 1]]` with values `data[...]`, and each row
/// has no repeated column.
pub struct Csr<'a> {
    pub n: usize,
    pub m: usize,
    pub indptr: &'a [usize],
    pub indices: &'a [usize],
    pub data: &'a [f64],
}

/// The result of `srqfn`: the dual `y` (length m), the iteration count `it`
/// (the Fortran `maxit` on return), and the error code `ierr` (0 when converged).
pub struct SfnOut {
    pub y: Vec<f64>,
    pub it: usize,
    pub ierr: i32,
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

/// `E = A' diag(q) A` as a dense m x m row-major matrix, and the largest diagonal
/// entry, which the Fortran `chlfct` calls `mxdiag`.
fn normal_matrix(a: &Csr, q: &[f64]) -> (Vec<f64>, f64) {
    let m = a.m;
    let mut e = vec![0.0; m * m];
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

/// `bound`: the largest step lengths (primal, dual) that keep x, s, z and w
/// positive, scaled by `beta` and capped at one.
fn bound(
    x: &[f64],
    dx: &[f64],
    s: &[f64],
    ds: &[f64],
    z: &[f64],
    dz: &[f64],
    w: &[f64],
    dw: &[f64],
) -> (f64, f64) {
    let mut deltap = BIG;
    let mut deltad = BIG;
    for i in 0..x.len() {
        if dx[i] < 0.0 {
            deltap = deltap.min(-x[i] / dx[i]);
        }
        if ds[i] < 0.0 {
            deltap = deltap.min(-s[i] / ds[i]);
        }
        if dz[i] < 0.0 {
            deltad = deltad.min(-z[i] / dz[i]);
        }
        if dw[i] < 0.0 {
            deltad = deltad.min(-w[i] / dw[i]);
        }
    }
    ((BETA * deltap).min(1.0), (BETA * deltad).min(1.0))
}

/// `srqfn`: the sparse Frisch-Newton iteration. `x`, `s`, `y`, `z` and `w` are
/// the starting values (`y` is the starting dual, `z` and `w` the starting dual
/// slacks). `small` is the gap tolerance, `tiny` and `large` the pivot rule, and
/// `maxit` the iteration limit.
pub fn srqfn(
    a: &Csr,
    rhs: &[f64],
    x0: &[f64],
    s0: &[f64],
    y0: &[f64],
    z0: &[f64],
    w0: &[f64],
    small: f64,
    tiny: f64,
    large: f64,
    maxit: usize,
) -> SfnOut {
    let (n, m) = (a.n, a.m);
    let mut x = x0.to_vec();
    let mut s = s0.to_vec();
    let mut y = y0.to_vec();
    let mut z = z0.to_vec();
    let mut w = w0.to_vec();
    let mut gap = dot(&z, &x) + dot(&w, &s);
    let mut it = 0usize;
    let mut ierr = 0;
    while !(gap < small || it > maxit) {
        it += 1;
        let q: Vec<f64> = (0..n).map(|i| 1.0 / (z[i] / x[i] + w[i] / s[i])).collect();
        let r: Vec<f64> = (0..n).map(|i| z[i] - w[i]).collect();
        let (e, mxdiag) = normal_matrix(a, &q);
        let qr: Vec<f64> = (0..n).map(|i| q[i] * r[i]).collect();
        let ax = at_times(a, &x);
        let aqr = at_times(a, &qr);
        // c = b - A'x + A'Q r
        let mut c: Vec<f64> = (0..m).map(|j| rhs[j] - ax[j] + aqr[j]).collect();
        let (u, ntiny) = cholesky(&e, m, mxdiag, tiny, large);
        if ntiny > 0 {
            ierr = 16 + ntiny as i32;
            break;
        }
        let mut dy = solve(&u, m, &c);
        let adx = a_times(a, &dy);
        let mut dx: Vec<f64> = (0..n).map(|i| q[i] * (adx[i] - r[i])).collect();
        let mut ds: Vec<f64> = dx.iter().map(|v| -v).collect();
        let mut dz: Vec<f64> = (0..n).map(|i| -z[i] * (1.0 + dx[i] / x[i])).collect();
        let mut dw: Vec<f64> = (0..n).map(|i| -w[i] * (1.0 + ds[i] / s[i])).collect();
        let (mut deltap, mut deltad) = bound(&x, &dx, &s, &ds, &z, &dz, &w, &dw);
        if deltap * deltad < 1.0 {
            // Mehrotra centring parameter mu
            let mut mu = dot(&z, &x) + dot(&w, &s);
            let g = dot(&z, &x)
                + deltap * dot(&z, &dx)
                + deltad * dot(&dz, &x)
                + deltad * deltap * dot(&dz, &dx)
                + dot(&w, &s)
                + deltap * dot(&w, &ds)
                + deltad * dot(&dw, &s)
                + deltad * deltap * dot(&dw, &ds);
            let ratio = g / mu;
            mu = mu * (ratio * ratio * ratio) / (2.0 * n as f64);
            let mut dxdz = vec![0.0; n];
            let mut dsdw = vec![0.0; n];
            let mut xinv = vec![0.0; n];
            let mut sinv = vec![0.0; n];
            let mut xi = vec![0.0; n];
            let mut ww1 = vec![0.0; n];
            for i in 0..n {
                dxdz[i] = dx[i] * dz[i];
                dsdw[i] = ds[i] * dw[i];
                xinv[i] = 1.0 / x[i];
                sinv[i] = 1.0 / s[i];
                xi[i] = xinv[i] * dxdz[i] - sinv[i] * dsdw[i] - mu * (xinv[i] - sinv[i]);
                ww1[i] = q[i] * xi[i];
            }
            let aw = at_times(a, &ww1);
            for j in 0..m {
                c[j] += aw[j];
            }
            dy = solve(&u, m, &c);
            let adx = a_times(a, &dy);
            for i in 0..n {
                dx[i] = q[i] * (adx[i] - xi[i] - r[i]);
                ds[i] = -dx[i];
                dz[i] = -z[i] + xinv[i] * (mu - z[i] * dx[i] - dxdz[i]);
                dw[i] = -w[i] + sinv[i] * (mu - w[i] * ds[i] - dsdw[i]);
            }
            let step = bound(&x, &dx, &s, &ds, &z, &dz, &w, &dw);
            deltap = step.0;
            deltad = step.1;
        }
        for i in 0..n {
            x[i] += deltap * dx[i];
            s[i] += deltap * ds[i];
            w[i] += deltad * dw[i];
            z[i] += deltad * dz[i];
        }
        for j in 0..m {
            y[j] += deltad * dy[j];
        }
        gap = dot(&z, &x) + dot(&w, &s);
    }
    SfnOut { y, it, ierr }
}
