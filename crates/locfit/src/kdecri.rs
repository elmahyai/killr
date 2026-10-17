//! Kernel density bandwidth criteria, ported from locfit 1.5-9.12 `band.c`
//! (`kdecri`, `compsda`) and `smisc.c` (`slscv`).
//!
//! `kdecri(x, h, c, k, ker, n)` evaluates one criterion `k` at bandwidth `h`
//! for the sample `x`. The result holds the criterion value in `res[0]`, its
//! derivative in `res[1]`, and (for the least-squares criterion, `k = 3`) the
//! degrees of freedom in `res[2]`.
//!
//! `slscv` is the entry point that R's `lscv.exact` calls: the exact
//! least-squares cross-validation criterion with the Gaussian kernel, which is
//! `kdecri(x, h, 0, 3, WGAUS, n)` returning `res[0]` and `res[2]`.

use crate::kernel::{
    w_fn, wconv1_fn, wconv4_fn, wconv5_fn, wconv_fn, wd_fn, wikk_fn, wint, Kernel,
};

const SQRT2: f64 = std::f64::consts::SQRT_2;

/// `compsda(x, h, n)` from locfit `band.c`: `n/(n-1) * int(fhat''(x)^2 dx)`
/// for a Gaussian-kernel estimate with bandwidth `h`.
pub fn compsda(x: &[f64], h: f64) -> Result<f64, String> {
    let n = x.len();
    let ik = wint(1, &[], Kernel::Gaus)?;
    let mut sd = 0.0;
    for i in 0..n {
        for j in i..n {
            let z = (x[i] - x[j]) / h;
            let mult = if i == j { 1.0 } else { 2.0 };
            sd += mult * wconv4_fn(z, Kernel::Gaus)? / (ik * ik);
        }
    }
    let nf = n as f64;
    Ok(sd / (nf * (nf - 1.0) * h * h * h * h * h))
}

/// `kdecri(x, h, res, c, k, ker, n)` from locfit `band.c`.
///
/// Returns `res[0..4]`. `k` is locfit's criterion code: 1 AIC, 2 OCV,
/// 3 LSCV, 4 BCV, 5 SJPI, 6 gas-k-k. Any other code is an error.
pub fn kdecri(x: &[f64], h: f64, c: f64, k: usize, ker: Kernel) -> Result<[f64; 4], String> {
    let n = x.len();
    let nf = n as f64;
    let mut res = [0.0_f64; 4];
    let ik = wint(1, &[], ker)?;

    match k {
        1 => {
            // aic
            let pen = 2.0;
            for i in 0..n {
                let mut r0 = 0.0;
                let mut d0 = 0.0;
                for j in 0..n {
                    let s = (x[i] - x[j]) / h;
                    r0 += w_fn(s, ker);
                    d0 += s * s * wd_fn(s, ker)?;
                }
                d0 = -(d0 + r0) / (nf * h * h * ik);
                r0 /= nf * h * ik;
                let w00 = w_fn(0.0, ker);
                res[0] += -2.0 * r0.ln() + pen * w00 / (nf * h * ik * r0);
                res[1] += -2.0 * d0 / r0
                    - pen * w00 / (nf * h * ik * r0) * (d0 / r0 + 1.0 / h);
            }
            Ok(res)
        }
        2 => {
            // ocv
            for i in 0..n {
                let mut r0 = 0.0;
                let mut d0 = 0.0;
                for j in 0..n {
                    if i != j {
                        let s = (x[i] - x[j]) / h;
                        r0 += w_fn(s, ker);
                        d0 += s * s * wd_fn(s, ker)?;
                    }
                }
                d0 = -(d0 + r0) / ((nf - 1.0) * h * h);
                r0 /= (nf - 1.0) * h;
                res[0] -= r0.ln();
                res[1] -= d0 / r0;
            }
            Ok(res)
        }
        3 => {
            // lscv
            let mut r0 = 0.0;
            let mut r1 = 0.0;
            let mut d0 = 0.0;
            let mut d1 = 0.0;
            let mut degfree = 0.0;
            for i in 0..n {
                let mut dfd = 0.0;
                for j in 0..n {
                    let s = (x[i] - x[j]) / h;
                    let wij = w_fn(s, ker);
                    dfd += wij;
                    r0 += wconv_fn(s, ker)?;
                    d0 += -s * s * wconv1_fn(s, ker)?;
                    if i != j {
                        r1 += wij;
                        d1 += -s * s * wd_fn(s, ker)?;
                    }
                }
                degfree += 1.0 / dfd;
            }
            d1 -= r1;
            d0 -= r0;
            res[0] = r0 / (nf * nf * h * ik * ik) - 2.0 * r1 / (nf * (nf - 1.0) * h * ik);
            res[1] = d0 / (nf * nf * h * h * ik * ik)
                - 2.0 * d1 / (nf * (nf - 1.0) * h * h * ik);
            res[2] = degfree;
            Ok(res)
        }
        4 => {
            // bcv
            let mut r0 = 0.0;
            let mut d0 = 0.0;
            for i in 0..n {
                for j in (i + 1)..n {
                    let s = (x[i] - x[j]) / h;
                    r0 += 2.0 * wconv4_fn(s, ker)?;
                    d0 += 2.0 * s * wconv5_fn(s, ker)?;
                }
            }
            d0 = (-d0 - r0) / (nf * nf * h * h * ik * ik);
            r0 /= nf * nf * ik * ik;
            let d1 = wint(1, &[2], ker)?;
            let r1 = wconv_fn(0.0, ker)?;
            res[0] = (d1 * d1 * r0 / 4.0 + r1 / (nf * h)) / (ik * ik);
            res[1] = (d1 * d1 * d0 / 4.0 - r1 / (nf * h * h)) / (ik * ik);
            Ok(res)
        }
        5 => {
            // sjpi
            let s = c * (5.0 * h.ln() / 7.0).exp() / SQRT2;
            let d0 = compsda(x, s)?;
            res[0] = d0;
            res[1] = ((wikk_fn(Kernel::Gaus, 0)? / (d0 * nf)).ln() / 5.0).exp() - h;
            Ok(res)
        }
        6 => {
            // gas-k-k
            let s = (nf.ln() / 10.0).exp() * h;
            let d0 = compsda(x, s)?;
            res[0] = d0;
            res[1] = ((wikk_fn(Kernel::Gaus, 0)? / (d0 * nf)).ln() / 5.0).exp() - h;
            Ok(res)
        }
        _ => Err("kdecri: what???".to_string()),
    }
}

/// `slscv(x, h, z, n)` from locfit `smisc.c`: the exact LSCV criterion and
/// degrees of freedom for the Gaussian kernel. Returns `[res[0], res[2]]`.
pub fn slscv(x: &[f64], h: f64) -> Result<[f64; 2], String> {
    let res = kdecri(x, h, 0.0, 3, Kernel::Gaus)?;
    Ok([res[0], res[2]])
}

