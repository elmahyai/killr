//! ECME kernels of the R package pan 2.0 (`src/pan.f`): `prelim`, `nopsi`, `ecme3`
//! and `bdiag`, the routines that `ecme()` calls through `.Fortran`.
//!
//! The Fortran is the kernel. `build.rs` compiles `vendor/pan.f` with gfortran and
//! links it statically, and this crate calls the routines by their Fortran symbols.
//! Nothing is re-ported, so the implicit REAL*4 `sum` and `sum1` in `gls` keep their
//! single precision exactly as R has them.
//!
//! Arrays are column-major and every index is 1-based, as in the Fortran. Each safe
//! function takes the inputs of the R `.Fortran` call in `ecme()`, with these changes:
//!
//! * `subj` gives the run number of each row (1, 1, 2, 2, 2, 3, ...). `m` is the
//!   number of runs, which equals `table(subj)` for contiguous subjects.
//! * `zcol` is passed with length `q`. An empty `zcol` (the `zcol = NULL` branch,
//!   where nopsi never reads `ztv` or `sig0`) gives `q = 0`, so the Fortran never reads
//!   `pred(., 0)`.

#![allow(clippy::too_many_arguments)]

#[cfg(feature = "python")]
mod python;

unsafe extern "C" {
    fn prelim_(
        ntot: *mut i32,
        subj: *mut i32,
        m: *mut i32,
        ist: *mut i32,
        ifin: *mut i32,
        occ: *mut i32,
        nmax: *mut i32,
        vmax: *mut f64,
        vh: *mut f64,
        vi: *mut f64,
        pcol: *mut i32,
        pred: *mut f64,
        q: *mut i32,
        zcol: *mut i32,
        ztv: *mut f64,
        sig0: *mut f64,
        iflag: *mut i32,
    );
    fn nopsi_(
        ntot: *mut i32,
        m: *mut i32,
        ist: *mut i32,
        ifin: *mut i32,
        occ: *mut i32,
        nmax: *mut i32,
        vi: *mut f64,
        vh: *mut f64,
        pcol: *mut i32,
        pred: *mut f64,
        q: *mut i32,
        zcol: *mut i32,
        ztv: *mut f64,
        sig0: *mut f64,
        iflag: *mut i32,
        sig: *mut f64,
        psi: *mut f64,
        sigma2: *mut f64,
        p: *mut i32,
        xcol: *mut i32,
        beta: *mut f64,
        wkq1: *mut f64,
        wkq2: *mut f64,
        wkq3: *mut f64,
        y: *mut f64,
        delta: *mut f64,
        b: *mut f64,
        wk: *mut f64,
        w: *mut f64,
        xtw: *mut f64,
        xtwx: *mut f64,
        xtwy: *mut f64,
        xtwxinv: *mut f64,
        ll: *mut f64,
    );
    fn ecme3_(
        ntot: *mut i32,
        subj: *mut i32,
        m: *mut i32,
        ist: *mut i32,
        ifin: *mut i32,
        occ: *mut i32,
        nmax: *mut i32,
        vi: *mut f64,
        vh: *mut f64,
        pcol: *mut i32,
        pred: *mut f64,
        q: *mut i32,
        zcol: *mut i32,
        ztv: *mut f64,
        sig0: *mut f64,
        iflag: *mut i32,
        sig: *mut f64,
        psi: *mut f64,
        sigma2: *mut f64,
        p: *mut i32,
        xcol: *mut i32,
        beta: *mut f64,
        wkq1: *mut f64,
        wkq2: *mut f64,
        wkq3: *mut f64,
        y: *mut f64,
        delta: *mut f64,
        b: *mut f64,
        wk: *mut f64,
        w: *mut f64,
        xtw: *mut f64,
        xtwx: *mut f64,
        xtwy: *mut f64,
        xtwxinv: *mut f64,
        llk: *mut f64,
        vmax: *mut f64,
        sflag: *mut i32,
        eps: *mut f64,
        obeta: *mut f64,
        opsi: *mut f64,
        maxits: *mut i32,
        iter: *mut i32,
        cvgd: *mut i32,
    );
    fn bdiag_(q: *mut i32, m: *mut i32, sig: *mut f64);
}

/// A zero-filled buffer of at least one element, so the Fortran always gets a valid pointer.
fn buf(n: usize) -> Vec<f64> {
    vec![0.0; n.max(1)]
}

fn ibuf(n: usize) -> Vec<i32> {
    vec![0; n.max(1)]
}

fn owned_f64(v: &[f64]) -> Vec<f64> {
    if v.is_empty() {
        vec![0.0]
    } else {
        v.to_vec()
    }
}

