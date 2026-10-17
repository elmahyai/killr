//! Covariance-model kernels from mclust `src/mclust.f`, `mclust2.f`, and `util.f`.
//!
//! Each function is the Fortran subroutine of the same name. Arrays are
//! column-major, matching R `.Fortran`. Logical flags (`EQPRO`, `CHOL`) are
//! 4-byte integers: `0` is false and `1` is true. Scalar outputs are overwritten
//! in place, the same way the Fortran dummy arguments are.

unsafe extern "C" {
    fn es1e_(x: *mut f64, mu: *mut f64, sigsq: *mut f64, pro: *mut f64, n: *mut i32, g: *mut i32, vinv: *mut f64, hood: *mut f64, z: *mut f64);
    fn hc1e_(x: *mut f64, n: *mut i32, ic: *mut i32, ng: *mut i32, ns: *mut i32, nd: *mut i32, d: *mut f64);
    fn me1e_(eqpro: *mut i32, x: *mut f64, n: *mut i32, g: *mut i32, vinv: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, mu: *mut f64, sigsq: *mut f64, pro: *mut f64);
    fn me1ep_(eqpro: *mut i32, x: *mut f64, n: *mut i32, g: *mut i32, vinv: *mut f64, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, mu: *mut f64, sigsq: *mut f64, pro: *mut f64);
    fn ms1e_(x: *mut f64, z: *mut f64, n: *mut i32, g: *mut i32, mu: *mut f64, sigsq: *mut f64, pro: *mut f64);
    fn ms1ep_(x: *mut f64, z: *mut f64, n: *mut i32, g: *mut i32, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, mu: *mut f64, sigsq: *mut f64, pro: *mut f64);
    fn eseee_(chol: *mut i32, x: *mut f64, mu: *mut f64, sigma: *mut f64, pro: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, w: *mut f64, hood: *mut f64, z: *mut f64);
    fn meeee_(eqpro: *mut i32, x: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, mu: *mut f64, u: *mut f64, pro: *mut f64, w: *mut f64);
    fn meeeep_(eqpro: *mut i32, x: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, mu: *mut f64, u: *mut f64, pro: *mut f64, w: *mut f64);
    fn mseee_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, w: *mut f64, mu: *mut f64, u: *mut f64, pro: *mut f64);
    fn mseeep_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, w: *mut f64, mu: *mut f64, u: *mut f64, pro: *mut f64);
    fn eseei_(x: *mut f64, mu: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, hood: *mut f64, z: *mut f64);
    fn meeei_(eqpro: *mut i32, x: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, mu: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64);
    fn meeeip_(eqpro: *mut i32, x: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, mu: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64);
    fn mseei_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, mu: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64);
    fn mseeip_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, mu: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64);
    fn eseev_(x: *mut f64, mu: *mut f64, scale: *mut f64, shape: *mut f64, o: *mut f64, pro: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, v: *mut f64, w: *mut f64, hood: *mut f64, z: *mut f64);
    fn meeev_(eqpro: *mut i32, x: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, lwork: *mut i32, mu: *mut f64, scale: *mut f64, shape: *mut f64, o: *mut f64, pro: *mut f64, w: *mut f64, s: *mut f64);
    fn meeevp_(eqpro: *mut i32, x: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, lwork: *mut i32, mu: *mut f64, scale: *mut f64, shape: *mut f64, o: *mut f64, pro: *mut f64, w: *mut f64, s: *mut f64);
    fn mseev_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, w: *mut f64, lwork: *mut i32, mu: *mut f64, scale: *mut f64, shape: *mut f64, o: *mut f64, pro: *mut f64);
    fn mseevp_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, w: *mut f64, lwork: *mut i32, mu: *mut f64, scale: *mut f64, shape: *mut f64, o: *mut f64, pro: *mut f64);
    fn eseii_(x: *mut f64, mu: *mut f64, sigsq: *mut f64, pro: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, hood: *mut f64, z: *mut f64);
    fn hceii_(x: *mut f64, n: *mut i32, p: *mut i32, ic: *mut i32, ng: *mut i32, ns: *mut i32, v: *mut f64, nd: *mut i32, d: *mut f64);
    fn meeii_(eqpro: *mut i32, x: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, mu: *mut f64, sigsq: *mut f64, pro: *mut f64);
    fn meeiip_(eqpro: *mut i32, x: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, mu: *mut f64, sigsq: *mut f64, pro: *mut f64);
    fn mseii_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, mu: *mut f64, sigsq: *mut f64, pro: *mut f64);
    fn mseiip_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, mu: *mut f64, sigsq: *mut f64, pro: *mut f64);
    fn esevi_(x: *mut f64, mu: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, hood: *mut f64, z: *mut f64);
    fn meevi_(eqpro: *mut i32, x: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, mu: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64);
    fn meevip_(eqpro: *mut i32, x: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, mu: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64);
    fn msevi_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, mu: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64);
    fn msevip_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, mu: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64);
    fn es1v_(x: *mut f64, mu: *mut f64, sigsq: *mut f64, pro: *mut f64, n: *mut i32, g: *mut i32, vinv: *mut f64, hood: *mut f64, z: *mut f64);
    fn hc1v_(x: *mut f64, n: *mut i32, ic: *mut i32, ng: *mut i32, ns: *mut i32, alpha: *mut f64, nd: *mut i32, d: *mut f64);
    fn me1v_(eqpro: *mut i32, x: *mut f64, n: *mut i32, g: *mut i32, vinv: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, mu: *mut f64, sigsq: *mut f64, pro: *mut f64);
    fn me1vp_(eqpro: *mut i32, x: *mut f64, n: *mut i32, g: *mut i32, vinv: *mut f64, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, mu: *mut f64, sigsq: *mut f64, pro: *mut f64);
    fn ms1v_(x: *mut f64, z: *mut f64, n: *mut i32, g: *mut i32, mu: *mut f64, sigsq: *mut f64, pro: *mut f64);
    fn ms1vp_(x: *mut f64, z: *mut f64, n: *mut i32, g: *mut i32, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, mu: *mut f64, sigsq: *mut f64, pro: *mut f64);
    fn esvei_(x: *mut f64, mu: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, hood: *mut f64, z: *mut f64);
    fn mevei_(eqpro: *mut i32, x: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, mu: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64, scl: *mut f64, shp: *mut f64, w: *mut f64);
    fn meveip_(eqpro: *mut i32, x: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, mu: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64, scl: *mut f64, shp: *mut f64, w: *mut f64);
    fn msvei_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, maxi: *mut i32, tol: *mut f64, mu: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64, scl: *mut f64, shp: *mut f64, w: *mut f64);
    fn msveip_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, maxi: *mut i32, tol: *mut f64, mu: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64, scl: *mut f64, shp: *mut f64, w: *mut f64);
    fn esvev_(x: *mut f64, mu: *mut f64, scale: *mut f64, shape: *mut f64, o: *mut f64, pro: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, v: *mut f64, w: *mut f64, hood: *mut f64, z: *mut f64);
    fn mevev_(eqpro: *mut i32, x: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, lwork: *mut i32, mu: *mut f64, scale: *mut f64, shape: *mut f64, o: *mut f64, pro: *mut f64, w: *mut f64, s: *mut f64);
    fn mevevp_(eqpro: *mut i32, x: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, lwork: *mut i32, mu: *mut f64, scale: *mut f64, shape: *mut f64, o: *mut f64, pro: *mut f64, w: *mut f64, s: *mut f64);
    fn msvev_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, w: *mut f64, lwork: *mut i32, maxi: *mut i32, tol: *mut f64, mu: *mut f64, scale: *mut f64, shape: *mut f64, o: *mut f64, pro: *mut f64);
    fn msvevp_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, w: *mut f64, lwork: *mut i32, maxi: *mut i32, tol: *mut f64, mu: *mut f64, scale: *mut f64, shape: *mut f64, o: *mut f64, pro: *mut f64);
    fn esvii_(x: *mut f64, mu: *mut f64, sigsq: *mut f64, pro: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, hood: *mut f64, z: *mut f64);
    fn hcvii_(x: *mut f64, n: *mut i32, p: *mut i32, ic: *mut i32, ng: *mut i32, ns: *mut i32, alpha: *mut f64, v: *mut f64, nd: *mut i32, d: *mut f64);
    fn mevii_(eqpro: *mut i32, x: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, mu: *mut f64, sigsq: *mut f64, pro: *mut f64);
    fn meviip_(eqpro: *mut i32, x: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, mu: *mut f64, sigsq: *mut f64, pro: *mut f64);
    fn msvii_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, mu: *mut f64, sigsq: *mut f64, pro: *mut f64);
    fn msviip_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, mu: *mut f64, sigsq: *mut f64, pro: *mut f64);
    fn esvvi_(x: *mut f64, mu: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, hood: *mut f64, z: *mut f64);
    fn mevvi_(eqpro: *mut i32, x: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, mu: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64);
    fn mevvip_(eqpro: *mut i32, x: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, mu: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64);
    fn msvvi_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, mu: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64);
    fn msvvip_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, mu: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64);
    fn esvvv_(chol: *mut i32, x: *mut f64, mu: *mut f64, sigma: *mut f64, pro: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, w: *mut f64, hood: *mut f64, z: *mut f64);
    fn hcvvv_(x: *mut f64, n: *mut i32, p: *mut i32, ic: *mut i32, ng: *mut i32, ns: *mut i32, alpha: *mut f64, beta: *mut f64, v: *mut f64, u: *mut f64, s: *mut f64, r: *mut f64, nd: *mut i32, d: *mut f64);
    fn mcltrw_(x: *mut f64, n: *mut i32, p: *mut i32, u: *mut f64, ss: *mut f64);
    fn mevvv_(eqpro: *mut i32, x: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, mu: *mut f64, u: *mut f64, pro: *mut f64, w: *mut f64, s: *mut f64);
    fn mevvvp_(eqpro: *mut i32, x: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, vinv: *mut f64, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, z: *mut f64, maxi: *mut i32, tol: *mut f64, eps: *mut f64, mu: *mut f64, u: *mut f64, pro: *mut f64, w: *mut f64, s: *mut f64);
    fn msvvv_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, w: *mut f64, mu: *mut f64, u: *mut f64, pro: *mut f64, s: *mut f64);
    fn msvvvp_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, w: *mut f64, mu: *mut f64, u: *mut f64, pro: *mut f64, s: *mut f64);
    fn mvn1d_(x: *mut f64, n: *mut i32, mu: *mut f64, sigsq: *mut f64, hood: *mut f64);
    fn mvn1p_(x: *mut f64, n: *mut i32, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, mu: *mut f64, sigsq: *mut f64, hood: *mut f64);
    fn mnxiip_(x: *mut f64, n: *mut i32, p: *mut i32, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, mu: *mut f64, sigsq: *mut f64, hood: *mut f64);
    fn mvnxii_(x: *mut f64, n: *mut i32, p: *mut i32, mu: *mut f64, sigsq: *mut f64, hood: *mut f64);
    fn mnxxip_(x: *mut f64, n: *mut i32, p: *mut i32, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, mu: *mut f64, scale: *mut f64, shape: *mut f64, hood: *mut f64);
    fn mvnxxi_(x: *mut f64, n: *mut i32, p: *mut i32, mu: *mut f64, scale: *mut f64, shape: *mut f64, hood: *mut f64);
    fn mnxxxp_(x: *mut f64, n: *mut i32, p: *mut i32, w: *mut f64, pshrnk: *mut f64, pmu: *mut f64, pscale: *mut f64, pdof: *mut f64, mu: *mut f64, u: *mut f64, hood: *mut f64);
    fn mvnxxx_(x: *mut f64, n: *mut i32, p: *mut i32, mu: *mut f64, u: *mut f64, hood: *mut f64);
    fn hceee_(x: *mut f64, n: *mut i32, p: *mut i32, ic: *mut i32, ng: *mut i32, ns: *mut i32, io: *mut i32, jo: *mut i32, v: *mut f64, s: *mut f64, u: *mut f64, r: *mut f64);
    fn msevv_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, mu: *mut f64, o: *mut f64, u: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64, lwork: *mut i32, info: *mut i32, eps: *mut f64);
    fn esevv_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, gnoise: *mut i32, mu: *mut f64, o: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64, vinv: *mut f64, loglik: *mut f64, eps: *mut f64);
    fn meevv_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, gnoise: *mut i32, mu: *mut f64, o: *mut f64, u: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64, vinv: *mut f64, loglik: *mut f64, eqpro: *mut i32, itmax: *mut i32, tol: *mut f64, eps: *mut f64, niterout: *mut i32, errout: *mut f64, lwork: *mut i32, info: *mut i32);
    fn msvee_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, mu: *mut f64, u: *mut f64, c: *mut f64, scale: *mut f64, pro: *mut f64, lwork: *mut i32, info: *mut i32, itmax: *mut i32, tol: *mut f64, niterin: *mut i32, errin: *mut f64);
    fn esvee_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, gnoise: *mut i32, mu: *mut f64, o: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64, vinv: *mut f64, loglik: *mut f64, eps: *mut f64);
    fn mevee_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, gnoise: *mut i32, mu: *mut f64, c: *mut f64, u: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64, vinv: *mut f64, loglik: *mut f64, eqpro: *mut i32, itmaxin: *mut i32, tolin: *mut f64, itmaxout: *mut i32, tolout: *mut f64, eps: *mut f64, niterin: *mut i32, errin: *mut f64, niterout: *mut i32, errout: *mut f64, lwork: *mut i32, info: *mut i32);
    fn mseve_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, mu: *mut f64, u: *mut f64, o: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64, lwork: *mut i32, info: *mut i32, itmax: *mut i32, tol: *mut f64, niterin: *mut i32, errin: *mut f64, eps: *mut f64);
    fn eseve_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, gnoise: *mut i32, mu: *mut f64, o: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64, vinv: *mut f64, loglik: *mut f64, eps: *mut f64);
    fn meeve_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, gnoise: *mut i32, mu: *mut f64, o: *mut f64, u: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64, vinv: *mut f64, loglik: *mut f64, eqpro: *mut i32, itmaxin: *mut i32, tolin: *mut f64, itmaxout: *mut i32, tolout: *mut f64, eps: *mut f64, niterin: *mut i32, errin: *mut f64, niterout: *mut i32, errout: *mut f64, lwork: *mut i32, info: *mut i32);
    fn msvve_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, mu: *mut f64, u: *mut f64, o: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64, lwork: *mut i32, info: *mut i32, itmax: *mut i32, tol: *mut f64, niterin: *mut i32, errin: *mut f64, eps: *mut f64);
    fn esvve_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, gnoise: *mut i32, mu: *mut f64, o: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64, vinv: *mut f64, loglik: *mut f64, eps: *mut f64);
    fn mevve_(x: *mut f64, z: *mut f64, n: *mut i32, p: *mut i32, g: *mut i32, gnoise: *mut i32, mu: *mut f64, o: *mut f64, u: *mut f64, scale: *mut f64, shape: *mut f64, pro: *mut f64, vinv: *mut f64, loglik: *mut f64, eqpro: *mut i32, itmaxin: *mut i32, tolin: *mut f64, itmaxout: *mut i32, tolout: *mut f64, eps: *mut f64, niterin: *mut i32, errin: *mut f64, niterout: *mut i32, errout: *mut f64, lwork: *mut i32, info: *mut i32);
    fn dmvnorm_(x: *mut f64, mu: *mut f64, sigma: *mut f64, n: *mut i32, p: *mut i32, w: *mut f64, hood: *mut f64, logdens: *mut f64);
}

