//! 1-based work arrays for PORT SUMSL. Index 0 is unused.
//! `G` is not a separate vector: it is `V(IV(G) ..)`.

use crate::blas_ref::{d1mach, dmax1, dot, nrm2};

pub struct Work {
    pub n: i32,
    pub iv: Vec<i32>,
    pub v: Vec<f64>,
    pub d: Vec<f64>,
    pub x: Vec<f64>,
    pub fx: f64,
    pub g1: i32,
}

impl Work {
    pub fn new(n: i32, x0: &[f64], liv: i32, lv: i32) -> Self {
        let mut x = vec![0.0; (n as usize) + 1];
        let mut d = vec![0.0; (n as usize) + 1];
        for i in 1..=n {
            x[i as usize] = x0[(i as usize) - 1];
            d[i as usize] = 1.0;
        }
        Self {
            n,
            iv: vec![0; (liv as usize) + 1],
            v: vec![0.0; (lv as usize) + 1],
            d,
            x,
            fx: 0.0,
            g1: 1,
        }
    }

    pub fn ig(&self, i: i32) -> i32 {
        self.iv[i as usize]
    }
    pub fn iset(&mut self, i: i32, val: i32) {
        self.iv[i as usize] = val;
    }
    pub fn vg(&self, i: i32) -> f64 {
        self.v[i as usize]
    }
    pub fn vs(&mut self, i: i32, val: f64) {
        self.v[i as usize] = val;
    }
    pub fn av(&self, base: i32, i: i32) -> f64 {
        self.v[(base + i - 1) as usize]
    }
    pub fn sv(&mut self, base: i32, i: i32, val: f64) {
        self.v[(base + i - 1) as usize] = val;
    }
    pub fn xg(&self, i: i32) -> f64 {
        self.x[i as usize]
    }
    pub fn xs(&mut self, i: i32, val: f64) {
        self.x[i as usize] = val;
    }
    pub fn dg(&self, i: i32) -> f64 {
        self.d[i as usize]
    }
    pub fn g(&self, i: i32) -> f64 {
        self.av(self.g1, i)
    }

    pub fn dotv(&self, n: i32, x: i32, y: i32) -> f64 {
        dot(&self.v, n, x, y)
    }
    pub fn nrm(&self, n: i32, x: i32) -> f64 {
        nrm2(&self.v, n, x)
    }

    pub fn copy_vv(&mut self, n: i32, src: i32, dst: i32) {
        if src == dst || n <= 0 {
            return;
        }
        let tmp: Vec<f64> = (0..n).map(|i| self.v[(src + i) as usize]).collect();
        for i in 0..n {
            self.v[(dst + i) as usize] = tmp[i as usize];
        }
    }
    pub fn copy_to_v(&mut self, n: i32, src: &[f64], src0: i32, dst: i32) {
        for i in 1..=n {
            self.v[(dst + i - 1) as usize] = src[(src0 + i - 1) as usize];
        }
    }
    pub fn copy_x_to_v(&mut self, n: i32, dst: i32) {
        for i in 1..=n {
            let val = self.x[i as usize];
            self.v[(dst + i - 1) as usize] = val;
        }
    }
    pub fn copy_v_to_x(&mut self, n: i32, src: i32) {
        for i in 1..=n {
            self.x[i as usize] = self.v[(src + i - 1) as usize];
        }
    }
    pub fn fill_v(&mut self, n: i32, base: i32, s: f64) {
        for i in 1..=n {
            self.sv(base, i, s);
        }
    }
    pub fn vaxpy_vv(&mut self, n: i32, w: i32, a: f64, x: i32, y: i32) {
        for i in 1..=n {
            let val = a * self.av(x, i) + self.av(y, i);
            self.sv(w, i, val);
        }
    }
    /// `W(i) = a * X(i) + Y(i)` with `X` and `Y` in `V` and `W` the parameter vector.
    pub fn vaxpy_x(&mut self, n: i32, a: f64, x: i32, y: i32) {
        for i in 1..=n {
            self.x[i as usize] = a * self.av(x, i) + self.av(y, i);
        }
    }
    pub fn vvmup(&mut self, n: i32, x: i32, y: i32, z_is_d: bool, mul: bool) {
        for i in 1..=n {
            let yv = self.av(y, i);
            let zv = if z_is_d { self.d[i as usize] } else { self.av(y, i) };
            let _ = zv;
            let val = if mul {
                self.av(y, i) * self.d[i as usize]
            } else {
                yv / self.d[i as usize]
            };
            self.sv(x, i, val);
        }
    }
}