fn owned_i32(v: &[i32]) -> Vec<i32> {
    if v.is_empty() {
        vec![0]
    } else {
        v.to_vec()
    }
}

fn dim(n: usize) -> i32 {
    i32::try_from(n).expect("dimension fits in a Fortran INTEGER")
}

fn trimmed(mut v: Vec<f64>, n: usize) -> Vec<f64> {
    v.truncate(n);
    v
}

/// Identity of size n x n, the V_i that pan uses when `vmax` is missing (iflag = 1).
fn identity(n: usize) -> Vec<f64> {
    let mut v = buf(n * n);
    for i in 0..n {
        v[i + i * n] = 1.0;
    }
    v
}

/// Number of runs of equal values in `subj`, which is the number of subjects istfin finds.
pub fn runs(subj: &[i32]) -> usize {
    if subj.is_empty() {
        0
    } else {
        1 + subj.windows(2).filter(|w| w[0] != w[1]).count()
    }
}

/// Largest occasion, which is nmax in pan.f.
pub fn nmax_of(occ: &[i32]) -> usize {
    occ.iter().copied().max().unwrap_or(0).max(0) as usize
}

/// Arrays that `prelim` fills. `vh` and `vi` are nmax x nmax x m, `ztv` is q x nmax x m
/// and `sig0` is q x q x m. With `vmax` missing, `vh` and `vi` are not used.
pub struct Prelim {
    pub m: usize,
    pub nmax: usize,
    pub q: usize,
    pub ist: Vec<i32>,
    pub ifin: Vec<i32>,
    pub vh: Vec<f64>,
    pub vi: Vec<f64>,
    pub ztv: Vec<f64>,
    pub sig0: Vec<f64>,
}

/// `prelim`: istfin, the inverse Cholesky factors of V_i, ztv and sig0 (pan.f).
pub fn prelim(
    subj: &[i32],
    occ: &[i32],
    pred: &[f64],
    pcol: usize,
    zcol: &[i32],
    vmax: Option<&[f64]>,
) -> Prelim {
    let ntot = subj.len();
    let m = runs(subj);
    let nmax = nmax_of(occ);
    let q = zcol.len();
    let iflag = i32::from(vmax.is_none());

    let mut subj_f = owned_i32(subj);
    let mut occ_f = owned_i32(occ);
    let mut pred_f = owned_f64(pred);
    let mut zcol_f = if q == 0 { vec![1] } else { zcol.to_vec() };
    let mut vmax_f = match vmax {
        Some(v) => owned_f64(v),
        None => identity(nmax),
    };
    let mut ist = ibuf(m);
    let mut ifin = ibuf(m);
    let mut vh = buf(nmax * nmax * m);
    let mut vi = buf(nmax * nmax * m);
    let mut ztv = buf(q * nmax * m);
    let mut sig0 = buf(q * q * m);

    let (mut ntot_, mut m_, mut nmax_, mut pcol_, mut q_, mut iflag_) = (
        dim(ntot),
        dim(m),
        dim(nmax),
        dim(pcol),
        dim(q),
        iflag,
    );
    unsafe {
        prelim_(
            &mut ntot_,
            subj_f.as_mut_ptr(),
            &mut m_,
            ist.as_mut_ptr(),
            ifin.as_mut_ptr(),
            occ_f.as_mut_ptr(),
            &mut nmax_,
            vmax_f.as_mut_ptr(),
            vh.as_mut_ptr(),
            vi.as_mut_ptr(),
            &mut pcol_,
            pred_f.as_mut_ptr(),
            &mut q_,
            zcol_f.as_mut_ptr(),
            ztv.as_mut_ptr(),
            sig0.as_mut_ptr(),
            &mut iflag_,
        );
    }
    Prelim {
        m,
        nmax,
        q,
        ist: trimmed_i32(ist, m),
        ifin: trimmed_i32(ifin, m),
        vh: trimmed(vh, nmax * nmax * m),
        vi: trimmed(vi, nmax * nmax * m),
        ztv: trimmed(ztv, q * nmax * m),
        sig0: trimmed(sig0, q * q * m),
    }
}

fn trimmed_i32(mut v: Vec<i32>, n: usize) -> Vec<i32> {
    v.truncate(n);
    v
}

/// Output of `nopsi`: GLS beta and sigma2 with psi = 0, the residuals, inv(X'WX) (upper
/// triangle), and the loglikelihood from mkll2.
pub struct NopsiOut {
    pub beta: Vec<f64>,
    pub sigma2: f64,
    pub delta: Vec<f64>,
    pub xtwxinv: Vec<f64>,
    pub ll: f64,
}