/// Names of the exported covariance-model kernels, in Fortran source order.
pub const KERNELS: &[&str] = &[
    "es1e",
    "hc1e",
    "me1e",
    "me1ep",
    "ms1e",
    "ms1ep",
    "eseee",
    "meeee",
    "meeeep",
    "mseee",
    "mseeep",
    "eseei",
    "meeei",
    "meeeip",
    "mseei",
    "mseeip",
    "eseev",
    "meeev",
    "meeevp",
    "mseev",
    "mseevp",
    "eseii",
    "hceii",
    "meeii",
    "meeiip",
    "mseii",
    "mseiip",
    "esevi",
    "meevi",
    "meevip",
    "msevi",
    "msevip",
    "es1v",
    "hc1v",
    "me1v",
    "me1vp",
    "ms1v",
    "ms1vp",
    "esvei",
    "mevei",
    "meveip",
    "msvei",
    "msveip",
    "esvev",
    "mevev",
    "mevevp",
    "msvev",
    "msvevp",
    "esvii",
    "hcvii",
    "mevii",
    "meviip",
    "msvii",
    "msviip",
    "esvvi",
    "mevvi",
    "mevvip",
    "msvvi",
    "msvvip",
    "esvvv",
    "hcvvv",
    "mevvv",
    "mevvvp",
    "msvvv",
    "msvvvp",
    "mvn1d",
    "mvn1p",
    "mnxiip",
    "mvnxii",
    "mnxxip",
    "mvnxxi",
    "mnxxxp",
    "mvnxxx",
    "hceee",
    "msevv",
    "esevv",
    "meevv",
    "msvee",
    "esvee",
    "mevee",
    "mseve",
    "eseve",
    "meeve",
    "msvve",
    "esvve",
    "mevve",
    "dmvnorm",
];

