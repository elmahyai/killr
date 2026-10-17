//! Gaussian mixture kernels from mclust 6.1.3.
//!
//! The EM, E-step, M-step, density, and hierarchical-clustering routines are
//! the Fortran in `vendor/`. `sim*` stays in R: it draws with `rnorm` and does
//! not have a Fortran body.

mod kernels;

#[cfg(feature = "python")]
mod python;

pub use kernels::*;

/// Milliseconds for one `me1e` call, measured with [`std::time::Instant`].
pub fn me1e_ms(
    eqpro: &mut i32,
    x: &mut [f64],
    n: &mut i32,
    g: &mut i32,
    vinv: &mut f64,
    z: &mut [f64],
    maxi: &mut i32,
    tol: &mut f64,
    eps: &mut f64,
    mu: &mut [f64],
    sigsq: &mut f64,
    pro: &mut [f64],
) -> f64 {
    let started = std::time::Instant::now();
    me1e(eqpro, x, n, g, vinv, z, maxi, tol, eps, mu, sigsq, pro);
    started.elapsed().as_secs_f64() * 1000.0
}
