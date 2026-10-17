//! L-BFGS-B as R's `optim(method = "L-BFGS-B")` runs it.
//!
//! This is a port of R 4.5.0 `src/appl/lbfgsb.c` (L-BFGS-B version 2.3, which
//! R ships), of the `lbfgsb()` driver in `src/appl/optim.c`, and of the bounded
//! numerical gradient `fmingr` in `src/library/stats/src/optim.c`. The C is
//! vendored in `vendor/` with R's GPL-2 notice. The LINPACK `dpofa` and `dtrsl`
//! are ported from `src/appl/dpofa.f` and `dtrsl.f`. The BLAS calls `ddot`,
//! `daxpy`, `dscal`, and `dcopy` are the reference sums in the same order.
//!
//! Vectors are 1-based, with index 0 unused, so each line keeps the C index.
//! Matrices are column-major with a leading dimension, and `Mat::g(i, j)` is
//! the 1-based element (i, j). Debug output (`iprint`) is not ported, because
//! `optim(trace = 0)` never prints it.

const CONV_PGTOL: &str = "CONVERGENCE: NORM OF PROJECTED GRADIENT <= PGTOL";
const FTOL: f64 = 0.001;
const GTOL: f64 = 0.9;
const XTOL: f64 = 0.1;
const STPMIN: f64 = 0.0;

/// A callback failure from R, or an error that the L-BFGS-B driver raises.
pub enum Failure<E> {
    Callback(E),
    Message(String),
}

/// What `optim()` returns for L-BFGS-B.
pub struct Output {
    pub par: Vec<f64>,
    pub value: f64,
    pub fail: i64,
    pub fncount: i64,
    pub grcount: i64,
    pub message: String,
}

/// C's `min` and `max` macros: `min(a, b)` is `(a > b) ? b : a`.
#[inline]
fn cmin(a: f64, b: f64) -> f64 {
    if a > b {
        b
    } else {
        a
    }
}

/// C's `max(a, b)` is `(a < b) ? b : a`.
#[inline]
fn cmax(a: f64, b: f64) -> f64 {
    if a < b {
        b
    } else {
        a
    }
}

/// A column-major matrix with leading dimension `ld` and 1-based indexing.
#[derive(Clone)]
struct Mat {
    ld: usize,
    d: Vec<f64>,
}

impl Mat {
    fn new(ld: usize, cols: usize) -> Mat {
        Mat {
            ld,
            d: vec![0.0; ld * cols],
        }
    }

    #[inline]
    fn ix(&self, i: usize, j: usize) -> usize {
        (i - 1) + (j - 1) * self.ld
    }

    #[inline]
    fn g(&self, i: usize, j: usize) -> f64 {
        self.d[self.ix(i, j)]
    }

    #[inline]
    fn s(&mut self, i: usize, j: usize, v: f64) {
        let k = self.ix(i, j);
        self.d[k] = v;
    }
}

/// LINPACK `dpofa`: the Cholesky factor of the upper triangle, in place.
/// `a[0]` is element (1, 1). Returns 0, or the order j where the matrix is not
/// positive definite.
fn dpofa(a: &mut [f64], lda: usize, n: usize) -> i64 {
    let eps = 1e-14;
    for j in 1..=n {
        let mut s = 0.0;
        let jm1 = j - 1;
        if jm1 >= 1 {
            for k in 1..=jm1 {
                let mut dot = 0.0;
                for i in 0..(k - 1) {
                    dot += a[i + (k - 1) * lda] * a[i + (j - 1) * lda];
                }
                let mut t = a[(k - 1) + (j - 1) * lda] - dot;
                t /= a[(k - 1) + (k - 1) * lda];
                a[(k - 1) + (j - 1) * lda] = t;
                s += t * t;
            }
        }
        let ajj = a[(j - 1) + (j - 1) * lda];
        s = ajj - s;
        if s <= eps * ajj.abs() {
            return j as i64;
        }
        a[(j - 1) + (j - 1) * lda] = s.sqrt();
    }
    0
}

/// LINPACK `dtrsl`: solves a triangular system with the matrix `t` (leading
/// dimension `ldt`) and right-hand side `b` (`b[0]` is b(1)). The job codes
/// are those of the Fortran: 1 solves T x = b with T upper, 11 solves
/// T' x = b with T upper, 10 and 00 use the lower triangle.
fn dtrsl(t: &[f64], ldt: usize, n: usize, b: &mut [f64], job: i32) -> i64 {
    let tt = |i: usize, j: usize| t[(i - 1) + (j - 1) * ldt];
    for info in 1..=n {
        if tt(info, info) == 0.0 {
            return info as i64;
        }
    }
    let mut kase = 1;
    if job % 10 != 0 {
        kase = 2;
    }
    if (job % 100) / 10 != 0 {
        kase += 2;
    }
    match kase {
        1 => {
            b[0] /= tt(1, 1);
            for j in 2..=n {
                let temp = -b[j - 2];
                for k in 0..(n - j + 1) {
                    b[j - 1 + k] += temp * tt(j + k, j - 1);
                }
                b[j - 1] /= tt(j, j);
            }
        }
        2 => {
            b[n - 1] /= tt(n, n);
            for jj in 2..=n {
                let j = n - jj + 1;
                let temp = -b[j];
                for k in 0..j {
                    b[k] += temp * tt(k + 1, j + 1);
                }
                b[j - 1] /= tt(j, j);
            }
        }
        3 => {
            b[n - 1] /= tt(n, n);
            for jj in 2..=n {
                let j = n - jj + 1;
                let mut dot = 0.0;
                for k in 0..(jj - 1) {
                    dot += tt(j + 1 + k, j) * b[j + k];
                }
                b[j - 1] -= dot;
                b[j - 1] /= tt(j, j);
            }
        }
        _ => {
            b[0] /= tt(1, 1);
            for j in 2..=n {
                let mut dot = 0.0;
                for k in 0..(j - 1) {
                    dot += tt(1 + k, j) * b[k];
                }
                b[j - 1] -= dot;
                b[j - 1] /= tt(j, j);
            }
        }
    }
    0
}

/// `bmv`: the product of the 2m x 2m middle matrix with `v`, for the first
/// `col` columns. `v` and `p` are 1-based. Returns the info of the solves.
fn bmv(sy: &Mat, wt: &Mat, m: usize, col: usize, v: &[f64], p: &mut [f64]) -> i64 {
    if col == 0 {
        return 0;
    }
    let colu = col;
    p[col + 1] = v[col + 1];
    for i in 2..=colu {
        let i2 = col + i;
        let mut sum = 0.0;
        for k in 1..=(i - 1) {
            sum += sy.g(i, k) * v[k] / sy.g(k, k);
        }
        p[i2] = v[i2] + sum;
    }
    let info = dtrsl(&wt.d, m, col, &mut p[(col + 1)..], 11);
    if info != 0 {
        return info;
    }
    for i in 1..=colu {
        p[i] = v[i] / sy.g(i, i).sqrt();
    }
    let info = dtrsl(&wt.d, m, col, &mut p[(col + 1)..], 1);
    if info != 0 {
        return info;
    }
    for i in 1..=colu {
        p[i] = -p[i] / sy.g(i, i).sqrt();
    }
    for i in 1..=colu {
        let mut sum = 0.0;
        for k in (i + 1)..=colu {
            sum += sy.g(k, i) * p[col + k] / sy.g(i, i);
        }
        p[i] += sum;
    }
    0
}

