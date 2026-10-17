//! Critical values for simultaneous bands, ported from locfit 1.5-9.12.
//!
//! Ported from `scb_crit.c` (`area`, `tailp_gaussian`, `taild_gaussian`,
//! `critval`) and the `scritval` entry point of `smisc.c`. The branch kept
//! here is the one R's `crit()` takes for a Gaussian process with two-sided
//! tails and no residual degrees of freedom (`rdf = 0`, process `GAUSS`).
//! The t-process (`rdf > 0`) and uniform process branches are not ported.
//!
//! Original copyright notice (`scb_crit.c`):
//!   Copyright (c) 1996-2004 Catherine Loader.
//! The locfit package is licensed GPL (>= 2), as is this crate.
//!
//! The C code prints a message when `alpha > 0.5` and returns 2.0 for an
//! invalid `alpha`. This port returns an error for an invalid `alpha` and does
//! not print the large-tail message.

use crate::kernel::lgamma;

const LOGPI: f64 = 1.144_729_885_849_400_174_143_427;

/// `A[d]` of `scb_crit.c`: the surface area of the unit sphere in R^d, for d < 10.
const AREA: [f64; 10] = [
    1.0,
    2.0,
    6.283_185_307_179_586_477,  // 2 pi
    12.566_370_614_359_172_954, // 4 pi
    19.739_208_802_178_717_238, // 2 pi^2
    26.318_945_069_571_622_985, // 8/3 pi^2
    31.006_276_680_299_820_177, // pi^3
    33.073_361_792_319_808_190, // 16/15 pi^3
    32.469_697_011_334_145_747, // 1/3 pi^4
    29.686_580_124_648_361_825, // 32/105 pi^4
];

/// `area(d)` of `scb_crit.c`: `2 pi^(d/2) / Gamma(d/2)`.
pub fn area(d: usize) -> f64 {
    if d < 10 {
        AREA[d]
    } else {
        let df = d as f64;
        2.0 * (df * LOGPI / 2.0 - lgamma(df / 2.0)).exp()
    }
}

/// Regularized lower incomplete gamma P(a, x) by its power series (x < a + 1).
fn gamma_series(a: f64, x: f64) -> f64 {
    let mut ap = a;
    let mut sum = 1.0 / a;
    let mut del = sum;
    for _ in 0..10_000 {
        ap += 1.0;
        del *= x / ap;
        sum += del;
        if del.abs() < sum.abs() * 1e-17 {
            break;
        }
    }
    sum * (-x + a * x.ln() - lgamma(a)).exp()
}

/// Regularized upper incomplete gamma Q(a, x) by Lentz's continued fraction
/// (x >= a + 1).
fn gamma_cf(a: f64, x: f64) -> f64 {
    const FPMIN: f64 = 1e-300;
    let mut b = x + 1.0 - a;
    let mut c = 1.0 / FPMIN;
    let mut d = 1.0 / b;
    let mut h = d;
    for i in 1..10_000 {
        let fi = i as f64;
        let an = -fi * (fi - a);
        b += 2.0;
        d = an * d + b;
        if d.abs() < FPMIN {
            d = FPMIN;
        }
        c = b + an / c;
        if c.abs() < FPMIN {
            c = FPMIN;
        }
        d = 1.0 / d;
        let del = d * c;
        h *= del;
        if (del - 1.0).abs() < 1e-16 {
            break;
        }
    }
    (-x + a * x.ln() - lgamma(a)).exp() * h
}

/// Upper tail `1 - pchisq(x, df)` = Q(df / 2, x / 2).
fn chisq_upper(x: f64, df: f64) -> f64 {
    if x <= 0.0 {
        return 1.0;
    }
    let a = df / 2.0;
    let z = x / 2.0;
    if z < a + 1.0 {
        1.0 - gamma_series(a, z)
    } else {
        gamma_cf(a, z)
    }
}

