//! Kernels of the R package quantreg 6.1, ported from its Fortran and C:
//! `src/rqfnb.f` (`rqfnb`, `lpfnb`, `stepy`), `src/pfnb.f` (`pfnb`),
//! `src/pwxy.f` (`pwxy`), `src/grexp.f` with `frand.c` (exponential draws),
//! and `src/mcmb.c` (`bootnp`, `func`, `sort2`).
//!
//! The Frisch-Newton interior point is shared by `rq.fit.fnb`, `rq.fit.pfnb`
//! and `boot.rq.pwxy`. `pfnb` is the preprocessed Frisch-Newton fit, `pwxy`
//! the preprocessed pairs bootstrap, and `bootnp` the Markov chain marginal
//! bootstrap behind `boot.rq.mcmb`.
//!
//! Layouts follow the Fortran. `a(p, n)` keeps the p entries of each
//! observation together, so `a[i * p + k]` is `a(k + 1, i + 1)`, which is the
//! row-major layout of an n x p design. Every 1-based Fortran index is 0-based
//! here, and each loop keeps the Fortran's order of operations where the
//! result depends on it. R's `.C` and `.Fortran` calls are replaced by plain
//! function calls. The random draws come from R's Mersenne-Twister, and the
//! state is passed in and returned, so the caller keeps R's `.Random.seed`
//! stream.

#![allow(clippy::too_many_arguments, clippy::needless_range_loop)]

pub mod sfn;

#[cfg(feature = "python")]
mod python;

/// `beta` and `eps` as the Fortran drivers pass them to `rqfnb`.
pub const BETA: f64 = 0.99995;
pub const EPS: f64 = 1.0e-6;
/// The artificial bounds `big` in `pfnb` and `pwxy`.
const BIG: f64 = 1.0e10;
/// The Frisch-Newton iteration cap `maxit` in `lpfnb`.
const MAXIT: i32 = 500;

const MT_N: usize = 624;
const MT_M: usize = 397;
const MATRIX_A: u32 = 0x9908_b0df;
const UPPER_MASK: u32 = 0x8000_0000;
const LOWER_MASK: u32 = 0x7fff_ffff;
const I2_32: f64 = 2.328_306_436_538_696_3e-10;
const I2_32M1: f64 = 2.328_306_437_080_797e-10;

/// `q[k-1] = sum(log(2)^k / k!)` from R's `exp_rand`.
const EXP_Q: [f64; 16] = [
    0.6931471805599453,
    0.9333736875190459,
    0.9888777961838675,
    0.9984959252914960040,
    0.9998292811061389,
    0.9999833164100727,
    0.9999985508193208,
    0.9999998906925558,
    0.9999999924734159,
    0.9999999995283275,
    0.9999999999728814,
    0.9999999999985598,
    0.9999999999999289,
    0.9999999999999968,
    0.9999999999999999,
    1.0000000000000000,
];

/// R's default generator (Mersenne-Twister with the R seeding), as in `.Random.seed`.
#[derive(Clone, Debug)]
pub struct Rng {
    mt: Vec<u32>,
    mti: usize,
}

impl Rng {
    /// Builds the generator from the 624 state words and the position `mti`.
    pub fn from_state(mt: &[u32], mti: usize) -> Result<Self, String> {
        if mt.len() != MT_N {
            return Err(format!("the Mersenne-Twister state needs {MT_N} words, got {}", mt.len()));
        }
        Ok(Self { mt: mt.to_vec(), mti })
    }

    /// The state words and the position, for the caller to store.
    pub fn state(&self) -> (Vec<u32>, usize) {
        (self.mt.clone(), self.mti)
    }