/// `nopsi`: prelim, then the GLS fit that pan.f runs when psi is zero.
pub fn nopsi(
    subj: &[i32],
    occ: &[i32],
    pred: &[f64],
    pcol: usize,
    xcol: &[i32],
    y: &[f64],
    vmax: Option<&[f64]>,
) -> NopsiOut {
    let mut pre = prelim(subj, occ, pred, pcol, &[], vmax);
    let ntot = subj.len();
    let (m, nmax) = (pre.m, pre.nmax);
    let p = xcol.len();
    let iflag = i32::from(vmax.is_none());

    let mut occ_f = owned_i32(occ);
    let mut pred_f = owned_f64(pred);
    let mut xcol_f = owned_i32(xcol);
    let mut y_f = owned_f64(y);
    let mut zcol_f = vec![1]; // q = 0: never read
    let mut sig = buf(0);
    let mut psi = buf(0);
    let mut wkq1 = buf(0);
    let mut wkq2 = buf(0);
    let mut wkq3 = buf(0);
    let mut b = buf(0);
    let mut wk = buf(0);
    let mut sigma2 = 0.0_f64;
    let mut beta = buf(p);
    let mut delta = buf(ntot);
    let mut w = buf(nmax * nmax * m);
    let mut xtw = buf(p * nmax);
    let mut xtwx = buf(p * p);
    let mut xtwy = buf(p);
    let mut xtwxinv = buf(p * p);
    let mut ll = 0.0_f64;

    let (mut ntot_, mut m_, mut nmax_, mut pcol_, mut q_, mut iflag_, mut p_) = (
        dim(ntot),
        dim(m),
        dim(nmax),
        dim(pcol),
        0,
        iflag,
        dim(p),
    );
    unsafe {
        nopsi_(
            &mut ntot_,
            &mut m_,
            pre.ist.as_mut_ptr(),
            pre.ifin.as_mut_ptr(),
            occ_f.as_mut_ptr(),
            &mut nmax_,
            pre.vi.as_mut_ptr(),
            pre.vh.as_mut_ptr(),
            &mut pcol_,
            pred_f.as_mut_ptr(),
            &mut q_,
            zcol_f.as_mut_ptr(),
            pre.ztv.as_mut_ptr(),
            pre.sig0.as_mut_ptr(),
            &mut iflag_,
            sig.as_mut_ptr(),
            psi.as_mut_ptr(),
            &mut sigma2,
            &mut p_,
            xcol_f.as_mut_ptr(),
            beta.as_mut_ptr(),
            wkq1.as_mut_ptr(),
            wkq2.as_mut_ptr(),
            wkq3.as_mut_ptr(),
            y_f.as_mut_ptr(),
            delta.as_mut_ptr(),
            b.as_mut_ptr(),
            wk.as_mut_ptr(),
            w.as_mut_ptr(),
            xtw.as_mut_ptr(),
            xtwx.as_mut_ptr(),
            xtwy.as_mut_ptr(),
            xtwxinv.as_mut_ptr(),
            &mut ll,
        );
    }
    NopsiOut {
        beta: trimmed(beta, p),
        sigma2,
        delta: trimmed(delta, ntot),
        xtwxinv: trimmed(xtwxinv, p * p),
        ll,
    }
}

/// Starting values for `ecme3`: beta (p), sigma2, and psi (q x q), as stval gives them.
pub struct Start {
    pub beta: Vec<f64>,
    pub sigma2: f64,
    pub psi: Vec<f64>,
}

/// Output of `ecme3`. `b` is q x m, `sig` is q x q x m (upper triangle, as from the
/// last iteration), and `llk` holds the loglikelihood of each iteration that ran.
pub struct Ecme3Out {
    pub beta: Vec<f64>,
    pub sigma2: f64,
    pub psi: Vec<f64>,
    pub llk: Vec<f64>,
    pub iter: usize,
    pub converged: bool,
    pub b: Vec<f64>,
    pub sig: Vec<f64>,
    pub xtwxinv: Vec<f64>,
}

