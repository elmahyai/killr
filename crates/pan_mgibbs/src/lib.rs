//! Sampler kernels of the R package pan 2.0 (`src/pan.f`): `mgibbs` (pan) and
//! `mgibbsbd` (pan.bd), with their support routines and the Fortran
//! single-precision generator (`rangen`, `gauss`, `gamm`, `bfac`).
//!
//! Arrays are column-major and every index is 1-based, as in the Fortran, so
//! each routine reads like its source. The R wrappers (`R/pan.R`) prepare the
//! index arrays; this crate takes them in the Fortran convention:
//!
//! * `subj` labels subjects in contiguous blocks (`istfin`);
//! * `patt` is 0 for a row with no observed value, otherwise 1..=npatt;
//! * `rmat` is npatt x r with 1 for an observed column;
//! * `iposn` is the row order sorted by `patt`;
//! * `pstfin` is npatt x 2, the row ranges of each pattern in `iposn` order;
//! * `xcol` and `zcol` are 1-based columns of `pred`.

#![allow(clippy::too_many_arguments, clippy::needless_range_loop)]

#[cfg(feature = "python")]
mod python;

#[inline(always)]
fn ix2(i: usize, j: usize, ld: usize) -> usize {
    (i - 1) + (j - 1) * ld
}

#[inline(always)]
fn ix3(i: usize, j: usize, k: usize, ld1: usize, ld2: usize) -> usize {
    (i - 1) + (j - 1) * ld1 + (k - 1) * ld1 * ld2
}

#[inline(always)]
fn ix4(i: usize, j: usize, k: usize, l: usize, ld1: usize, ld2: usize, ld3: usize) -> usize {
    (i - 1) + (j - 1) * ld1 + (k - 1) * ld1 * ld2 + (l - 1) * ld1 * ld2 * ld3
}

/// The SAVE state of `rangen` (`ix`) and `gauss` (`alt`, `next`).
#[derive(Debug, Clone)]
pub struct Rng {
    ix: i32,
    alt: i32,
    next: f32,
}

impl Default for Rng {
    fn default() -> Self {
        Self::new()
    }
}

impl Rng {
    pub const fn new() -> Self {
        Rng {
            ix: 0,
            alt: 0,
            next: 0.0,
        }
    }

    /// `rangen(init)`: Park-Miller minimal standard generator (a = 16807,
    /// m = 2^31 - 1) by Schrage's method, returned as REAL*4. A non-zero
    /// `init` resets the state before the step, as `rngs` relies on.
    pub fn rangen(&mut self, init: i32) -> f32 {
        const A: i32 = 16807;
        const B15: i32 = 32768;
        const B16: i32 = 65536;
        const P: i32 = 2147483647;
        if init != 0 {
            self.ix = init;
        }
        let ix0 = self.ix;
        let xhi = ix0 / B16;
        let xalo = (ix0 - xhi * B16).wrapping_mul(A);
        let leftflo = xalo / B16;
        let fhi = xhi.wrapping_mul(A).wrapping_add(leftflo);
        let k = fhi / B15;
        let ix = (xalo - leftflo * B16)
            .wrapping_sub(P)
            .wrapping_add((fhi - k * B15).wrapping_mul(B16))
            .wrapping_add(k);
        let ix = if ix < 0 { ix.wrapping_add(P) } else { ix };
        self.ix = ix;
        (ix as f32) * 4.656612875E-10_f32
    }

    /// `gauss()`: Box-Muller pair, both values kept in REAL*4.
    pub fn gauss(&mut self) -> f32 {
        const PI: f32 = 3.141593;
        if self.alt != 0 && self.alt != 1 {
            self.alt = 0;
        }
        if self.alt == 0 {
            let u1 = self.rangen(0);
            let u2 = self.rangen(0);
            let root = (-2.0_f32 * u1.ln()).sqrt();
            let g = root * (2.0_f32 * PI * u2).cos();
            self.next = root * (2.0_f32 * PI * u2).sin();
            self.alt = 1;
            g
        } else {
            self.alt = 0;
            self.next
        }
    }

    /// `gamm(a)`: gamma deviate, Fishman (1976) for a >= 1 and Ahrens (1974)
    /// for a < 1, in REAL*4.
    pub fn gamm(&mut self, a: f32) -> f32 {
        const E: f32 = 2.718282;
        if a >= 1.0 {
            loop {
                let u = self.rangen(0);
                let y = -(self.rangen(0).ln());
                let lq = (a - 1.0) * (y.ln() - (y - 1.0));
                let q = lq.exp();
                if u <= q {
                    return a * y;
                }
            }
        }
        let b = (E + a) / E;
        loop {
            let u = self.rangen(0);
            let p = b * u;
            if p > 1.0 {
                let x = -((b - p) / a).ln();
                let u1 = self.rangen(0);
                if u1 > x.powf(a - 1.0) {
                    continue;
                }
                return x;
            }
            let x = p.powf(1.0 / a);
            let u1 = self.rangen(0);
            if u1 > E.powf(-x) {
                continue;
            }
            return x;
        }
    }

