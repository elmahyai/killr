//! Rust replicas of the C helpers in R 4.5.0 `stats/src/port.c` that `portsrc.f`
//! calls. port.c is R glue and is not compiled. Each helper is exported under
//! the Fortran symbol name (trailing underscore, arguments by reference), so the
//! Fortran objects link to these directly.
//!
//! BLAS calls (`ddot`, `dnrm2`, `dswap`) go to the system `libblas.so.3`, the
//! same library R loads on this machine, so rounding matches R's.
//!
//! Helpers that only print (`ditsum`, `dn2cvp`, `dn2rdp`, `ds7cpr`) are no-ops.
//! They print only when the trace option is on, and this crate does not
//! reproduce that output.

use std::os::raw::c_int;

#[link(name = "blas")]
unsafe extern "C" {
    fn ddot_(n: *const c_int, x: *const f64, incx: *const c_int, y: *const f64, incy: *const c_int) -> f64;
    fn dnrm2_(n: *const c_int, x: *const f64, incx: *const c_int) -> f64;
    fn dswap_(n: *const c_int, x: *mut f64, incx: *const c_int, y: *mut f64, incy: *const c_int);
}

unsafe extern "C" {
    /// `DV7DFL` from `portsrc.f`: PORT default values for `v`.
    fn dv7dfl_(alg: *const c_int, lv: *const c_int, v: *mut f64);
}

// Indices are 1-based, as in port.c and portsrc.f.
const IVNEED: usize = 3;
const VNEED: usize = 4;
const MXFCAL: usize = 17;
const MXITER: usize = 18;
const OUTLEV: usize = 19;
const PARPRT: usize = 20;
const PRUNIT: usize = 21;
const SOLPRT: usize = 22;
const STATPR: usize = 23;
const X0PRT: usize = 24;
const INITS: usize = 25;
const COVPRT: usize = 14;
const COVREQ: usize = 15;
const DTYPE: usize = 16;
const ALGSAV: usize = 51;
const PARSAV: usize = 49;
const NFCOV: usize = 52;
const NGCOV: usize = 53;
const NVDFLT: usize = 50;
const HC: usize = 71;
const IERR: usize = 75;
const INITH: usize = 25;
const IPIVOT: usize = 76;
const LASTIV: usize = 44;
const LASTV: usize = 45;
const LMAT: usize = 42;
const PERM: usize = 58;
const QRTYP: usize = 80;
const RDREQ: usize = 57;
const RMAT: usize = 78;
const VSAVE: usize = 60;
const AFCTOL: usize = 31;

const MINIV: [usize; 5] = [0, 82, 59, 103, 103];
const MINV: [usize; 5] = [0, 98, 71, 101, 85];

/// `Rf_divset` from port.c: default `iv` and `v` for algorithm `alg`.
pub fn divset(alg: i32, iv: &mut [i32], v: &mut [f64]) {
    let liv = iv.len();
    let lv = v.len();
    let set = |iv: &mut [i32], k: usize, val: i32| {
        if k <= liv {
            iv[k - 1] = val;
        }
    };
    if !(1..=4).contains(&alg) {
        return;
    }
    let alg_u = alg as usize;
    set(iv, PRUNIT, 0);
    set(iv, ALGSAV, alg);
    let miv = MINIV[alg_u];
    if liv < miv {
        iv[0] = 15;
        return;
    }
    let mv = MINV[alg_u];
    if lv < mv {
        iv[0] = 16;
        return;
    }
    let alg1 = (alg - 1) % 2 + 1;
    let lv_c = lv as c_int;
    unsafe { dv7dfl_(&alg1, &lv_c, v.as_mut_ptr()) };
    iv[0] = 12;
    set(iv, IVNEED, 0);
    set(iv, LASTIV, miv as i32);
    set(iv, LASTV, mv as i32);
    set(iv, LMAT, (mv + 1) as i32);
    set(iv, MXFCAL, 200);
    set(iv, MXITER, 150);
    set(iv, OUTLEV, 0);
    set(iv, PARPRT, 1);
    set(iv, PERM, (miv + 1) as i32);
    set(iv, SOLPRT, 0);
    set(iv, STATPR, 0);
    set(iv, VNEED, 0);
    set(iv, X0PRT, 1);

    if alg1 >= 2 {
        // General optimization constants: nlminb().
        set(iv, DTYPE, 0);
        set(iv, INITS, 1);
        set(iv, NFCOV, 0);
        set(iv, NGCOV, 0);
        set(iv, NVDFLT, 25);
        set(iv, PARSAV, if alg > 2 { 61 } else { 47 });
        v[AFCTOL - 1] = 0.0;
    } else {
        // Regression constants: nls().
        set(iv, COVPRT, 3);
        set(iv, COVREQ, 1);
        set(iv, DTYPE, 1);
        set(iv, HC, 0);
        set(iv, IERR, 0);
        set(iv, INITH, 0);
        set(iv, IPIVOT, 0);
        set(iv, NVDFLT, 32);
        set(iv, VSAVE, if alg > 2 { 61 } else { 58 });
        let vsave = iv[VSAVE - 1];
        set(iv, PARSAV, vsave + 9);
        set(iv, QRTYP, 1);
        set(iv, RDREQ, 3);
        set(iv, RMAT, 0);
    }
}