/// `ecme3`: the ECME loop of pan.f. Starting values come from stval unless `start` is
/// given (sflag = 1). Stops when beta, psi and sigma2 move by less than `eps` relatively,
/// or after `maxits` iterations.
pub fn ecme3(
    subj: &[i32],
    occ: &[i32],
    pred: &[f64],
    pcol: usize,
    xcol: &[i32],
    zcol: &[i32],
    y: &[f64],
    vmax: Option<&[f64]>,
    start: Option<&Start>,
    eps: f64,
    maxits: usize,
) -> Ecme3Out {
    let ntot = subj.len();
    let m = runs(subj);
    let nmax = nmax_of(occ);
    let q = zcol.len();
    let p = xcol.len();
    let iflag = i32::from(vmax.is_none());
    let vmax_v = match vmax {
        Some(v) => owned_f64(v),
        None => identity(nmax),
    };

    let (sflag, mut sigma2, beta_in, psi_in) = match start {
        Some(s) => (1, s.sigma2, owned_f64(&s.beta), owned_f64(&s.psi)),
        None => (0, 0.0, buf(p), buf(q * q)),
    };
    let mut beta = beta_in;
    let mut psi = psi_in;

    let mut subj_f = owned_i32(subj);
    let mut occ_f = owned_i32(occ);
    let mut pred_f = owned_f64(pred);
    let mut xcol_f = owned_i32(xcol);
    let mut zcol_f = if q == 0 { vec![1] } else { zcol.to_vec() };
    let mut y_f = owned_f64(y);
    let mut vmax_f = vmax_v;

    let mut ist = ibuf(m);
    let mut ifin = ibuf(m);
    let mut vi = buf(nmax * nmax * m);
    let mut vh = buf(nmax * nmax * m);
    let mut ztv = buf(q * nmax * m);
    let mut sig0 = buf(q * q * m);
    let mut sig = buf(q * q * m);
    let mut wkq1 = buf(q * q);
    let mut wkq2 = buf(q * q);
    let mut wkq3 = buf(q * q);
    let mut delta = buf(ntot);
    let mut b = buf(q * m);
    let mut wk = buf(q * nmax * m);
    let mut w = buf(nmax * nmax * m);
    let mut xtw = buf(p * nmax);
    let mut xtwx = buf(p * p);
    let mut xtwy = buf(p);
    let mut xtwxinv = buf(p * p);
    let mut llk = buf(maxits);
    let mut obeta = buf(p);
    let mut opsi = buf(q * q);
    let mut eps_ = eps;

    let (mut ntot_, mut m_, mut nmax_, mut pcol_, mut q_, mut iflag_, mut p_) = (
        dim(ntot),
        dim(m),
        dim(nmax),
        dim(pcol),
        dim(q),
        iflag,
        dim(p),
    );
    let mut sflag_ = sflag;
    let mut maxits_ = dim(maxits);
    let mut iter_: i32 = 0;
    let mut cvgd_: i32 = 0;
    unsafe {
        ecme3_(
            &mut ntot_,
            subj_f.as_mut_ptr(),
            &mut m_,
            ist.as_mut_ptr(),
            ifin.as_mut_ptr(),
            occ_f.as_mut_ptr(),
            &mut nmax_,
            vi.as_mut_ptr(),
            vh.as_mut_ptr(),
            &mut pcol_,
            pred_f.as_mut_ptr(),
            &mut q_,
            zcol_f.as_mut_ptr(),
            ztv.as_mut_ptr(),
            sig0.as_mut_ptr(),
            &mut iflag_,
            sig.as_mut_ptr(),
            psi.as_mut_ptr(),
            &mut sigma2,
            &mut p_,
            xcol_f.as_mut_ptr(),
            beta.as_mut_ptr(),
            wkq1.as_mut_ptr(),
            wkq2.as_mut_ptr(),
            wkq3.as_mut_ptr(),
            y_f.as_mut_ptr(),
            delta.as_mut_ptr(),
            b.as_mut_ptr(),
            wk.as_mut_ptr(),
            w.as_mut_ptr(),
            xtw.as_mut_ptr(),
            xtwx.as_mut_ptr(),
            xtwy.as_mut_ptr(),
            xtwxinv.as_mut_ptr(),
            llk.as_mut_ptr(),
            vmax_f.as_mut_ptr(),
            &mut sflag_,
            &mut eps_,
            obeta.as_mut_ptr(),
            opsi.as_mut_ptr(),
            &mut maxits_,
            &mut iter_,
            &mut cvgd_,
        );
    }
    let iter = iter_.max(0) as usize;
    Ecme3Out {
        beta: trimmed(beta, p),
        sigma2,
        psi: trimmed(psi, q * q),
        llk: trimmed(llk, iter),
        iter,
        converged: cvgd_ == 1,
        b: trimmed(b, q * m),
        sig: trimmed(sig, q * q * m),
        xtwxinv: trimmed(xtwxinv, p * p),
    }
}

/// `bdiag`: fills the lower triangle of each q x q layer of `sig` from its upper triangle.
pub fn bdiag(q: usize, m: usize, sig: &mut [f64]) {
    assert!(sig.len() >= q * q * m, "sig must hold q x q x m values");
    let (mut q_, mut m_) = (dim(q), dim(m));
    unsafe {
        bdiag_(&mut q_, &mut m_, sig.as_mut_ptr());
    }
}