    /// `bfac(p, m, b)`: upper triangular square root of a Wishart(m, I) by
    /// the Bartlett decomposition. `m` is REAL*4 as in the Fortran.
    pub fn bfac(&mut self, p: usize, m: f32, b: &mut [f64], ld: usize) {
        let _junk = self.gauss();
        for j in 1..=p {
            let g = self.gamm((m - j as f32 + 1.0) / 2.0);
            b[ix2(j, j, ld)] = (2.0_f32 * g).sqrt() as f64;
        }
        for j in 1..p {
            for k in j + 1..=p {
                b[ix2(j, k, ld)] = self.gauss() as f64;
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Dense linear algebra on the upper triangle (chfc, bkslv, mm, and the sweeps)
// ---------------------------------------------------------------------------

/// `chfc(p, pw, s)`: overwrites the upper triangle of the leading pw x pw block
/// with its Cholesky factor.
fn chfc(s: &mut [f64], ld: usize, pw: usize) {
    for i in 1..=pw {
        let mut sum = 0.0;
        for k in 1..i {
            sum += s[ix2(k, i, ld)] * s[ix2(k, i, ld)];
        }
        s[ix2(i, i, ld)] = (s[ix2(i, i, ld)] - sum).sqrt();
        for j in i + 1..=pw {
            let mut sum = 0.0;
            for k in 1..i {
                sum += s[ix2(k, i, ld)] * s[ix2(k, j, ld)];
            }
            s[ix2(i, j, ld)] = (s[ix2(i, j, ld)] - sum) / s[ix2(i, i, ld)];
        }
    }
}

/// `bkslv(p, pw, s)`: inverts an upper triangular pw x pw block in place.
fn bkslv(s: &mut [f64], ld: usize, pw: usize) {
    s[ix2(1, 1, ld)] = 1.0 / s[ix2(1, 1, ld)];
    for k in 2..=pw {
        s[ix2(k, k, ld)] = 1.0 / s[ix2(k, k, ld)];
        for j in 1..k {
            let mut sum = 0.0;
            for i in j..k {
                sum += s[ix2(j, i, ld)] * s[ix2(i, k, ld)];
            }
            s[ix2(j, k, ld)] = -sum * s[ix2(k, k, ld)];
        }
    }
}

/// `mm(p, pw, wm, cm)`: upper triangle of cm = wm %*% t(wm), wm upper triangular.
fn mm(wm: &[f64], cm: &mut [f64], ld: usize, pw: usize) {
    for i in 1..=pw {
        for j in i..=pw {
            let mut sum = 0.0;
            for k in i.max(j)..=pw {
                sum += wm[ix2(i, k, ld)] * wm[ix2(j, k, ld)];
            }
            cm[ix2(i, j, ld)] = sum;
        }
    }
}

/// `swp(n, mat, p)`: sweep of the upper triangle of mat on position p.
fn swp(mat: &mut [f64], n: usize, p: usize) {
    let ld = n;
    mat[ix2(p, p, ld)] = -1.0 / mat[ix2(p, p, ld)];
    for i in 1..p {
        mat[ix2(i, p, ld)] = -mat[ix2(i, p, ld)] * mat[ix2(p, p, ld)];
    }
    for j in p + 1..=n {
        mat[ix2(p, j, ld)] = -mat[ix2(p, j, ld)] * mat[ix2(p, p, ld)];
    }
    for i in 1..p {
        for j in i..p {
            mat[ix2(i, j, ld)] =
                mat[ix2(i, j, ld)] + mat[ix2(i, p, ld)] * mat[ix2(j, p, ld)] / mat[ix2(p, p, ld)];
        }
        for j in p + 1..=n {
            mat[ix2(i, j, ld)] =
                mat[ix2(i, j, ld)] + mat[ix2(i, p, ld)] * mat[ix2(p, j, ld)] / mat[ix2(p, p, ld)];
        }
    }
    for i in p + 1..=n {
        for j in i..=n {
            mat[ix2(i, j, ld)] =
                mat[ix2(i, j, ld)] + mat[ix2(p, i, ld)] * mat[ix2(p, j, ld)] / mat[ix2(p, p, ld)];
        }
    }
}

/// `rsw(n, mat, p)`: reverse sweep of the upper triangle of mat on position p.
fn rsw(mat: &mut [f64], n: usize, p: usize) {
    let ld = n;
    mat[ix2(p, p, ld)] = -1.0 / mat[ix2(p, p, ld)];
    for i in 1..p {
        mat[ix2(i, p, ld)] = mat[ix2(i, p, ld)] * mat[ix2(p, p, ld)];
    }
    for j in p + 1..=n {
        mat[ix2(p, j, ld)] = mat[ix2(p, j, ld)] * mat[ix2(p, p, ld)];
    }
    for i in 1..p {
        for j in i..p {
            mat[ix2(i, j, ld)] =
                mat[ix2(i, j, ld)] + mat[ix2(i, p, ld)] * mat[ix2(j, p, ld)] / mat[ix2(p, p, ld)];
        }
        for j in p + 1..=n {
            mat[ix2(i, j, ld)] =
                mat[ix2(i, j, ld)] + mat[ix2(i, p, ld)] * mat[ix2(p, j, ld)] / mat[ix2(p, p, ld)];
        }
    }
    for i in p + 1..=n {
        for j in i..=n {
            mat[ix2(i, j, ld)] =
                mat[ix2(i, j, ld)] + mat[ix2(p, i, ld)] * mat[ix2(p, j, ld)] / mat[ix2(p, p, ld)];
        }
    }
}

// ---------------------------------------------------------------------------
// Problem data and the preliminary step (istfin, prelimm)
// ---------------------------------------------------------------------------

/// The data a pan run needs, in Fortran conventions, with the preliminary
/// quantities of `prelimm` already computed.
pub struct Problem {
    pub ntot: usize,
    pub m: usize,
    pub r: usize,
    pub q: usize,
    pub p: usize,
    pub pcol: usize,
    pub npatt: usize,
    pub nstar: usize,
    pub pred: Vec<f64>,
    pub xcol: Vec<usize>,
    pub zcol: Vec<usize>,
    pub patt: Vec<usize>,
    pub rmat: Vec<i64>,
    pub iposn: Vec<usize>,
    pub pstfin: Vec<usize>,
    pub hyp: Vec<f64>,
    pub ist: Vec<usize>,
    pub ifin: Vec<usize>,
    pub ztz: Vec<f64>,
    pub xtxinv: Vec<f64>,
}

impl Problem {
    /// Builds the problem from the Fortran-convention arrays. `pred` is
    /// ntot x pcol, `rmat` is npatt x r, `pstfin` is npatt x 2, all column-major.
    pub fn new(
        subj: &[i64],
        pred: Vec<f64>,
        pcol: usize,
        xcol: Vec<usize>,
        zcol: Vec<usize>,
        patt: Vec<usize>,
        rmat: Vec<i64>,
        npatt: usize,
        r: usize,
        iposn: Vec<usize>,
        pstfin: Vec<usize>,
        hyp: Vec<f64>,
    ) -> Result<Problem, String> {
        let ntot = subj.len();
        let p = xcol.len();
        let q = zcol.len();
        if ntot == 0 || r == 0 || p == 0 || q == 0 {
            return Err("subj, y, xcol and zcol must be non-empty".into());
        }
        if pred.len() != ntot * pcol {
            return Err("pred must have one row per subject row".into());
        }
        if patt.len() != ntot || iposn.len() != ntot {
            return Err("patt and iposn must have length ntot".into());
        }
        if rmat.len() != npatt * r || pstfin.len() != 2 * npatt {
            return Err("rmat must be npatt x r and pstfin npatt x 2".into());
        }
        if xcol.iter().chain(zcol.iter()).any(|&c| c < 1 || c > pcol) {
            return Err("xcol and zcol must be 1-based columns of pred".into());
        }
        if patt.iter().any(|&t| t > npatt) {
            return Err("patt must be 0 or a pattern number in 1..=npatt".into());
        }
        let (ist, ifin) = istfin(subj)?;
        let m = ist.len();
        let nstar = patt.iter().filter(|&&t| t != 0).count();

        // prelimm: ztz(q, q, m) and xtxinv = inv(sum_i t(X_i) X_i) on observed rows.
        let mut ztz = vec![0.0; q * q * m];
        for s in 1..=m {
            for i in 1..=q {
                for j in i..=q {
                    let mut sum = 0.0;
                    for k in ist[s - 1]..=ifin[s - 1] {
                        if patt[k - 1] != 0 {
                            sum += pred[ix2(k, zcol[i - 1], ntot)] * pred[ix2(k, zcol[j - 1], ntot)];
                        }
                    }
                    ztz[ix3(i, j, s, q, q)] = sum;
                    if i != j {
                        ztz[ix3(j, i, s, q, q)] = sum;
                    }
                }
            }
        }
        let mut wkpp = vec![0.0; p * p];
        for i in 1..=p {
            for j in i..=p {
                let mut sum = 0.0;
                for k in 1..=ntot {
                    if patt[k - 1] != 0 {
                        sum += pred[ix2(k, xcol[i - 1], ntot)] * pred[ix2(k, xcol[j - 1], ntot)];
                    }
                }
                wkpp[ix2(i, j, p)] = sum;
            }
        }
        chfc(&mut wkpp, p, p);
        bkslv(&mut wkpp, p, p);
        let mut xtxinv = vec![0.0; p * p];
        mm(&wkpp, &mut xtxinv, p, p);
        for i in 1..=p {
            for j in i..=p {
                xtxinv[ix2(j, i, p)] = xtxinv[ix2(i, j, p)];
            }
        }

        Ok(Problem {
            ntot,
            m,
            r,
            q,
            p,
            pcol,
            npatt,
            nstar,
            pred,
            xcol,
            zcol,
            patt,
            rmat,
            iposn,
            pstfin,
            hyp,
            ist,
            ifin,
            ztz,
            xtxinv,
        })
    }

    #[inline(always)]
    fn pred_at(&self, i: usize, col: usize) -> f64 {
        self.pred[ix2(i, col, self.ntot)]
    }

    #[inline(always)]
    fn rmat_at(&self, pt: usize, j: usize) -> i64 {
        self.rmat[ix2(pt, j, self.npatt)]
    }
}

/// `istfin(ntot, subj, m, ist, ifin)`: first and last rows of each subject.
fn istfin(subj: &[i64]) -> Result<(Vec<usize>, Vec<usize>), String> {
    let ntot = subj.len();
    let mut ist = Vec::new();
    let mut scur = -999i64;
    for i in 1..=ntot {
        if subj[i - 1] != scur {
            ist.push(i);
            scur = subj[i - 1];
        }
    }
    let m = ist.len();
    if m == 0 {
        return Err("no subjects".into());
    }
    let mut ifin = vec![0usize; m];
    for i in 0..m - 1 {
        ifin[i] = ist[i + 1] - 1;
    }
    ifin[m - 1] = ntot;
    Ok((ist, ifin))
}

// ---------------------------------------------------------------------------
// Support routines shared by mgibbs and mgibbsbd
// ---------------------------------------------------------------------------

/// `mimpy`: unconditional mean imputation of the missing entries of y.
fn mimpy(pr: &Problem, y: &mut [f64]) {
    let ntot = pr.ntot;
    for j in 1..=pr.r {
        let mut sum = 0.0;
        let mut denom: i64 = 0;
        for i in 1..=ntot {
            if pr.patt[i - 1] != 0 {
                let rij = pr.rmat_at(pr.patt[i - 1], j);
                sum += rij as f64 * y[ix2(i, j, ntot)];
                denom += rij;
            }
        }
        let mean = sum / denom as f64;
        for i in 1..=ntot {
            if pr.patt[i - 1] != 0 && pr.rmat_at(pr.patt[i - 1], j) == 0 {
                y[ix2(i, j, ntot)] = mean;
            }
        }
    }
}

/// `mkxty`: xty = t(X) %*% y over observed rows, p x r.
fn mkxty(pr: &Problem, y: &[f64], xty: &mut [f64]) {
    let (ntot, p, r) = (pr.ntot, pr.p, pr.r);
    for i in 1..=p {
        for j in 1..=r {
            let mut sum = 0.0;
            for k in 1..=ntot {
                if pr.patt[k - 1] != 0 {
                    sum += pr.pred_at(k, pr.xcol[i - 1]) * y[ix2(k, j, ntot)];
                }
            }
            xty[ix2(i, j, p)] = sum;
        }
    }
}

/// `mkbeta`: beta = xtxinv %*% xty.
fn mkbeta(pr: &Problem, xty: &[f64], beta: &mut [f64]) {
    let (p, r) = (pr.p, pr.r);
    for i in 1..=p {
        for j in 1..=r {
            let mut sum = 0.0;
            for k in 1..=p {
                sum += pr.xtxinv[ix2(i, k, p)] * xty[ix2(k, j, p)];
            }
            beta[ix2(i, j, p)] = sum;
        }
    }
}

/// `mkeps1`: eps = y - X %*% beta on observed rows.
fn mkeps1(pr: &Problem, y: &[f64], beta: &[f64], eps: &mut [f64]) {
    let (ntot, p, r) = (pr.ntot, pr.p, pr.r);
    for i in 1..=ntot {
        if pr.patt[i - 1] != 0 {
            for j in 1..=r {
                let mut sum = 0.0;
                for k in 1..=p {
                    sum += pr.pred_at(i, pr.xcol[k - 1]) * beta[ix2(k, j, p)];
                }
                eps[ix2(i, j, ntot)] = y[ix2(i, j, ntot)] - sum;
            }
        }
    }
}

/// `mkeps2`: eps = y - Z %*% b, subject by subject, on observed rows.
fn mkeps2(pr: &Problem, y: &[f64], b: &[f64], eps: &mut [f64]) {
    let (ntot, q, r) = (pr.ntot, pr.q, pr.r);
    for s in 1..=pr.m {
        for i in pr.ist[s - 1]..=pr.ifin[s - 1] {
            if pr.patt[i - 1] != 0 {
                for j in 1..=r {
                    let mut sum = 0.0;
                    for k in 1..=q {
                        sum += pr.pred_at(i, pr.zcol[k - 1]) * b[ix3(k, j, s, q, r)];
                    }
                    eps[ix2(i, j, ntot)] = y[ix2(i, j, ntot)] - sum;
                }
            }
        }
    }
}

/// `mksigma`: sigma = (1/nstar) * sum_i t(eps_i) %*% eps_i over observed rows.
fn mksigma(pr: &Problem, eps: &[f64], sigma: &mut [f64]) {
    let (ntot, r) = (pr.ntot, pr.r);
    for i in 1..=r {
        for j in i..=r {
            sigma[ix2(i, j, r)] = 0.0;
        }
    }
    for i in 1..=ntot {
        if pr.patt[i - 1] != 0 {
            for j in 1..=r {
                for k in j..=r {
                    sigma[ix2(j, k, r)] += eps[ix2(i, j, ntot)] * eps[ix2(i, k, ntot)];
                }
            }
        }
    }
    for i in 1..=r {
        for j in i..=r {
            sigma[ix2(i, j, r)] /= pr.nstar as f64;
            if i != j {
                sigma[ix2(j, i, r)] = sigma[ix2(i, j, r)];
            }
        }
    }
}

/// `mksig`: sig(:,:,s) = chol-factor of inv(inv(psi) + inv(sigma) (x) ztz_s).
/// With `zflag`, psi is first set to its prior guess from hyp. On return
/// `wkrr2` holds inv(sigma).
fn mksig(
    pr: &Problem,
    zflag: bool,
    psi: &mut [f64],
    sigma: &[f64],
    sig: &mut [f64],
    wkrr1: &mut [f64],
    wkrr2: &mut [f64],
    wkrqrq1: &mut [f64],
    wkrqrq2: &mut [f64],
) {
    let (r, q, m) = (pr.r, pr.q, pr.m);
    let rq = r * q;
    if zflag {
        let mut k = r * (r + 1) / 2 + 2;
        let c = pr.hyp[k - 1];
        for i in 1..=rq {
            for j in i..=rq {
                k += 1;
                psi[ix2(i, j, rq)] = pr.hyp[k - 1] / c;
            }
        }
    }
    for i in 1..=rq {
        for j in i..=rq {
            wkrqrq1[ix2(i, j, rq)] = psi[ix2(i, j, rq)];
        }
    }
    chfc(wkrqrq1, rq, rq);
    bkslv(wkrqrq1, rq, rq);
    mm(wkrqrq1, wkrqrq2, rq, rq);
    for i in 1..=r {
        for j in i..=r {
            wkrr1[ix2(i, j, r)] = sigma[ix2(i, j, r)];
        }
    }
    chfc(wkrr1, r, r);
    bkslv(wkrr1, r, r);
    mm(wkrr1, wkrr2, r, r);
    for i in 1..=r {
        for j in i + 1..=r {
            wkrr2[ix2(j, i, r)] = wkrr2[ix2(i, j, r)];
        }
    }
    for s in 1..=m {
        for i in 1..=r {
            for j in i..=r {
                for ii in 1..=q {
                    for jj in 1..=q {
                        let ia = (i - 1) * q + ii;
                        let ja = (j - 1) * q + jj;
                        sig[ix3(ia, ja, s, rq, rq)] =
                            wkrr2[ix2(i, j, r)] * pr.ztz[ix3(ii, jj, s, q, q)];
                    }
                }
            }
        }
        for i in 1..=rq {
            for j in i..=rq {
                sig[ix3(i, j, s, rq, rq)] += wkrqrq2[ix2(i, j, rq)];
            }
        }
        let off = (s - 1) * rq * rq;
        chfc(&mut sig[off..off + rq * rq], rq, rq);
        bkslv(&mut sig[off..off + rq * rq], rq, rq);
    }
}

/// `mksigbd`: block-diagonal version of `mksig`; psi is q x q x r.
fn mksigbd(
    pr: &Problem,
    zflag: bool,
    psi: &mut [f64],
    sigma: &[f64],
    sig: &mut [f64],
    wkrr1: &mut [f64],
    wkrr2: &mut [f64],
    wkrqrq2: &mut [f64],
    wkqq1: &mut [f64],
    wkqq2: &mut [f64],
) {
    let (r, q, m) = (pr.r, pr.q, pr.m);
    let rq = r * q;
    if zflag {
        let mut k1 = 1 + r * (r + 1) / 2;
        let mut k2 = 1 + r * (r + 1) / 2 + r;
        for l in 1..=r {
            k1 += 1;
            let c = pr.hyp[k1 - 1];
            for i in 1..=q {
                for j in i..=q {
                    k2 += 1;
                    psi[ix3(i, j, l, q, q)] = pr.hyp[k2 - 1] / c;
                }
            }
        }
    }
    for i in 1..=rq {
        for j in i..=rq {
            wkrqrq2[ix2(i, j, rq)] = 0.0;
        }
    }
    for l in 1..=r {
        for i in 1..=q {
            for j in i..=q {
                wkqq1[ix2(i, j, q)] = psi[ix3(i, j, l, q, q)];
            }
        }
        chfc(wkqq1, q, q);
        bkslv(wkqq1, q, q);
        mm(wkqq1, wkqq2, q, q);
        for i in 1..=q {
            for j in i..=q {
                let ii = (l - 1) * q + i;
                let jj = (l - 1) * q + j;
                wkrqrq2[ix2(ii, jj, rq)] = wkqq2[ix2(i, j, q)];
            }
        }
    }
    for i in 1..=r {
        for j in i..=r {
            wkrr1[ix2(i, j, r)] = sigma[ix2(i, j, r)];
        }
    }
    chfc(wkrr1, r, r);
    bkslv(wkrr1, r, r);
    mm(wkrr1, wkrr2, r, r);
    for i in 1..=r {
        for j in i + 1..=r {
            wkrr2[ix2(j, i, r)] = wkrr2[ix2(i, j, r)];
        }
    }
    for s in 1..=m {
        for i in 1..=r {
            for j in i..=r {
                for ii in 1..=q {
                    for jj in 1..=q {
                        let ia = (i - 1) * q + ii;
                        let ja = (j - 1) * q + jj;
                        sig[ix3(ia, ja, s, rq, rq)] =
                            wkrr2[ix2(i, j, r)] * pr.ztz[ix3(ii, jj, s, q, q)];
                    }
                }
            }
        }
        for i in 1..=rq {
            for j in i..=rq {
                sig[ix3(i, j, s, rq, rq)] += wkrqrq2[ix2(i, j, rq)];
            }
        }
        let off = (s - 1) * rq * rq;
        chfc(&mut sig[off..off + rq * rq], rq, rq);
        bkslv(&mut sig[off..off + rq * rq], rq, rq);
    }
}

/// `mkpsi0`: starting psi from the average of the per-subject sig matrices.
fn mkpsi0(pr: &Problem, psi: &mut [f64], sig: &[f64], wkrqrq1: &mut [f64]) {
    let (r, q, m) = (pr.r, pr.q, pr.m);
    let rq = r * q;
    for i in 1..=rq {
        for j in i..=rq {
            psi[ix2(i, j, rq)] = 0.0;
        }
    }
    for s in 1..=m {
        let off = (s - 1) * rq * rq;
        mm(&sig[off..off + rq * rq], wkrqrq1, rq, rq);
        for i in 1..=rq {
            for j in i..=rq {
                psi[ix2(i, j, rq)] += wkrqrq1[ix2(i, j, rq)];
            }
        }
    }
    for i in 1..=rq {
        for j in i..=rq {
            psi[ix2(i, j, rq)] /= m as f64;
            if i != j {
                psi[ix2(j, i, rq)] = psi[ix2(i, j, rq)];
            }
        }
    }
}

/// `mkpsi0bd`: block-diagonal `mkpsi0`; psi is q x q x r.
fn mkpsi0bd(pr: &Problem, psi: &mut [f64], sig: &[f64], wkrqrq1: &mut [f64]) {
    let (r, q, m) = (pr.r, pr.q, pr.m);
    let rq = r * q;
    for l in 1..=r {
        for i in 1..=q {
            for j in i..=q {
                psi[ix3(i, j, l, q, q)] = 0.0;
            }
        }
    }
    for s in 1..=m {
        let off = (s - 1) * rq * rq;
        mm(&sig[off..off + rq * rq], wkrqrq1, rq, rq);
        for l in 1..=r {
            for i in 1..=q {
                for j in i..=q {
                    let ii = (l - 1) * q + i;
                    let jj = (l - 1) * q + j;
                    psi[ix3(i, j, l, q, q)] += wkrqrq1[ix2(ii, jj, rq)];
                }
            }
        }
    }
    for l in 1..=r {
        for i in 1..=q {
            for j in i..=q {
                psi[ix3(i, j, l, q, q)] /= m as f64;
                if i != j {
                    psi[ix3(j, i, l, q, q)] = psi[ix3(i, j, l, q, q)];
                }
            }
        }
    }
}

/// `drb`: draws the subject random effects b(q, r, m) given eps and inv(sigma).
fn drb(
    pr: &Problem,
    b: &mut [f64],
    sigmainv: &[f64],
    eps: &[f64],
    wkqr1: &mut [f64],
    wkqr2: &mut [f64],
    sig: &[f64],
    wkrqrq2: &mut [f64],
    wkqrv: &mut [f64],
    rng: &mut Rng,
) {
    let (ntot, r, q, m) = (pr.ntot, pr.r, pr.q, pr.m);
    let rq = r * q;
    for s in 1..=m {
        let st = pr.ist[s - 1];
        let fin = pr.ifin[s - 1];
        for j in 1..=r {
            for i in 1..=q {
                let mut sum = 0.0;
                for k in st..=fin {
                    if pr.patt[k - 1] != 0 {
                        sum += pr.pred_at(k, pr.zcol[i - 1]) * eps[ix2(k, j, ntot)];
                    }
                }
                wkqr1[ix2(i, j, q)] = sum;
            }
        }
        for j in 1..=r {
            for i in 1..=q {
                let mut sum = 0.0;
                for k in 1..=r {
                    sum += sigmainv[ix2(j, k, r)] * wkqr1[ix2(i, k, q)];
                }
                wkqr2[ix2(i, j, q)] = sum;
            }
        }
        let off = (s - 1) * rq * rq;
        mm(&sig[off..off + rq * rq], wkrqrq2, rq, rq);
        for i in 1..=rq {
            for j in i + 1..=rq {
                wkrqrq2[ix2(j, i, rq)] = wkrqrq2[ix2(i, j, rq)];
            }
        }
        let mut ia = 0;
        for i in 1..=r {
            for ii in 1..=q {
                ia += 1;
                let mut ja = 0;
                let mut sum = 0.0;
                for j in 1..=r {
                    for jj in 1..=q {
                        ja += 1;
                        sum += wkrqrq2[ix2(ia, ja, rq)] * wkqr2[ix2(jj, j, q)];
                    }
                }
                b[ix3(ii, i, s, q, r)] = sum;
            }
        }
        for i in 1..=rq {
            wkqrv[i - 1] = rng.gauss() as f64;
        }
        let mut ia = 0;
        for i in 1..=r {
            for ii in 1..=q {
                ia += 1;
                let mut sum = 0.0;
                for ja in ia..=rq {
                    sum += sig[ix3(ia, ja, s, rq, rq)] * wkqrv[ja - 1];
                }
                b[ix3(ii, i, s, q, r)] += sum;
            }
        }
    }
}

/// `drpsi`: draws psi (rq x rq) from its inverse Wishart given b.
fn drpsi(
    pr: &Problem,
    psi: &mut [f64],
    wkrqrq1: &mut [f64],
    wkrqrq2: &mut [f64],
    wkqrv: &mut [f64],
    b: &[f64],
    rng: &mut Rng,
) {
    let (r, q, m) = (pr.r, pr.q, pr.m);
    let rq = r * q;
    let mut k = r * (r + 1) / 2 + 2;
    let c = pr.hyp[k - 1];
    for i in 1..=rq {
        for j in i..=rq {
            k += 1;
            wkrqrq1[ix2(i, j, rq)] = pr.hyp[k - 1];
        }
    }
    for s in 1..=m {
        let mut ia = 0;
        for j in 1..=r {
            for i in 1..=q {
                ia += 1;
                wkqrv[ia - 1] = b[ix3(i, j, s, q, r)];
            }
        }
        for i in 1..=rq {
            for j in i..=rq {
                wkrqrq1[ix2(i, j, rq)] += wkqrv[i - 1] * wkqrv[j - 1];
            }
        }
    }
    chfc(wkrqrq1, rq, rq);
    rng.bfac(rq, (c as f32) + (m as f32), psi, rq);
    bkslv(psi, rq, rq);
    for i in 1..=rq {
        for j in 1..=rq {
            let mut sum = 0.0;
            for kk in 1..=i.min(j) {
                sum += wkrqrq1[ix2(kk, i, rq)] * psi[ix2(kk, j, rq)];
            }
            wkrqrq2[ix2(i, j, rq)] = sum;
        }
    }
    for i in 1..=rq {
        for j in i..=rq {
            let mut sum = 0.0;
            for kk in 1..=rq {
                sum += wkrqrq2[ix2(i, kk, rq)] * wkrqrq2[ix2(j, kk, rq)];
            }
            psi[ix2(i, j, rq)] = sum;
            if i != j {
                psi[ix2(j, i, rq)] = psi[ix2(i, j, rq)];
            }
        }
    }
}

/// `drpsibd`: block-diagonal `drpsi`; psi is q x q x r.
fn drpsibd(
    pr: &Problem,
    psi: &mut [f64],
    wkqq1: &mut [f64],
    wkqq2: &mut [f64],
    wkqrv: &mut [f64],
    b: &[f64],
    rng: &mut Rng,
) {
    let (r, q, m) = (pr.r, pr.q, pr.m);
    for l in 1..=r {
        let k0 = 1 + r * (r + 1) / 2 + l;
        let c = pr.hyp[k0 - 1];
        let mut k = 1 + r * (r + 1) / 2 + r + (l - 1) * q * (q + 1) / 2;
        for i in 1..=q {
            for j in i..=q {
                k += 1;
                wkqq1[ix2(i, j, q)] = pr.hyp[k - 1];
            }
        }
        for s in 1..=m {
            for i in 1..=q {
                wkqrv[i - 1] = b[ix3(i, l, s, q, r)];
            }
            for i in 1..=q {
                for j in i..=q {
                    wkqq1[ix2(i, j, q)] += wkqrv[i - 1] * wkqrv[j - 1];
                }
            }
        }
        chfc(wkqq1, q, q);
        rng.bfac(q, (c as f32) + (m as f32), wkqq2, q);
        bkslv(wkqq2, q, q);
        for i in 1..=q {
            for j in 1..=q {
                let mut sum = 0.0;
                for kk in 1..=i.min(j) {
                    sum += wkqq1[ix2(kk, i, q)] * wkqq2[ix2(kk, j, q)];
                }
                psi[ix3(i, j, l, q, q)] = sum;
            }
        }
        for i in 1..=q {
            for j in 1..=q {
                wkqq2[ix2(i, j, q)] = psi[ix3(i, j, l, q, q)];
            }
        }
        for i in 1..=q {
            for j in i..=q {
                let mut sum = 0.0;
                for kk in 1..=q {
                    sum += wkqq2[ix2(i, kk, q)] * wkqq2[ix2(j, kk, q)];
                }
                psi[ix3(i, j, l, q, q)] = sum;
                if i != j {
                    psi[ix3(j, i, l, q, q)] = psi[ix3(i, j, l, q, q)];
                }
            }
        }
    }
}

/// `drsigma`: draws sigma from its inverse Wishart given delta on observed rows.
fn drsigma(
    pr: &Problem,
    delta: &[f64],
    sigma: &mut [f64],
    wkrr1: &mut [f64],
    wkrr2: &mut [f64],
    rng: &mut Rng,
) {
    let (ntot, r) = (pr.ntot, pr.r);
    let a = pr.hyp[0];
    let mut k = 1usize;
    for i in 1..=r {
        for j in i..=r {
            k += 1;
            wkrr1[ix2(i, j, r)] = pr.hyp[k - 1];
        }
    }
    for i in 1..=ntot {
        if pr.patt[i - 1] != 0 {
            for j in 1..=r {
                for kk in j..=r {
                    wkrr1[ix2(j, kk, r)] += delta[ix2(i, j, ntot)] * delta[ix2(i, kk, ntot)];
                }
            }
        }
    }
    chfc(wkrr1, r, r);
    let dof = pr.nstar as i64 - pr.p as i64;
    rng.bfac(r, (a as f32) + (dof as f32), sigma, r);
    bkslv(sigma, r, r);
    // In drsigma.f `sum` has no declaration, so Fortran makes it REAL*4: each
    // partial sum is rounded to single precision. Mirror that with an f32 accumulator.
    for i in 1..=r {
        for j in 1..=r {
            let mut sum: f32 = 0.0;
            for kk in 1..=i.min(j) {
                sum = (sum as f64 + wkrr1[ix2(kk, i, r)] * sigma[ix2(kk, j, r)]) as f32;
            }
            wkrr2[ix2(i, j, r)] = sum as f64;
        }
    }
    for i in 1..=r {
        for j in i..=r {
            let mut sum: f32 = 0.0;
            for kk in 1..=r {
                sum = (sum as f64 + wkrr2[ix2(i, kk, r)] * wkrr2[ix2(j, kk, r)]) as f32;
            }
            sigma[ix2(i, j, r)] = sum as f64;
            if i != j {
                sigma[ix2(j, i, r)] = sigma[ix2(i, j, r)];
            }
        }
    }
}

/// `drbeta`: adds normal(0, sigma (x) xtxinv) noise to beta.
fn drbeta(
    pr: &Problem,
    sigma: &[f64],
    beta: &mut [f64],
    wkrr1: &mut [f64],
    wkpp: &mut [f64],
    wkpr: &mut [f64],
    rng: &mut Rng,
) {
    let (r, p) = (pr.r, pr.p);
    for i in 1..=r {
        for j in i..=r {
            wkrr1[ix2(i, j, r)] = sigma[ix2(i, j, r)];
        }
    }
    for i in 1..=p {
        for j in i..=p {
            wkpp[ix2(i, j, p)] = pr.xtxinv[ix2(i, j, p)];
        }
    }
    chfc(wkrr1, r, r);
    chfc(wkpp, p, p);
    for i in 1..=p {
        for j in 1..=r {
            wkpr[ix2(i, j, p)] = rng.gauss() as f64;
        }
    }
    for j in 1..=r {
        for i in (1..=p).rev() {
            let mut sum = 0.0;
            for k in 1..=i {
                sum += wkpp[ix2(k, i, p)] * wkpr[ix2(k, j, p)];
            }
            wkpr[ix2(i, j, p)] = sum;
        }
    }
    for j in 1..=r {
        for i in 1..=j {
            for k in 1..=p {
                beta[ix2(k, j, p)] += wkrr1[ix2(i, j, r)] * wkpr[ix2(k, i, p)];
            }
        }
    }
}

/// `swp` / `rsw` on the pattern selected by `swpobs`.
fn swpobs(pr: &Problem, sigma: &mut [f64], pt: usize) {
    let r = pr.r;
    for col in 1..=r {
        if pr.rmat_at(pt, col) == 1 && sigma[ix2(col, col, r)] > 0.0 {
            swp(sigma, r, col);
        }
        if pr.rmat_at(pt, col) == 0 && sigma[ix2(col, col, r)] <= 0.0 {
            rsw(sigma, r, col);
        }
    }
}

/// `dreps`: draws the residuals of the missing entries of delta.
fn dreps(
    pr: &Problem,
    delta: &mut [f64],
    sigma: &[f64],
    wkrr1: &mut [f64],
    wkrr2: &mut [f64],
    rng: &mut Rng,
) {
    let (ntot, r, npatt) = (pr.ntot, pr.r, pr.npatt);
    let mut wkr = vec![0.0f64; r + 1];
    let mut oc = vec![0usize; r + 1];
    let mut mc = vec![0usize; r + 1];
    let first = pr.pstfin[0];
    // Completely missing cases come first in iposn.
    if first != 1 {
        for i in 1..=r {
            for j in i..=r {
                wkrr1[ix2(i, j, r)] = sigma[ix2(i, j, r)];
            }
        }
        chfc(wkrr1, r, r);
        for i in 1..first {
            for j in 1..=r {
                wkr[j - 1] = rng.gauss() as f64;
            }
            for j in (1..=r).rev() {
                let mut sum = 0.0;
                for k in 1..=j {
                    sum += wkrr1[ix2(k, j, r)] * wkr[k - 1];
                }
                wkr[j - 1] = sum;
            }
            let row = pr.iposn[i - 1];
            for j in 1..=r {
                delta[ix2(row, j, ntot)] = wkr[j - 1];
            }
        }
    }
    // Partially observed cases, one pattern at a time.
    for i in 1..=r {
        for j in i..=r {
            wkrr1[ix2(i, j, r)] = sigma[ix2(i, j, r)];
        }
    }
    for pt in 1..=npatt {
        swpobs(pr, wkrr1, pt);
        for i in 1..=r {
            for j in i + 1..=r {
                wkrr1[ix2(j, i, r)] = wkrr1[ix2(i, j, r)];
            }
        }
        // getmc: missing columns of the pattern; getoc: observed columns.
        let mut nmc = 0;
        for j in 1..=r {
            if pr.rmat_at(pt, j) == 0 {
                nmc += 1;
                mc[nmc - 1] = j;
            }
        }
        let mut noc = 0;
        for j in 1..=r {
            if pr.rmat_at(pt, j) == 1 {
                noc += 1;
                oc[noc - 1] = j;
            }
        }
        // chsub: Cholesky factor of the missing-by-missing block.
        for i in 1..=nmc {
            for j in i..=nmc {
                wkrr2[ix2(i, j, r)] = wkrr1[ix2(mc[i - 1], mc[j - 1], r)];
            }
        }
        chfc(wkrr2, r, nmc);
        for i in pr.pstfin[pt - 1]..=pr.pstfin[pt - 1 + npatt] {
            let row = pr.iposn[i - 1];
            for j in 1..=nmc {
                wkr[j - 1] = rng.gauss() as f64;
            }
            for j in (1..=nmc).rev() {
                let mut sum = 0.0;
                for k in 1..=j {
                    sum += wkrr2[ix2(k, j, r)] * wkr[k - 1];
                }
                wkr[j - 1] = sum;
            }
            for j in 1..=nmc {
                let mut sum = 0.0;
                for k in 1..=noc {
                    sum += wkrr1[ix2(oc[k - 1], mc[j - 1], r)] * delta[ix2(row, oc[k - 1], ntot)];
                }
                delta[ix2(row, mc[j - 1], ntot)] = sum + wkr[j - 1];
            }
        }
    }
}

/// `mky`: imputes the missing entries of y from the fixed and random parts.
fn mky(pr: &Problem, delta: &[f64], beta: &[f64], b: &[f64], y: &mut [f64]) {
    let (ntot, r, p, q) = (pr.ntot, pr.r, pr.p, pr.q);
    for s in 1..=pr.m {
        for i in pr.ist[s - 1]..=pr.ifin[s - 1] {
            let pat = pr.patt[i - 1];
            for j in 1..=r {
                if pat != 0 && pr.rmat_at(pat, j) != 0 {
                    continue;
                }
                let mut sum = 0.0;
                for k in 1..=p {
                    sum += pr.pred_at(i, pr.xcol[k - 1]) * beta[ix2(k, j, p)];
                }
                for k in 1..=q {
                    sum += pr.pred_at(i, pr.zcol[k - 1]) * b[ix3(k, j, s, q, r)];
                }
                y[ix2(i, j, ntot)] = sum + delta[ix2(i, j, ntot)];
            }
        }
    }
}

/// `store`: records beta, sigma and psi (rq x rq) for iteration `it`.
fn store(pr: &Problem, it: usize, beta: &[f64], sigma: &[f64], psi: &[f64], out: &mut Chain) {
    let (p, r) = (pr.p, pr.r);
    let rq = pr.r * pr.q;
    for j in 1..=r {
        for i in 1..=p {
            out.betas[ix3(i, j, it, p, r)] = beta[ix2(i, j, p)];
        }
    }
    for j in 1..=rq {
        for i in 1..=rq {
            out.psis[ix3(i, j, it, rq, rq)] = psi[ix2(i, j, rq)];
        }
    }
    for j in 1..=r {
        for i in 1..=r {
            out.sigmas[ix3(i, j, it, r, r)] = sigma[ix2(i, j, r)];
        }
    }
}

/// `storebd`: records beta, sigma and psi (q x q x r) for iteration `it`.
fn storebd(pr: &Problem, it: usize, beta: &[f64], sigma: &[f64], psi: &[f64], out: &mut Chain) {
    let (p, r, q) = (pr.p, pr.r, pr.q);
    for j in 1..=r {
        for i in 1..=p {
            out.betas[ix3(i, j, it, p, r)] = beta[ix2(i, j, p)];
        }
    }
    for l in 1..=r {
        for j in 1..=q {
            for i in 1..=q {
                out.psis[ix4(i, j, l, it, q, q, r)] = psi[ix3(i, j, l, q, q)];
            }
        }
    }
    for j in 1..=r {
        for i in 1..=r {
            out.sigmas[ix3(i, j, it, r, r)] = sigma[ix2(i, j, r)];
        }
    }
}

// ---------------------------------------------------------------------------
// Drivers
// ---------------------------------------------------------------------------

/// Starting values for a run with `sflag == 1`.
pub struct Start {
    pub beta: Vec<f64>,
    pub sigma: Vec<f64>,
    pub psi: Vec<f64>,
    pub eps: Vec<f64>,
}

/// Chains and the final imputed y, column-major.
pub struct Chain {
    pub beta: Vec<f64>,
    pub sigma: Vec<f64>,
    pub psi: Vec<f64>,
    pub y: Vec<f64>,
    pub betas: Vec<f64>,
    pub sigmas: Vec<f64>,
    pub psis: Vec<f64>,
}

/// `mgibbs`: conventional Gibbs sampler for the full (q x q x r block-free) psi.
/// `start` is `None` for `sflag == 0` and `Some` for `sflag == 1`.
pub fn mgibbs(pr: &Problem, rng: &mut Rng, y0: &[f64], start: Option<Start>, iter: usize) -> Chain {
    let (ntot, r, p, q, m) = (pr.ntot, pr.r, pr.p, pr.q, pr.m);
    let rq = r * q;
    let mut y = y0.to_vec();
    let mut b = vec![0.0; q * r * m];
    let mut wkpp = vec![0.0; p * p];
    let mut wkpr = vec![0.0; p * r];
    let mut eps = vec![0.0; ntot * r];
    let mut delta = vec![0.0; ntot * r];
    let mut wkrqrq1 = vec![0.0; rq * rq];
    let mut wkrqrq2 = vec![0.0; rq * rq];
    let mut sig = vec![0.0; rq * rq * m];
    let mut wkrr1 = vec![0.0; r * r];
    let mut wkrr2 = vec![0.0; r * r];
    let mut wkqr1 = vec![0.0; q * r];
    let mut wkqr2 = vec![0.0; q * r];
    let mut wkqrv = vec![0.0; rq];
    let mut beta = vec![0.0; p * r];
    let mut sigma = vec![0.0; r * r];
    let mut psi = vec![0.0; rq * rq];
    let mut out = Chain {
        beta: Vec::new(),
        sigma: Vec::new(),
        psi: Vec::new(),
        y: Vec::new(),
        betas: vec![0.0; p * r * iter],
        sigmas: vec![0.0; r * r * iter],
        psis: vec![0.0; rq * rq * iter],
    };

    let _junk = rng.gauss();
    match start {
        None => {
            mimpy(pr, &mut y);
            mkxty(pr, &y, &mut wkpr);
            mkbeta(pr, &wkpr, &mut beta);
            mkeps1(pr, &y, &beta, &mut eps);
            mksigma(pr, &eps, &mut sigma);
            mksig(pr, true, &mut psi, &sigma, &mut sig, &mut wkrr1, &mut wkrr2, &mut wkrqrq1, &mut wkrqrq2);
            mkpsi0(pr, &mut psi, &sig, &mut wkrqrq1);
        }
        Some(st) => {
            beta = st.beta;
            sigma = st.sigma;
            psi = st.psi;
            y = st.eps;
        }
    }

    for it in 1..=iter {
        mkeps1(pr, &y, &beta, &mut eps);
        mksig(pr, false, &mut psi, &sigma, &mut sig, &mut wkrr1, &mut wkrr2, &mut wkrqrq1, &mut wkrqrq2);
        drb(pr, &mut b, &wkrr2, &eps, &mut wkqr1, &mut wkqr2, &sig, &mut wkrqrq2, &mut wkqrv, rng);
        drpsi(pr, &mut psi, &mut wkrqrq1, &mut wkrqrq2, &mut wkqrv, &b, rng);
        mkeps2(pr, &y, &b, &mut eps);
        mkxty(pr, &eps, &mut wkpr);
        mkbeta(pr, &wkpr, &mut beta);
        mkeps1(pr, &eps, &beta, &mut delta);
        drsigma(pr, &delta, &mut sigma, &mut wkrr1, &mut wkrr2, rng);
        drbeta(pr, &sigma, &mut beta, &mut wkrr1, &mut wkpp, &mut wkpr, rng);
        mkeps1(pr, &eps, &beta, &mut delta);
        dreps(pr, &mut delta, &sigma, &mut wkrr1, &mut wkrr2, rng);
        mky(pr, &delta, &beta, &b, &mut y);
        store(pr, it, &beta, &sigma, &psi, &mut out);
    }
    out.beta = beta;
    out.sigma = sigma;
    out.psi = psi;
    out.y = y;
    out
}

/// `mgibbsbd`: conventional Gibbs sampler for the block-diagonal psi (q x q x r).
pub fn mgibbsbd(pr: &Problem, rng: &mut Rng, y0: &[f64], start: Option<Start>, iter: usize) -> Chain {
    let (ntot, r, p, q, m) = (pr.ntot, pr.r, pr.p, pr.q, pr.m);
    let rq = r * q;
    let mut y = y0.to_vec();
    let mut b = vec![0.0; q * r * m];
    let mut wkpp = vec![0.0; p * p];
    let mut wkpr = vec![0.0; p * r];
    let mut eps = vec![0.0; ntot * r];
    let mut delta = vec![0.0; ntot * r];
    let mut wkrqrq1 = vec![0.0; rq * rq];
    let mut wkrqrq2 = vec![0.0; rq * rq];
    let mut sig = vec![0.0; rq * rq * m];
    let mut wkrr1 = vec![0.0; r * r];
    let mut wkrr2 = vec![0.0; r * r];
    let mut wkqr1 = vec![0.0; q * r];
    let mut wkqr2 = vec![0.0; q * r];
    let mut wkqrv = vec![0.0; rq];
    let mut wkqq1 = vec![0.0; q * q];
    let mut wkqq2 = vec![0.0; q * q];
    let mut beta = vec![0.0; p * r];
    let mut sigma = vec![0.0; r * r];
    let mut psi = vec![0.0; q * q * r];
    let mut out = Chain {
        beta: Vec::new(),
        sigma: Vec::new(),
        psi: Vec::new(),
        y: Vec::new(),
        betas: vec![0.0; p * r * iter],
        sigmas: vec![0.0; r * r * iter],
        psis: vec![0.0; q * q * r * iter],
    };

    let _junk = rng.gauss();
    match start {
        None => {
            mimpy(pr, &mut y);
            mkxty(pr, &y, &mut wkpr);
            mkbeta(pr, &wkpr, &mut beta);
            mkeps1(pr, &y, &beta, &mut eps);
            mksigma(pr, &eps, &mut sigma);
            mksigbd(pr, true, &mut psi, &sigma, &mut sig, &mut wkrr1, &mut wkrr2, &mut wkrqrq2, &mut wkqq1, &mut wkqq2);
            mkpsi0bd(pr, &mut psi, &sig, &mut wkrqrq1);
        }
        Some(st) => {
            beta = st.beta;
            sigma = st.sigma;
            psi = st.psi;
            y = st.eps;
        }
    }

    for it in 1..=iter {
        mkeps1(pr, &y, &beta, &mut eps);
        mksigbd(pr, false, &mut psi, &sigma, &mut sig, &mut wkrr1, &mut wkrr2, &mut wkrqrq2, &mut wkqq1, &mut wkqq2);
        drb(pr, &mut b, &wkrr2, &eps, &mut wkqr1, &mut wkqr2, &sig, &mut wkrqrq2, &mut wkqrv, rng);
        drpsibd(pr, &mut psi, &mut wkqq1, &mut wkqq2, &mut wkqrv, &b, rng);
        mkeps2(pr, &y, &b, &mut eps);
        mkxty(pr, &eps, &mut wkpr);
        mkbeta(pr, &wkpr, &mut beta);
        mkeps1(pr, &eps, &beta, &mut delta);
        drsigma(pr, &delta, &mut sigma, &mut wkrr1, &mut wkrr2, rng);
        drbeta(pr, &sigma, &mut beta, &mut wkrr1, &mut wkpp, &mut wkpr, rng);
        mkeps1(pr, &eps, &beta, &mut delta);
        dreps(pr, &mut delta, &sigma, &mut wkrr1, &mut wkrr2, rng);
        mky(pr, &delta, &beta, &b, &mut y);
        storebd(pr, it, &beta, &sigma, &psi, &mut out);
    }
    out.beta = beta;
    out.sigma = sigma;
    out.psi = psi;
    out.y = y;
    out
}

/// Number of hyperparameters `mgibbs` reads: a, Binv (upper), c, Dinv (rq x rq upper).
pub fn nhyp_full(r: usize, q: usize) -> usize {
    2 + r * (r + 1) / 2 + (r * q) * (r * q + 1) / 2
}

/// Number of hyperparameters `mgibbsbd` reads: a, Binv (upper), c (length r), Dinv (q x q x r upper).
pub fn nhyp_bd(r: usize, q: usize) -> usize {
    1 + r * (r + 1) / 2 + r + r * q * (q + 1) / 2
}
