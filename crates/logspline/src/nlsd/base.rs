//! Types and helpers of `src/nlsd.c`: the data and model structs, the
//! matrix allocators (`dsmatrix` gives an (r+1) x (c+1) array so that the
//! 1-based C indices carry over unchanged), the LU routines, `five`
//! (starting knots), and `definespace` / `swapspace`.

/// Largest number of knots (`MAXKNOTS` in `nlsd.c`).
pub const MAXKNOTS: usize = 60;

/// A dense matrix stored as rows of `Vec<f64>`, indexed as `m[row][col]`.
pub type Mat = Vec<Vec<f64>>;

/// Allocate a matrix with `r` rows and `c` columns (C's `dsmatrix(r-1, c-1)`
/// is `mat(r, c)` here, so indices run 0..r and 0..c).
pub fn mat(r: usize, c: usize) -> Mat {
    vec![vec![0.0; c]; r]
}

/// Data for one fit: `struct datastruct` in the C source.
pub struct DataS {
    pub ndata: i32,
    pub data: Vec<f64>,
    pub idata: Vec<i32>,
    pub same: Vec<i16>,
}

/// One basis function: `struct basisfunct`.
#[derive(Clone)]
pub struct Basis {
    pub beta: f64,
    pub c1: Vec<f64>,
    pub c2: Mat,
    pub sumunc: f64,
    pub c3: [i32; 2],
    pub iks: [i32; 5],
}

/// One model (a space of spline bases): `struct space`.
#[derive(Clone)]
pub struct Space {
    pub ndim: i32,
    pub nk: i32,
    pub nip: i32,
    pub iknots: Vec<i32>,
    pub ilow: i32,
    pub iupp: i32,
    pub knots: Vec<f64>,
    pub aic: f64,
    pub info: Mat,
    pub score: Vec<f64>,
    pub ips: Vec<f64>,
    pub low: f64,
    pub upp: f64,
    pub cth: f64,
    pub basis: Vec<Basis>,
}

/// `swapspace(s1, s2)`: copy the live part of `s2` into `s1`, field for field as
/// the C routine does. Stale entries outside the live part are left alone,
/// because later code accumulates into some of them.
pub fn swapspace(s1: &mut Space, s2: &Space) {
    s1.ndim = s2.ndim;
    s1.nk = s2.nk;
    s1.cth = s2.cth;
    s1.nip = s2.nip;
    s1.aic = s2.aic;
    s1.low = s2.low;
    s1.upp = s2.upp;
    s1.ilow = s2.ilow;
    s1.iupp = s2.iupp;
    for i in 0..s1.nip as usize {
        s1.ips[i] = s2.ips[i];
    }
    for i in 0..s1.nk as usize {
        s1.knots[i] = s2.knots[i];
        s1.iknots[i] = s2.iknots[i];
    }
    for i in 0..s1.ndim as usize {
        for j in 0..5 {
            s1.basis[i].iks[j] = s2.basis[i].iks[j];
        }
        s1.score[i] = s2.score[i];
        for j in 0..s1.ndim as usize {
            s1.info[i][j] = s2.info[i][j];
        }
        s1.basis[i].beta = s2.basis[i].beta;
        for j in 0..2 {
            s1.basis[i].c3[j] = s2.basis[i].c3[j];
        }
        s1.basis[i].sumunc = s2.basis[i].sumunc;
        for j in 0..(s1.nk + 2) as usize {
            s1.basis[i].c1[j] = s2.basis[i].c1[j];
        }
        for j in 0..4 {
            for k in 0..s1.nip as usize {
                s1.basis[i].c2[k][j] = s2.basis[i].c2[k][j];
            }
        }
    }
}

/// `definespace(nd)`: allocate and zero one model.
pub fn definespace(nd: i32) -> Space {
    let k = MAXKNOTS + 10 + (nd / 100) as usize + 300;
    let mut basis = Vec::with_capacity(MAXKNOTS);
    for _ in 0..MAXKNOTS {
        basis.push(Basis {
            beta: 0.0,
            c1: vec![0.0; MAXKNOTS + 6],
            c2: mat(k + 1, 5),
            sumunc: 0.0,
            c3: [0, 0],
            iks: [0; 5],
        });
    }
    Space {
        ndim: 0,
        nk: 0,
        nip: k as i32,
        iknots: vec![0; MAXKNOTS + 6],
        ilow: 0,
        iupp: 0,
        knots: vec![0.0; MAXKNOTS + 6],
        aic: 10f64.powf(100.0),
        info: mat(MAXKNOTS + 6, MAXKNOTS + 6),
        score: vec![0.0; MAXKNOTS + 6],
        ips: vec![0.0; k + 1],
        low: 0.0,
        upp: 0.0,
        cth: 0.0,
        basis,
    }
}