    /// R's `unif_rand()` for the Mersenne-Twister, in (0, 1).
    pub fn unif_rand(&mut self) -> f64 {
        let mt = &mut self.mt;
        if self.mti >= MT_N {
            let mag01 = [0u32, MATRIX_A];
            for kk in 0..MT_N - MT_M {
                let y = (mt[kk] & UPPER_MASK) | (mt[kk + 1] & LOWER_MASK);
                mt[kk] = mt[kk + MT_M] ^ (y >> 1) ^ mag01[(y & 1) as usize];
            }
            for kk in MT_N - MT_M..MT_N - 1 {
                let y = (mt[kk] & UPPER_MASK) | (mt[kk + 1] & LOWER_MASK);
                mt[kk] = mt[kk + MT_M - MT_N] ^ (y >> 1) ^ mag01[(y & 1) as usize];
            }
            let y = (mt[MT_N - 1] & UPPER_MASK) | (mt[0] & LOWER_MASK);
            mt[MT_N - 1] = mt[MT_M - 1] ^ (y >> 1) ^ mag01[(y & 1) as usize];
            self.mti = 0;
        }
        let mut y = mt[self.mti];
        self.mti += 1;
        y ^= y >> 11;
        y ^= (y << 7) & 0x9d2c_5680;
        y ^= (y << 15) & 0xefc6_0000;
        y ^= y >> 18;
        let x = y as f64 * I2_32;
        if x <= 0.0 {
            0.5 * I2_32M1
        } else if 1.0 - x <= 0.0 {
            1.0 - 0.5 * I2_32M1
        } else {
            x
        }
    }

    /// R's `exp_rand()`, the standard exponential deviate that `rexp(1)` returns.
    pub fn exp_rand(&mut self) -> f64 {
        let mut a = 0.0;
        let mut u = self.unif_rand();
        while u <= 0.0 || u >= 1.0 {
            u = self.unif_rand();
        }
        loop {
            u += u;
            if u > 1.0 {
                break;
            }
            a += EXP_Q[0];
        }
        u -= 1.0;
        if u <= EXP_Q[0] {
            return a + u;
        }
        let mut i = 0usize;
        let mut ustar = self.unif_rand();
        let mut umin = ustar;
        loop {
            ustar = self.unif_rand();
            if umin > ustar {
                umin = ustar;
            }
            i += 1;
            if !(u > EXP_Q[i]) {
                break;
            }
        }
        a + umin * EXP_Q[0]
    }
}

/// `stepy`: `ada = A diag(d) A'` (upper triangle, p x p column-major), then
/// the Cholesky solve of `ada y = b` in place. Returns the LAPACK `info`.
fn stepy(n: usize, p: usize, a: &[f64], d: &[f64], b: &mut [f64], ada: &mut [f64]) -> i32 {
    ada.iter_mut().for_each(|v| *v = 0.0);
    for i in 0..n {
        let ai = &a[i * p..(i + 1) * p];
        for j in 0..p {
            let temp = d[i] * ai[j];
            for k in 0..=j {
                ada[k + j * p] += ai[k] * temp;
            }
        }
    }
    dposv_upper(p, ada, b)
}

/// LAPACK `dpotrf2('U')` on the block at rows `r0..`, columns `c0..` of the
/// column-major matrix with leading dimension `lda`. This is the recursive
/// factorisation that `dpotrf` runs for n below its block size, with the
/// operation order of the reference BLAS (`dtrsm`, `dsyrk`). Returns `info`.
fn potrf2(a: &mut [f64], lda: usize, r0: usize, c0: usize, n: usize) -> i32 {
    if n == 1 {
        let v = a[r0 + c0 * lda];
        if v <= 0.0 || v.is_nan() {
            return 1;
        }
        a[r0 + c0 * lda] = v.sqrt();
        return 0;
    }
    let n1 = n / 2;
    let n2 = n - n1;
    let info = potrf2(a, lda, r0, c0, n1);
    if info != 0 {
        return info;
    }
    // dtrsm('L', 'U', 'T', 'N'): A12 := inv(U11') A12
    for j in 0..n2 {
        for i in 0..n1 {
            let mut temp = a[(r0 + i) + (c0 + n1 + j) * lda];
            for k in 0..i {
                temp -= a[(r0 + k) + (c0 + i) * lda] * a[(r0 + k) + (c0 + n1 + j) * lda];
            }
            temp /= a[(r0 + i) + (c0 + i) * lda];
            a[(r0 + i) + (c0 + n1 + j) * lda] = temp;
        }
    }
    // dsyrk('U', 'T', n2, n1, -1, A12, 1, A22)
    for j in 0..n2 {
        for i in 0..=j {
            let mut temp = 0.0;
            for l in 0..n1 {
                temp += a[(r0 + l) + (c0 + n1 + i) * lda] * a[(r0 + l) + (c0 + n1 + j) * lda];
            }
            let cij = (r0 + n1 + i) + (c0 + n1 + j) * lda;
            a[cij] = -temp + a[cij];
        }
    }
    let info = potrf2(a, lda, r0 + n1, c0 + n1, n2);
    if info != 0 {
        return info + n1 as i32;
    }
    0
}