/// `hpsolb`: heap sort of the breakpoints `t` with the index `iorder`.
fn hpsolb(n: usize, t: &mut [f64], iorder: &mut [usize], iheap: i64) {
    if iheap == 0 {
        for k in 2..=n {
            let ddum = t[k];
            let indxin = iorder[k];
            let mut i = k;
            while i > 1 {
                let j = i / 2;
                if ddum < t[j] {
                    t[i] = t[j];
                    iorder[i] = iorder[j];
                    i = j;
                } else {
                    break;
                }
            }
            t[i] = ddum;
            iorder[i] = indxin;
        }
    }
    if n > 1 {
        let mut i = 1;
        let out = t[1];
        let indxou = iorder[1];
        let ddum = t[n];
        let indxin = iorder[n];
        loop {
            let mut j = i + i;
            if j <= n - 1 {
                if t[j + 1] < t[j] {
                    j += 1;
                }
                if t[j] < ddum {
                    t[i] = t[j];
                    iorder[i] = iorder[j];
                    i = j;
                    continue;
                }
            }
            break;
        }
        t[i] = ddum;
        iorder[i] = indxin;
        t[n] = out;
        iorder[n] = indxou;
    }
}

/// Moré and Thuente line search state (the statics of `dcsrch`).
#[derive(Default)]
struct LineSearch {
    stage: i32,
    brackt: bool,
    ginit: f64,
    gtest: f64,
    gx: f64,
    gy: f64,
    finit: f64,
    fx: f64,
    fy: f64,
    stx: f64,
    sty: f64,
    stmin: f64,
    stmax: f64,
    width: f64,
    width1: f64,
}

/// `dcstep`: safeguarded cubic and quadratic step.
#[allow(clippy::too_many_arguments)]
fn dcstep(
    stx: &mut f64,
    fx: &mut f64,
    dx: &mut f64,
    sty: &mut f64,
    fy: &mut f64,
    dy: &mut f64,
    stp: &mut f64,
    fp: f64,
    dp: f64,
    brackt: &mut bool,
    stpmin: f64,
    stpmax: f64,
) {
    let sgnd = dp * (*dx / dx.abs());
    let stpf;
    if fp > *fx {
        let theta = (*fx - fp) * 3.0 / (*stp - *stx) + *dx + dp;
        let s = cmax(cmax(theta.abs(), dx.abs()), dp.abs());
        let mut gamm = s * ((theta / s) * (theta / s) - *dx / s * (dp / s)).sqrt();
        if *stp < *stx {
            gamm = -gamm;
        }
        let p = gamm - *dx + theta;
        let q = gamm - *dx + gamm + dp;
        let r = p / q;
        let stpc = *stx + r * (*stp - *stx);
        let stpq = *stx + *dx / ((*fx - fp) / (*stp - *stx) + *dx) / 2.0 * (*stp - *stx);
        if (stpc - *stx).abs() < (stpq - *stx).abs() {
            stpf = stpc;
        } else {
            stpf = stpc + (stpq - stpc) / 2.0;
        }
        *brackt = true;
    } else if sgnd < 0.0 {
        let theta = (*fx - fp) * 3.0 / (*stp - *stx) + *dx + dp;
        let s = cmax(cmax(theta.abs(), dx.abs()), dp.abs());
        let mut gamm = s * ((theta / s) * (theta / s) - *dx / s * (dp / s)).sqrt();
        if *stp > *stx {
            gamm = -gamm;
        }
        let p = gamm - dp + theta;
        let q = gamm - dp + gamm + *dx;
        let r = p / q;
        let stpc = *stp + r * (*stx - *stp);
        let stpq = *stp + dp / (dp - *dx) * (*stx - *stp);
        if (stpc - *stp).abs() > (stpq - *stp).abs() {
            stpf = stpc;
        } else {
            stpf = stpq;
        }
        *brackt = true;
    } else if dp.abs() < dx.abs() {
        let theta = (*fx - fp) * 3.0 / (*stp - *stx) + *dx + dp;
        let s = cmax(cmax(theta.abs(), dx.abs()), dp.abs());
        let d1 = theta / s;
        let d1 = d1 * d1 - *dx / s * (dp / s);
        let mut gamm = if d1 < 0.0 { 0.0 } else { s * d1.sqrt() };
        if *stp > *stx {
            gamm = -gamm;
        }
        let p = gamm - dp + theta;
        let q = gamm + (*dx - dp) + gamm;
        let r = p / q;
        let stpc = if r < 0.0 && gamm != 0.0 {
            *stp + r * (*stx - *stp)
        } else if *stp > *stx {
            stpmax
        } else {
            stpmin
        };
        let stpq = *stp + dp / (dp - *dx) * (*stx - *stp);
        if *brackt {
            let sf = if (stpc - *stp).abs() < (stpq - *stp).abs() {
                stpc
            } else {
                stpq
            };
            let d1 = *stp + (*sty - *stp) * 0.66;
            stpf = if *stp > *stx {
                cmin(d1, sf)
            } else {
                cmax(d1, sf)
            };
        } else {
            let sf = if (stpc - *stp).abs() > (stpq - *stp).abs() {
                stpc
            } else {
                stpq
            };
            stpf = cmax(stpmin, cmin(stpmax, sf));
        }
    } else if *brackt {
        let theta = (fp - *fy) * 3.0 / (*sty - *stp) + *dy + dp;
        let s = cmax(cmax(theta.abs(), dy.abs()), dp.abs());
        let mut gamm = s * ((theta / s) * (theta / s) - *dy / s * (dp / s)).sqrt();
        if *stp > *sty {
            gamm = -gamm;
        }
        let p = gamm - dp + theta;
        let q = gamm - dp + gamm + *dy;
        let r = p / q;
        stpf = *stp + r * (*sty - *stp);
    } else if *stp > *stx {
        stpf = stpmax;
    } else {
        stpf = stpmin;
    }

    if fp > *fx {
        *sty = *stp;
        *fy = fp;
        *dy = dp;
    } else {
        if sgnd < 0.0 {
            *sty = *stx;
            *fy = *fx;
            *dy = *dx;
        }
        *stx = *stp;
        *fx = fp;
        *dx = dp;
    }
    *stp = stpf;
}

