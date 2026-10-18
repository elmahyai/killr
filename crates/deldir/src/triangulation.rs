//! Delaunay triangulation and Dirichlet tile kernels, ported from deldir 2.0-4.
//!
//! Source: deldir 2.0-4 `src/*.f90` (Fortran 90) and `src/init.c`.
//! Copyright (C) Rolf Turner. Licensed under the GNU General Public License,
//! version 2 or later (DESCRIPTION: `GPL (>= 2)`).
//!
//! Entry points used by `deldir()` and `triang.list()` on the default path:
//!   * `binsrt`  -> `src/binsrt.f90`, called from R `binsrtR()`.
//!   * `master`  -> `src/master.f90`, called from `deldir()`. It drives the
//!     routines `insrt`, `addpt`, `delseg`, `delout`, `dirseg`, `dirout`.
//!   * `intri`   -> `src/intri.f90`, called from `triang.list()`.
//!
//! Adjacency lists are unbounded `Vec`s. The Fortran `madj`/`ndel`/`ndir`
//! storage limits and the `incAdj`/`incSeg` retry loop in `deldir.R` only
//! size the scratch arrays, so the results are the same without them.
//!
//! Indices follow the Fortran. Vertices run from -3 to `ntot`; the ideal
//! points are -3..0 and the data points are 1..nn. Positions in an adjacency
//! list are 1-based in the code comments and stored 0-based.

/// Result of a kernel. `Err` carries the message `rexit()` printed in Fortran.
pub type Res<T> = Result<T, String>;

fn ideal(v: i64) -> i32 {
    if v <= 0 {
        1
    } else {
        0
    }
}

/// Normalized cross product (`src/cross.f90`).
///
/// `x` and `y` are copies. The Fortran routine rewrites its arguments for
/// ideal points, so the caller's arrays are unchanged.
fn cross(mut x: [f64; 3], mut y: [f64; 3], ijk: i32) -> f64 {
    let mut smin = 0.0;
    if ijk == 0 {
        smin = -1.0;
        for i in 0..3 {
            let ip = (i + 1) % 3;
            let a = x[ip] - x[i];
            let b = y[ip] - y[i];
            let s = a * a + b * b;
            if smin < 0.0 || s < smin {
                smin = s;
            }
        }
    }
    if ijk == 1 {
        x[1] -= x[0];
        y[1] -= y[0];
        x[0] = 0.0;
        y[0] = 0.0;
        let cn = (x[1] * x[1] + y[1] * y[1]).sqrt();
        x[1] /= cn;
        y[1] /= cn;
        smin = 1.0;
    }
    if ijk == 2 {
        x[2] -= x[0];
        y[2] -= y[0];
        x[0] = 0.0;
        y[0] = 0.0;
        let cn = (x[2] * x[2] + y[2] * y[2]).sqrt();
        x[2] /= cn;
        y[2] /= cn;
        smin = 1.0;
    }
    if ijk == 3 {
        x[0] = 0.0;
        y[0] = 0.0;
        smin = 2.0;
    }
    if ijk == 4 {
        x[2] -= x[1];
        y[2] -= y[1];
        x[1] = 0.0;
        y[1] = 0.0;
        let cn = (x[2] * x[2] + y[2] * y[2]).sqrt();
        x[2] /= cn;
        y[2] /= cn;
        smin = 1.0;
    }
    if ijk == 5 {
        x[1] = 0.0;
        y[1] = 0.0;
        smin = 2.0;
    }
    if ijk == 6 {
        x[2] = 0.0;
        y[2] = 0.0;
        smin = 2.0;
    }
    if ijk == 7 {
        smin = 4.0;
    }
    let a = x[1] - x[0];
    let b = y[1] - y[0];
    let c = x[2] - x[0];
    let d = y[2] - y[0];
    (a * d - b * c) / smin
}

/// Fortran `testeq`: are `a` and `b` equal to within `eps`, relative to `b`?
fn testeq(a: f64, b: f64, eps: f64) -> bool {
    let one = 1.0;
    let ten = 1.0e10;
    if b.abs() <= eps {
        return a.abs() <= eps;
    }
    if a.abs() > ten * b.abs() || a.abs() < one * b.abs() {
        return false;
    }
    let c = a / b;
    (c - 1.0).abs() <= eps
}

/// Fortran `triar`: signed area of a triangle.
fn triar(x0: f64, y0: f64, x1: f64, y1: f64, x2: f64, y2: f64) -> f64 {
    0.5 * ((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0))
}