/// Chi-square density `dchisq(x, df, 0)`.
fn chisq_density(x: f64, df: f64) -> f64 {
    if x == 0.0 {
        return if df < 2.0 {
            f64::INFINITY
        } else if df == 2.0 {
            0.5
        } else {
            0.0
        };
    }
    let a = df / 2.0;
    ((a - 1.0) * x.ln() - x / 2.0 - lgamma(a) - a * std::f64::consts::LN_2).exp()
}

/// `tailp_gaussian(c, k0, m, d, TWO_SIDED, n)`: the tail probability of the
/// Gaussian process at level `c`.
fn tailp_gaussian(c: f64, k0: &[f64], d: usize) -> f64 {
    let mut p = 0.0;
    for (i, &k) in k0.iter().enumerate() {
        if k != 0.0 {
            let df = d + 1 - i;
            p += k * chisq_upper(c * c, df as f64) / area(df);
        }
    }
    2.0 * p
}

/// `taild_gaussian(c, k0, m, d, TWO_SIDED, n)`: the derivative of the tail
/// probability with respect to `c`.
fn taild_gaussian(c: f64, k0: &[f64], d: usize) -> f64 {
    let mut p = 0.0;
    for (i, &k) in k0.iter().enumerate() {
        if k != 0.0 {
            let df = d + 1 - i;
            p += k * 2.0 * c * chisq_density(c * c, df as f64) / area(df);
        }
    }
    2.0 * p
}

/// `critval(alpha, k0, m, d, TWO_SIDED, 0, GAUSS)` of `scb_crit.c`: the
/// critical value `c` with tail probability `alpha`, by Newton steps kept
/// inside the bracket, at most 20 iterations.
pub fn critval(alpha: f64, k0: &[f64], d: usize) -> Result<f64, String> {
    const MAXIT: usize = 20;
    if !(alpha > 0.0 && alpha < 1.0) {
        return Err(format!("critval: invalid alpha {alpha}"));
    }
    let mut d = d;
    let mut k0 = k0.to_vec();
    if k0.len() > d + 1 {
        k0.truncate(d + 1);
    }
    if k0.is_empty() {
        d = 0;
        k0 = vec![1.0];
    }

    let mut c = 2.0;
    let mut c0 = 0.0;
    let mut c1 = 0.0;
    for _ in 0..MAXIT {
        let tp = tailp_gaussian(c, &k0, d) - alpha;
        let td = taild_gaussian(c, &k0, d);
        if tp > 0.0 {
            c0 = c;
        }
        if tp < 0.0 {
            c1 = c;
        }
        let mut cn = c + tp / td;
        if cn < c0 {
            cn = (c + c0) / 2.0;
        }
        if c1 > 0.0 && cn > c1 {
            cn = (c + c1) / 2.0;
        }
        c = cn;
        if (tp / alpha).abs() < 1.0e-10 {
            return Ok(c);
        }
    }
    Ok(c)
}

/// `scritval(k0, d, cov, m, rdf = 0, z, k = 1)` of `smisc.c`: the critical
/// value for coverage `cov`, with the Gaussian process (rdf = 0).
pub fn scritval(k0: &[f64], d: usize, cov: f64) -> Result<f64, String> {
    critval(1.0 - cov, k0, d)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn d1_matches_normal_quantile() {
        // For const (0, 1) and d = 1 the band is the two-sided Gaussian quantile.
        let z = scritval(&[0.0, 1.0], 1, 0.95).unwrap();
        assert!((z - 1.959_963_984_540_054).abs() < 1e-8, "{z}");
    }

    #[test]
    fn d2_tail_is_consistent() {
        // The returned c must zero the tail probability it was solved for.
        let k0 = [0.0, 1.0];
        let c = scritval(&k0, 2, 0.95).unwrap();
        let tp = tailp_gaussian(c, &k0, 2);
        assert!((tp - 0.05).abs() < 1e-10, "{tp}");
    }

    #[test]
    fn invalid_alpha_is_error() {
        assert!(critval(0.0, &[0.0, 1.0], 2).is_err());
        assert!(critval(1.0, &[0.0, 1.0], 2).is_err());
    }
}