/// `dcsrch`: reverse-communication line search with the `task` string.
#[allow(clippy::too_many_arguments)]
fn dcsrch(
    ls: &mut LineSearch,
    f: f64,
    g: f64,
    stp: &mut f64,
    ftol: f64,
    gtol: f64,
    xtol: f64,
    stpmin: f64,
    stpmax: f64,
    task: &mut String,
) {
    if task.starts_with("START") {
        if *stp < stpmin {
            *task = "ERROR: STP .LT. STPMIN".into();
        }
        if *stp > stpmax {
            *task = "ERROR: STP .GT. STPMAX".into();
        }
        if g >= 0.0 {
            *task = "ERROR: INITIAL G .GE. ZERO".into();
        }
        if ftol < 0.0 {
            *task = "ERROR: FTOL .LT. ZERO".into();
        }
        if gtol < 0.0 {
            *task = "ERROR: GTOL .LT. ZERO".into();
        }
        if xtol < 0.0 {
            *task = "ERROR: XTOL .LT. ZERO".into();
        }
        if stpmin < 0.0 {
            *task = "ERROR: STPMIN .LT. ZERO".into();
        }
        if stpmax < stpmin {
            *task = "ERROR: STPMAX .LT. STPMIN".into();
        }
        if task.starts_with("ERROR") {
            return;
        }
        ls.brackt = false;
        ls.stage = 1;
        ls.finit = f;
        ls.ginit = g;
        ls.gtest = ftol * ls.ginit;
        ls.width = stpmax - stpmin;
        ls.width1 = ls.width / 0.5;
        ls.stx = 0.0;
        ls.fx = ls.finit;
        ls.gx = ls.ginit;
        ls.sty = 0.0;
        ls.fy = ls.finit;
        ls.gy = ls.ginit;
        ls.stmin = 0.0;
        ls.stmax = *stp + *stp * 4.0;
        *task = "FG".into();
        return;
    }

    let ftest = ls.finit + *stp * ls.gtest;
    if ls.stage == 1 && f <= ftest && g >= 0.0 {
        ls.stage = 2;
    }
    if ls.brackt && (*stp <= ls.stmin || *stp >= ls.stmax) {
        *task = "WARNING: ROUNDING ERRORS PREVENT PROGRESS".into();
    }
    if ls.brackt && ls.stmax - ls.stmin <= xtol * ls.stmax {
        *task = "WARNING: XTOL TEST SATISFIED".into();
    }
    if *stp == stpmax && f <= ftest && g <= ls.gtest {
        *task = "WARNING: STP = STPMAX".into();
    }
    if *stp == stpmin && (f > ftest || g >= ls.gtest) {
        *task = "WARNING: STP = STPMIN".into();
    }
    if f <= ftest && g.abs() <= gtol * (-ls.ginit) {
        *task = "CONVERGENCE".into();
    }
    if task.starts_with("WARN") || task.starts_with("CONV") {
        return;
    }

    if ls.stage == 1 && f <= ls.fx && f > ftest {
        let fm = f - *stp * ls.gtest;
        let mut fxm = ls.fx - ls.stx * ls.gtest;
        let mut fym = ls.fy - ls.sty * ls.gtest;
        let gm = g - ls.gtest;
        let mut gxm = ls.gx - ls.gtest;
        let mut gym = ls.gy - ls.gtest;
        let (stmin, stmax) = (ls.stmin, ls.stmax);
        dcstep(
            &mut ls.stx,
            &mut fxm,
            &mut gxm,
            &mut ls.sty,
            &mut fym,
            &mut gym,
            stp,
            fm,
            gm,
            &mut ls.brackt,
            stmin,
            stmax,
        );
        ls.fx = fxm + ls.stx * ls.gtest;
        ls.fy = fym + ls.sty * ls.gtest;
        ls.gx = gxm + ls.gtest;
        ls.gy = gym + ls.gtest;
    } else {
        let (stmin, stmax) = (ls.stmin, ls.stmax);
        dcstep(
            &mut ls.stx,
            &mut ls.fx,
            &mut ls.gx,
            &mut ls.sty,
            &mut ls.fy,
            &mut ls.gy,
            stp,
            f,
            g,
            &mut ls.brackt,
            stmin,
            stmax,
        );
    }

    if ls.brackt {
        if (ls.sty - ls.stx).abs() >= ls.width1 * 0.66 {
            *stp = ls.stx + (ls.sty - ls.stx) * 0.5;
        }
        ls.width1 = ls.width;
        ls.width = (ls.sty - ls.stx).abs();
    }
    if ls.brackt {
        ls.stmin = cmin(ls.stx, ls.sty);
        ls.stmax = cmax(ls.stx, ls.sty);
    } else {
        ls.stmin = *stp + (*stp - ls.stx) * 1.1;
        ls.stmax = *stp + (*stp - ls.stx) * 4.0;
    }
    if *stp < stpmin {
        *stp = stpmin;
    }
    if *stp > stpmax {
        *stp = stpmax;
    }
    if (ls.brackt && (*stp <= ls.stmin || *stp >= ls.stmax))
        || (ls.brackt && (ls.stmax - ls.stmin <= xtol * ls.stmax))
    {
        *stp = ls.stx;
    }
    *task = "FG".into();
}

#[derive(Clone, Copy)]
enum Lbl {
    L111,
    L222,
    L333,
    L444,
    L555,
    L666,
    L777,
    L888,
}

/// The L-BFGS-B state. The fields hold the statics that `mainlb` keeps
/// between calls, which R's driver relies on through `setulb`.
pub struct Lbfgsb {
    n: usize,
    m: usize,
    factr: f64,
    pgtol: f64,
    x: Vec<f64>,
    l: Vec<f64>,
    u: Vec<f64>,
    nbd: Vec<i32>,
    g: Vec<f64>,
    f: f64,
    task: String,
    csave: String,
    ws: Mat,
    wy: Mat,
    sy: Mat,
    ss: Mat,
    wt: Mat,
    wn: Mat,
    snd: Mat,
    z: Vec<f64>,
    r: Vec<f64>,
    d: Vec<f64>,
    t: Vec<f64>,
    wp: Vec<f64>,
    wc: Vec<f64>,
    wbp: Vec<f64>,
    wv: Vec<f64>,
    indx: Vec<usize>,
    iwhere: Vec<i32>,
    indx2: Vec<usize>,
    ls: LineSearch,
    prjctd: bool,
    cnstnd: bool,
    boxed: bool,
    updatd: bool,
    nintol: i64,
    iback: i64,
    nskip: i64,
    head: usize,
    col: usize,
    itail: usize,
    iter: i64,
    iupdat: usize,
    nint: i64,
    nfgv: i64,
    info: i64,
    ifun: i64,
    iword: i64,
    nfree: usize,
    nact: i64,
    ileave: usize,
    nenter: usize,
    theta: f64,
    fold: f64,
    tol: f64,
    dnorm: f64,
    epsmch: f64,
    gd: f64,
    stpmx: f64,
    sbgnrm: f64,
    stp: f64,
    gdold: f64,
    dtd: f64,
    xstep: f64,
}

impl Lbfgsb {
    /// `lower`, `upper` and `nbd` are 0-based, as the caller passes them.
    fn new(
        x0: &[f64],
        lower: &[f64],
        upper: &[f64],
        nbd: &[i32],
        m: usize,
        factr: f64,
        pgtol: f64,
    ) -> Lbfgsb {
        let n = x0.len();
        let one = |v: &[f64]| {
            let mut out = vec![0.0; n + 1];
            out[1..].copy_from_slice(&v[..n]);
            out
        };
        let mut nbd1 = vec![0i32; n + 1];
        nbd1[1..].copy_from_slice(&nbd[..n]);
        Lbfgsb {
            n,
            m,
            factr,
            pgtol,
            x: one(x0),
            l: one(lower),
            u: one(upper),
            nbd: nbd1,
            g: vec![0.0; n + 1],
            f: 0.0,
            task: "START".into(),
            csave: String::new(),
            ws: Mat::new(n, m),
            wy: Mat::new(n, m),
            sy: Mat::new(m, m),
            ss: Mat::new(m, m),
            wt: Mat::new(m, m),
            wn: Mat::new(2 * m, 2 * m),
            snd: Mat::new(2 * m, 2 * m),
            z: vec![0.0; n + 1],
            r: vec![0.0; n + 1],
            d: vec![0.0; n + 1],
            t: vec![0.0; n + 1],
            wp: vec![0.0; 2 * m + 1],
            wc: vec![0.0; 2 * m + 1],
            wbp: vec![0.0; 2 * m + 1],
            wv: vec![0.0; 2 * m + 1],
            indx: vec![0; n + 1],
            iwhere: vec![0; n + 1],
            indx2: vec![0; n + 1],
            ls: LineSearch::default(),
            prjctd: false,
            cnstnd: false,
            boxed: false,
            updatd: false,
            nintol: 0,
            iback: 0,
            nskip: 0,
            head: 1,
            col: 0,
            itail: 0,
            iter: 0,
            iupdat: 0,
            nint: 0,
            nfgv: 0,
            info: 0,
            ifun: 0,
            iword: 0,
            nfree: n,
            nact: 0,
            ileave: 0,
            nenter: 0,
            theta: 1.0,
            fold: 0.0,
            tol: 0.0,
            dnorm: 0.0,
            epsmch: f64::EPSILON,
            gd: 0.0,
            stpmx: 0.0,
            sbgnrm: 0.0,
            stp: 0.0,
            gdold: 0.0,
            dtd: 0.0,
            xstep: 0.0,
        }
    }

