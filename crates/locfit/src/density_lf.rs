// Density family for locfit 1.5-9.12, ported from the locfit C sources
// (GPL-2.0-or-later, copyright (c) 1996-2001 Lucent Technologies; see the
// README of the CRAN tarball). The routines followed are `densinit`
// (density.c), `mlinint` and `prodint` with the link `ident` (density.c), and
// `gridf` (startlf.c / ev_main.c), for one dimension, degree 0, and no user
// limits (`xlim`), which is the default `density.lf` path.
//
// With link `ident` and degree 0, the local likelihood is linear in the
// coefficient, so the fitted density at a grid point `g` is
//
//     f(g) = sum_i W(|x_i - g| / h) / (n * h * int W),
//
// where `int W` is the integral of the kernel over its support (`wint`). For
// the Gaussian kernel the integral is over the whole line, because locfit's
// integration ignores the limits for Gaussian weights (the `prodint` /
// `onedint` path). The sum runs over every observation, as `densinit` does.
//
// Not ported here: degree 1 and higher, multi-dimensional and angular
// domains, user limits, `renorm = TRUE`, and the log link.

use crate::kernel::{w_fn, wint, Kernel};

/// Density estimate of `density.lf` on a grid of points, for one dimension,
/// degree 0, link `ident`, and bandwidth `h`. `x` are the observations and
/// `grid` the evaluation points, in any order.
pub fn density_grid(x: &[f64], grid: &[f64], h: f64, ker: Kernel) -> Result<Vec<f64>, String> {
    if x.is_empty() {
        return Err("density.lf needs at least one observation".to_string());
    }
    if !(h > 0.0) {
        return Err("density.lf needs a positive bandwidth".to_string());
    }
    let n = x.len() as f64;
    // Integral of the kernel over its support (for the Gaussian, over R).
    let kint = wint(1, &[], ker)?;
    if !(kint > 0.0) {
        return Err("density.lf: kernel integral is not positive".to_string());
    }
    let scale = 1.0 / (n * h * kint);
    let out = grid
        .iter()
        .map(|&g| {
            let s: f64 = x
                .iter()
                .map(|&xi| w_fn((xi - g).abs() / h, ker))
                .sum();
            s * scale
        })
        .collect();
    Ok(out)
}