/// Fortran `stoke` (`src/stoke.f90`). Returns `(area, s1)`.
fn stoke(
    x1: f64,
    y1: f64,
    x2: f64,
    y2: f64,
    rw: [f64; 4],
    eps: f64,
) -> Res<(f64, f64)> {
    let zero = 0.0;
    if testeq(x1, x2, eps) {
        return Ok((0.0, 0.0));
    }
    let (xl0, yl0, xr0, yr0, s1) = if x1 < x2 {
        (x1, y1, x2, y2, -1.0)
    } else {
        (x2, y2, x1, y1, 1.0)
    };
    let (xmin, xmax, ymin, ymax) = (rw[0], rw[1], rw[2], rw[3]);

    let slope = (yl0 - yr0) / (xl0 - xr0);
    let xl = xl0.max(xmin);
    let yl = yl0 + slope * (xl - xl0);
    let xr = xr0.min(xmax);
    let yr = yr0 + slope * (xr - xr0);

    if xr <= xmin || xl >= xmax {
        return Ok((0.0, s1));
    }

    let ybot = yl.min(yr);
    let ytop = yl.max(yr);

    // Case 1: ymax <= ybot.
    if ymax <= ybot {
        return Ok(((xr - xl) * (ymax - ymin), s1));
    }

    // Case 2: ymin <= ybot <= ymax <= ytop.
    if ymin <= ybot && ymax <= ytop {
        let (w1, w2);
        if testeq(slope, zero, eps) {
            w1 = 0.0;
            w2 = xr - xl;
        } else {
            let xit = xl + (ymax - yl) / slope;
            let mut a1 = xit - xl;
            let mut a2 = xr - xit;
            if slope < 0.0 {
                std::mem::swap(&mut a1, &mut a2);
            }
            w1 = a1;
            w2 = a2;
        }
        let area = 0.5 * w1 * ((ybot - ymin) + (ymax - ymin)) + w2 * (ymax - ymin);
        return Ok((area, s1));
    }

    // Case 3: ybot <= ymin <= ymax <= ytop.
    if ybot <= ymin && ymax <= ytop {
        let xit = xl + (ymax - yl) / slope;
        let xib = xl + (ymin - yl) / slope;
        let (w1, w2) = if slope > 0.0 {
            (xit - xib, xr - xit)
        } else {
            (xib - xit, xit - xl)
        };
        let area = 0.5 * w1 * (ymax - ymin) + w2 * (ymax - ymin);
        return Ok((area, s1));
    }

    // Case 4: ymin <= ybot <= ytop <= ymax.
    if ymin <= ybot && ytop <= ymax {
        let area = 0.5 * (xr - xl) * ((ytop - ymin) + (ybot - ymin));
        return Ok((area, s1));
    }

    // Case 5: ybot <= ymin <= ytop <= ymax.
    if ybot <= ymin && ymin <= ytop {
        if testeq(slope, zero, eps) {
            return Ok((0.0, s1));
        }
        let xib = xl + (ymin - yl) / slope;
        let w = if slope > 0.0 { xr - xib } else { xib - xl };
        let area = 0.5 * w * (ytop - ymin);
        return Ok((area, s1));
    }

    // Case 6: ytop <= ymin.
    if ytop <= ymin {
        return Ok((0.0, s1));
    }

    Err("Fell through all six cases. Chaos and havoc in stoke.".to_string())
}

/// Fortran `dldins` (`src/dldins.f90`).
///
/// Returns `(ai, bi, intfnd, bpt, nedge)`. `intfnd` says an intersection with
/// the window was found; `bpt` says the returned point is on the boundary.
fn dldins(a: f64, b: f64, slope: f64, rwu: bool, rw: [f64; 4]) -> (f64, f64, bool, bool, i64) {
    let (xmin, xmax, ymin, ymax) = (rw[0], rw[1], rw[2], rw[3]);
    let mut ai = 0.0;
    let mut bi = 0.0;
    let mut nedge = 0i64;

    if xmin <= a && a <= xmax && ymin <= b && b <= ymax {
        return (a, b, true, false, 0);
    }

    if !rwu {
        if b < ymin {
            ai = a;
            bi = ymin;
            nedge = 1;
            if xmin <= ai && ai <= xmax {
                return (ai, bi, true, true, nedge);
            }
        }
        if b > ymax {
            ai = a;
            bi = ymax;
            nedge = 3;
            if xmin <= ai && ai <= xmax {
                return (ai, bi, true, true, nedge);
            }
        }
        return (ai, bi, false, true, nedge);
    }

    // Line 1: x = xmin.
    if a < xmin {
        ai = xmin;
        bi = b + slope * (ai - a);
        nedge = 2;
        if ymin <= bi && bi <= ymax {
            return (ai, bi, true, true, nedge);
        }
    }

    // Line 2: y = ymin.
    if b < ymin {
        bi = ymin;
        ai = a + (bi - b) / slope;
        nedge = 1;
        if xmin <= ai && ai <= xmax {
            return (ai, bi, true, true, nedge);
        }
    }

    // Line 3: x = xmax.
    if a > xmax {
        ai = xmax;
        bi = b + slope * (ai - a);
        nedge = 4;
        if ymin <= bi && bi <= ymax {
            return (ai, bi, true, true, nedge);
        }
    }

    // Line 4: y = ymax.
    if b > ymax {
        bi = ymax;
        ai = a + (bi - b) / slope;
        nedge = 3;
        if xmin <= ai && ai <= xmax {
            return (ai, bi, true, true, nedge);
        }
    }

    (ai, bi, false, true, nedge)
}

