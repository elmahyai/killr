//! Genz–Bretz multivariate probabilities, compiled from mvtnorm's Fortran.
//!
//! Uniforms, the normal and t cdfs, and the chi-squared quantile are callbacks
//! so the draws and the univariate margins stay the ones the Python side uses.

use std::os::raw::{c_double, c_int};

unsafe extern "C" {
    fn c_mvn_set_callbacks(
        unif: Option<extern "C" fn() -> c_double>,
        pnorm: Option<extern "C" fn(c_double) -> c_double>,
        qnorm: Option<extern "C" fn(c_double) -> c_double>,
        pt: Option<extern "C" fn(c_int, c_double) -> c_double>,
        sqrt_qchisq: Option<extern "C" fn(c_int, c_double) -> c_double>,
    );
    fn c_mvn_mvtdst(
        n: c_int,
        nu: c_int,
        lower: *mut c_double,
        upper: *mut c_double,
        infin: *mut c_int,
        correl: *mut c_double,
        delta: *mut c_double,
        maxpts: c_int,
        abseps: c_double,
        releps: c_double,
        error: *mut c_double,
        value: *mut c_double,
        inform: *mut c_int,
    );
    fn c_mvn_tvtl(
        nu: c_int,
        h: *mut c_double,
        r: *mut c_double,
        epsi: c_double,
        tvtl: *mut c_double,
    );
    fn c_mvn_bvtl(nu: c_int, dh: c_double, dk: c_double, r: c_double, bvtl: *mut c_double);
    fn c_mvn_miwa(
        steps: c_int,
        dim: c_int,
        corr: *const c_double,
        upper: *const c_double,
        lower: *const c_double,
        infin: *const c_int,
    ) -> c_double;
}

#[no_mangle]
pub unsafe extern "C" fn mvn_set_callbacks(
    unif: Option<extern "C" fn() -> c_double>,
    pnorm: Option<extern "C" fn(c_double) -> c_double>,
    qnorm: Option<extern "C" fn(c_double) -> c_double>,
    pt: Option<extern "C" fn(c_int, c_double) -> c_double>,
    sqrt_qchisq: Option<extern "C" fn(c_int, c_double) -> c_double>,
) {
    unsafe { c_mvn_set_callbacks(unif, pnorm, qnorm, pt, sqrt_qchisq) }
}

#[no_mangle]
pub unsafe extern "C" fn mvn_mvtdst(
    n: c_int,
    nu: c_int,
    lower: *mut c_double,
    upper: *mut c_double,
    infin: *mut c_int,
    correl: *mut c_double,
    delta: *mut c_double,
    maxpts: c_int,
    abseps: c_double,
    releps: c_double,
    error: *mut c_double,
    value: *mut c_double,
    inform: *mut c_int,
) {
    unsafe {
        c_mvn_mvtdst(
            n, nu, lower, upper, infin, correl, delta, maxpts, abseps, releps, error, value,
            inform,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn mvn_tvtl(
    nu: c_int,
    h: *mut c_double,
    r: *mut c_double,
    epsi: c_double,
    tvtl: *mut c_double,
) {
    unsafe { c_mvn_tvtl(nu, h, r, epsi, tvtl) }
}

#[no_mangle]
pub unsafe extern "C" fn mvn_miwa(
    steps: c_int,
    dim: c_int,
    corr: *const c_double,
    upper: *const c_double,
    lower: *const c_double,
    infin: *const c_int,
) -> c_double {
    unsafe { c_mvn_miwa(steps, dim, corr, upper, lower, infin) }
}

#[no_mangle]
pub unsafe extern "C" fn mvn_bvtl(
    nu: c_int,
    dh: c_double,
    dk: c_double,
    r: c_double,
    bvtl: *mut c_double,
) {
    unsafe { c_mvn_bvtl(nu, dh, dk, r, bvtl) }
}