pub fn put_scaled(w: &mut Work, base: i32, idx: i32, val: f64) {
    w.v[(base + idx - 1) as usize] = val;
}

pub fn dvdflt(w: &mut Work, alg: i32, base: i32) {
    let machep = d1mach(4);
    let one = 1.0;
    let three = 3.0;
    let sqteps = d1mach(4).sqrt();
    let mepcrt = machep.powf(one / three);
    let mut afctol = 1.0e-20;
    if machep > 1.0e-10 {
        afctol = machep * machep;
    }
    put_scaled(w, base, 31, afctol);
    put_scaled(w, base, 22, 0.5);
    put_scaled(w, base, 41, 0.6);
    put_scaled(w, base, 44, sqteps);
    put_scaled(w, base, 39, 1.0e-6);
    put_scaled(w, base, 40, 1.0);
    put_scaled(w, base, 19, 0.1);
    put_scaled(w, base, 23, 2.0);
    put_scaled(w, base, 35, 1.0);
    put_scaled(w, base, 36, 1.0);
    put_scaled(w, base, 20, -0.1);
    put_scaled(w, base, 21, 0.1);
    put_scaled(w, base, 24, 0.1);
    put_scaled(w, base, 25, 4.0);
    let rfctol = dmax1(1.0e-10, mepcrt * mepcrt);
    put_scaled(w, base, 32, rfctol);
    put_scaled(w, base, 37, rfctol);
    put_scaled(w, base, 26, 0.1);
    put_scaled(w, base, 27, 1.0e-4);
    put_scaled(w, base, 28, 0.75);
    put_scaled(w, base, 29, 0.5);
    put_scaled(w, base, 30, 0.75);
    put_scaled(w, base, 33, sqteps);
    put_scaled(w, base, 34, 1.0e2 * machep);
    if alg >= 2 {
        put_scaled(w, base, 43, 0.8);
        put_scaled(w, base, 38, -1.0);
        put_scaled(w, base, 42, 1.0e3 * machep);
        return;
    }
    put_scaled(w, base, 47, dmax1(1.0e-6, 1.0e2 * machep));
    put_scaled(w, base, 38, 0.0);
    put_scaled(w, base, 42, mepcrt);
    put_scaled(w, base, 43, sqteps);
    put_scaled(w, base, 45, 1.5);
    put_scaled(w, base, 48, 0.7);
    put_scaled(w, base, 46, d1mach(2).sqrt() * 16.0);
    put_scaled(w, base, 49, 1.0e-2);
    put_scaled(w, base, 50, 1.0e-4);
}