/// Adjacency structure and point coordinates for one triangulation.
///
/// `x`, `y`, and `adj` are indexed by vertex `v` at position `v + 3`, so
/// vertices -3..=ntot fit in the vectors.
pub struct Mesh {
    eps: f64,
    ntot: i64,
    x: Vec<f64>,
    y: Vec<f64>,
    adj: Vec<Vec<i64>>,
}

fn pos(v: i64) -> usize {
    (v + 3) as usize
}

impl Mesh {
    fn new(nn: usize, eps: f64) -> Mesh {
        let ntot = nn as i64 + 4;
        let len = (ntot + 4) as usize;
        Mesh {
            eps,
            ntot,
            x: vec![0.0; len],
            y: vec![0.0; len],
            adj: vec![Vec::new(); len],
        }
    }

    fn xv(&self, v: i64) -> f64 {
        self.x[pos(v)]
    }

    fn yv(&self, v: i64) -> f64 {
        self.y[pos(v)]
    }

    /// Fortran `acchk`: are i, j, k anticlockwise?
    fn acchk(&self, i: i64, j: i64, k: i64) -> bool {
        let ijk = ideal(i) * 4 + ideal(j) * 2 + ideal(k);
        let xt = [self.xv(i), self.xv(j), self.xv(k)];
        let yt = [self.yv(i), self.yv(j), self.yv(k)];
        let cprd = cross(xt, yt, ijk);
        cprd > self.eps
    }

    /// Fortran `adjchk`: are i and j adjacent? Errors on contradictory lists.
    fn adjchk(&self, i: i64, j: i64) -> Res<bool> {
        let mut adj = false;
        if self.adj[pos(i)].contains(&j) {
            adj = true;
        }
        for &v in self.adj[pos(j)].iter() {
            if v == i {
                if adj {
                    return Ok(true);
                }
                return Err("Contradictory adjacency lists. Bailing out of adjchk.".to_string());
            }
        }
        if adj {
            return Err("Contradictory adjacency lists. Bailing out of adjchk.".to_string());
        }
        Ok(false)
    }

    /// Fortran `pred`: the predecessor of j in the adjacency list of i.
    fn pred(&self, i: i64, j: i64) -> Res<i64> {
        let list = &self.adj[pos(i)];
        let n = list.len();
        if n == 0 {
            return Err("Adjacency list of i is empty, and so cannot contain j. Bailing out of pred.".to_string());
        }
        match list.iter().position(|&v| v == j) {
            Some(p) => {
                let km = if p == 0 { n - 1 } else { p - 1 };
                Ok(list[km])
            }
            None => Err("Adjacency list of i does not contain j. Bailing out of pred.".to_string()),
        }
    }

    /// Fortran `succ`: the successor of j in the adjacency list of i.
    fn succ(&self, i: i64, j: i64) -> Res<i64> {
        let list = &self.adj[pos(i)];
        let n = list.len();
        if n == 0 {
            return Err("Adjacency list of i is empty, and so cannot contain j. Bailing out of succ.".to_string());
        }
        match list.iter().position(|&v| v == j) {
            Some(p) => Ok(list[(p + 1) % n]),
            None => Err("Adjacency list of i does not contain j. Bailing out of succ.".to_string()),
        }
    }

    /// Fortran `locn`: the 1-based place j takes in the list of i.
    fn locn(&self, i: i64, j: i64) -> usize {
        let list = &self.adj[pos(i)];
        let n = list.len();
        if n == 0 {
            return 1;
        }
        let mut before = false;
        for ks in 1..=n {
            let mut kj = ks;
            let k = list[kj - 1];
            before = self.acchk(i, j, k);
            if before {
                let km = if kj == 1 { n } else { kj - 1 };
                let k2 = list[km - 1];
                before = self.acchk(i, j, k2);
                if !before {
                    if kj == 1 {
                        kj = n + 1;
                    }
                    return kj;
                }
            }
        }
        if before {
            1
        } else {
            n + 1
        }
    }

    /// Fortran `insrt1`: put j at 1-based place kj in the list of i.
    fn insrt1(&mut self, i: i64, j: i64, kj: usize) {
        let list = &mut self.adj[pos(i)];
        if list.is_empty() {
            list.push(j);
        } else {
            list.insert(kj - 1, j);
        }
    }

    /// Fortran `insrt`: join i and j in each other's lists.
    fn insrt(&mut self, i: i64, j: i64) -> Res<()> {
        if self.adjchk(i, j)? {
            return Ok(());
        }
        let kj = self.locn(i, j);
        let ki = self.locn(j, i);
        self.insrt1(i, j, kj);
        self.insrt1(j, i, ki);
        Ok(())
    }

    /// Fortran `delet1`: remove j from the list of i.
    fn delet1(&mut self, i: i64, j: i64) {
        let list = &mut self.adj[pos(i)];
        if let Some(p) = list.iter().position(|&v| v == j) {
            list.remove(p);
        }
    }

