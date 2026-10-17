//! Kernels of the R package mix 1.0-13 (`src/mix.f`): the routines that `prelim.mix`,
//! `em.mix`, `da.mix`, `imp.mix` and `rngseed` call through `.Fortran`.
//!
//! The Fortran is the kernel. `build.rs` compiles `vendor/mix.f` with gfortran and
//! links it statically, and this crate calls each routine by its Fortran symbol with
//! the argument list of the R `.Fortran` call. Nothing is re-ported, so the Park-Miller
//! generator (`rangen`), the Box-Muller normal (`gauss`) and the gamma deviate (`gamm`)
//! keep their state and their single precision exactly as R has them.
//!
//! Every argument is passed by reference, as Fortran expects. The Python layer copies
//! each argument into a new Fortran-ordered array before the call, so the caller's
//! arrays are not changed, as R's `.Fortran` does not change them.
//!
//! Indices are 1-based, as in the Fortran. The state of `rangen` (its seed) and of
//! `gauss` (the cached second deviate) lives in the loaded library and persists across
//! calls, as it does in an R session.

#![allow(clippy::too_many_arguments)]

#[cfg(feature = "python")]
mod python;

unsafe extern "C" {
    pub fn rngs_(seed: *mut i32);
    pub fn mkpsi_(p: *mut i32, psi: *mut i32);
    pub fn ctrsc_(
        x: *mut f64,
        n: *mut i32,
        p: *mut i32,
        xbar: *mut f64,
        sdv: *mut f64,
        mvcode: *mut f64,
    );
    pub fn tobsm_(
        q: *mut i32,
        psi: *mut i32,
        npsi: *mut i32,
        t1: *mut f64,
        ncells: *mut i32,
        t2: *mut f64,
        t3: *mut f64,
        npattz: *mut i32,
        rz: *mut i32,
        mdpzgrp: *mut i32,
        npattw: *mut i32,
        p: *mut i32,
        rw: *mut i32,
        mdpwgrp: *mut i32,
        ngrp: *mut i32,
        mobs: *mut i32,
        mobsst: *mut i32,
        nmobs: *mut i32,
        n: *mut i32,
        z: *mut f64,
        ocw: *mut i32,
        ocz: *mut i32,
    );
    pub fn stvlm_(
        q: *mut i32,
        psi: *mut i32,
        npsi: *mut i32,
        t1: *mut f64,
        ncells: *mut i32,
        t2: *mut f64,
    );
    pub fn estepm_(
        q: *mut i32,
        psi: *mut i32,
        npsi: *mut i32,
        ncells: *mut i32,
        sigma: *mut f64,
        mu: *mut f64,
        pii: *mut f64,
        kn1: *mut f64,
        kn2: *mut f64,
        kn3: *mut f64,
        t1: *mut f64,
        t2: *mut f64,
        t3: *mut f64,
        npattz: *mut i32,
        rz: *mut i32,
        mcz: *mut i32,
        ocz: *mut i32,
        mdpzgrp: *mut i32,
        npattw: *mut i32,
        p: *mut i32,
        rw: *mut i32,
        mcw: *mut i32,
        mdpwgrp: *mut i32,
        ngrp: *mut i32,
        mobs: *mut i32,
        mobsst: *mut i32,
        nmobs: *mut i32,
        n: *mut i32,
        z: *mut f64,
        d: *mut i32,
        jmp: *mut i32,
        c: *mut i32,
        theta: *mut f64,
    );
    pub fn mstepm_(
        q: *mut i32,
        psi: *mut i32,
        npsi: *mut i32,
        ncells: *mut i32,
        t1: *mut f64,
        t2: *mut f64,
        t3: *mut f64,
        n: *mut i32,
        prior: *mut f64,
    );
    pub fn istepm_(
        q: *mut i32,
        psi: *mut i32,
        npsi: *mut i32,
        ncells: *mut i32,
        sigma: *mut f64,
        mu: *mut f64,
        pii: *mut f64,
        kn1: *mut f64,
        kn2: *mut f64,
        kn3: *mut f64,
        t1: *mut f64,
        t2: *mut f64,
        t3: *mut f64,
        npattz: *mut i32,
        rz: *mut i32,
        mcz: *mut i32,
        ocz: *mut i32,
        mdpzgrp: *mut i32,
        npattw: *mut i32,
        p: *mut i32,
        rw: *mut i32,
        mcw: *mut i32,
        mdpwgrp: *mut i32,
        ngrp: *mut i32,
        mobs: *mut i32,
        mobsst: *mut i32,
        nmobs: *mut i32,
        n: *mut i32,
        z: *mut f64,
        d: *mut i32,
        jmp: *mut i32,
        c: *mut i32,
        theta: *mut f64,
        chf: *mut f64,
        w: *mut i32,
        zz: *mut f64,
    );
    pub fn pstepm_(
        q: *mut i32,
        psi: *mut i32,
        npsi: *mut i32,
        ncells: *mut i32,
        t1: *mut f64,
        t2: *mut f64,
        t3: *mut f64,
        n: *mut i32,
        p: *mut i32,
        prior: *mut f64,
        chf: *mut f64,
        mx: *mut f64,
        zz: *mut f64,
        mcz: *mut i32,
        err: *mut f64,
    );
    pub fn lobsm_(
        q: *mut i32,
        psi: *mut i32,
        npsi: *mut i32,
        ncells: *mut i32,
        sigma: *mut f64,
        mu: *mut f64,
        pii: *mut f64,
        npattz: *mut i32,
        rz: *mut i32,
        mcz: *mut i32,
        ocz: *mut i32,
        mdpzgrp: *mut i32,
        npattw: *mut i32,
        p: *mut i32,
        rw: *mut i32,
        mcw: *mut i32,
        mdpwgrp: *mut i32,
        ngrp: *mut i32,
        mobs: *mut i32,
        mobsst: *mut i32,
        nmobs: *mut i32,
        n: *mut i32,
        z: *mut f64,
        d: *mut i32,
        jmp: *mut i32,
        c: *mut i32,
        ll: *mut f64,
    );
    pub fn mstepcm_(
        q: *mut i32,
        psi: *mut i32,
        npsi: *mut i32,
        ncells: *mut i32,
        t1: *mut f64,
        t2: *mut f64,
        t3: *mut f64,
        sigma: *mut f64,
        mu: *mut f64,
        n: *mut i32,
        r: *mut i32,
        design: *mut f64,
        wk: *mut f64,
        mcr: *mut i32,
        psir: *mut i32,
        npsir: *mut i32,
        wkr: *mut f64,
        wkd: *mut f64,
        beta: *mut f64,
    );
    pub fn ipf_(
        ncells: *mut i32,
        table: *mut f64,
        fit: *mut f64,
        ncon: *mut i32,
        con: *mut i32,
        p: *mut i32,
        d: *mut i32,
        jmp: *mut i32,
        c: *mut i32,
        marg: *mut i32,
        rest: *mut i32,
        eps: *mut f64,
    );
    pub fn pstepcm_(
        q: *mut i32,
        psi: *mut i32,
        npsi: *mut i32,
        ncells: *mut i32,
        t1: *mut f64,
        t2: *mut f64,
        t3: *mut f64,
        sigma: *mut f64,
        mu: *mut f64,
        n: *mut i32,
        r: *mut i32,
        design: *mut f64,
        wk: *mut f64,
        mcr: *mut i32,
        psir: *mut i32,
        npsir: *mut i32,
        wkr: *mut f64,
        wkd: *mut f64,
        mcz: *mut i32,
        chf: *mut f64,
        beta: *mut f64,
        mx: *mut f64,
    );
    pub fn bipf_(
        ncells: *mut i32,
        table: *mut f64,
        theta: *mut f64,
        prior: *mut f64,
        ncon: *mut i32,
        con: *mut i32,
        p: *mut i32,
        d: *mut i32,
        jmp: *mut i32,
        c: *mut i32,
        marg: *mut i32,
        rest: *mut i32,
        err: *mut i32,
    );
}

/// Called by `rangen` when it is used before `rngs` has set a seed. R stops with an
/// error here. Returning would let `gamm` loop forever on a zero generator, so the
/// process stops with the same message. The Python layer checks for a seed before any
/// call that draws, so this is not reached in normal use.
#[no_mangle]
pub extern "C" fn rexit_(msg: *const u8, len: usize) {
    let text = unsafe { std::slice::from_raw_parts(msg, len) };
    eprintln!("mix_kernel: {}", String::from_utf8_lossy(text));
    std::process::abort();
}