pub fn ddeflt(w: &mut Work, alg: i32) {
    const ALGSAV: i32 = 51;
    const COVPRT: i32 = 14;
    const COVREQ: i32 = 15;
    const DTYPE: i32 = 16;
    const HC: i32 = 71;
    const IERR: i32 = 75;
    const INITH: i32 = 25;
    const IPIVOT: i32 = 76;
    const IVNEED: i32 = 3;
    const LASTIV: i32 = 44;
    const LASTV: i32 = 45;
    const LMAT: i32 = 42;
    const MXFCAL: i32 = 17;
    const MXITER: i32 = 18;
    const NFCOV: i32 = 52;
    const NGCOV: i32 = 53;
    const NVDFLT: i32 = 50;
    const OUTLEV: i32 = 19;
    const PARPRT: i32 = 20;
    const PARSAV: i32 = 49;
    const PERM: i32 = 58;
    const PRUNIT: i32 = 21;
    const QRTYP: i32 = 80;
    const RDREQ: i32 = 57;
    const RMAT: i32 = 78;
    const SOLPRT: i32 = 22;
    const STATPR: i32 = 23;
    const VNEED: i32 = 4;
    const VSAVE: i32 = 60;
    const X0PRT: i32 = 24;
    if alg < 1 || alg > 2 {
        w.iset(1, 67);
        return;
    }
    let miniv = [0, 80, 59];
    let minv = [0, 98, 71];
    let miv = miniv[alg as usize];
    let liv = (w.iv.len() as i32) - 1;
    let lv = (w.v.len() as i32) - 1;
    if liv < miv {
        w.iset(1, 15);
        return;
    }
    let mv = minv[alg as usize];
    if lv < mv {
        w.iset(1, 16);
        return;
    }
    dvdflt(w, alg, 1);
    w.iset(1, 12);
    w.iset(ALGSAV, alg);
    w.iset(IVNEED, 0);
    w.iset(LASTIV, miv);
    w.iset(LASTV, mv);
    w.iset(LMAT, mv + 1);
    w.iset(MXFCAL, 200);
    w.iset(MXITER, 150);
    w.iset(OUTLEV, 1);
    w.iset(PARPRT, 1);
    w.iset(PERM, miv + 1);
    w.iset(PRUNIT, 6);
    w.iset(SOLPRT, 1);
    w.iset(STATPR, 1);
    w.iset(VNEED, 0);
    w.iset(X0PRT, 1);
    if alg >= 2 {
        w.iset(DTYPE, 0);
        w.iset(INITH, 1);
        w.iset(NFCOV, 0);
        w.iset(NGCOV, 0);
        w.iset(NVDFLT, 25);
        w.iset(PARSAV, 47);
        return;
    }
    w.iset(COVPRT, 3);
    w.iset(COVREQ, 1);
    w.iset(DTYPE, 1);
    w.iset(HC, 0);
    w.iset(IERR, 0);
    w.iset(INITH, 0);
    w.iset(IPIVOT, 0);
    w.iset(NVDFLT, 32);
    w.iset(PARSAV, 67);
    w.iset(QRTYP, 1);
    w.iset(RDREQ, 3);
    w.iset(RMAT, 0);
    w.iset(VSAVE, 58);
}

fn imax(a: i32, b: i32) -> i32 {
    if a >= b { a } else { b }
}