    /// Fortran `delet`: remove i and j from each other's lists.
    fn delet(&mut self, i: i64, j: i64) -> Res<()> {
        if self.adjchk(i, j)? {
            self.delet1(i, j);
            self.delet1(j, i);
        }
        Ok(())
    }

    /// Fortran `circen`: circumcentre of triangle (i, j, k).
    /// Returns `(collinear, x0, y0)`. The centre is unset when collinear.
    fn circen(&self, i: i64, j: i64, k: i64) -> Res<(bool, f64, f64)> {
        let xt = [self.xv(i), self.xv(j), self.xv(k)];
        let yt = [self.yv(i), self.yv(j), self.yv(k)];
        let cprd = cross(xt, yt, 0);
        let collin = cprd.abs() < self.eps;

        let mut a = self.xv(j) - self.xv(i);
        let mut b = self.yv(j) - self.yv(i);
        let mut c = self.xv(k) - self.xv(i);
        let mut d = self.yv(k) - self.yv(i);
        let c1 = (a * a + b * b).sqrt();
        let c2 = (c * c + d * d).sqrt();
        a /= c1;
        b /= c1;
        c /= c2;
        d /= c2;

        if collin {
            let alpha = a * c + b * d;
            if alpha > 0.0 {
                return Err("Points are collinear but in the wrong order. Bailing out of circen.".to_string());
            }
            return Ok((true, 0.0, 0.0));
        }

        let crss = a * d - b * c;
        let x0 = self.xv(i) + 0.5 * (c1 * d - c2 * b) / crss;
        let y0 = self.yv(i) + 0.5 * (c2 * a - c1 * c) / crss;
        Ok((false, x0, y0))
    }

    /// Fortran `qtest1`: Lee-Schacter LOP test for four real points.
    fn qtest1(&self, h: i64, i: i64, j: i64, k: i64) -> Res<bool> {
        let xt = [self.xv(h), self.xv(i), self.xv(k)];
        let yt = [self.yv(h), self.yv(i), self.yv(k)];
        let cprd = cross(xt, yt, 0);
        let collin = cprd.abs() < self.eps;

        // Collinear h, i, k: the circumcircle has infinite radius, so the
        // swap is taken if h lies between i and k. Otherwise the order check
        // is an error.
        if collin {
            let mut a = xt[1] - xt[0];
            let mut b = yt[1] - yt[0];
            let mut c = xt[2] - xt[0];
            let mut d = yt[2] - yt[0];
            let c1 = (a * a + b * b).sqrt();
            let c2 = (c * c + d * d).sqrt();
            a /= c1;
            b /= c1;
            c /= c2;
            d /= c2;
            let alpha = a * c + b * d;
            if alpha > 0.0 {
                return Err("Points are collinear but h is not between i and k. Bailing out of qtest1.".to_string());
            }
            return Ok(true);
        }

        let xh = self.xv(h);
        let yh = self.yv(h);
        let xj = self.xv(j);
        let yj = self.yv(j);

        let (_, x0, y0) = self.circen(h, i, k)?;

        let mut a = x0 - xh;
        let mut b = y0 - yh;
        let r2 = a * a + b * b;
        a = x0 - xj;
        b = y0 - yj;
        let ch = a * a + b * b;
        Ok(ch < r2)
    }

    /// Fortran `qtest`: should the diagonal i-k be swapped for h-j?
    fn qtest(&self, h: i64, i: i64, j: i64, k: i64) -> Res<bool> {
        let ijk = ideal(i) * 4 + ideal(j) * 2 + ideal(k);
        match ijk {
            // case 7
            7 => Ok(true),
            // case 6: i and j ideal.
            6 => {
                let xh = self.xv(h);
                let yh = self.yv(h);
                let xk = self.xv(k);
                let yk = self.yv(k);
                let ss = (1 - 2 * ((-j) % 2)) as f64;
                let test = (xh * yk + xk * yh - xh * yh - xk * yk) * ss;
                let mut shdswp = test > 0.0;
                if shdswp {
                    shdswp = self.acchk(j, k, h);
                }
                Ok(shdswp)
            }
            // case 5
            5 => Ok(true),
            // case 4: only i ideal.
            4 => Ok(self.acchk(j, k, h)),
            // case 3: j and k ideal.
            3 => {
                let xi = self.xv(i);
                let yi = self.yv(i);
                let xh = self.xv(h);
                let yh = self.yv(h);
                let ss = (1 - 2 * ((-j) % 2)) as f64;
                let test = (xh * yi + xi * yh - xh * yh - xi * yi) * ss;
                let mut shdswp = test > 0.0;
                if shdswp {
                    shdswp = self.acchk(h, i, j);
                }
                Ok(shdswp)
            }
            // case 2: only j ideal.
            2 => Ok(false),
            // case 1: only k ideal.
            1 => Ok(self.acchk(h, i, j)),
            // case 0: all four real.
            0 => self.qtest1(h, i, j, k),
            _ => Err("Indicator ijk is out of range. Bailing out of qtest.".to_string()),
        }
    }