    /// `setulb`: one reverse-communication call. `csave` is local to each
    /// call, as in the C.
    fn setulb(&mut self) {
        self.csave.clear();
        self.mainlb();
    }

    /// The `info`-triggered restart of the limited memory matrices.
    fn reset_memory(&mut self) {
        self.info = 0;
        self.col = 0;
        self.head = 1;
        self.theta = 1.0;
        self.iupdat = 0;
        self.updatd = false;
    }

    fn errclb(&mut self) {
        let n = self.n;
        if n == 0 {
            self.task = "ERROR: N .LE. 0".into();
        }
        if self.m == 0 {
            self.task = "ERROR: M .LE. 0".into();
        }
        if self.factr < 0.0 {
            self.task = "ERROR: FACTR .LT. 0".into();
        }
        for i in 1..=n {
            if self.nbd[i] < 0 || self.nbd[i] > 3 {
                self.task = "ERROR: INVALID NBD".into();
                self.info = -6;
            }
            if self.nbd[i] == 2 && self.l[i] > self.u[i] {
                self.task = "ERROR: NO FEASIBLE SOLUTION".into();
                self.info = -7;
            }
        }
    }

    /// `active`: projects x into the box and sets iwhere.
    fn active(&mut self) {
        let n = self.n;
        self.prjctd = false;
        self.cnstnd = false;
        self.boxed = true;
        for i in 1..=n {
            if self.nbd[i] > 0 {
                if self.nbd[i] <= 2 && self.x[i] <= self.l[i] {
                    if self.x[i] < self.l[i] {
                        self.prjctd = true;
                        self.x[i] = self.l[i];
                    }
                } else if self.nbd[i] >= 2 && self.x[i] >= self.u[i] {
                    if self.x[i] > self.u[i] {
                        self.prjctd = true;
                        self.x[i] = self.u[i];
                    }
                }
            }
        }
        for i in 1..=n {
            if self.nbd[i] != 2 {
                self.boxed = false;
            }
            if self.nbd[i] == 0 {
                self.iwhere[i] = -1;
            } else {
                self.cnstnd = true;
                if self.nbd[i] == 2 && self.u[i] - self.l[i] <= 0.0 {
                    self.iwhere[i] = 3;
                } else {
                    self.iwhere[i] = 0;
                }
            }
        }
    }

    /// `projgr`: the infinity norm of the projected gradient.
    fn projgr(&mut self) {
        self.sbgnrm = 0.0;
        for i in 1..=self.n {
            let mut gi = self.g[i];
            if self.nbd[i] != 0 {
                if gi < 0.0 {
                    if self.nbd[i] >= 2 {
                        let d1 = self.x[i] - self.u[i];
                        if gi < d1 {
                            gi = d1;
                        }
                    }
                } else if self.nbd[i] <= 2 {
                    let d1 = self.x[i] - self.l[i];
                    if gi > d1 {
                        gi = d1;
                    }
                }
            }
            let a = gi.abs();
            if self.sbgnrm < a {
                self.sbgnrm = a;
            }
        }
    }

    /// `cauchy`: the generalized Cauchy point, in z.
    fn cauchy(&mut self) {
        let n = self.n;
        let m = self.m;
        if self.sbgnrm <= 0.0 {
            for i in 1..=n {
                self.z[i] = self.x[i];
            }
            return;
        }
        let mut bnded = true;
        let mut nfree = n + 1;
        let mut nbreak: usize = 0;
        let mut ibkmin: usize = 0;
        let mut bkmin = 0.0;
        let col = self.col;
        let col2 = col * 2;
        let theta = self.theta;
        let mut f1 = 0.0;
        for i in 1..=col2 {
            self.wp[i] = 0.0;
        }
        let mut tl = 0.0;
        let mut tu = 0.0;
        for i in 1..=n {
            let neggi = -self.g[i];
            if self.iwhere[i] != 3 && self.iwhere[i] != -1 {
                if self.nbd[i] <= 2 {
                    tl = self.x[i] - self.l[i];
                }
                if self.nbd[i] >= 2 {
                    tu = self.u[i] - self.x[i];
                }
                let xlower = self.nbd[i] <= 2 && tl <= 0.0;
                let xupper = self.nbd[i] >= 2 && tu <= 0.0;
                self.iwhere[i] = 0;
                if xlower {
                    if neggi <= 0.0 {
                        self.iwhere[i] = 1;
                    }
                } else if xupper {
                    if neggi >= 0.0 {
                        self.iwhere[i] = 2;
                    }
                } else if neggi.abs() <= 0.0 {
                    self.iwhere[i] = -3;
                }
            }
            let mut pointr = self.head;
            if self.iwhere[i] != 0 && self.iwhere[i] != -1 {
                self.d[i] = 0.0;
            } else {
                self.d[i] = neggi;
                f1 -= neggi * neggi;
                for j in 1..=col {
                    self.wp[j] += self.wy.g(i, pointr) * neggi;
                    self.wp[col + j] += self.ws.g(i, pointr) * neggi;
                    pointr = pointr % m + 1;
                }
                if self.nbd[i] <= 2 && self.nbd[i] != 0 && neggi < 0.0 {
                    nbreak += 1;
                    self.indx2[nbreak] = i;
                    self.t[nbreak] = tl / (-neggi);
                    if nbreak == 1 || self.t[nbreak] < bkmin {
                        bkmin = self.t[nbreak];
                        ibkmin = nbreak;
                    }
                } else if self.nbd[i] >= 2 && neggi > 0.0 {
                    nbreak += 1;
                    self.indx2[nbreak] = i;
                    self.t[nbreak] = tu / neggi;
                    if nbreak == 1 || self.t[nbreak] < bkmin {
                        bkmin = self.t[nbreak];
                        ibkmin = nbreak;
                    }
                } else {
                    nfree -= 1;
                    self.indx2[nfree] = i;
                    if neggi.abs() > 0.0 {
                        bnded = false;
                    }
                }
            }
        }
        if theta != 1.0 {
            for j in (col + 1)..=col2 {
                self.wp[j] *= theta;
            }
        }
        for i in 1..=n {
            self.z[i] = self.x[i];
        }
        if nbreak == 0 && nfree == n + 1 {
            return;
        }
        for j in 1..=col2 {
            self.wc[j] = 0.0;
        }
        let mut f2 = -theta * f1;
        let f2_org = f2;
        if col > 0 {
            let info = bmv(&self.sy, &self.wt, m, col, &self.wp, &mut self.wv);
            self.info = info;
            if info != 0 {
                return;
            }
            let mut dot = 0.0;
            for j in 1..=col2 {
                dot += self.wv[j] * self.wp[j];
            }
            f2 -= dot;
        }
        let mut dtm = -f1 / f2;
        let mut tsum = 0.0;
        self.nint = 1;
        let mut skip_to_l999 = false;
        if nbreak > 0 {
            let mut nleft = nbreak;
            let mut iter: i64 = 1;
            let mut tj = 0.0;
            loop {
                let tj0 = tj;
                let ibp;
                if iter == 1 {
                    tj = bkmin;
                    ibp = self.indx2[ibkmin];
                } else {
                    if iter == 2 && ibkmin != nbreak {
                        self.t[ibkmin] = self.t[nbreak];
                        self.indx2[ibkmin] = self.indx2[nbreak];
                    }
                    hpsolb(nleft, &mut self.t, &mut self.indx2, iter - 2);
                    tj = self.t[nleft];
                    ibp = self.indx2[nleft];
                }
                let dt = tj - tj0;
                if dtm < dt {
                    break;
                }
                tsum += dt;
                nleft -= 1;
                iter += 1;
                let dibp = self.d[ibp];
                self.d[ibp] = 0.0;
                let zibp;
                if dibp > 0.0 {
                    zibp = self.u[ibp] - self.x[ibp];
                    self.z[ibp] = self.u[ibp];
                    self.iwhere[ibp] = 2;
                } else {
                    zibp = self.l[ibp] - self.x[ibp];
                    self.z[ibp] = self.l[ibp];
                    self.iwhere[ibp] = 1;
                }
                if nleft == 0 && nbreak == n {
                    dtm = dt;
                    skip_to_l999 = true;
                    break;
                }
                self.nint += 1;
                let dibp2 = dibp * dibp;
                f1 += dt * f2 + dibp2 - theta * dibp * zibp;
                f2 -= theta * dibp2;
                if col > 0 {
                    for j in 1..=col2 {
                        self.wc[j] += dt * self.wp[j];
                    }
                    let mut pointr = self.head;
                    for j in 1..=col {
                        self.wbp[j] = self.wy.g(ibp, pointr);
                        self.wbp[col + j] = theta * self.ws.g(ibp, pointr);
                        pointr = pointr % m + 1;
                    }
                    let info = bmv(&self.sy, &self.wt, m, col, &self.wbp, &mut self.wv);
                    self.info = info;
                    if info != 0 {
                        return;
                    }
                    let mut wmc = 0.0;
                    let mut wmp = 0.0;
                    let mut wmw = 0.0;
                    for j in 1..=col2 {
                        wmc += self.wc[j] * self.wv[j];
                    }
                    for j in 1..=col2 {
                        wmp += self.wp[j] * self.wv[j];
                    }
                    for j in 1..=col2 {
                        wmw += self.wbp[j] * self.wv[j];
                    }
                    let neg = -dibp;
                    for j in 1..=col2 {
                        self.wp[j] += neg * self.wbp[j];
                    }
                    f1 += dibp * wmc;
                    f2 += 2.0 * dibp * wmp - dibp2 * wmw;
                }
                let f2min = self.epsmch * f2_org;
                if f2 < f2min {
                    f2 = f2min;
                }
                if nleft > 0 {
                    dtm = -f1 / f2;
                    continue;
                } else if bnded {
                    f1 = 0.0;
                    f2 = 0.0;
                    dtm = 0.0;
                } else {
                    dtm = -f1 / f2;
                }
                break;
            }
        }
        if !skip_to_l999 {
            if dtm <= 0.0 {
                dtm = 0.0;
            }
            tsum += dtm;
            for i in 1..=n {
                self.z[i] += tsum * self.d[i];
            }
        }
        if col > 0 {
            for j in 1..=col2 {
                self.wc[j] += dtm * self.wp[j];
            }
        }
    }