/// LAPACK `dpotrf('U')` for a p x p column-major matrix. Returns `info`.
fn chol_upper(p: usize, a: &mut [f64]) -> i32 {
    potrf2(a, p, 0, 0, p)
}

/// LAPACK `dpotrs('U')` with the factor from `chol_upper`: the transposed
/// forward solve (`dtrsm('L','U','T','N')`), then the backward solve in the
/// column order of `dtrsm('L','U','N','N')`.
fn chol_solve(p: usize, a: &[f64], b: &mut [f64]) {
    for i in 0..p {
        let mut t = b[i];
        for k in 0..i {
            t -= a[k + i * p] * b[k];
        }
        b[i] = t / a[i + i * p];
    }
    for k in (0..p).rev() {
        if b[k] != 0.0 {
            b[k] /= a[k + k * p];
            let bk = b[k];
            for i in 0..k {
                b[i] -= bk * a[i + k * p];
            }
        }
    }
}

/// LAPACK `dposv('U')`: factor and solve. Returns `info`; `b` is left alone on failure.
fn dposv_upper(p: usize, a: &mut [f64], b: &mut [f64]) -> i32 {
    let info = chol_upper(p, a);
    if info == 0 {
        chol_solve(p, a, b);
    }
    info
}

/// `y = A c` for the p x n design `a`, where `c` has n entries.
fn a_times(n: usize, p: usize, a: &[f64], c: &[f64]) -> Vec<f64> {
    let mut y = vec![0.0; p];
    for i in 0..n {
        let t = c[i];
        for k in 0..p {
            y[k] += t * a[i * p + k];
        }
    }
    y
}

/// `out_i = sum_k a(k, i) * v_k`, the transposed product `A' v`.
fn at_times(n: usize, p: usize, a: &[f64], v: &[f64]) -> Vec<f64> {
    (0..n)
        .map(|i| {
            let mut temp = 0.0;
            for k in 0..p {
                temp += a[i * p + k] * v[k];
            }
            temp
        })
        .collect()
}

fn dot(x: &[f64], y: &[f64]) -> f64 {
    let mut s = 0.0;
    for i in 0..x.len() {
        s += x[i] * y[i];
    }
    s
}

/// Output of `rqfnb`: the dual `y` (the coefficient is its negative), the
/// three counters `nit`, and the LAPACK `info`.
#[derive(Clone, Debug)]
pub struct Fnb {
    pub y: Vec<f64>,
    pub nit: [i32; 3],
    pub info: i32,
}