    /// Fortran `swap`: swap the diagonal k1-k2 for j-k if the LOP fails.
    fn swap(&mut self, j: i64, k1: i64, k2: i64) -> Res<bool> {
        let mut shdswp = self.adjchk(k1, k2)?;
        if !shdswp {
            return Ok(false);
        }
        let k = self.pred(k1, k2)?;
        let kk = self.succ(k2, k1)?;
        if kk != k {
            return Ok(false);
        }
        shdswp = self.qtest(j, k1, k, k2)?;
        if shdswp {
            self.delet(k1, k2)?;
            self.insrt(j, k)?;
        }
        Ok(shdswp)
    }

    /// Fortran `trifnd`: the triangle of the current triangulation that
    /// contains point j. Returns `(tau, nedge)`.
    fn trifnd(&self, j: i64, ntri: i64) -> Res<([i64; 3], i64)> {
        if j == 1 {
            return Err("No triangles to find. Bailing out of trifnd.".to_string());
        }
        let j1 = j - 1;
        let mut tau = [0i64; 3];
        tau[0] = j1;
        tau[2] = *self.adj[pos(j1)]
            .first()
            .ok_or_else(|| "Adjacency list is empty in trifnd.".to_string())?;
        tau[1] = self.pred(j1, tau[2])?;
        if !self.adjchk(tau[1], tau[2])? {
            tau[2] = tau[1];
            tau[1] = self.pred(j1, tau[2])?;
        }

        let mut ktri = 0i64;
        loop {
            let mut anticl = self.acchk(tau[0], tau[1], tau[2]);
            if !anticl {
                anticl = self.acchk(tau[2], tau[1], tau[0]);
                if !anticl {
                    return Err("Both vertex orderings are clockwise. Bailing out of trifnd.".to_string());
                }
                tau.swap(0, 2);
            }

            let mut ntau = 0usize;
            let mut nedge = 0i64;
            for i in 1..=3usize {
                let ip = if i == 3 { 1 } else { i + 1 };
                let ti = tau[i - 1];
                let tip = tau[ip - 1];
                let xt = [self.xv(ti), self.xv(tip), self.xv(j)];
                let yt = [self.yv(ti), self.yv(tip), self.yv(j)];
                let ijk = ideal(ti) * 4 + ideal(tip) * 2;
                let cprd = cross(xt, yt, ijk);
                if cprd >= self.eps {
                    continue;
                }
                if cprd > -self.eps {
                    nedge = ip as i64;
                } else {
                    ntau = ip;
                    break;
                }
            }

            if ntau == 0 {
                return Ok((tau, nedge));
            }

            match ntau {
                1 => {
                    tau[1] = tau[2];
                    tau[2] = self.succ(tau[0], tau[1])?;
                }
                2 => {
                    tau[2] = tau[1];
                    tau[1] = self.pred(tau[0], tau[2])?;
                }
                _ => {
                    tau[0] = tau[2];
                    tau[2] = self.succ(tau[0], tau[1])?;
                }
            }

            ktri += 1;
            if ktri > ntri {
                return Err("Cannot find an enclosing triangle. Bailing out of trifnd.".to_string());
            }
        }
    }

    /// Fortran `initad`: join new point j to its enclosing triangle.
    fn initad(&mut self, j: i64, ntri: i64) -> Res<()> {
        let (tau, nedge) = self.trifnd(j, ntri)?;
        if nedge != 0 {
            let ip = nedge as usize;
            let i = if ip == 1 { 3 } else { ip - 1 };
            let ti = tau[i - 1];
            let tip = tau[ip - 1];
            let k = self.pred(ti, tip)?;
            let kk = self.succ(tip, ti)?;
            self.delet(ti, tip)?;
            if k == kk {
                self.insrt(j, k)?;
            }
        }
        for t in tau.iter() {
            self.insrt(j, *t)?;
        }
        Ok(())
    }

    /// Fortran `addpt`: add point j and restore local optimality.
    fn addpt(&mut self, j: i64, ntri: i64) -> Res<()> {
        self.initad(j, ntri)?;
        let list = &self.adj[pos(j)];
        if list.len() < 2 {
            return Err("Point has fewer than two neighbours in addpt.".to_string());
        }
        let mut now = list[0];
        let mut nxt = list[1];
        let mut ngap = 0usize;
        loop {
            let didswp = self.swap(j, now, nxt)?;
            let n = self.adj[pos(j)].len();
            if !didswp {
                now = nxt;
                ngap += 1;
            }
            nxt = self.succ(j, now)?;
            if ngap == n {
                break;
            }
        }
        Ok(())
    }