    /// `cmprlb`: the reduced gradient r = -Z'(B(xcp - x) + g).
    fn cmprlb(&mut self) {
        let n = self.n;
        let m = self.m;
        let col = self.col;
        if !self.cnstnd && col > 0 {
            for i in 1..=n {
                self.r[i] = -self.g[i];
            }
        } else {
            let n_f = self.nfree;
            let theta = self.theta;
            for i in 1..=n_f {
                let k = self.indx[i];
                self.r[i] = -theta * (self.z[k] - self.x[k]) - self.g[k];
            }
            let info = bmv(&self.sy, &self.wt, m, col, &self.wc, &mut self.wp);
            self.info = info;
            if info != 0 {
                self.info = -8;
                return;
            }
            let mut pointr = self.head;
            for j in 1..=col {
                let a1 = self.wp[j];
                let a2 = theta * self.wp[col + j];
                for i in 1..=n_f {
                    let k = self.indx[i];
                    self.r[i] += self.wy.g(k, pointr) * a1 + self.ws.g(k, pointr) * a2;
                }
                pointr = pointr % m + 1;
            }
        }
    }

    /// `subsm`: the subspace minimization, with the step cut at the bounds.
    fn subsm(&mut self) {
        let m = self.m;
        let col = self.col;
        let theta = self.theta;
        let ns = self.nfree;
        if ns == 0 {
            return;
        }
        let mut pointr = self.head;
        for i in 1..=col {
            let mut temp1 = 0.0;
            let mut temp2 = 0.0;
            for j in 1..=ns {
                let k = self.indx[j];
                temp1 += self.wy.g(k, pointr) * self.r[j];
                temp2 += self.ws.g(k, pointr) * self.r[j];
            }
            self.wp[i] = temp1;
            self.wp[col + i] = theta * temp2;
            pointr = pointr % m + 1;
        }
        let m2 = 2 * m;
        let col2 = 2 * col;
        let info = dtrsl(&self.wn.d, m2, col2, &mut self.wp[1..], 11);
        self.info = info;
        if info != 0 {
            return;
        }
        for i in 1..=col {
            self.wp[i] = -self.wp[i];
        }
        let info = dtrsl(&self.wn.d, m2, col2, &mut self.wp[1..], 1);
        self.info = info;
        if info != 0 {
            return;
        }
        let mut pointr = self.head;
        for jy in 1..=col {
            let js = col + jy;
            for i in 1..=ns {
                let k = self.indx[i];
                self.r[i] += self.wy.g(k, pointr) * self.wp[jy] / theta
                    + self.ws.g(k, pointr) * self.wp[js];
            }
            pointr = pointr % m + 1;
        }
        for i in 1..=ns {
            self.r[i] /= theta;
        }
        let mut alpha = 1.0;
        let mut temp1 = alpha;
        let mut ibd = 0usize;
        for i in 1..=ns {
            let k = self.indx[i];
            let dk = self.r[i];
            if self.nbd[k] != 0 {
                if dk < 0.0 && self.nbd[k] <= 2 {
                    let temp2 = self.l[k] - self.z[k];
                    if temp2 >= 0.0 {
                        temp1 = 0.0;
                    } else if dk * alpha < temp2 {
                        temp1 = temp2 / dk;
                    }
                } else if dk > 0.0 && self.nbd[k] >= 2 {
                    let temp2 = self.u[k] - self.z[k];
                    if temp2 <= 0.0 {
                        temp1 = 0.0;
                    } else if dk * alpha > temp2 {
                        temp1 = temp2 / dk;
                    }
                }
                if temp1 < alpha {
                    alpha = temp1;
                    ibd = i;
                }
            }
        }
        if alpha < 1.0 {
            let dk = self.r[ibd];
            let k = self.indx[ibd];
            if dk > 0.0 {
                self.z[k] = self.u[k];
                self.r[ibd] = 0.0;
            } else if dk < 0.0 {
                self.z[k] = self.l[k];
                self.r[ibd] = 0.0;
            }
        }
        for i in 1..=ns {
            let k = self.indx[i];
            self.z[k] += alpha * self.r[i];
        }
        self.iword = if alpha < 1.0 { 1 } else { 0 };
    }

    /// `freev`: the free and active variables at the Cauchy point.
    fn freev(&mut self, wrk: &mut bool) {
        let n = self.n;
        self.nenter = 0;
        self.ileave = n + 1;
        if self.iter > 0 && self.cnstnd {
            for i in 1..=self.nfree {
                let k = self.indx[i];
                if self.iwhere[k] > 0 {
                    self.ileave -= 1;
                    let il = self.ileave;
                    self.indx2[il] = k;
                }
            }
            for i in (self.nfree + 1)..=n {
                let k = self.indx[i];
                if self.iwhere[k] <= 0 {
                    self.nenter += 1;
                    let ne = self.nenter;
                    self.indx2[ne] = k;
                }
            }
        }
        *wrk = self.ileave < n + 1 || self.nenter > 0 || self.updatd;
        self.nfree = 0;
        let mut iact = n + 1;
        for i in 1..=n {
            if self.iwhere[i] <= 0 {
                self.nfree += 1;
                let nf = self.nfree;
                self.indx[nf] = i;
            } else {
                iact -= 1;
                self.indx[iact] = i;
            }
        }
    }