/// `getsame`: `s[i] = 1` if observation i equals (or almost equals) the one
/// before it.
pub fn getsame(x: &[f64], n: usize, s: &mut [i16]) {
    s[0] = 0;
    for i in 1..n {
        if x[i] == x[i - 1] {
            s[i] = 1;
        } else if x[i] != 0.0 {
            let r = (x[i - 1] / x[i] - 1.0).abs();
            s[i] = if r < 0.0000000000001 { 1 } else { 0 };
        } else {
            s[i] = 0;
        }
    }
}

/// `five00`: Gauss-type spacing of `k` points on 1..n, written into `rr`.
fn five00(rr: &mut [f64], k: i32, n: i32) {
    let fi = 4.0f64;
    let kf = k as f64;
    let nf = n as f64;
    let j = ((kf - 1.0) / 2.0 + 0.99).floor() as i32;
    let j2 = ((kf - 1.0) / 2.0).floor() as i32;
    let mut eps1 = fi - ((nf - 1.0) / fi).powf(1.0 / (j as f64 - 1.0));
    if eps1 > 0.0 {
        eps1 = 0.0;
    }
    let mut eps2 = fi - 1.0;
    for i in 0..k as usize {
        rr[i] = 0.0;
    }
    rr[0] = 1.0;
    rr[k as usize] = nf;
    let mut i1 = 0;
    while i1 < 100 {
        if !(i1 == 0 || eps2 - eps1 > 0.0001) {
            break;
        }
        let eps = (eps1 + eps2) / 2.0;
        let mut s = 1.0f64;
        let mut w = fi;
        for i in 1..=j2 {
            let mut v = i as f64;
            s += w;
            rr[i as usize] = s;
            rr[(k - i - 1) as usize] = nf + 1.0 - s;
            v = fi - v * eps;
            if v < 1.0 {
                v = 1.0;
            }
            w *= v;
        }
        if 2 * j == k {
            s += w / 2.0;
        } else {
            rr[j as usize] = (nf + 1.0) / 2.0;
        }
        if 2.0 * s >= nf + 1.0 {
            eps1 = eps;
        } else {
            eps2 = eps;
        }
        i1 += 1;
    }
    for i in 0..k as usize {
        rr[i] = (rr[i] - 1.0) / (nf - 1.0);
    }
}

/// `five01`: spacing for one free end.
fn five01(rr: &mut [f64], k: usize, n: usize, il: i32) {
    five00(rr, (2 * k - 1) as i32, (2 * n) as i32);
    for i in 0..k {
        rr[i] *= 2.0;
    }
    if il == 0 {
        for i in 0..k {
            rr[i] = 1.0 - rr[2 * k - 2 - i];
        }
    }
}

/// `five`: starting knots placed at the quantiles of the data, with the
/// spacing from `five00` / `five01`.
pub fn five(data: &[f64], kts: &mut [f64], intpars: &[i32], same: &[i16]) {
    let n1 = intpars[0] as usize;
    let k = intpars[2] as usize;
    let mut rr = vec![0.0f64; n1 + 2 * MAXKNOTS + 6];
    if intpars[4] + intpars[5] == 2 {
        five00(&mut rr, k as i32, n1 as i32);
    }
    if intpars[4] + intpars[5] == 1 {
        five01(&mut rr, k, n1, intpars[5]);
    }
    if intpars[4] + intpars[5] == 0 {
        for i in 0..k {
            rr[i] = i as f64 / (k - 1) as f64;
        }
    }
    let mut ee = vec![0.0f64; n1 + MAXKNOTS + 6];
    let mut h1 = vec![0.0f64; n1 + MAXKNOTS + 6];
    ee[0] = 1.0;
    h1[0] = 0.0;
    h1[1] = 1.0;
    let mut l = 0usize;
    for i in 1..n1 {
        if same[i] == 1 {
            h1[l + 1] += 1.0;
        } else {
            l += 1;
            ee[l] = data[i];
            h1[l + 1] = h1[l] + 1.0;
        }
    }
    for i in 0..l {
        h1[i] = 0.5 * (h1[i] + h1[i + 1]);
    }
    let h2 = h1[0];
    let mut h3 = 0.0f64;
    for i in 0..l {
        h1[i] -= h2;
        if h1[i] > h3 {
            h3 = h1[i];
        }
    }
    for i in 0..l {
        h1[i] /= h3;
    }
    kts[0] = data[0];
    kts[k - 1] = data[n1 - 1];
    for i in 1..k - 1 {
        let mut g1 = 0usize;
        let mut g2 = l;
        for j in 0..l {
            if h1[j] <= rr[i] && j > g1 {
                g1 = j;
            }
            if h1[j] > rr[i] && j < g2 {
                g2 = j;
            }
        }
        let h2 = h1[g1];
        let mut h3 = h1[g2];
        h3 = (rr[i] - h2) / (h3 - h2);
        kts[i] = h3 * ee[g2] + (1.0 - h3) * ee[g1];
    }
}