    /// Data neighbours j of i with 1 <= j < i, in increasing order. These are
    /// the only j for which the Fortran pair loop `do j = 1,i-1; adjchk(i,j)`
    /// can report adjacency, so the loop visits them directly.
    fn lower_neighbours(&self, i: i64) -> Vec<i64> {
        let mut js: Vec<i64> = self.adj[pos(i)]
            .iter()
            .copied()
            .filter(|&j| j >= 1 && j < i)
            .collect();
        js.sort_unstable();
        js
    }

    /// Fortran `delseg`: endpoints of the Delaunay edges. Each row is
    /// `(x_i, y_i, x_j, y_j, i, j)` with `j < i`.
    fn delseg(&self, nn: usize) -> Res<Vec<[f64; 6]>> {
        let mut out = Vec::new();
        for i in 2..=nn as i64 {
            for j in self.lower_neighbours(i) {
                if self.adjchk(i, j)? {
                    out.push([
                        self.xv(i),
                        self.yv(i),
                        self.xv(j),
                        self.yv(j),
                        i as f64,
                        j as f64,
                    ]);
                }
            }
        }
        Ok(out)
    }

    /// Fortran `delout`: one row `(x, y, n.tri, area)` for each data point.
    fn delout(&self, nn: usize) -> Res<Vec<[f64; 4]>> {
        let mut out = Vec::with_capacity(nn);
        for i in 1..=nn as i64 {
            let mut area = 0.0;
            let list = &self.adj[pos(i)];
            let np = list.len();
            let xi = self.xv(i);
            let yi = self.yv(i);
            let mut npt = np as i64;
            for k in 0..np {
                let kp = if k + 1 == np { 0 } else { k + 1 };
                if list[k] <= 0 || list[kp] <= 0 {
                    npt -= 1;
                }
            }
            for j1 in 0..np {
                let j = list[j1];
                if j <= 0 {
                    continue;
                }
                let xj = self.xv(j);
                let yj = self.yv(j);
                let k = self.succ(i, j)?;
                if k <= 0 {
                    continue;
                }
                let xk = self.xv(k);
                let yk = self.yv(k);
                let tmp = triar(xi, yi, xj, yj, xk, yk);
                area = area + tmp / 3.0;
            }
            out.push([xi, yi, npt as f64, area]);
        }
        Ok(out)
    }

    /// Fortran `dirseg`: add four far corners, then the Dirichlet boundary
    /// segments. Each row is 10 values: `ai, bi, ci, di, i, j, bp1, bp2,
    /// thirdv1, thirdv2`.
    fn dirseg(&mut self, nn: usize, rw: [f64; 4], ntri: i64) -> Res<Vec<[f64; 10]>> {
        let (xmin, xmax, ymin, ymax) = (rw[0], rw[1], rw[2], rw[3]);
        let a0 = xmax - xmin;
        let b0 = ymax - ymin;
        let c0 = (a0 * a0 + b0 * b0).sqrt();
        let nn_i = nn as i64;
        let nstt = nn_i + 1;
        let ntot = self.ntot;

        let corners = [
            (xmin - c0, ymin - c0),
            (xmax + c0, ymin - c0),
            (xmax + c0, ymax + c0),
            (xmin - c0, ymax + c0),
        ];
        for (idx, (cx, cy)) in corners.iter().enumerate() {
            let v = nstt + idx as i64;
            self.x[pos(v)] = *cx;
            self.y[pos(v)] = *cy;
        }

        let mut ntri = ntri;
        for j in nstt..=ntot {
            self.addpt(j, ntri)?;
            ntri += 3;
        }

        let mut out = Vec::new();
        for i in 2..=nn_i {
            for j in self.lower_neighbours(i) {
                if !self.adjchk(i, j)? {
                    continue;
                }
                let k = self.pred(i, j)?;
                let (collin, a, b) = self.circen(i, k, j)?;
                if collin {
                    return Err("Vertices of triangle are collinear. Bailing out of dirseg.".to_string());
                }
                let l = self.succ(i, j)?;
                let (collin, c, d) = self.circen(i, j, l)?;
                if collin {
                    return Err("Vertices of triangle are collinear. Bailing out of dirseg.".to_string());
                }

                let xi = self.xv(i);
                let xj = self.xv(j);
                let yi = self.yv(i);
                let yj = self.yv(j);
                let (slope, rwu) = if yi != yj {
                    ((xi - xj) / (yj - yi), true)
                } else {
                    (0.0, false)
                };

                let (ai, bi, intfnd, bptab, nedgeab) = dldins(a, b, slope, rwu, rw);
                if !intfnd {
                    return Err("Line from midpoint to circumcenter does not intersect rectangle boundary! Bailing out of dirseg.".to_string());
                }
                let (ci, di, intfnd, bptcd, nedgecd) = dldins(c, d, slope, rwu, rw);
                if !intfnd {
                    return Err("Line from midpoint to circumcenter does not intersect rectangle boundary! Bailing out of dirseg.".to_string());
                }

                let mut goferit = false;
                if bptab && bptcd {
                    let xm = 0.5 * (ai + ci);
                    let ym = 0.5 * (bi + di);
                    if xmin < xm && xm < xmax && ymin < ym && ym < ymax {
                        goferit = true;
                    }
                }
                if !bptab || !bptcd {
                    goferit = true;
                }

                if goferit {
                    let bp1 = if bptab { 1.0 } else { 0.0 };
                    let bp2 = if bptcd { 1.0 } else { 0.0 };
                    let thirdv1 = if bptab { -nedgeab as f64 } else { k as f64 };
                    let thirdv2 = if bptcd { -nedgecd as f64 } else { l as f64 };
                    out.push([
                        ai,
                        bi,
                        ci,
                        di,
                        i as f64,
                        j as f64,
                        bp1,
                        bp2,
                        thirdv1,
                        thirdv2,
                    ]);
                }
            }
        }
        Ok(out)
    }