    /// `formk`: the middle matrix of the subspace problem (sets info).
    fn formk(&mut self) {
        let n = self.n;
        let m = self.m;
        let nsub = self.nfree;
        let nenter = self.nenter;
        let ileave = self.ileave;
        let col = self.col;
        let head = self.head;
        let theta = self.theta;
        let upcl;
        if self.updatd {
            if self.iupdat > m {
                for jy in 1..m {
                    let js = m + jy;
                    let i2 = m - jy;
                    for k in 0..i2 {
                        let v = self.snd.g(jy + 1 + k, jy + 1);
                        self.snd.s(jy + k, jy, v);
                    }
                    for k in 0..i2 {
                        let v = self.snd.g(js + 1 + k, js + 1);
                        self.snd.s(js + k, js, v);
                    }
                    for k in 0..(m - 1) {
                        let v = self.snd.g(m + 2 + k, jy + 1);
                        self.snd.s(m + 1 + k, jy, v);
                    }
                }
            }
            let pbegin = 1;
            let pend = nsub;
            let dbegin = nsub + 1;
            let dend = n;
            let mut ipntr = head + col - 1;
            if ipntr > m {
                ipntr -= m;
            }
            let mut jpntr = head;
            for jy in 1..=col {
                let js = m + jy;
                let mut temp1 = 0.0;
                let mut temp2 = 0.0;
                let mut temp3 = 0.0;
                for k in pbegin..=pend {
                    let k1 = self.indx[k];
                    temp1 += self.wy.g(k1, ipntr) * self.wy.g(k1, jpntr);
                }
                for k in dbegin..=dend {
                    let k1 = self.indx[k];
                    temp2 += self.ws.g(k1, ipntr) * self.ws.g(k1, jpntr);
                    temp3 += self.ws.g(k1, ipntr) * self.wy.g(k1, jpntr);
                }
                self.snd.s(col, jy, temp1);
                self.snd.s(m + col, js, temp2);
                self.snd.s(m + col, jy, temp3);
                jpntr = jpntr % m + 1;
            }
            let jy = col;
            let mut jpntr = head + col - 1;
            if jpntr > m {
                jpntr -= m;
            }
            let mut ipntr = head;
            for i in 1..=col {
                let is = m + i;
                let mut temp3 = 0.0;
                for k in pbegin..=pend {
                    let k1 = self.indx[k];
                    temp3 += self.ws.g(k1, ipntr) * self.wy.g(k1, jpntr);
                }
                ipntr = ipntr % m + 1;
                self.snd.s(is, jy, temp3);
            }
            upcl = col - 1;
        } else {
            upcl = col;
        }

        let mut ipntr = head;
        for iy in 1..=upcl {
            let is = m + iy;
            let mut jpntr = head;
            for jy in 1..=iy {
                let js = m + jy;
                let mut temp1 = 0.0;
                let mut temp2 = 0.0;
                let mut temp3 = 0.0;
                let mut temp4 = 0.0;
                for k in 1..=nenter {
                    let k1 = self.indx2[k];
                    temp1 += self.wy.g(k1, ipntr) * self.wy.g(k1, jpntr);
                    temp2 += self.ws.g(k1, ipntr) * self.ws.g(k1, jpntr);
                }
                for k in ileave..=n {
                    let k1 = self.indx2[k];
                    temp3 += self.wy.g(k1, ipntr) * self.wy.g(k1, jpntr);
                    temp4 += self.ws.g(k1, ipntr) * self.ws.g(k1, jpntr);
                }
                let a = self.snd.g(iy, jy) + temp1 - temp3;
                self.snd.s(iy, jy, a);
                let b = self.snd.g(is, js) - temp2 + temp4;
                self.snd.s(is, js, b);
                jpntr = jpntr % m + 1;
            }
            ipntr = ipntr % m + 1;
        }

        let mut ipntr = head;
        for is in (m + 1)..=(m + upcl) {
            let mut jpntr = head;
            for jy in 1..=upcl {
                let mut temp1 = 0.0;
                let mut temp3 = 0.0;
                for k in 1..=nenter {
                    let k1 = self.indx2[k];
                    temp1 += self.ws.g(k1, ipntr) * self.wy.g(k1, jpntr);
                }
                for k in ileave..=n {
                    let k1 = self.indx2[k];
                    temp3 += self.ws.g(k1, ipntr) * self.wy.g(k1, jpntr);
                }
                let cur = self.snd.g(is, jy);
                if is <= jy + m {
                    self.snd.s(is, jy, cur + (temp1 - temp3));
                } else {
                    self.snd.s(is, jy, cur + (-temp1 + temp3));
                }
                jpntr = jpntr % m + 1;
            }
            ipntr = ipntr % m + 1;
        }

        let m2 = 2 * m;
        for iy in 1..=col {
            let is = col + iy;
            let is1 = m + iy;
            for jy in 1..=iy {
                let js = col + jy;
                let js1 = m + jy;
                let a = self.snd.g(iy, jy) / theta;
                self.wn.s(jy, iy, a);
                let b = self.snd.g(is1, js1) * theta;
                self.wn.s(js, is, b);
            }
            for jy in 1..iy {
                let v = -self.snd.g(is1, jy);
                self.wn.s(jy, is, v);
            }
            for jy in iy..=col {
                let v = self.snd.g(is1, jy);
                self.wn.s(jy, is, v);
            }
            let cur = self.wn.g(iy, iy);
            self.wn.s(iy, iy, cur + self.sy.g(iy, iy));
        }

        let info = dpofa(&mut self.wn.d, m2, col);
        if info != 0 {
            self.info = -1;
            return;
        }
        let col2 = 2 * col;
        for js in (col + 1)..=col2 {
            let mut b: Vec<f64> = (1..=col).map(|i| self.wn.g(i, js)).collect();
            let _ = dtrsl(&self.wn.d, m2, col, &mut b, 11);
            for i in 1..=col {
                self.wn.s(i, js, b[i - 1]);
            }
        }
        for is in (col + 1)..=col2 {
            for js in is..=col2 {
                let mut dot = 0.0;
                for k in 1..=col {
                    dot += self.wn.g(k, is) * self.wn.g(k, js);
                }
                let cur = self.wn.g(is, js);
                self.wn.s(is, js, cur + dot);
            }
        }
        let off = self.wn.ix(col + 1, col + 1);
        let info = dpofa(&mut self.wn.d[off..], m2, col);
        if info != 0 {
            self.info = -2;
            return;
        }
        self.info = 0;
    }

    /// `formt`: the middle matrix T of the BFGS update (sets info).
    fn formt(&mut self) {
        let m = self.m;
        let col = self.col;
        let theta = self.theta;
        for j in 1..=col {
            let v = theta * self.ss.g(1, j);
            self.wt.s(1, j, v);
        }
        for i in 2..=col {
            for j in i..=col {
                let k1 = std::cmp::min(i, j) - 1;
                let mut ddum = 0.0;
                for k in 1..=k1 {
                    ddum += self.sy.g(i, k) * self.sy.g(j, k) / self.sy.g(k, k);
                }
                let v = ddum + theta * self.ss.g(i, j);
                self.wt.s(i, j, v);
            }
        }
        let info = dpofa(&mut self.wt.d, m, col);
        self.info = if info != 0 { -3 } else { 0 };
    }