/// Fortran `es1e` from `mclust.f`.
pub fn es1e(x: &mut [f64], mu: &mut [f64], sigsq: &mut f64, pro: &mut [f64], n: &mut i32, g: &mut i32, vinv: &mut f64, hood: &mut f64, z: &mut [f64]) {
    unsafe { es1e_(x.as_mut_ptr(), mu.as_mut_ptr(), sigsq, pro.as_mut_ptr(), n, g, vinv, hood, z.as_mut_ptr()) }
}

/// Fortran `hc1e` from `mclust.f`.
pub fn hc1e(x: &mut [f64], n: &mut i32, ic: &mut [i32], ng: &mut i32, ns: &mut i32, nd: &mut i32, d: &mut [f64]) {
    unsafe { hc1e_(x.as_mut_ptr(), n, ic.as_mut_ptr(), ng, ns, nd, d.as_mut_ptr()) }
}

/// Fortran `me1e` from `mclust.f`.
pub fn me1e(eqpro: &mut i32, x: &mut [f64], n: &mut i32, g: &mut i32, vinv: &mut f64, z: &mut [f64], maxi: &mut i32, tol: &mut f64, eps: &mut f64, mu: &mut [f64], sigsq: &mut f64, pro: &mut [f64]) {
    unsafe { me1e_(eqpro, x.as_mut_ptr(), n, g, vinv, z.as_mut_ptr(), maxi, tol, eps, mu.as_mut_ptr(), sigsq, pro.as_mut_ptr()) }
}

/// Fortran `me1ep` from `mclust.f`.
pub fn me1ep(eqpro: &mut i32, x: &mut [f64], n: &mut i32, g: &mut i32, vinv: &mut f64, pshrnk: &mut f64, pmu: &mut f64, pscale: &mut f64, pdof: &mut f64, z: &mut [f64], maxi: &mut i32, tol: &mut f64, eps: &mut f64, mu: &mut [f64], sigsq: &mut f64, pro: &mut [f64]) {
    unsafe { me1ep_(eqpro, x.as_mut_ptr(), n, g, vinv, pshrnk, pmu, pscale, pdof, z.as_mut_ptr(), maxi, tol, eps, mu.as_mut_ptr(), sigsq, pro.as_mut_ptr()) }
}

/// Fortran `ms1e` from `mclust.f`.
pub fn ms1e(x: &mut [f64], z: &mut [f64], n: &mut i32, g: &mut i32, mu: &mut [f64], sigsq: &mut f64, pro: &mut [f64]) {
    unsafe { ms1e_(x.as_mut_ptr(), z.as_mut_ptr(), n, g, mu.as_mut_ptr(), sigsq, pro.as_mut_ptr()) }
}

/// Fortran `ms1ep` from `mclust.f`.
pub fn ms1ep(x: &mut [f64], z: &mut [f64], n: &mut i32, g: &mut i32, pshrnk: &mut f64, pmu: &mut f64, pscale: &mut f64, pdof: &mut f64, mu: &mut [f64], sigsq: &mut f64, pro: &mut [f64]) {
    unsafe { ms1ep_(x.as_mut_ptr(), z.as_mut_ptr(), n, g, pshrnk, pmu, pscale, pdof, mu.as_mut_ptr(), sigsq, pro.as_mut_ptr()) }
}

/// Fortran `eseee` from `mclust.f`.
pub fn eseee(chol: &mut i32, x: &mut [f64], mu: &mut [f64], sigma: &mut [f64], pro: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, w: &mut [f64], hood: &mut f64, z: &mut [f64]) {
    unsafe { eseee_(chol, x.as_mut_ptr(), mu.as_mut_ptr(), sigma.as_mut_ptr(), pro.as_mut_ptr(), n, p, g, vinv, w.as_mut_ptr(), hood, z.as_mut_ptr()) }
}

/// Fortran `meeee` from `mclust.f`.
pub fn meeee(eqpro: &mut i32, x: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, z: &mut [f64], maxi: &mut i32, tol: &mut f64, eps: &mut f64, mu: &mut [f64], u: &mut [f64], pro: &mut [f64], w: &mut [f64]) {
    unsafe { meeee_(eqpro, x.as_mut_ptr(), n, p, g, vinv, z.as_mut_ptr(), maxi, tol, eps, mu.as_mut_ptr(), u.as_mut_ptr(), pro.as_mut_ptr(), w.as_mut_ptr()) }
}

/// Fortran `meeeep` from `mclust.f`.
pub fn meeeep(eqpro: &mut i32, x: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, pshrnk: &mut f64, pmu: &mut [f64], pscale: &mut [f64], pdof: &mut f64, z: &mut [f64], maxi: &mut i32, tol: &mut f64, eps: &mut f64, mu: &mut [f64], u: &mut [f64], pro: &mut [f64], w: &mut [f64]) {
    unsafe { meeeep_(eqpro, x.as_mut_ptr(), n, p, g, vinv, pshrnk, pmu.as_mut_ptr(), pscale.as_mut_ptr(), pdof, z.as_mut_ptr(), maxi, tol, eps, mu.as_mut_ptr(), u.as_mut_ptr(), pro.as_mut_ptr(), w.as_mut_ptr()) }
}