    /// Fortran `dirout`: one row `(n.tri, nbpt, area)` for each data point,
    /// with the Dirichlet tile for point i.
    fn dirout(&self, nn: usize, rw: [f64; 4], eps: f64) -> Res<Vec<[f64; 3]>> {
        let (xmin, xmax, ymin, ymax) = (rw[0], rw[1], rw[2], rw[3]);
        let mut out = Vec::with_capacity(nn);
        for i in 1..=nn as i64 {
            let mut area = 0.0;
            let mut nbpt: i64 = 0;
            let mut npt: i64 = 0;
            for &j in self.adj[pos(i)].iter() {
                let k = self.pred(i, j)?;
                let l = self.succ(i, j)?;
                let (collin, a, b) = self.circen(i, k, j)?;
                if collin {
                    return Err("Vertices of triangle are collinear. Bailing out of dirout.".to_string());
                }
                let (collin, c, d) = self.circen(i, j, l)?;
                if collin {
                    return Err("Vertices of triangle are collinear. Bailing out of dirout.".to_string());
                }

                let (tmp, sn) = stoke(a, b, c, d, rw, eps)?;
                area = area + sn * tmp;

                let xi = self.xv(i);
                let xj = self.xv(j);
                let yi = self.yv(i);
                let yj = self.yv(j);
                let (slope, rwu) = if yi != yj {
                    ((xi - xj) / (yj - yi), true)
                } else {
                    (0.0, false)
                };

                let (ai, bi, intfnd, bptab, _) = dldins(a, b, slope, rwu, rw);
                if intfnd {
                    let (ci, di, intfnd2, bptcd, _) = dldins(c, d, slope, rwu, rw);
                    if !intfnd2 {
                        return Err("Line from midpoint to circumcenter does not intersect rectangle boundary! Bailing out of dirout.".to_string());
                    }
                    if bptab && bptcd {
                        let xm = 0.5 * (ai + ci);
                        let ym = 0.5 * (bi + di);
                        if xmin < xm && xm < xmax && ymin < ym && ym < ymax {
                            nbpt += 2;
                            npt += 1;
                        }
                    } else {
                        npt += 1;
                        if bptab || bptcd {
                            nbpt += 1;
                        }
                    }
                }
            }
            out.push([npt as f64, nbpt as f64, area]);
        }
        Ok(out)
    }
}

/// Output of `binsrt`: points in bin order, and the index maps.
#[derive(Clone, Debug)]
pub struct BinsrtOut {
    pub tx: Vec<f64>,
    pub ty: Vec<f64>,
    /// `ind[i]` is the 1-based position of original point i in bin order.
    pub ind: Vec<i64>,
    /// `rind[k]` is the 1-based original index of the k-th point in bin order.
    pub rind: Vec<i64>,
}

/// Fortran `binsrt` (`src/binsrt.f90`). Sorts points into about sqrt(n) bins.
pub fn binsrt(x: &[f64], y: &[f64], rw: [f64; 4]) -> Res<BinsrtOut> {
    let n = x.len();
    if y.len() != n {
        return Err("x and y must have the same length.".to_string());
    }
    let nn = n as i64;
    let kdiv = (1.0 + (n as f64).powf(0.25)).trunc() as i64;
    let xkdiv = kdiv as f64;

    let (xmin, xmax, ymin, ymax) = (rw[0], rw[1], rw[2], rw[3]);
    let w = xmax - xmin;
    let h = ymax - ymin;
    let dw = w / xkdiv;
    let dh = h / xkdiv;

    let mut kx: i64 = 1;
    let mut ky: i64 = 1;
    let mut ink: i64 = 1;
    let mut k: i64 = 0;
    let mut ilst = vec![0i32; n];
    let mut ind = vec![0i64; n];
    let mut rind = vec![0i64; n];
    let mut tx = vec![0.0f64; n];
    let mut ty = vec![0.0f64; n];

    loop {
        for i in 0..n {
            if ilst[i] != 1 {
                let xt = x[i];
                let yt = y[i];
                let mut ix = (1.0 + (xt - xmin) / dw).trunc() as i64;
                if ix > kdiv {
                    ix = kdiv;
                }
                let mut jy = (1.0 + (yt - ymin) / dh).trunc() as i64;
                if jy > kdiv {
                    jy = kdiv;
                }
                if ix == kx && jy == ky {
                    k += 1;
                    ind[i] = k;
                    rind[(k - 1) as usize] = i as i64 + 1;
                    tx[(k - 1) as usize] = xt;
                    ty[(k - 1) as usize] = yt;
                    ilst[i] = 1;
                }
            }
        }
        let kc = kx + ink;
        if 1 <= kc && kc <= kdiv {
            kx = kc;
        } else {
            ky += 1;
            ink = -ink;
        }
        if ky > kdiv {
            break;
        }
    }

    if k != nn {
        return Err("Mismatch between number of points and number of sorted points. Bailing out of binsrt.".to_string());
    }

    Ok(BinsrtOut { tx, ty, ind, rind })
}