/// `lpfnb`: the Frisch-Newton interior point for the dual problem.
///
/// `a` is p x n, `c` the response, `b` the right-hand side, `u` the upper
/// bounds, and `x0` the starting primal (`1 - tau` in rq.fit.fnb).
fn lpfnb(n: usize, p: usize, a: &[f64], c: &[f64], b: &[f64], u_in: &[f64], beta: f64, eps: f64, x0: &[f64]) -> Fnb {
    let mut nit = [0i32, 0, n as i32];
    let mut d = vec![1.0; n];
    let mut u = u_in.to_vec();
    let mut x = x0.to_vec();
    let mut s = vec![0.0; n];
    let mut z = vec![0.0; n];
    let mut w = vec![0.0; n];
    let mut dx = vec![0.0; n];
    let mut ds = vec![0.0; n];
    let mut dz = vec![0.0; n];
    let mut dw = vec![0.0; n];
    let mut dr = vec![0.0; n];
    let mut ada = vec![0.0; p * p];
    let mut dy = vec![0.0; p];
    let mut rhs = vec![0.0; p];

    let mut y = a_times(n, p, a, c);
    let info = stepy(n, p, a, &d, &mut y, &mut ada);
    if info != 0 {
        return Fnb { y, nit, info };
    }
    let aty = at_times(n, p, a, &y);
    for i in 0..n {
        s[i] = c[i] - aty[i];
    }
    for i in 0..n {
        if s[i].abs() < eps {
            z[i] = s[i].max(0.0) + eps;
            w[i] = (-s[i]).max(0.0) + eps;
        } else {
            z[i] = s[i].max(0.0);
            w[i] = (-s[i]).max(0.0);
        }
        s[i] = u[i] - x[i];
    }
    let mut gap = dot(&z, &x) + dot(&w, &s);

    while gap > eps && nit[0] < MAXIT {
        nit[0] += 1;
        for i in 0..n {
            d[i] = 1.0 / (z[i] / x[i] + w[i] / s[i]);
            ds[i] = z[i] - w[i];
            dz[i] = d[i] * ds[i];
        }
        // dy = b - A x + A dz
        dy.copy_from_slice(b);
        for i in 0..n {
            let t = -x[i];
            for k in 0..p {
                dy[k] += t * a[i * p + k];
            }
        }
        for i in 0..n {
            let t = dz[i];
            for k in 0..p {
                dy[k] += t * a[i * p + k];
            }
        }
        rhs.copy_from_slice(&dy);
        let info = stepy(n, p, a, &d, &mut dy, &mut ada);
        if info != 0 {
            return Fnb { y, nit, info };
        }
        let atdy = at_times(n, p, a, &dy);
        for i in 0..n {
            ds[i] = atdy[i] - ds[i];
        }

        let mut deltap = BIG;
        let mut deltad = BIG;
        for i in 0..n {
            dx[i] = d[i] * ds[i];
            ds[i] = -dx[i];
            dz[i] = -z[i] * (dx[i] / x[i] + 1.0);
            dw[i] = -w[i] * (ds[i] / s[i] + 1.0);
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
        deltap = (beta * deltap).min(1.0);
        deltad = (beta * deltad).min(1.0);

        if deltap.min(deltad) < 1.0 {
            nit[1] += 1;
            let mut mu = dot(&x, &z) + dot(&s, &w);
            let g = mu
                + deltap * dot(&dx, &z)
                + deltad * dot(&dz, &x)
                + deltap * deltad * dot(&dz, &dx)
                + deltap * dot(&ds, &w)
                + deltad * dot(&dw, &s)
                + deltap * deltad * dot(&ds, &dw);
            mu = mu * (g / mu).powi(3) / ((2 * n) as f64);
            for i in 0..n {
                dr[i] = d[i] * (mu * (1.0 / s[i] - 1.0 / x[i]) + dx[i] * dz[i] / x[i] - ds[i] * dw[i] / s[i]);
            }
            // corrector: dy = (b - A x + A dz) + A dr, solved with the predictor's factor
            dy.copy_from_slice(&rhs);
            for i in 0..n {
                let t = dr[i];
                for k in 0..p {
                    dy[k] += t * a[i * p + k];
                }
            }
            chol_solve(p, &ada, &mut dy);
            let u_new = at_times(n, p, a, &dy);
            u.copy_from_slice(&u_new);

            deltap = BIG;
            deltad = BIG;
            for i in 0..n {
                let dxdz = dx[i] * dz[i];
                let dsdw = ds[i] * dw[i];
                dx[i] = d[i] * (u[i] - z[i] + w[i]) - dr[i];
                ds[i] = -dx[i];
                dz[i] = -z[i] + (mu - z[i] * dx[i] - dxdz) / x[i];
                dw[i] = -w[i] + (mu - w[i] * ds[i] - dsdw) / s[i];
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
            deltap = (beta * deltap).min(1.0);
            deltad = (beta * deltad).min(1.0);
        }

        for i in 0..n {
            x[i] += deltap * dx[i];
            s[i] += deltap * ds[i];
        }
        for k in 0..p {
            y[k] += deltad * dy[k];
        }
        for i in 0..n {
            z[i] += deltad * dz[i];
            w[i] += deltad * dw[i];
        }
        gap = dot(&z, &x) + dot(&w, &s);
    }
    Fnb { y, nit, info: 0 }
}

/// `rqfnb`: the Frisch-Newton dual solve on the n x p design `a` (row-major,
/// one row per observation). Returns the dual `y`, `nit`, and `info`.
pub fn rqfnb(n: usize, p: usize, a: &[f64], c: &[f64], rhs: &[f64], u: &[f64], x0: &[f64], beta: f64, eps: f64) -> Fnb {
    lpfnb(n, p, a, c, rhs, u, beta, eps, x0)
}

/// Output of `pfnb`. `b` is p x m column-major (`b[iq * p + k]`), `nit` is
/// 5 x m column-major (`nit[iq * 5 + r]`), and `info` is the last LAPACK
/// status, which the Fortran writes into the first element of its `info` array.
#[derive(Clone, Debug)]
pub struct Pfnb {
    pub b: Vec<f64>,
    pub nit: Vec<i32>,
    pub info: i32,
}

fn order_statistic(values: &[f64], k: usize) -> f64 {
    let mut sorted = values.to_vec();
    sorted.sort_by(|a, b| a.total_cmp(b));
    sorted[k.clamp(1, sorted.len()) - 1]
}

/// `pfnb`: the preprocessed Frisch-Newton fit for m taus.
///
/// `a` is the n x p design, `y` the response, `q` the taus, `r` the residuals
/// of the subsample fit, `band` the scale of each row, and `m0` the subsample
/// size. The residuals carry over between taus, as they do in the Fortran.
pub fn pfnb(n: usize, p: usize, a: &[f64], y: &[f64], q: &[f64], r_in: &[f64], band: &[f64], m0: usize) -> Pfnb {
    let m = q.len();
    let mut r = r_in.to_vec();
    let mut b = vec![0.0; p * m];
    let mut nit = vec![0i32; 5 * m];
    let mut info = 0i32;
    let fnn = n as f64;
    for iq in 0..m {
        let tau = q[iq];
        let mut notopt = true;
        let mut mm = m0;
        let mut ifix = 0i32;
        let mut ibad = 0i32;
        while notopt {
            ibad += 1;
            let fm = mm as f64;
            let kk1 = ((fnn * (1.0 / fnn).max(tau - fm / (2.0 * fnn))) as usize) + 1;
            let kk2 = (fnn * (tau + fm / (2.0 * fnn)).min((fnn - 1.0) / fnn)) as usize;
            let u: Vec<f64> = (0..n).map(|i| r[i] / band[i]).collect();
            let qk1 = order_statistic(&u, kk1);
            let qk2 = order_statistic(&u, kk2);
            let mut slo = vec![0i32; n];
            let mut shi = vec![0i32; n];
            for i in 0..n {
                if r[i] < band[i] * qk1 {
                    slo[i] = 1;
                } else if r[i] > band[i] * qk2 {
                    shi[i] = 1;
                }
            }
            loop {
                ifix += 1;
                let mut glob = vec![0.0; p];
                let mut ghib = vec![0.0; p];
                let mut aa = vec![0.0; p * (n + 2)];
                let mut yy = vec![0.0; n + 2];
                let mut k = 0usize;
                for i in 0..n {
                    if slo[i] == 0 && shi[i] == 0 {
                        aa[k * p..(k + 1) * p].copy_from_slice(&a[i * p..(i + 1) * p]);
                        yy[k] = -y[i];
                        k += 1;
                    } else if slo[i] == 1 {
                        for j in 0..p {
                            glob[j] += a[i * p + j];
                        }
                    } else if shi[i] == 1 {
                        for j in 0..p {
                            ghib[j] += a[i * p + j];
                        }
                    }
                }
                aa[k * p..(k + 1) * p].copy_from_slice(&glob);
                aa[(k + 1) * p..(k + 2) * p].copy_from_slice(&ghib);
                yy[k] = BIG;
                yy[k + 1] = -BIG;
                let nk = k + 2;
                let mut rhs = vec![0.0; p];
                for j in 0..nk {
                    let temp = 1.0 - tau;
                    for i in 0..p {
                        rhs[i] += temp * aa[j * p + i];
                    }
                }
                let x0 = vec![1.0 - tau; nk];
                let ones = vec![1.0; nk];
                let sol = lpfnb(nk, p, &aa[..p * nk], &yy[..nk], &rhs, &ones, BETA, EPS, &x0);
                b[iq * p..(iq + 1) * p].copy_from_slice(&sol.y);
                nit[iq * 5..iq * 5 + 3].copy_from_slice(&sol.nit);
                info = sol.info;
                let atb = at_times(n, p, a, &b[iq * p..(iq + 1) * p]);
                for i in 0..n {
                    r[i] = y[i] + atb[i];
                }
                let mut sumbad = 0usize;
                for i in 0..n {
                    if r[i] > 0.0 && slo[i] == 1 {
                        slo[i] = 0;
                        sumbad += 1;
                    }
                    if r[i] < 0.0 && shi[i] == 1 {
                        shi[i] = 0;
                        sumbad += 1;
                    }
                }
                if sumbad == 0 {
                    notopt = false;
                    break;
                }
                if (sumbad as f64) > 0.1 * (mm as f64) {
                    mm = (2 * mm).min(n);
                    break;
                }
            }
            nit[iq * 5 + 3] = ifix;
            nit[iq * 5 + 4] = ibad;
        }
    }
    Pfnb { b, nit, info }
}

/// Output of `pwxy`: `b` is p x m column-major, `nit` is 5 x m column-major,
/// and `info` has one LAPACK status per replicate.
#[derive(Clone, Debug)]
pub struct Pwxy {
    pub b: Vec<f64>,
    pub nit: Vec<i32>,
    pub info: Vec<i32>,
}

/// `pwxy`: the preprocessed pairs bootstrap, with `m` replicates.
///
/// `a` is the n x p design and `y` the response, both already sorted by the
/// scaled residual `r`. Each replicate draws n exponential weights from R's
/// generator, in replicate order, as `grexp` does.
pub fn pwxy(n: usize, p: usize, a: &[f64], y: &[f64], tau: f64, r: &[f64], m: usize, n0: usize, rng: &mut Rng) -> Pwxy {
    let mut b = vec![0.0; p * m];
    let mut nit = vec![0i32; 5 * m];
    let mut info = vec![0i32; m];
    let fnn = n as f64;
    for ir in 0..m {
        let w: Vec<f64> = (0..n).map(|_| rng.exp_rand()).collect();
        let mut notopt = true;
        let mut nn = n0;
        let mut ifix = 0i32;
        let mut ibad = 0i32;
        while notopt {
            ibad += 1;
            let loq = ((fnn * tau - nn as f64 / 2.0) as i64).max(1) as usize;
            let hiq = ((fnn * tau + nn as f64 / 2.0) as i64).min(n as i64).max(1) as usize;
            let qk1 = r[loq - 1];
            let qk2 = r[hiq - 1];
            let mut slo = vec![0i32; n];
            let mut shi = vec![0i32; n];
            for i in 0..n {
                if r[i] < qk1 {
                    slo[i] = 1;
                } else if r[i] > qk2 {
                    shi[i] = 1;
                }
            }
            loop {
                ifix += 1;
                let mut glob = vec![0.0; p];
                let mut ghib = vec![0.0; p];
                let mut aa = vec![0.0; p * (n + 2)];
                let mut yy = vec![0.0; n + 2];
                let mut k = 0usize;
                for i in 0..n {
                    if slo[i] == 0 && shi[i] == 0 {
                        for j in 0..p {
                            aa[k * p + j] = w[i] * a[i * p + j];
                        }
                        yy[k] = -y[i] * w[i];
                        k += 1;
                    } else if slo[i] == 1 {
                        for j in 0..p {
                            glob[j] += a[i * p + j] * w[i];
                        }
                    } else if shi[i] == 1 {
                        for j in 0..p {
                            ghib[j] += a[i * p + j] * w[i];
                        }
                    }
                }
                aa[k * p..(k + 1) * p].copy_from_slice(&glob);
                aa[(k + 1) * p..(k + 2) * p].copy_from_slice(&ghib);
                yy[k] = BIG;
                yy[k + 1] = -BIG;
                let nk = k + 2;
                let mut rhs = vec![0.0; p];
                for j in 0..nk {
                    let temp = 1.0 - tau;
                    for i in 0..p {
                        rhs[i] += temp * aa[j * p + i];
                    }
                }
                let x0 = vec![1.0 - tau; nk];
                let ones = vec![1.0; nk];
                let sol = lpfnb(nk, p, &aa[..p * nk], &yy[..nk], &rhs, &ones, BETA, EPS, &x0);
                b[ir * p..(ir + 1) * p].copy_from_slice(&sol.y);
                nit[ir * 5..ir * 5 + 3].copy_from_slice(&sol.nit);
                info[ir] = sol.info;
                let atb = at_times(n, p, a, &b[ir * p..(ir + 1) * p]);
                let mut u = vec![0.0; n];
                for i in 0..n {
                    u[i] = y[i] + atb[i];
                }
                let mut sumbad = 0usize;
                for i in 0..n {
                    if u[i] > 0.0 && slo[i] == 1 {
                        slo[i] = 0;
                        sumbad += 1;
                    }
                    if u[i] < 0.0 && shi[i] == 1 {
                        shi[i] = 0;
                        sumbad += 1;
                    }
                }
                if sumbad == 0 {
                    notopt = false;
                    break;
                }
                if (sumbad as f64) > 0.1 * (nn as f64) {
                    nn = (2 * nn).min(n);
                    break;
                }
            }
            nit[ir * 5 + 3] = ifix;
            nit[ir * 5 + 4] = ibad;
        }
    }
    Pwxy { b, nit, info }
}

/// `mprodx` in mcmb.c: the dot product of a row of x with the vector.
fn mprodx(x: &[f64], c: &[f64]) -> f64 {
    let mut sum = 0.0;
    for i in 0..c.len() {
        sum += x[i] * c[i];
    }
    sum
}

fn sign(x: f64) -> f64 {
    if x > 0.0 {
        1.0
    } else if x < 0.0 {
        -1.0
    } else {
        0.0
    }
}

/// `func` in mcmb.c: the weighted tau* quantile for coordinate j. Returns the
/// error text where the C calls `error()`, which ends the R call.
fn func(
    x: &[f64],
    y: &[f64],
    tau: f64,
    t_tilde: &[f64],
    sum_right: f64,
    sumxij: f64,
    sumabsxij: f64,
    j: usize,
    p: usize,
    n: usize,
) -> Result<f64, String> {
    let mut xj = vec![0.0; n + 1];
    for i in 0..n {
        xj[i] = x[i * p + j];
    }
    xj[n] = -sum_right / tau;
    let wtsum = sumabsxij + xj[n].abs();

    let mut z: Vec<f64> = Vec::with_capacity(n + 1);
    let mut wt: Vec<f64> = Vec::with_capacity(n + 1);
    for i in 0..n {
        if xj[i].abs() > 10e-16 {
            let row = &x[i * p..(i + 1) * p];
            z.push((y[i] - mprodx(row, t_tilde) + t_tilde[j] * xj[i]) / xj[i]);
            wt.push(xj[i].abs() / wtsum);
        } else {
            return Err("fabs(xj[i])<10e-16".to_string());
        }
    }
    z.push(10e16 * sign(xj[n]));
    wt.push(xj[n].abs() / wtsum);
    if z.is_empty() {
        return Err("Error: one design variable contains all 0s.".to_string());
    }

    let taustar = (tau - 0.5) * (sumxij + xj[n]) / wtsum + 0.5;

    // sort2 orders z with its weights. Equal z values give the same answer, so a stable sort is enough.
    let mut order: Vec<usize> = (0..z.len()).collect();
    order.sort_by(|&a, &b| z[a].total_cmp(&z[b]));
    let zs: Vec<f64> = order.iter().map(|&i| z[i]).collect();
    let ws: Vec<f64> = order.iter().map(|&i| wt[i]).collect();

    let mut pwtsum = 0.0;
    let mut i = 1usize;
    let mut ans = zs[0];
    while pwtsum <= taustar && i < n + 1 {
        pwtsum += ws[i - 1];
        ans = zs[i - 1];
        i += 1;
    }
    if ans.abs() > 10e15 {
        return Err("Picked infinity; need to resample".to_string());
    }
    Ok(ans)
}

/// `bootnp` in mcmb.c: the Markov chain marginal bootstrap for `reps` draws.
///
/// `x` is the n x p design after the `A` transform, row-major. `zstar` is
/// `ZTilda` in column-major order, as R passes it. `theta_tilde` is the
/// starting coefficient. The result is p x (reps + 1) column-major, where the
/// first column is `theta_tilde`.
pub fn bootnp(
    n: usize,
    p: usize,
    x: &[f64],
    y: &[f64],
    tau: f64,
    theta_tilde: &[f64],
    zstar: &[f64],
    sumxij: &[f64],
    sumabsxij: &[f64],
    reps: usize,
    rng: &mut Rng,
) -> Result<Vec<f64>, String> {
    if n <= p {
        return Err("bootnp needs n > p".to_string());
    }
    let mut theta = vec![0.0; p * (reps + 1)];
    theta[..p].copy_from_slice(theta_tilde);
    let mut t_tilde = theta_tilde.to_vec();
    let mut s = vec![0.0; p];
    let nn = n as f64;
    // k is i64 because the C loop steps back with k = k - 1 to redraw a replicate.
    let mut k: i64 = 0;
    while k < reps as i64 {
        let kk = k as usize;
        for j in 0..p {
            let mut sum = 0.0;
            for _ in 0..n {
                let rand_ind = ((n * j) as f64 + nn * rng.unif_rand()) as usize;
                sum += zstar[rand_ind];
            }
            s[j] = nn.sqrt() / ((n - p) as f64).sqrt() * sum;
        }
        let mut restart = false;
        for j in 0..p {
            let value = func(x, y, tau, &t_tilde, s[j], sumxij[j], sumabsxij[j], j, p, n)?;
            theta[(kk + 1) * p + j] = value;
            if value == 1.0 {
                for jj in 0..p {
                    t_tilde[jj] = theta[kk * p + jj];
                }
                restart = true;
                break;
            } else {
                t_tilde[j] = value;
            }
        }
        if restart {
            k -= 1;
        }
        k += 1;
    }
    Ok(theta)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unif_rand_matches_r_seed_one() {
        // set.seed(1) in R 4.5: runif(3) is 0.2655087 0.3721239 0.5728534
        let mut mt = vec![0u32; MT_N];
        let mut seed: u32 = 1;
        for _ in 0..50 {
            seed = seed.wrapping_mul(69069).wrapping_add(1);
        }
        let mut dummy = Vec::with_capacity(MT_N + 1);
        for _ in 0..(1 + MT_N) {
            seed = seed.wrapping_mul(69069).wrapping_add(1);
            dummy.push(seed);
        }
        mt.copy_from_slice(&dummy[1..]);
        // FixupSeeds sets dummy[0] to N, so the first draw regenerates the block.
        let mut rng = Rng::from_state(&mt, MT_N).unwrap();
        let first = rng.unif_rand();
        assert!((first - 0.2655086631).abs() < 1e-9, "{first}");
    }
}
