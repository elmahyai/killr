//! FFI to R's `optif9` (Dennis–Schnabel), compiled from `src/optif9.c`.

use std::os::raw::{c_int, c_void};

pub type Fcn = extern "C" fn(c_int, *mut f64, *mut f64, *mut c_void);
pub type D2Fcn = extern "C" fn(c_int, c_int, *mut f64, *mut f64, *mut c_void);

extern "C" {
    pub fn optif9(
        nr: c_int,
        n: c_int,
        x: *mut f64,
        fcn: Fcn,
        d1fcn: Fcn,
        d2fcn: Option<D2Fcn>,
        state: *mut c_void,
        typsiz: *mut f64,
        fscale: f64,
        method: c_int,
        iexp: c_int,
        msg: *mut c_int,
        ndigit: c_int,
        itnlim: c_int,
        iagflg: c_int,
        iahflg: c_int,
        dlt: f64,
        gradtl: f64,
        stepmx: f64,
        steptl: f64,
        xpls: *mut f64,
        fpls: *mut f64,
        gpls: *mut f64,
        itrmcd: *mut c_int,
        a: *mut f64,
        wrk: *mut f64,
        itncnt: *mut c_int,
    );
}

pub extern "C" fn dummy_grad(n: c_int, _x: *mut f64, g: *mut f64, _state: *mut c_void) {
    unsafe {
        for i in 0..n as usize {
            *g.add(i) = 0.0;
        }
    }
}