/// `ludcmp`: LU decomposition with partial pivoting. `a`, `indx` and the
/// results use the 1-based C indices (`a[1..=n][1..=n]`). Returns 0 if the
/// matrix is singular.
pub fn ludcmp(a: &mut Mat, n: usize, indx: &mut [i32], d: &mut f64) -> i32 {
    let mut vv = vec![0.0f64; n + 2];
    *d = 1.0;
    for i in 1..=n {
        let mut big = 0.0f64;
        for j in 1..=n {
            let temp = a[i][j].abs();
            if temp > big {
                big = temp;
            }
        }
        if big == 0.0 {
            return 0;
        }
        vv[i] = 1.0 / big;
    }
    let mut imax = 0usize;
    for j in 1..=n {
        for i in 1..j {
            let mut sum = a[i][j];
            for k in 1..i {
                sum -= a[i][k] * a[k][j];
            }
            a[i][j] = sum;
        }
        let mut big = 0.0f64;
        for i in j..=n {
            let mut sum = a[i][j];
            for k in 1..j {
                sum -= a[i][k] * a[k][j];
            }
            a[i][j] = sum;
            let dum = vv[i] * sum.abs();
            if dum >= big {
                big = dum;
                imax = i;
            }
        }
        if j != imax {
            for k in 1..=n {
                let dum = a[imax][k];
                a[imax][k] = a[j][k];
                a[j][k] = dum;
            }
            *d = -(*d);
            vv[imax] = vv[j];
        }
        indx[j] = imax as i32;
        if a[j][j] == 0.0 {
            a[j][j] = 1.0e-20;
        }
        if j != n {
            let dum = 1.0 / a[j][j];
            for i in j + 1..=n {
                a[i][j] *= dum;
            }
        }
    }
    1
}

/// `lubksb`: back substitution with `b` 1-based (`b[1..=n]`).
pub fn lubksb(a: &Mat, n: usize, indx: &[i32], b: &mut [f64]) {
    let mut ii = 0usize;
    for i in 1..=n {
        let ip = indx[i] as usize;
        let mut sum = b[ip];
        b[ip] = b[i];
        if ii != 0 {
            for j in ii..i {
                sum -= a[i][j] * b[j];
            }
        } else if sum != 0.0 {
            ii = i;
        }
        b[i] = sum;
    }
    for i in (1..=n).rev() {
        let mut sum = b[i];
        for j in i + 1..=n {
            sum -= a[i][j] * b[j];
        }
        b[i] = sum / a[i][i];
    }
}

/// `luinverse`: invert the n x n matrix `a` (0-based, `a[row][col]`) in place.
pub fn luinverse(a: &mut Mat, n: usize) {
    let mut c = mat(n + 1, n + 1);
    let mut indx = vec![0i32; n + 1];
    let mut d = vec![0.0f64; n + 1];
    for j in 1..=n {
        for k in 1..=n {
            c[j][k] = a[j - 1][k - 1];
        }
    }
    let mut r = 0.0f64;
    if ludcmp(&mut c, n, &mut indx, &mut r) == 0 {
        crate::lsdall::rprintf("singular matrix in routine LUDCMP\n");
    }
    for j in 1..=n {
        for k in 1..=n {
            d[k] = 0.0;
        }
        d[j] = 1.0;
        lubksb(&c, n, &indx, &mut d);
        for k in 1..=n {
            a[k - 1][j - 1] = d[k];
        }
    }
}

/// `lusolve2`: solve `a x = b` for `x`, writing the solution into `b`
/// (0-based). Returns 0 if `a` is singular.
pub fn lusolve2(a: &Mat, n: usize, b: &mut [f64]) -> i32 {
    let mut c = mat(n + 1, n + 1);
    let mut indx = vec![0i32; n + 1];
    for j in 0..n {
        for k in 0..n {
            c[j + 1][k + 1] = a[j][k];
        }
    }
    let mut r = 0.0f64;
    if ludcmp(&mut c, n, &mut indx, &mut r) == 0 {
        return 0;
    }
    let mut b1 = vec![0.0f64; n + 1];
    for k in 0..n {
        b1[k + 1] = b[k];
    }
    lubksb(&c, n, &indx, &mut b1);
    for k in 0..n {
        b[k] = b1[k + 1];
    }
    1
}

/// `mylog`: log with a floor at a tiny positive value.
pub fn mylog(x: f64) -> f64 {
    if x < 10.0e-250 {
        -575.64627
    } else {
        x.ln()
    }
}

/// `myexp`: exp with the argument capped at 576.
pub fn myexp(x: f64) -> f64 {
    if x > 576.0 {
        576.0f64.exp()
    } else {
        x.exp()
    }
}