/// Output of `master`, in row-major order (one row per segment or point).
#[derive(Clone, Debug)]
pub struct MasterOut {
    /// Delaunay edges: `(x1, y1, x2, y2, ind1, ind2)`.
    pub delsgs: Vec<[f64; 6]>,
    /// Per point: `(x, y, n.tri, del.area)`.
    pub delsum: Vec<[f64; 4]>,
    /// Dirichlet edges: `(x1, y1, x2, y2, ind1, ind2, bp1, bp2, thirdv1, thirdv2)`.
    pub dirsgs: Vec<[f64; 10]>,
    /// Per point: `(n.tside, nbpt, dir.area)`.
    pub dirsum: Vec<[f64; 3]>,
}

/// Fortran `master` (`src/master.f90`). `x` and `y` are the bin-sorted data
/// points, with no padding. `rw` is `(xmin, xmax, ymin, ymax)`.
pub fn master(x: &[f64], y: &[f64], rw: [f64; 4], eps: f64) -> Res<MasterOut> {
    let nn = x.len();
    if y.len() != nn {
        return Err("x and y must have the same length.".to_string());
    }
    if nn < 2 {
        return Err("At least two points are needed to triangulate.".to_string());
    }
    let mut m = Mesh::new(nn, eps);
    for i in 0..nn {
        m.x[i + 4] = x[i];
        m.y[i + 4] = y[i];
    }

    // The four ideal points: (-3) = (-1,1), (-2) = (1,1), (-1) = (1,-1),
    // (0) = (-1,-1).
    m.x[0] = -1.0;
    m.y[0] = 1.0;
    m.x[1] = 1.0;
    m.y[1] = 1.0;
    m.x[2] = 1.0;
    m.y[2] = -1.0;
    m.x[3] = -1.0;
    m.y[3] = -1.0;

    for i in 1..=4i64 {
        let j = i - 4;
        let mut k = j + 1;
        if k > 0 {
            k = -3;
        }
        m.insrt(j, k)?;
    }
    for i in 1..=4i64 {
        let j = i - 4;
        m.insrt(1, j)?;
    }
    let mut ntri: i64 = 4;

    for j in 2..=nn as i64 {
        m.addpt(j, ntri)?;
        ntri += 3;
    }

    let delsgs = m.delseg(nn)?;
    let delsum = m.delout(nn)?;
    let dirsgs = m.dirseg(nn, rw, ntri)?;
    let dirsum_rows = m.dirout(nn, rw, eps)?;
    let dirsum = dirsum_rows
        .into_iter()
        .map(|r| [r[0], r[1], r[2]])
        .collect();

    Ok(MasterOut {
        delsgs,
        delsum,
        dirsgs,
        dirsum,
    })
}

/// Fortran `intri` (`src/intri.f90`). Returns 0 if any of the points
/// `(u, v)` lies strictly inside the triangle, and 1 otherwise. Called once
/// per candidate triangle from `triang.list()`.
pub fn intri(x: [f64; 3], y: [f64; 3], u: &[f64], v: &[f64]) -> Res<i32> {
    if u.len() != v.len() {
        return Err("u and v must have the same length.".to_string());
    }
    let mut s = 1.0f64;
    let a = x[1] - x[0];
    let b = y[1] - y[0];
    let c = x[2] - x[0];
    let d = y[2] - y[0];
    let cp = a * d - b * c;
    if cp < 0.0 {
        s = -s;
    }
    // Edge vectors (x[jp] - x[j], y[jp] - y[j]) do not depend on the point,
    // so they are computed once here. The per-point arithmetic is unchanged.
    let ea = [x[1] - x[0], x[2] - x[1], x[0] - x[2]];
    let eb = [y[1] - y[0], y[2] - y[1], y[0] - y[2]];
    for i in 0..u.len() {
        let mut inside = true;
        for j in 0..3 {
            let c = u[i] - x[j];
            let d = v[i] - y[j];
            let cp = s * (ea[j] * d - eb[j] * c);
            if cp <= 0.0 {
                inside = false;
                break;
            }
        }
        if inside {
            return Ok(0);
        }
    }
    Ok(1)
}