pub fn dparck(w: &mut Work, alg: i32) {
    const ALGSAV: i32 = 51;
    const DINIT: i32 = 38;
    const DTYPE: i32 = 16;
    const DTYPE0: i32 = 54;
    const EPSLON: i32 = 19;
    const IVNEED: i32 = 3;
    const LASTIV: i32 = 44;
    const LASTV: i32 = 45;
    const LMAT: i32 = 42;
    const NEXTIV: i32 = 46;
    const NEXTV: i32 = 47;
    const NVDFLT: i32 = 50;
    const OLDN: i32 = 38;
    const PARPRT: i32 = 20;
    const PARSAV: i32 = 49;
    const PERM: i32 = 58;
    const PRUNIT: i32 = 21;
    const VNEED: i32 = 4;
    let liv = (w.iv.len() as i32) - 1;
    let lv = (w.v.len() as i32) - 1;
    if alg < 1 || alg > 2 {
        w.iset(1, 67);
        return;
    }
    if w.ig(1) == 0 {
        ddeflt(w, alg);
    }
    let pu = w.ig(PRUNIT);
    let miniv = [0, 80, 59];
    let mut miv1 = miniv[alg as usize];
    if PERM <= liv {
        miv1 = imax(miv1, w.ig(PERM) - 1);
    }
    let miv2 = if IVNEED <= liv {
        miv1 + imax(w.ig(IVNEED), 0)
    } else {
        0
    };
    if LASTIV <= liv {
        w.iset(LASTIV, miv2);
    }
    if liv < miv1 {
        w.iset(1, 15);
        return;
    }
    w.iset(IVNEED, 0);
    w.iset(LASTV, imax(w.ig(VNEED), 0) + w.ig(LMAT) - 1);
    if liv < miv2 {
        w.iset(1, 15);
        return;
    }
    if lv < w.ig(LASTV) {
        w.iset(1, 16);
        return;
    }
    w.iset(VNEED, 0);
    if alg != w.ig(ALGSAV) {
        w.iset(1, 82);
        return;
    }
    let mut iv1 = w.ig(1);
    if (12..15).contains(&iv1) {
        if w.n < 1 {
            w.iset(1, 81);
            return;
        }
        if iv1 != 14 {
            w.iset(NEXTIV, w.ig(PERM));
            w.iset(NEXTV, w.ig(LMAT));
        }
        if iv1 == 13 {
            return;
        }
        let k = w.ig(PARSAV) - EPSLON;
        dvdflt(w, alg, k + 1);
        w.iset(DTYPE0, 2 - alg);
        w.iset(OLDN, w.n);
    } else if w.n != w.ig(OLDN) {
        w.iset(1, 17);
        return;
    } else if !(1..=11).contains(&iv1) {
        w.iset(1, 80);
        return;
    }
    if iv1 == 14 {
        iv1 = 12;
    }
    let tiny = d1mach(1);
    let machep = d1mach(4);
    let big = d1mach(2);
    let mut vm = [0.0; 35];
    let mut vx = [0.0; 35];
    vm[1] = 1.0e-3;
    vm[2] = -0.99;
    vm[3] = 1.0e-3;
    vm[4] = 1.0e-2;
    vm[5] = 1.2;
    vm[6] = 1.0e-2;
    vm[7] = 1.2;
    vm[10] = 1.0e-3;
    vm[11] = -1.0;
    vm[20] = -10.0;
    vm[27] = 1.01;
    vx[1] = 0.9;
    vx[2] = -1.0e-3;
    vx[3] = 10.0;
    vx[4] = 0.8;
    vx[5] = 100.0;
    vx[6] = 0.8;
    vx[7] = 100.0;
    vx[8] = 0.5;
    vx[9] = 0.5;
    vx[10] = 1.0;
    vx[11] = 1.0;
    vx[14] = 0.1;
    vx[15] = 1.0;
    vx[16] = 1.0;
    vx[19] = 1.0;
    vx[23] = 1.0;
    vx[24] = 1.0;
    vx[25] = 1.0;
    vx[26] = 1.0;
    vx[27] = 1.0e10;
    vx[29] = 1.0;
    vx[31] = 1.0;
    vx[32] = 1.0;
    vx[33] = 1.0;
    vx[34] = 1.0;
    vm[12] = machep;
    vx[12] = big;
    vm[13] = tiny;
    vx[13] = big;
    vm[14] = machep;
    vm[17] = tiny;
    vx[17] = big;
    vm[18] = tiny;
    vx[18] = big;
    vx[20] = big;
    vx[21] = big;
    vx[22] = big;
    vm[24] = machep;
    vm[25] = machep;
    vm[26] = machep;
    vx[28] = d1mach(2).sqrt() * 16.0;
    vm[29] = machep;
    vx[30] = big;
    vm[33] = machep;
    let jlim = [0, 0, 24];
    let ndflt = [0, 32, 25];
    let ijmp = 33;
    let mut m = 0i32;
    let mut i = 1i32;
    let j = jlim[alg as usize];
    let mut k = EPSLON;
    let ndfalt = ndflt[alg as usize];
    for _l in 1..=ndfalt {
        let vk = w.vg(k);
        if !(vk >= vm[i as usize] && vk <= vx[i as usize]) {
            m = k;
        }
        k += 1;
        i += 1;
        if i == j {
            i = ijmp;
        }
    }
    if w.ig(NVDFLT) != ndfalt {
        w.iset(1, 51);
        return;
    }
    let skip_d = (w.ig(DTYPE) > 0 || w.vg(DINIT) > 0.0) && iv1 == 12;
    if !skip_d {
        for ii in 1..=w.n {
            if w.dg(ii) > 0.0 {
                break;
            }
            m = 18;
        }
    }
    if m != 0 {
        w.iset(1, m);
        return;
    }
    if pu == 0 || w.ig(PARPRT) == 0 {
        return;
    }
    // Trace printing does not change the step. Copy the saved defaults the
    // way DPARCK does when the print unit is on, then return.
    w.iset(DTYPE0, w.ig(DTYPE));
    let parsv1 = w.ig(PARSAV);
    w.copy_vv(w.ig(NVDFLT), EPSLON, parsv1);
}