    /// `matupd`: adds the newest correction pair to the limited memory.
    fn matupd(&mut self, rr: f64, dr: f64, stp: f64, dtd: f64) {
        let n = self.n;
        let m = self.m;
        if self.iupdat <= m {
            self.col = self.iupdat;
            self.itail = (self.head + self.iupdat - 2) % m + 1;
        } else {
            self.itail = self.itail % m + 1;
            self.head = self.head % m + 1;
        }
        let itail = self.itail;
        for i in 1..=n {
            self.ws.s(i, itail, self.d[i]);
        }
        for i in 1..=n {
            self.wy.s(i, itail, self.r[i]);
        }
        self.theta = rr / dr;
        if self.iupdat > m {
            for j in 1..self.col {
                for i in 0..j {
                    let v = self.ss.g(2 + i, j + 1);
                    self.ss.s(1 + i, j, v);
                }
                let i2 = self.col - j;
                for k in 0..i2 {
                    let v = self.sy.g(j + 1 + k, j + 1);
                    self.sy.s(j + k, j, v);
                }
            }
        }
        let col = self.col;
        let mut pointr = self.head;
        for j in 1..col {
            let mut s1 = 0.0;
            for i in 1..=n {
                s1 += self.d[i] * self.wy.g(i, pointr);
            }
            self.sy.s(col, j, s1);
            let mut s2 = 0.0;
            for i in 1..=n {
                s2 += self.ws.g(i, pointr) * self.d[i];
            }
            self.ss.s(j, col, s2);
            pointr = pointr % m + 1;
        }
        if stp == 1.0 {
            self.ss.s(col, col, dtd);
        } else {
            self.ss.s(col, col, stp * stp * dtd);
        }
        self.sy.s(col, col, dr);
    }

    /// `lnsrlb`: the line search, with the step in stp and x set to the trial point.
    fn lnsrlb(&mut self) {
        let n = self.n;
        if !self.task.starts_with("FG_LN") {
            let mut dtd = 0.0;
            for i in 1..=n {
                dtd += self.d[i] * self.d[i];
            }
            self.dtd = dtd;
            self.dnorm = dtd.sqrt();
            self.stpmx = 1e10;
            if self.cnstnd {
                if self.iter == 0 {
                    self.stpmx = 1.0;
                } else {
                    for i in 1..=n {
                        let a1 = self.d[i];
                        if self.nbd[i] != 0 {
                            if a1 < 0.0 && self.nbd[i] <= 2 {
                                let a2 = self.l[i] - self.x[i];
                                if a2 >= 0.0 {
                                    self.stpmx = 0.0;
                                } else if a1 * self.stpmx < a2 {
                                    self.stpmx = a2 / a1;
                                }
                            } else if a1 > 0.0 && self.nbd[i] >= 2 {
                                let a2 = self.u[i] - self.x[i];
                                if a2 <= 0.0 {
                                    self.stpmx = 0.0;
                                } else if a1 * self.stpmx > a2 {
                                    self.stpmx = a2 / a1;
                                }
                            }
                        }
                    }
                }
            }
            if self.iter == 0 && !self.boxed {
                let d1 = 1.0 / self.dnorm;
                self.stp = cmin(d1, self.stpmx);
            } else {
                self.stp = 1.0;
            }
            for i in 1..=n {
                self.t[i] = self.x[i];
            }
            for i in 1..=n {
                self.r[i] = self.g[i];
            }
            self.fold = self.f;
            self.ifun = 0;
            self.iback = 0;
            self.csave = "START".into();
        }
        // L556
        let mut gd = 0.0;
        for i in 1..=n {
            gd += self.g[i] * self.d[i];
        }
        self.gd = gd;
        if self.ifun == 0 {
            self.gdold = self.gd;
            if self.gd >= 0.0 {
                self.info = -4;
                return;
            }
        }
        let mut csave = std::mem::take(&mut self.csave);
        let mut stp = self.stp;
        dcsrch(
            &mut self.ls,
            self.f,
            self.gd,
            &mut stp,
            FTOL,
            GTOL,
            XTOL,
            STPMIN,
            self.stpmx,
            &mut csave,
        );
        self.stp = stp;
        self.csave = csave;
        self.xstep = self.stp * self.dnorm;
        if !(self.csave.starts_with("CONV") || self.csave.starts_with("WARN")) {
            self.task = "FG_LNSRCH".into();
            self.ifun += 1;
            self.nfgv += 1;
            self.iback = self.ifun - 1;
            if self.stp == 1.0 {
                for i in 1..=n {
                    self.x[i] = self.z[i];
                }
            } else {
                for i in 1..=n {
                    self.x[i] = self.stp * self.d[i] + self.t[i];
                }
            }
        } else {
            self.task = "NEW_X".into();
        }
    }