/// Fortran `mseee` from `mclust.f`.
pub fn mseee(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, w: &mut [f64], mu: &mut [f64], u: &mut [f64], pro: &mut [f64]) {
    unsafe { mseee_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, w.as_mut_ptr(), mu.as_mut_ptr(), u.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `mseeep` from `mclust.f`.
pub fn mseeep(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, pshrnk: &mut f64, pmu: &mut [f64], pscale: &mut [f64], pdof: &mut f64, w: &mut [f64], mu: &mut [f64], u: &mut [f64], pro: &mut [f64]) {
    unsafe { mseeep_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, pshrnk, pmu.as_mut_ptr(), pscale.as_mut_ptr(), pdof, w.as_mut_ptr(), mu.as_mut_ptr(), u.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `eseei` from `mclust.f`.
pub fn eseei(x: &mut [f64], mu: &mut [f64], scale: &mut f64, shape: &mut [f64], pro: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, hood: &mut f64, z: &mut [f64]) {
    unsafe { eseei_(x.as_mut_ptr(), mu.as_mut_ptr(), scale, shape.as_mut_ptr(), pro.as_mut_ptr(), n, p, g, vinv, hood, z.as_mut_ptr()) }
}

/// Fortran `meeei` from `mclust.f`.
pub fn meeei(eqpro: &mut i32, x: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, z: &mut [f64], maxi: &mut i32, tol: &mut f64, eps: &mut f64, mu: &mut [f64], scale: &mut f64, shape: &mut [f64], pro: &mut [f64]) {
    unsafe { meeei_(eqpro, x.as_mut_ptr(), n, p, g, vinv, z.as_mut_ptr(), maxi, tol, eps, mu.as_mut_ptr(), scale, shape.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `meeeip` from `mclust.f`.
pub fn meeeip(eqpro: &mut i32, x: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, pshrnk: &mut f64, pmu: &mut [f64], pscale: &mut f64, pdof: &mut f64, z: &mut [f64], maxi: &mut i32, tol: &mut f64, eps: &mut f64, mu: &mut [f64], scale: &mut f64, shape: &mut [f64], pro: &mut [f64]) {
    unsafe { meeeip_(eqpro, x.as_mut_ptr(), n, p, g, vinv, pshrnk, pmu.as_mut_ptr(), pscale, pdof, z.as_mut_ptr(), maxi, tol, eps, mu.as_mut_ptr(), scale, shape.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `mseei` from `mclust.f`.
pub fn mseei(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, mu: &mut [f64], scale: &mut f64, shape: &mut [f64], pro: &mut [f64]) {
    unsafe { mseei_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, mu.as_mut_ptr(), scale, shape.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `mseeip` from `mclust.f`.
pub fn mseeip(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, pshrnk: &mut f64, pmu: &mut [f64], pscale: &mut f64, pdof: &mut f64, mu: &mut [f64], scale: &mut f64, shape: &mut [f64], pro: &mut [f64]) {
    unsafe { mseeip_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, pshrnk, pmu.as_mut_ptr(), pscale, pdof, mu.as_mut_ptr(), scale, shape.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `eseev` from `mclust.f`.
pub fn eseev(x: &mut [f64], mu: &mut [f64], scale: &mut f64, shape: &mut [f64], o: &mut [f64], pro: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, v: &mut [f64], w: &mut [f64], hood: &mut f64, z: &mut [f64]) {
    unsafe { eseev_(x.as_mut_ptr(), mu.as_mut_ptr(), scale, shape.as_mut_ptr(), o.as_mut_ptr(), pro.as_mut_ptr(), n, p, g, vinv, v.as_mut_ptr(), w.as_mut_ptr(), hood, z.as_mut_ptr()) }
}

/// Fortran `meeev` from `mclust.f`.
pub fn meeev(eqpro: &mut i32, x: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, z: &mut [f64], maxi: &mut i32, tol: &mut f64, eps: &mut f64, lwork: &mut i32, mu: &mut [f64], scale: &mut f64, shape: &mut [f64], o: &mut [f64], pro: &mut [f64], w: &mut [f64], s: &mut [f64]) {
    unsafe { meeev_(eqpro, x.as_mut_ptr(), n, p, g, vinv, z.as_mut_ptr(), maxi, tol, eps, lwork, mu.as_mut_ptr(), scale, shape.as_mut_ptr(), o.as_mut_ptr(), pro.as_mut_ptr(), w.as_mut_ptr(), s.as_mut_ptr()) }
}

/// Fortran `meeevp` from `mclust.f`.
pub fn meeevp(eqpro: &mut i32, x: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, pshrnk: &mut f64, pmu: &mut [f64], pscale: &mut [f64], pdof: &mut f64, z: &mut [f64], maxi: &mut i32, tol: &mut f64, eps: &mut f64, lwork: &mut i32, mu: &mut [f64], scale: &mut f64, shape: &mut [f64], o: &mut [f64], pro: &mut [f64], w: &mut [f64], s: &mut [f64]) {
    unsafe { meeevp_(eqpro, x.as_mut_ptr(), n, p, g, vinv, pshrnk, pmu.as_mut_ptr(), pscale.as_mut_ptr(), pdof, z.as_mut_ptr(), maxi, tol, eps, lwork, mu.as_mut_ptr(), scale, shape.as_mut_ptr(), o.as_mut_ptr(), pro.as_mut_ptr(), w.as_mut_ptr(), s.as_mut_ptr()) }
}

/// Fortran `mseev` from `mclust.f`.
pub fn mseev(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, w: &mut [f64], lwork: &mut i32, mu: &mut [f64], scale: &mut f64, shape: &mut [f64], o: &mut [f64], pro: &mut [f64]) {
    unsafe { mseev_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, w.as_mut_ptr(), lwork, mu.as_mut_ptr(), scale, shape.as_mut_ptr(), o.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `mseevp` from `mclust.f`.
pub fn mseevp(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, pshrnk: &mut f64, pmu: &mut [f64], pscale: &mut [f64], pdof: &mut f64, w: &mut [f64], lwork: &mut i32, mu: &mut [f64], scale: &mut f64, shape: &mut [f64], o: &mut [f64], pro: &mut [f64]) {
    unsafe { mseevp_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, pshrnk, pmu.as_mut_ptr(), pscale.as_mut_ptr(), pdof, w.as_mut_ptr(), lwork, mu.as_mut_ptr(), scale, shape.as_mut_ptr(), o.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `eseii` from `mclust.f`.
pub fn eseii(x: &mut [f64], mu: &mut [f64], sigsq: &mut f64, pro: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, hood: &mut f64, z: &mut [f64]) {
    unsafe { eseii_(x.as_mut_ptr(), mu.as_mut_ptr(), sigsq, pro.as_mut_ptr(), n, p, g, vinv, hood, z.as_mut_ptr()) }
}

/// Fortran `hceii` from `mclust.f`.
pub fn hceii(x: &mut [f64], n: &mut i32, p: &mut i32, ic: &mut [i32], ng: &mut i32, ns: &mut i32, v: &mut [f64], nd: &mut i32, d: &mut [f64]) {
    unsafe { hceii_(x.as_mut_ptr(), n, p, ic.as_mut_ptr(), ng, ns, v.as_mut_ptr(), nd, d.as_mut_ptr()) }
}

/// Fortran `meeii` from `mclust.f`.
pub fn meeii(eqpro: &mut i32, x: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, z: &mut [f64], maxi: &mut i32, tol: &mut f64, eps: &mut f64, mu: &mut [f64], sigsq: &mut f64, pro: &mut [f64]) {
    unsafe { meeii_(eqpro, x.as_mut_ptr(), n, p, g, vinv, z.as_mut_ptr(), maxi, tol, eps, mu.as_mut_ptr(), sigsq, pro.as_mut_ptr()) }
}

/// Fortran `meeiip` from `mclust.f`.
pub fn meeiip(eqpro: &mut i32, x: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, pshrnk: &mut f64, pmu: &mut [f64], pscale: &mut f64, pdof: &mut f64, z: &mut [f64], maxi: &mut i32, tol: &mut f64, eps: &mut f64, mu: &mut [f64], sigsq: &mut f64, pro: &mut [f64]) {
    unsafe { meeiip_(eqpro, x.as_mut_ptr(), n, p, g, vinv, pshrnk, pmu.as_mut_ptr(), pscale, pdof, z.as_mut_ptr(), maxi, tol, eps, mu.as_mut_ptr(), sigsq, pro.as_mut_ptr()) }
}

/// Fortran `mseii` from `mclust.f`.
pub fn mseii(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, mu: &mut [f64], sigsq: &mut f64, pro: &mut [f64]) {
    unsafe { mseii_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, mu.as_mut_ptr(), sigsq, pro.as_mut_ptr()) }
}

/// Fortran `mseiip` from `mclust.f`.
pub fn mseiip(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, pshrnk: &mut f64, pmu: &mut [f64], pscale: &mut f64, pdof: &mut f64, mu: &mut [f64], sigsq: &mut f64, pro: &mut [f64]) {
    unsafe { mseiip_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, pshrnk, pmu.as_mut_ptr(), pscale, pdof, mu.as_mut_ptr(), sigsq, pro.as_mut_ptr()) }
}

/// Fortran `esevi` from `mclust.f`.
pub fn esevi(x: &mut [f64], mu: &mut [f64], scale: &mut f64, shape: &mut [f64], pro: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, hood: &mut f64, z: &mut [f64]) {
    unsafe { esevi_(x.as_mut_ptr(), mu.as_mut_ptr(), scale, shape.as_mut_ptr(), pro.as_mut_ptr(), n, p, g, vinv, hood, z.as_mut_ptr()) }
}

/// Fortran `meevi` from `mclust.f`.
pub fn meevi(eqpro: &mut i32, x: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, z: &mut [f64], maxi: &mut i32, tol: &mut f64, eps: &mut f64, mu: &mut [f64], scale: &mut f64, shape: &mut [f64], pro: &mut [f64]) {
    unsafe { meevi_(eqpro, x.as_mut_ptr(), n, p, g, vinv, z.as_mut_ptr(), maxi, tol, eps, mu.as_mut_ptr(), scale, shape.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `meevip` from `mclust.f`.
pub fn meevip(eqpro: &mut i32, x: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, pshrnk: &mut f64, pmu: &mut [f64], pscale: &mut f64, pdof: &mut f64, z: &mut [f64], maxi: &mut i32, tol: &mut f64, eps: &mut f64, mu: &mut [f64], scale: &mut f64, shape: &mut [f64], pro: &mut [f64]) {
    unsafe { meevip_(eqpro, x.as_mut_ptr(), n, p, g, vinv, pshrnk, pmu.as_mut_ptr(), pscale, pdof, z.as_mut_ptr(), maxi, tol, eps, mu.as_mut_ptr(), scale, shape.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `msevi` from `mclust.f`.
pub fn msevi(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, mu: &mut [f64], scale: &mut f64, shape: &mut [f64], pro: &mut [f64]) {
    unsafe { msevi_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, mu.as_mut_ptr(), scale, shape.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `msevip` from `mclust.f`.
pub fn msevip(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, pshrnk: &mut f64, pmu: &mut [f64], pscale: &mut f64, pdof: &mut f64, mu: &mut [f64], scale: &mut f64, shape: &mut [f64], pro: &mut [f64]) {
    unsafe { msevip_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, pshrnk, pmu.as_mut_ptr(), pscale, pdof, mu.as_mut_ptr(), scale, shape.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `es1v` from `mclust.f`.
pub fn es1v(x: &mut [f64], mu: &mut [f64], sigsq: &mut [f64], pro: &mut [f64], n: &mut i32, g: &mut i32, vinv: &mut f64, hood: &mut f64, z: &mut [f64]) {
    unsafe { es1v_(x.as_mut_ptr(), mu.as_mut_ptr(), sigsq.as_mut_ptr(), pro.as_mut_ptr(), n, g, vinv, hood, z.as_mut_ptr()) }
}

/// Fortran `hc1v` from `mclust.f`.
pub fn hc1v(x: &mut [f64], n: &mut i32, ic: &mut [i32], ng: &mut i32, ns: &mut i32, alpha: &mut f64, nd: &mut i32, d: &mut [f64]) {
    unsafe { hc1v_(x.as_mut_ptr(), n, ic.as_mut_ptr(), ng, ns, alpha, nd, d.as_mut_ptr()) }
}

/// Fortran `me1v` from `mclust.f`.
pub fn me1v(eqpro: &mut i32, x: &mut [f64], n: &mut i32, g: &mut i32, vinv: &mut f64, z: &mut [f64], maxi: &mut i32, tol: &mut f64, eps: &mut f64, mu: &mut [f64], sigsq: &mut [f64], pro: &mut [f64]) {
    unsafe { me1v_(eqpro, x.as_mut_ptr(), n, g, vinv, z.as_mut_ptr(), maxi, tol, eps, mu.as_mut_ptr(), sigsq.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `me1vp` from `mclust.f`.
pub fn me1vp(eqpro: &mut i32, x: &mut [f64], n: &mut i32, g: &mut i32, vinv: &mut f64, pshrnk: &mut f64, pmu: &mut f64, pscale: &mut f64, pdof: &mut f64, z: &mut [f64], maxi: &mut i32, tol: &mut f64, eps: &mut f64, mu: &mut [f64], sigsq: &mut [f64], pro: &mut [f64]) {
    unsafe { me1vp_(eqpro, x.as_mut_ptr(), n, g, vinv, pshrnk, pmu, pscale, pdof, z.as_mut_ptr(), maxi, tol, eps, mu.as_mut_ptr(), sigsq.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `ms1v` from `mclust.f`.
pub fn ms1v(x: &mut [f64], z: &mut [f64], n: &mut i32, g: &mut i32, mu: &mut [f64], sigsq: &mut [f64], pro: &mut [f64]) {
    unsafe { ms1v_(x.as_mut_ptr(), z.as_mut_ptr(), n, g, mu.as_mut_ptr(), sigsq.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `ms1vp` from `mclust.f`.
pub fn ms1vp(x: &mut [f64], z: &mut [f64], n: &mut i32, g: &mut i32, pshrnk: &mut f64, pmu: &mut f64, pscale: &mut f64, pdof: &mut f64, mu: &mut [f64], sigsq: &mut [f64], pro: &mut [f64]) {
    unsafe { ms1vp_(x.as_mut_ptr(), z.as_mut_ptr(), n, g, pshrnk, pmu, pscale, pdof, mu.as_mut_ptr(), sigsq.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `esvei` from `mclust.f`.
pub fn esvei(x: &mut [f64], mu: &mut [f64], scale: &mut [f64], shape: &mut [f64], pro: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, hood: &mut f64, z: &mut [f64]) {
    unsafe { esvei_(x.as_mut_ptr(), mu.as_mut_ptr(), scale.as_mut_ptr(), shape.as_mut_ptr(), pro.as_mut_ptr(), n, p, g, vinv, hood, z.as_mut_ptr()) }
}

/// Fortran `mevei` from `mclust.f`.
pub fn mevei(eqpro: &mut i32, x: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, z: &mut [f64], maxi: &mut [i32], tol: &mut [f64], eps: &mut f64, mu: &mut [f64], scale: &mut [f64], shape: &mut [f64], pro: &mut [f64], scl: &mut [f64], shp: &mut [f64], w: &mut [f64]) {
    unsafe { mevei_(eqpro, x.as_mut_ptr(), n, p, g, vinv, z.as_mut_ptr(), maxi.as_mut_ptr(), tol.as_mut_ptr(), eps, mu.as_mut_ptr(), scale.as_mut_ptr(), shape.as_mut_ptr(), pro.as_mut_ptr(), scl.as_mut_ptr(), shp.as_mut_ptr(), w.as_mut_ptr()) }
}

/// Fortran `meveip` from `mclust.f`.
pub fn meveip(eqpro: &mut i32, x: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, pshrnk: &mut f64, pmu: &mut [f64], pscale: &mut f64, pdof: &mut f64, z: &mut [f64], maxi: &mut [i32], tol: &mut [f64], eps: &mut f64, mu: &mut [f64], scale: &mut [f64], shape: &mut [f64], pro: &mut [f64], scl: &mut [f64], shp: &mut [f64], w: &mut [f64]) {
    unsafe { meveip_(eqpro, x.as_mut_ptr(), n, p, g, vinv, pshrnk, pmu.as_mut_ptr(), pscale, pdof, z.as_mut_ptr(), maxi.as_mut_ptr(), tol.as_mut_ptr(), eps, mu.as_mut_ptr(), scale.as_mut_ptr(), shape.as_mut_ptr(), pro.as_mut_ptr(), scl.as_mut_ptr(), shp.as_mut_ptr(), w.as_mut_ptr()) }
}

/// Fortran `msvei` from `mclust.f`.
pub fn msvei(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, maxi: &mut i32, tol: &mut f64, mu: &mut [f64], scale: &mut [f64], shape: &mut [f64], pro: &mut [f64], scl: &mut [f64], shp: &mut [f64], w: &mut [f64]) {
    unsafe { msvei_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, maxi, tol, mu.as_mut_ptr(), scale.as_mut_ptr(), shape.as_mut_ptr(), pro.as_mut_ptr(), scl.as_mut_ptr(), shp.as_mut_ptr(), w.as_mut_ptr()) }
}

/// Fortran `msveip` from `mclust.f`.
pub fn msveip(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, pshrnk: &mut f64, pmu: &mut [f64], pscale: &mut f64, pdof: &mut f64, maxi: &mut i32, tol: &mut f64, mu: &mut [f64], scale: &mut [f64], shape: &mut [f64], pro: &mut [f64], scl: &mut [f64], shp: &mut [f64], w: &mut [f64]) {
    unsafe { msveip_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, pshrnk, pmu.as_mut_ptr(), pscale, pdof, maxi, tol, mu.as_mut_ptr(), scale.as_mut_ptr(), shape.as_mut_ptr(), pro.as_mut_ptr(), scl.as_mut_ptr(), shp.as_mut_ptr(), w.as_mut_ptr()) }
}

/// Fortran `esvev` from `mclust.f`.
pub fn esvev(x: &mut [f64], mu: &mut [f64], scale: &mut [f64], shape: &mut [f64], o: &mut [f64], pro: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, v: &mut [f64], w: &mut [f64], hood: &mut f64, z: &mut [f64]) {
    unsafe { esvev_(x.as_mut_ptr(), mu.as_mut_ptr(), scale.as_mut_ptr(), shape.as_mut_ptr(), o.as_mut_ptr(), pro.as_mut_ptr(), n, p, g, vinv, v.as_mut_ptr(), w.as_mut_ptr(), hood, z.as_mut_ptr()) }
}

/// Fortran `mevev` from `mclust.f`.
pub fn mevev(eqpro: &mut i32, x: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, z: &mut [f64], maxi: &mut [i32], tol: &mut [f64], eps: &mut f64, lwork: &mut i32, mu: &mut [f64], scale: &mut [f64], shape: &mut [f64], o: &mut [f64], pro: &mut [f64], w: &mut [f64], s: &mut [f64]) {
    unsafe { mevev_(eqpro, x.as_mut_ptr(), n, p, g, vinv, z.as_mut_ptr(), maxi.as_mut_ptr(), tol.as_mut_ptr(), eps, lwork, mu.as_mut_ptr(), scale.as_mut_ptr(), shape.as_mut_ptr(), o.as_mut_ptr(), pro.as_mut_ptr(), w.as_mut_ptr(), s.as_mut_ptr()) }
}

/// Fortran `mevevp` from `mclust.f`.
pub fn mevevp(eqpro: &mut i32, x: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, pshrnk: &mut f64, pmu: &mut [f64], pscale: &mut [f64], pdof: &mut f64, z: &mut [f64], maxi: &mut [i32], tol: &mut [f64], eps: &mut f64, lwork: &mut i32, mu: &mut [f64], scale: &mut [f64], shape: &mut [f64], o: &mut [f64], pro: &mut [f64], w: &mut [f64], s: &mut [f64]) {
    unsafe { mevevp_(eqpro, x.as_mut_ptr(), n, p, g, vinv, pshrnk, pmu.as_mut_ptr(), pscale.as_mut_ptr(), pdof, z.as_mut_ptr(), maxi.as_mut_ptr(), tol.as_mut_ptr(), eps, lwork, mu.as_mut_ptr(), scale.as_mut_ptr(), shape.as_mut_ptr(), o.as_mut_ptr(), pro.as_mut_ptr(), w.as_mut_ptr(), s.as_mut_ptr()) }
}

/// Fortran `msvev` from `mclust.f`.
pub fn msvev(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, w: &mut [f64], lwork: &mut i32, maxi: &mut i32, tol: &mut f64, mu: &mut [f64], scale: &mut [f64], shape: &mut [f64], o: &mut [f64], pro: &mut [f64]) {
    unsafe { msvev_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, w.as_mut_ptr(), lwork, maxi, tol, mu.as_mut_ptr(), scale.as_mut_ptr(), shape.as_mut_ptr(), o.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `msvevp` from `mclust.f`.
pub fn msvevp(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, pshrnk: &mut f64, pmu: &mut [f64], pscale: &mut [f64], pdof: &mut f64, w: &mut [f64], lwork: &mut i32, maxi: &mut i32, tol: &mut f64, mu: &mut [f64], scale: &mut [f64], shape: &mut [f64], o: &mut [f64], pro: &mut [f64]) {
    unsafe { msvevp_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, pshrnk, pmu.as_mut_ptr(), pscale.as_mut_ptr(), pdof, w.as_mut_ptr(), lwork, maxi, tol, mu.as_mut_ptr(), scale.as_mut_ptr(), shape.as_mut_ptr(), o.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `esvii` from `mclust.f`.
pub fn esvii(x: &mut [f64], mu: &mut [f64], sigsq: &mut [f64], pro: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, hood: &mut f64, z: &mut [f64]) {
    unsafe { esvii_(x.as_mut_ptr(), mu.as_mut_ptr(), sigsq.as_mut_ptr(), pro.as_mut_ptr(), n, p, g, vinv, hood, z.as_mut_ptr()) }
}

/// Fortran `hcvii` from `mclust.f`.
pub fn hcvii(x: &mut [f64], n: &mut i32, p: &mut i32, ic: &mut [i32], ng: &mut i32, ns: &mut i32, alpha: &mut f64, v: &mut [f64], nd: &mut i32, d: &mut [f64]) {
    unsafe { hcvii_(x.as_mut_ptr(), n, p, ic.as_mut_ptr(), ng, ns, alpha, v.as_mut_ptr(), nd, d.as_mut_ptr()) }
}

/// Fortran `mevii` from `mclust.f`.
pub fn mevii(eqpro: &mut i32, x: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, z: &mut [f64], maxi: &mut i32, tol: &mut f64, eps: &mut f64, mu: &mut [f64], sigsq: &mut [f64], pro: &mut [f64]) {
    unsafe { mevii_(eqpro, x.as_mut_ptr(), n, p, g, vinv, z.as_mut_ptr(), maxi, tol, eps, mu.as_mut_ptr(), sigsq.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `meviip` from `mclust.f`.
pub fn meviip(eqpro: &mut i32, x: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, pshrnk: &mut f64, pmu: &mut [f64], pscale: &mut f64, pdof: &mut f64, z: &mut [f64], maxi: &mut i32, tol: &mut f64, eps: &mut f64, mu: &mut [f64], sigsq: &mut [f64], pro: &mut [f64]) {
    unsafe { meviip_(eqpro, x.as_mut_ptr(), n, p, g, vinv, pshrnk, pmu.as_mut_ptr(), pscale, pdof, z.as_mut_ptr(), maxi, tol, eps, mu.as_mut_ptr(), sigsq.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `msvii` from `mclust.f`.
pub fn msvii(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, mu: &mut [f64], sigsq: &mut [f64], pro: &mut [f64]) {
    unsafe { msvii_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, mu.as_mut_ptr(), sigsq.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `msviip` from `mclust.f`.
pub fn msviip(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, pshrnk: &mut f64, pmu: &mut [f64], pscale: &mut f64, pdof: &mut f64, mu: &mut [f64], sigsq: &mut [f64], pro: &mut [f64]) {
    unsafe { msviip_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, pshrnk, pmu.as_mut_ptr(), pscale, pdof, mu.as_mut_ptr(), sigsq.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `esvvi` from `mclust.f`.
pub fn esvvi(x: &mut [f64], mu: &mut [f64], scale: &mut [f64], shape: &mut [f64], pro: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, hood: &mut f64, z: &mut [f64]) {
    unsafe { esvvi_(x.as_mut_ptr(), mu.as_mut_ptr(), scale.as_mut_ptr(), shape.as_mut_ptr(), pro.as_mut_ptr(), n, p, g, vinv, hood, z.as_mut_ptr()) }
}

/// Fortran `mevvi` from `mclust.f`.
pub fn mevvi(eqpro: &mut i32, x: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, z: &mut [f64], maxi: &mut i32, tol: &mut f64, eps: &mut f64, mu: &mut [f64], scale: &mut [f64], shape: &mut [f64], pro: &mut [f64]) {
    unsafe { mevvi_(eqpro, x.as_mut_ptr(), n, p, g, vinv, z.as_mut_ptr(), maxi, tol, eps, mu.as_mut_ptr(), scale.as_mut_ptr(), shape.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `mevvip` from `mclust.f`.
pub fn mevvip(eqpro: &mut i32, x: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, pshrnk: &mut f64, pmu: &mut [f64], pscale: &mut f64, pdof: &mut f64, z: &mut [f64], maxi: &mut i32, tol: &mut f64, eps: &mut f64, mu: &mut [f64], scale: &mut [f64], shape: &mut [f64], pro: &mut [f64]) {
    unsafe { mevvip_(eqpro, x.as_mut_ptr(), n, p, g, vinv, pshrnk, pmu.as_mut_ptr(), pscale, pdof, z.as_mut_ptr(), maxi, tol, eps, mu.as_mut_ptr(), scale.as_mut_ptr(), shape.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `msvvi` from `mclust.f`.
pub fn msvvi(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, mu: &mut [f64], scale: &mut [f64], shape: &mut [f64], pro: &mut [f64]) {
    unsafe { msvvi_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, mu.as_mut_ptr(), scale.as_mut_ptr(), shape.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `msvvip` from `mclust.f`.
pub fn msvvip(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, pshrnk: &mut f64, pmu: &mut [f64], pscale: &mut f64, pdof: &mut f64, mu: &mut [f64], scale: &mut [f64], shape: &mut [f64], pro: &mut [f64]) {
    unsafe { msvvip_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, pshrnk, pmu.as_mut_ptr(), pscale, pdof, mu.as_mut_ptr(), scale.as_mut_ptr(), shape.as_mut_ptr(), pro.as_mut_ptr()) }
}

/// Fortran `esvvv` from `mclust.f`.
pub fn esvvv(chol: &mut i32, x: &mut [f64], mu: &mut [f64], sigma: &mut [f64], pro: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, w: &mut [f64], hood: &mut f64, z: &mut [f64]) {
    unsafe { esvvv_(chol, x.as_mut_ptr(), mu.as_mut_ptr(), sigma.as_mut_ptr(), pro.as_mut_ptr(), n, p, g, vinv, w.as_mut_ptr(), hood, z.as_mut_ptr()) }
}

/// Fortran `mcltrw` from `mclust.f`, the routine behind R `traceW`.
/// `x` is overwritten with the centred values, as in the Fortran.
pub fn mcltrw(x: &mut [f64], n: &mut i32, p: &mut i32, u: &mut [f64], ss: &mut f64) {
    unsafe { mcltrw_(x.as_mut_ptr(), n, p, u.as_mut_ptr(), ss) }
}

/// Fortran `hcvvv` from `mclust.f`.
pub fn hcvvv(x: &mut [f64], n: &mut i32, p: &mut i32, ic: &mut [i32], ng: &mut i32, ns: &mut i32, alpha: &mut f64, beta: &mut f64, v: &mut [f64], u: &mut [f64], s: &mut [f64], r: &mut [f64], nd: &mut i32, d: &mut [f64]) {
    unsafe { hcvvv_(x.as_mut_ptr(), n, p, ic.as_mut_ptr(), ng, ns, alpha, beta, v.as_mut_ptr(), u.as_mut_ptr(), s.as_mut_ptr(), r.as_mut_ptr(), nd, d.as_mut_ptr()) }
}

/// Fortran `mevvv` from `mclust.f`.
pub fn mevvv(eqpro: &mut i32, x: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, z: &mut [f64], maxi: &mut i32, tol: &mut f64, eps: &mut f64, mu: &mut [f64], u: &mut [f64], pro: &mut [f64], w: &mut [f64], s: &mut [f64]) {
    unsafe { mevvv_(eqpro, x.as_mut_ptr(), n, p, g, vinv, z.as_mut_ptr(), maxi, tol, eps, mu.as_mut_ptr(), u.as_mut_ptr(), pro.as_mut_ptr(), w.as_mut_ptr(), s.as_mut_ptr()) }
}

/// Fortran `mevvvp` from `mclust.f`.
pub fn mevvvp(eqpro: &mut i32, x: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, vinv: &mut f64, pshrnk: &mut f64, pmu: &mut [f64], pscale: &mut [f64], pdof: &mut f64, z: &mut [f64], maxi: &mut i32, tol: &mut f64, eps: &mut f64, mu: &mut [f64], u: &mut [f64], pro: &mut [f64], w: &mut [f64], s: &mut [f64]) {
    unsafe { mevvvp_(eqpro, x.as_mut_ptr(), n, p, g, vinv, pshrnk, pmu.as_mut_ptr(), pscale.as_mut_ptr(), pdof, z.as_mut_ptr(), maxi, tol, eps, mu.as_mut_ptr(), u.as_mut_ptr(), pro.as_mut_ptr(), w.as_mut_ptr(), s.as_mut_ptr()) }
}

/// Fortran `msvvv` from `mclust.f`.
pub fn msvvv(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, w: &mut [f64], mu: &mut [f64], u: &mut [f64], pro: &mut [f64], s: &mut [f64]) {
    unsafe { msvvv_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, w.as_mut_ptr(), mu.as_mut_ptr(), u.as_mut_ptr(), pro.as_mut_ptr(), s.as_mut_ptr()) }
}

/// Fortran `msvvvp` from `mclust.f`.
pub fn msvvvp(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, pshrnk: &mut f64, pmu: &mut [f64], pscale: &mut [f64], pdof: &mut f64, w: &mut [f64], mu: &mut [f64], u: &mut [f64], pro: &mut [f64], s: &mut [f64]) {
    unsafe { msvvvp_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, pshrnk, pmu.as_mut_ptr(), pscale.as_mut_ptr(), pdof, w.as_mut_ptr(), mu.as_mut_ptr(), u.as_mut_ptr(), pro.as_mut_ptr(), s.as_mut_ptr()) }
}

/// Fortran `mvn1d` from `mclust.f`.
pub fn mvn1d(x: &mut [f64], n: &mut i32, mu: &mut f64, sigsq: &mut f64, hood: &mut f64) {
    unsafe { mvn1d_(x.as_mut_ptr(), n, mu, sigsq, hood) }
}

/// Fortran `mvn1p` from `mclust.f`.
pub fn mvn1p(x: &mut [f64], n: &mut i32, pshrnk: &mut f64, pmu: &mut f64, pscale: &mut f64, pdof: &mut f64, mu: &mut f64, sigsq: &mut f64, hood: &mut f64) {
    unsafe { mvn1p_(x.as_mut_ptr(), n, pshrnk, pmu, pscale, pdof, mu, sigsq, hood) }
}

/// Fortran `mnxiip` from `mclust.f`.
pub fn mnxiip(x: &mut [f64], n: &mut i32, p: &mut i32, pshrnk: &mut f64, pmu: &mut [f64], pscale: &mut f64, pdof: &mut f64, mu: &mut [f64], sigsq: &mut f64, hood: &mut f64) {
    unsafe { mnxiip_(x.as_mut_ptr(), n, p, pshrnk, pmu.as_mut_ptr(), pscale, pdof, mu.as_mut_ptr(), sigsq, hood) }
}

/// Fortran `mvnxii` from `mclust.f`.
pub fn mvnxii(x: &mut [f64], n: &mut i32, p: &mut i32, mu: &mut [f64], sigsq: &mut f64, hood: &mut f64) {
    unsafe { mvnxii_(x.as_mut_ptr(), n, p, mu.as_mut_ptr(), sigsq, hood) }
}

/// Fortran `mnxxip` from `mclust.f`.
pub fn mnxxip(x: &mut [f64], n: &mut i32, p: &mut i32, pshrnk: &mut f64, pmu: &mut [f64], pscale: &mut f64, pdof: &mut f64, mu: &mut [f64], scale: &mut f64, shape: &mut [f64], hood: &mut f64) {
    unsafe { mnxxip_(x.as_mut_ptr(), n, p, pshrnk, pmu.as_mut_ptr(), pscale, pdof, mu.as_mut_ptr(), scale, shape.as_mut_ptr(), hood) }
}

/// Fortran `mvnxxi` from `mclust.f`.
pub fn mvnxxi(x: &mut [f64], n: &mut i32, p: &mut i32, mu: &mut [f64], scale: &mut f64, shape: &mut [f64], hood: &mut f64) {
    unsafe { mvnxxi_(x.as_mut_ptr(), n, p, mu.as_mut_ptr(), scale, shape.as_mut_ptr(), hood) }
}

/// Fortran `mnxxxp` from `mclust.f`.
pub fn mnxxxp(x: &mut [f64], n: &mut i32, p: &mut i32, w: &mut [f64], pshrnk: &mut f64, pmu: &mut [f64], pscale: &mut [f64], pdof: &mut f64, mu: &mut [f64], u: &mut [f64], hood: &mut f64) {
    unsafe { mnxxxp_(x.as_mut_ptr(), n, p, w.as_mut_ptr(), pshrnk, pmu.as_mut_ptr(), pscale.as_mut_ptr(), pdof, mu.as_mut_ptr(), u.as_mut_ptr(), hood) }
}

/// Fortran `mvnxxx` from `mclust.f`.
pub fn mvnxxx(x: &mut [f64], n: &mut i32, p: &mut i32, mu: &mut [f64], u: &mut [f64], hood: &mut f64) {
    unsafe { mvnxxx_(x.as_mut_ptr(), n, p, mu.as_mut_ptr(), u.as_mut_ptr(), hood) }
}

/// Fortran `hceee` from `mclust.f`.
pub fn hceee(x: &mut [f64], n: &mut i32, p: &mut i32, ic: &mut [i32], ng: &mut i32, ns: &mut i32, io: &mut [i32], jo: &mut [i32], v: &mut [f64], s: &mut [f64], u: &mut [f64], r: &mut [f64]) {
    unsafe { hceee_(x.as_mut_ptr(), n, p, ic.as_mut_ptr(), ng, ns, io.as_mut_ptr(), jo.as_mut_ptr(), v.as_mut_ptr(), s.as_mut_ptr(), u.as_mut_ptr(), r.as_mut_ptr()) }
}

/// Fortran `msevv` from `mclust2.f`.
pub fn msevv(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, mu: &mut [f64], o: &mut [f64], u: &mut [f64], scale: &mut [f64], shape: &mut [f64], pro: &mut [f64], lwork: &mut i32, info: &mut i32, eps: &mut f64) {
    unsafe { msevv_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, mu.as_mut_ptr(), o.as_mut_ptr(), u.as_mut_ptr(), scale.as_mut_ptr(), shape.as_mut_ptr(), pro.as_mut_ptr(), lwork, info, eps) }
}

/// Fortran `esevv` from `mclust2.f`.
pub fn esevv(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, gnoise: &mut i32, mu: &mut [f64], o: &mut [f64], scale: &mut f64, shape: &mut [f64], pro: &mut [f64], vinv: &mut f64, loglik: &mut f64, eps: &mut f64) {
    unsafe { esevv_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, gnoise, mu.as_mut_ptr(), o.as_mut_ptr(), scale, shape.as_mut_ptr(), pro.as_mut_ptr(), vinv, loglik, eps) }
}

/// Fortran `meevv` from `mclust2.f`.
pub fn meevv(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, gnoise: &mut i32, mu: &mut [f64], o: &mut [f64], u: &mut [f64], scale: &mut [f64], shape: &mut [f64], pro: &mut [f64], vinv: &mut f64, loglik: &mut f64, eqpro: &mut i32, itmax: &mut i32, tol: &mut f64, eps: &mut f64, niterout: &mut i32, errout: &mut f64, lwork: &mut i32, info: &mut i32) {
    unsafe { meevv_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, gnoise, mu.as_mut_ptr(), o.as_mut_ptr(), u.as_mut_ptr(), scale.as_mut_ptr(), shape.as_mut_ptr(), pro.as_mut_ptr(), vinv, loglik, eqpro, itmax, tol, eps, niterout, errout, lwork, info) }
}

/// Fortran `msvee` from `mclust2.f`.
pub fn msvee(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, mu: &mut [f64], u: &mut [f64], c: &mut [f64], scale: &mut [f64], pro: &mut [f64], lwork: &mut i32, info: &mut i32, itmax: &mut i32, tol: &mut f64, niterin: &mut i32, errin: &mut f64) {
    unsafe { msvee_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, mu.as_mut_ptr(), u.as_mut_ptr(), c.as_mut_ptr(), scale.as_mut_ptr(), pro.as_mut_ptr(), lwork, info, itmax, tol, niterin, errin) }
}

/// Fortran `esvee` from `mclust2.f`.
pub fn esvee(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, gnoise: &mut i32, mu: &mut [f64], o: &mut [f64], scale: &mut [f64], shape: &mut [f64], pro: &mut [f64], vinv: &mut f64, loglik: &mut f64, eps: &mut f64) {
    unsafe { esvee_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, gnoise, mu.as_mut_ptr(), o.as_mut_ptr(), scale.as_mut_ptr(), shape.as_mut_ptr(), pro.as_mut_ptr(), vinv, loglik, eps) }
}

/// Fortran `mevee` from `mclust2.f`.
pub fn mevee(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, gnoise: &mut i32, mu: &mut [f64], c: &mut [f64], u: &mut [f64], scale: &mut [f64], shape: &mut [f64], pro: &mut [f64], vinv: &mut f64, loglik: &mut f64, eqpro: &mut i32, itmaxin: &mut i32, tolin: &mut f64, itmaxout: &mut i32, tolout: &mut f64, eps: &mut f64, niterin: &mut i32, errin: &mut f64, niterout: &mut i32, errout: &mut f64, lwork: &mut i32, info: &mut i32) {
    unsafe { mevee_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, gnoise, mu.as_mut_ptr(), c.as_mut_ptr(), u.as_mut_ptr(), scale.as_mut_ptr(), shape.as_mut_ptr(), pro.as_mut_ptr(), vinv, loglik, eqpro, itmaxin, tolin, itmaxout, tolout, eps, niterin, errin, niterout, errout, lwork, info) }
}

/// Fortran `mseve` from `mclust2.f`.
pub fn mseve(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, mu: &mut [f64], u: &mut [f64], o: &mut [f64], scale: &mut f64, shape: &mut [f64], pro: &mut [f64], lwork: &mut i32, info: &mut i32, itmax: &mut i32, tol: &mut f64, niterin: &mut i32, errin: &mut f64, eps: &mut f64) {
    unsafe { mseve_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, mu.as_mut_ptr(), u.as_mut_ptr(), o.as_mut_ptr(), scale, shape.as_mut_ptr(), pro.as_mut_ptr(), lwork, info, itmax, tol, niterin, errin, eps) }
}

/// Fortran `eseve` from `mclust2.f`.
pub fn eseve(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, gnoise: &mut i32, mu: &mut [f64], o: &mut [f64], scale: &mut f64, shape: &mut [f64], pro: &mut [f64], vinv: &mut f64, loglik: &mut f64, eps: &mut f64) {
    unsafe { eseve_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, gnoise, mu.as_mut_ptr(), o.as_mut_ptr(), scale, shape.as_mut_ptr(), pro.as_mut_ptr(), vinv, loglik, eps) }
}

/// Fortran `meeve` from `mclust2.f`.
pub fn meeve(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, gnoise: &mut i32, mu: &mut [f64], o: &mut [f64], u: &mut [f64], scale: &mut f64, shape: &mut [f64], pro: &mut [f64], vinv: &mut f64, loglik: &mut f64, eqpro: &mut i32, itmaxin: &mut i32, tolin: &mut f64, itmaxout: &mut i32, tolout: &mut f64, eps: &mut f64, niterin: &mut i32, errin: &mut f64, niterout: &mut i32, errout: &mut f64, lwork: &mut i32, info: &mut i32) {
    unsafe { meeve_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, gnoise, mu.as_mut_ptr(), o.as_mut_ptr(), u.as_mut_ptr(), scale, shape.as_mut_ptr(), pro.as_mut_ptr(), vinv, loglik, eqpro, itmaxin, tolin, itmaxout, tolout, eps, niterin, errin, niterout, errout, lwork, info) }
}

/// Fortran `msvve` from `mclust2.f`.
pub fn msvve(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, mu: &mut [f64], u: &mut [f64], o: &mut [f64], scale: &mut [f64], shape: &mut [f64], pro: &mut [f64], lwork: &mut i32, info: &mut i32, itmax: &mut i32, tol: &mut f64, niterin: &mut i32, errin: &mut f64, eps: &mut f64) {
    unsafe { msvve_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, mu.as_mut_ptr(), u.as_mut_ptr(), o.as_mut_ptr(), scale.as_mut_ptr(), shape.as_mut_ptr(), pro.as_mut_ptr(), lwork, info, itmax, tol, niterin, errin, eps) }
}

/// Fortran `esvve` from `mclust2.f`.
pub fn esvve(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, gnoise: &mut i32, mu: &mut [f64], o: &mut [f64], scale: &mut [f64], shape: &mut [f64], pro: &mut [f64], vinv: &mut f64, loglik: &mut f64, eps: &mut f64) {
    unsafe { esvve_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, gnoise, mu.as_mut_ptr(), o.as_mut_ptr(), scale.as_mut_ptr(), shape.as_mut_ptr(), pro.as_mut_ptr(), vinv, loglik, eps) }
}

/// Fortran `mevve` from `mclust2.f`.
pub fn mevve(x: &mut [f64], z: &mut [f64], n: &mut i32, p: &mut i32, g: &mut i32, gnoise: &mut i32, mu: &mut [f64], o: &mut [f64], u: &mut [f64], scale: &mut [f64], shape: &mut [f64], pro: &mut [f64], vinv: &mut f64, loglik: &mut f64, eqpro: &mut i32, itmaxin: &mut i32, tolin: &mut f64, itmaxout: &mut i32, tolout: &mut f64, eps: &mut f64, niterin: &mut i32, errin: &mut f64, niterout: &mut i32, errout: &mut f64, lwork: &mut i32, info: &mut i32) {
    unsafe { mevve_(x.as_mut_ptr(), z.as_mut_ptr(), n, p, g, gnoise, mu.as_mut_ptr(), o.as_mut_ptr(), u.as_mut_ptr(), scale.as_mut_ptr(), shape.as_mut_ptr(), pro.as_mut_ptr(), vinv, loglik, eqpro, itmaxin, tolin, itmaxout, tolout, eps, niterin, errin, niterout, errout, lwork, info) }
}

/// Fortran `dmvnorm` from `util.f`.
pub fn dmvnorm(x: &mut [f64], mu: &mut [f64], sigma: &mut [f64], n: &mut i32, p: &mut i32, w: &mut [f64], hood: &mut f64, logdens: &mut [f64]) {
    unsafe { dmvnorm_(x.as_mut_ptr(), mu.as_mut_ptr(), sigma.as_mut_ptr(), n, p, w.as_mut_ptr(), hood, logdens.as_mut_ptr()) }
}