#[no_mangle]
pub unsafe extern "C" fn divset_(alg: *const c_int, iv: *mut c_int, liv: *const c_int, lv: *const c_int, v: *mut f64) {
    let iv = std::slice::from_raw_parts_mut(iv, *liv as usize);
    let v = std::slice::from_raw_parts_mut(v, *lv as usize);
    divset(*alg, iv, v);
}

#[no_mangle]
pub unsafe extern "C" fn dd7tpr_(p: *const c_int, x: *const f64, y: *const f64) -> f64 {
    let one: c_int = 1;
    ddot_(p, x, &one, y, &one)
}

#[no_mangle]
pub unsafe extern "C" fn dv2nrm_(n: *const c_int, x: *const f64) -> f64 {
    let one: c_int = 1;
    dnrm2_(n, x, &one)
}

#[no_mangle]
pub unsafe extern "C" fn dv2axy_(n: *const c_int, w: *mut f64, a: *const f64, x: *const f64, y: *const f64) {
    let n = *n as usize;
    let a = *a;
    for i in 0..n {
        *w.add(i) = a * *x.add(i) + *y.add(i);
    }
}

#[no_mangle]
pub unsafe extern "C" fn dv7cpy_(n: *const c_int, dest: *mut f64, src: *const f64) {
    let n = *n as usize;
    if n > 0 {
        std::ptr::copy(src, dest, n);
    }
}

#[no_mangle]
pub unsafe extern "C" fn dv7scp_(n: *const c_int, dest: *mut f64, c: *const f64) {
    let n = *n as usize;
    let c = *c;
    for i in 0..n {
        *dest.add(i) = c;
    }
}

#[no_mangle]
pub unsafe extern "C" fn dv7scl_(n: *const c_int, dest: *mut f64, scal: *const f64, src: *const f64) {
    let n = *n as usize;
    let sc = *scal;
    for i in 0..n {
        *dest.add(i) = sc * *src.add(i);
    }
}

#[no_mangle]
pub unsafe extern "C" fn dv7swp_(n: *const c_int, x: *mut f64, y: *mut f64) {
    let one: c_int = 1;
    dswap_(n, x, &one, y, &one);
}

#[no_mangle]
pub unsafe extern "C" fn dv7ipr_(n: *const c_int, ip: *const c_int, x: *mut f64) {
    // x[i] := x[ip[i]]  (ip holds 1-based indices)
    let n = *n as usize;
    let tmp: Vec<f64> = (0..n).map(|i| *x.add((*ip.add(i) - 1) as usize)).collect();
    for (i, val) in tmp.into_iter().enumerate() {
        *x.add(i) = val;
    }
}

#[no_mangle]
pub unsafe extern "C" fn dv7prm_(n: *const c_int, ip: *const c_int, x: *mut f64) {
    // x[ip[i]] := x[i]  (ip holds 1-based indices)
    let n = *n as usize;
    let mut tmp = vec![0.0f64; n];
    for i in 0..n {
        tmp[(*ip.add(i) - 1) as usize] = *x.add(i);
    }
    for (i, val) in tmp.into_iter().enumerate() {
        *x.add(i) = val;
    }
}

#[no_mangle]
pub unsafe extern "C" fn i7copy_(n: *const c_int, dest: *mut c_int, src: *const c_int) {
    let n = *n as usize;
    for i in 0..n {
        *dest.add(i) = *src.add(i);
    }
}

#[no_mangle]
pub unsafe extern "C" fn i7pnvr_(n: *const c_int, x: *mut c_int, y: *const c_int) {
    // x[y[i]] := i + 1  (y holds 1-based indices)
    let n = *n as usize;
    for i in 0..n {
        *x.add((*y.add(i) - 1) as usize) = (i + 1) as c_int;
    }
}

/// `D1MACH` for IEEE double, as in R's `appl/d1mach.c`.
#[no_mangle]
pub unsafe extern "C" fn d1mach_(i: *const c_int) -> f64 {
    match *i {
        1 => f64::MIN_POSITIVE,
        2 => f64::MAX,
        3 => f64::EPSILON / 2.0,
        4 => f64::EPSILON,
        5 => std::f64::consts::LOG10_2,
        _ => 0.0,
    }
}

#[no_mangle]
pub unsafe extern "C" fn ditsum_(
    _d: *const f64,
    _g: *const f64,
    _iv: *const c_int,
    _liv: *const c_int,
    _lv: *const c_int,
    _n: *const c_int,
    _v: *const f64,
    _x: *const f64,
) {
}

#[no_mangle]
pub unsafe extern "C" fn dn2cvp_(_iv: *const c_int, _liv: *const c_int, _lv: *const c_int, _p: *const c_int, _v: *const f64) {}

#[no_mangle]
pub unsafe extern "C" fn dn2rdp_(
    _iv: *const c_int,
    _liv: *const c_int,
    _lv: *const c_int,
    _n: *const c_int,
    _rd: *const f64,
    _v: *const f64,
) {
}

#[no_mangle]
pub unsafe extern "C" fn ds7cpr_(_c: *const f64, _iv: *const c_int, _l: *const c_int, _liv: *const c_int) {}