    /// `mainlb`: the L-BFGS-B iteration, as a state machine over the C labels.
    fn mainlb(&mut self) {
        let n = self.n;
        let mut wrk = false;
        let mut lbl;
        if self.task.starts_with("START") {
            self.epsmch = f64::EPSILON;
            self.fold = 0.0;
            self.dnorm = 0.0;
            self.gd = 0.0;
            self.sbgnrm = 0.0;
            self.stp = 0.0;
            self.xstep = 0.0;
            self.stpmx = 0.0;
            self.gdold = 0.0;
            self.dtd = 0.0;
            self.col = 0;
            self.head = 1;
            self.theta = 1.0;
            self.iupdat = 0;
            self.updatd = false;
            self.iback = 0;
            self.itail = 0;
            self.ifun = 0;
            self.iword = 0;
            self.nact = 0;
            self.ileave = 0;
            self.nenter = 0;
            self.iter = 0;
            self.nfgv = 0;
            self.nint = 0;
            self.nintol = 0;
            self.nskip = 0;
            self.nfree = n;
            self.tol = self.factr * self.epsmch;
            self.info = 0;
            self.errclb();
            if self.task.starts_with("ERROR") {
                return;
            }
            self.active();
            self.task = "FG_START".into();
            return;
        } else if self.task.starts_with("FG_LN") {
            lbl = Lbl::L666;
        } else if self.task.starts_with("NEW_X") {
            lbl = Lbl::L777;
        } else if self.task.starts_with("FG_ST") {
            lbl = Lbl::L111;
        } else if self.task.starts_with("STOP") {
            if self.task.get(6..).is_some_and(|s| s.starts_with("CPU")) {
                for i in 1..=n {
                    self.x[i] = self.t[i];
                }
                for i in 1..=n {
                    self.g[i] = self.r[i];
                }
                self.f = self.fold;
            }
            return;
        } else {
            self.task = "FG_START".into();
            return;
        }

        loop {
            match lbl {
                Lbl::L111 => {
                    self.nfgv = 1;
                    self.projgr();
                    if self.sbgnrm <= self.pgtol {
                        self.task = CONV_PGTOL.into();
                        return;
                    }
                    lbl = Lbl::L222;
                }
                Lbl::L222 => {
                    self.iword = -1;
                    if !self.cnstnd && self.col > 0 {
                        for i in 1..=n {
                            self.z[i] = self.x[i];
                        }
                        wrk = self.updatd;
                        self.nint = 0;
                        lbl = Lbl::L333;
                    } else {
                        self.cauchy();
                        if self.info != 0 {
                            self.reset_memory();
                            lbl = Lbl::L222;
                        } else {
                            self.nintol += self.nint;
                            self.freev(&mut wrk);
                            self.nact = (n - self.nfree) as i64;
                            lbl = Lbl::L333;
                        }
                    }
                }
                Lbl::L333 => {
                    if self.nfree == 0 || self.col == 0 {
                        lbl = Lbl::L555;
                    } else {
                        if wrk {
                            self.formk();
                        }
                        if self.info != 0 {
                            self.reset_memory();
                            lbl = Lbl::L222;
                        } else {
                            self.cmprlb();
                            if self.info != 0 {
                                lbl = Lbl::L444;
                            } else {
                                self.subsm();
                                lbl = Lbl::L444;
                            }
                        }
                    }
                }
                Lbl::L444 => {
                    if self.info != 0 {
                        self.reset_memory();
                        lbl = Lbl::L222;
                    } else {
                        lbl = Lbl::L555;
                    }
                }
                Lbl::L555 => {
                    for i in 1..=n {
                        self.d[i] = self.z[i] - self.x[i];
                    }
                    lbl = Lbl::L666;
                }
                Lbl::L666 => {
                    self.lnsrlb();
                    if self.info != 0 || self.iback >= 20 {
                        for i in 1..=n {
                            self.x[i] = self.t[i];
                        }
                        for i in 1..=n {
                            self.g[i] = self.r[i];
                        }
                        self.f = self.fold;
                        if self.col == 0 {
                            if self.info == 0 {
                                self.info = -9;
                                self.nfgv -= 1;
                                self.ifun -= 1;
                                self.iback -= 1;
                            }
                            self.task = "ERROR: ABNORMAL_TERMINATION_IN_LNSRCH".into();
                            self.iter += 1;
                            return;
                        } else {
                            if self.info == 0 {
                                self.nfgv -= 1;
                            }
                            self.reset_memory();
                            self.task = "RESTART_FROM_LNSRCH".into();
                            lbl = Lbl::L222;
                        }
                    } else if self.task.starts_with("FG_LN") {
                        return;
                    } else {
                        self.iter += 1;
                        self.projgr();
                        return;
                    }
                }
                Lbl::L777 => {
                    if self.sbgnrm <= self.pgtol {
                        self.task = CONV_PGTOL.into();
                        return;
                    }
                    let ddum = cmax(cmax(self.fold.abs(), self.f.abs()), 1.0);
                    if self.fold - self.f <= self.tol * ddum {
                        self.task = "CONVERGENCE: REL_REDUCTION_OF_F <= FACTR*EPSMCH".into();
                        if self.iback >= 10 {
                            self.info = -5;
                        }
                        return;
                    }
                    for i in 1..=n {
                        self.r[i] = self.g[i] - self.r[i];
                    }
                    let mut rr = 0.0;
                    for i in 1..=n {
                        rr += self.r[i] * self.r[i];
                    }
                    let (dr, ddum2) = if self.stp == 1.0 {
                        (self.gd - self.gdold, -self.gdold)
                    } else {
                        let dr = (self.gd - self.gdold) * self.stp;
                        for i in 1..=n {
                            self.d[i] *= self.stp;
                        }
                        (dr, -self.gdold * self.stp)
                    };
                    if dr <= self.epsmch * ddum2 {
                        self.nskip += 1;
                        self.updatd = false;
                        lbl = Lbl::L888;
                    } else {
                        self.updatd = true;
                        self.iupdat += 1;
                        let (stp, dtd) = (self.stp, self.dtd);
                        self.matupd(rr, dr, stp, dtd);
                        self.formt();
                        if self.info != 0 {
                            self.reset_memory();
                            lbl = Lbl::L222;
                        } else {
                            lbl = Lbl::L888;
                        }
                    }
                }
                Lbl::L888 => {
                    lbl = Lbl::L222;
                }
            }
        }
    }
}

/// `fminfn`: the objective, with R's check on the parameters.
fn fminfn<E, F>(p: &[f64], fcn: &mut F) -> Result<f64, Failure<E>>
where
    F: FnMut(&[f64]) -> Result<f64, E>,
{
    for &v in p {
        if !v.is_finite() {
            return Err(Failure::Message(
                "non-finite value supplied by optim".into(),
            ));
        }
    }
    fcn(p).map_err(Failure::Callback)
}

/// `fmingr` with bounds: the central difference, with each step clipped to the box.
fn fmingr<E, F>(
    p: &[f64],
    df: &mut [f64],
    fcn: &mut F,
    lower: &[f64],
    upper: &[f64],
    ndeps: &[f64],
) -> Result<(), Failure<E>>
where
    F: FnMut(&[f64]) -> Result<f64, E>,
{
    let n = p.len();
    let mut x = p.to_vec();
    for i in 0..n {
        let mut eps = ndeps[i];
        let mut epsused = eps;
        let mut tmp = p[i] + eps;
        if tmp > upper[i] {
            tmp = upper[i];
            epsused = tmp - p[i];
        }
        x[i] = tmp;
        let val1 = fminfn(&x, fcn)?;
        tmp = p[i] - eps;
        if tmp < lower[i] {
            tmp = lower[i];
            eps = p[i] - tmp;
        }
        x[i] = tmp;
        let val2 = fminfn(&x, fcn)?;
        df[i] = (val1 - val2) / (epsused + eps);
        if !df[i].is_finite() {
            return Err(Failure::Message(format!(
                "non-finite finite-difference value [{}]",
                i + 1
            )));
        }
        x[i] = p[i];
    }
    Ok(())
}

/// `optim(par, fn, method = "L-BFGS-B", lower, upper, control)` with R's
/// defaults: `ndeps` the numerical step, `factr` and `pgtol` the stopping
/// tests, `lmm` the memory size, and `maxit` the iteration cap.
#[allow(clippy::too_many_arguments)]
pub fn optim_lbfgsb<E, F>(
    par: &[f64],
    lower: &[f64],
    upper: &[f64],
    ndeps: &[f64],
    fcn: &mut F,
    factr: f64,
    pgtol: f64,
    lmm: usize,
    maxit: i64,
) -> Result<Output, Failure<E>>
where
    F: FnMut(&[f64]) -> Result<f64, E>,
{
    let n = par.len();
    let nbd: Vec<i32> = (0..n)
        .map(|i| match (lower[i].is_finite(), upper[i].is_finite()) {
            (false, false) => 0,
            (false, true) => 3,
            (true, false) => 1,
            (true, true) => 2,
        })
        .collect();

    if n == 0 {
        let value = fminfn(&[], fcn)?;
        return Ok(Output {
            par: Vec::new(),
            value,
            fail: 0,
            fncount: 1,
            grcount: 0,
            message: "NOTHING TO DO".into(),
        });
    }

    let mut s = Lbfgsb::new(par, lower, upper, &nbd, lmm, factr, pgtol);
    let mut iter: i64 = 0;
    let mut fail: i64 = 0;
    loop {
        s.setulb();
        if s.task.starts_with("FG") {
            let xv: Vec<f64> = s.x[1..=n].to_vec();
            let f = fminfn(&xv, fcn)?;
            if !f.is_finite() {
                return Err(Failure::Message(
                    "L-BFGS-B needs finite values of 'fn'".into(),
                ));
            }
            s.f = f;
            let mut gv = vec![0.0; n];
            fmingr(&xv, &mut gv, fcn, lower, upper, ndeps)?;
            for i in 0..n {
                s.g[i + 1] = gv[i];
            }
        } else if s.task.starts_with("NEW_X") {
            iter += 1;
            if iter > maxit {
                fail = 1;
                break;
            }
        } else if s.task.starts_with("WARN") {
            fail = 51;
            break;
        } else if s.task.starts_with("CONV") {
            break;
        } else {
            fail = 52;
            break;
        }
    }
    Ok(Output {
        par: s.x[1..=n].to_vec(),
        value: s.f,
        fail,
        fncount: s.nfgv,
        grcount: s.nfgv,
        message: s.task.clone(),
    })
}
