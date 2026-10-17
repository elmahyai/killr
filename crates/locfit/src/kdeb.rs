//! Kernel density bandwidth selection, ported from locfit 1.5-9.12 `band.c`
//! (`widthsj`, `esolve`, `kdeselect`) and `lf_nbhd.c` (`kordstat`).
//!
//! R's `kdeb()` calls the C entry point `kdeb` (`smisc.c`) through
//! `.C("kdeb")`. That entry point runs `kdeselect`: it estimates the SJPI
//! pilot scale from the inter-quartile range, then solves each requested
//! criterion for its bandwidth by a bracketed secant search (`esolve`).
//!
//! Only the Gaussian kernel is used by R's default `kdeb(kern = "gauss")`.
//! The other kernel names are accepted, and the criteria that need a
//! kernel-convolution derivative return an error for them, as locfit does.

use crate::kdecri::{compsda, kdecri};
use crate::kernel::{wconv4_fn, wconv6_fn, wconv_fn, wint, Kernel};

const GFACT: f64 = 2.5;
const SQRT2: f64 = std::f64::consts::SQRT_2;

/// Method codes, in R's `match(meth, c("AIC", "LCV", "LSCV", "BCV", "SJPI", "GKK"))`
/// order. These are also locfit's `kdecri` criterion codes 1 to 6.
pub fn meth_from_str(s: &str) -> Result<usize, String> {
    Ok(match s {
        "AIC" => 1,
        "LCV" => 2,
        "LSCV" => 3,
        "BCV" => 4,
        "SJPI" => 5,
        "GKK" => 6,
        other => return Err(format!("kdeb: unknown method '{other}'")),
    })
}

/// Kernel names in R's `pmatch(kern, c("rect", "epan", "bisq", "tcub", "trwt", "gauss"))`.
pub fn kern_from_r(s: &str) -> Result<Kernel, String> {
    Ok(match s {
        "rect" => Kernel::Rect,
        "epan" => Kernel::Epan,
        "bisq" => Kernel::Bisq,
        "tcub" => Kernel::Tcub,
        "trwt" => Kernel::Trwt,
        "gauss" => Kernel::Gaus,
        other => return Err(format!("kdeb: unknown kernel '{other}'")),
    })
}

/// `widthsj(x, lambda, n)` from locfit `band.c`: the Sheather-Jones pilot
/// bandwidth for the 4th-derivative functional, with scale `lambda`.
fn widthsj(x: &[f64], lambda: f64) -> Result<f64, String> {
    let n = x.len();
    let nf = n as f64;
    let a = GFACT * 0.920 * lambda * (-(nf.ln()) / 7.0).exp() / SQRT2;
    let b = GFACT * 0.912 * lambda * (-(nf.ln()) / 9.0).exp() / SQRT2;
    let ik = wint(1, &[], Kernel::Gaus)?;

    let mut td = 0.0;
    for i in 0..n {
        for j in i..n {
            let z = (x[i] - x[j]) / b;
            let mult = if i == j { 1.0 } else { 2.0 };
            td += mult * wconv6_fn(z, Kernel::Gaus)? / (ik * ik);
        }
    }
    td = -td / (nf * (nf - 1.0));

    let c1 = wconv4_fn(0.0, Kernel::Gaus)?;
    let c2 = wint(1, &[2], Kernel::Gaus)?;
    let c3 = wconv_fn(0.0, Kernel::Gaus)?;
    let sa = compsda(x, a)?;
    let g4 = GFACT * GFACT * GFACT * GFACT;
    Ok(b * ((c1 * ik / (c2 * c3 * g4) * sa / td).ln() / 7.0).exp() * SQRT2)
}

/// `esolve(x, j, h0, h1, k, c, ker, n)` from locfit `band.c`: the bandwidth
/// that solves criterion `j` on `[h0, h1]`, scanning `k` log-spaced steps for
/// a sign change of the derivative, then refining it by secant steps.
/// Criteria 4 to 6 (BCV, SJPI, GKK) return the first root found.
fn esolve(x: &[f64], j: usize, h0: f64, h1: f64, k: usize, c: f64, ker: Kernel) -> Result<f64, String> {
    let mut h = [0.0_f64; 7];
    let mut d = [0.0_f64; 7];
    let mut r = [0.0_f64; 7];
    let mut min = 1.0e30_f64;
    let mut minh = 0.0_f64;
    let fact = 1.00001_f64;

    h[6] = h0;
    let res = kdecri(x, h[6], c, j, ker)?;
    r[6] = res[0];
    d[6] = res[1];
    let mut nc = 0usize;
    for i in 0..k {
        h[5] = h[6];
        r[5] = r[6];
        d[5] = d[6];
        h[6] = h0 * ((i + 1) as f64 * (h1 / h0).ln() / k as f64).exp();
        let res = kdecri(x, h[6], c, j, ker)?;
        r[6] = res[0];
        d[6] = res[1];
        if d[5] * d[6] < 0.0 {
            h[2] = h[5];
            h[0] = h[5];
            d[2] = d[5];
            d[0] = d[5];
            r[2] = r[5];
            r[0] = r[5];
            h[3] = h[6];
            h[1] = h[6];
            d[3] = d[6];
            d[1] = d[6];
            r[3] = r[6];
            r[1] = r[6];
            while h[3] > fact * h[2] || h[2] > fact * h[3] {
                h[4] = h[3] - d[3] * (h[3] - h[2]) / (d[3] - d[2]);
                if h[4] < h[0] || h[4] > h[1] {
                    h[4] = (h[0] + h[1]) / 2.0;
                }
                let res = kdecri(x, h[4], c, j, ker)?;
                r[4] = res[0];
                d[4] = res[1];
                h[2] = h[3];
                h[3] = h[4];
                d[2] = d[3];
                d[3] = d[4];
                r[2] = r[3];
                r[3] = r[4];
                if d[4] * d[0] > 0.0 {
                    h[0] = h[4];
                    d[0] = d[4];
                    r[0] = r[4];
                } else {
                    h[1] = h[4];
                    d[1] = d[4];
                    r[1] = r[4];
                }
            }
            if j >= 4 {
                return Ok(h[4]); // first min for BCV etc
            }
            if r[4] <= min {
                min = r[4];
                minh = h[4];
            }
            nc += 1;
        }
    }
    if nc == 0 {
        minh = if r[5] < r[6] { h0 } else { h1 };
    }
    Ok(minh)
}

/// `kdeselect(band, x, ind, h0, h1, meth, nm, ker, n)` from locfit `band.c`.
///
/// `kordstat` in the C code is the k-th smallest value, so a sorted copy gives
/// the same two quartile values. `h0` and `h1` are already scaled by `gf`.
pub fn kdeselect(x: &[f64], h0: f64, h1: f64, meth: &[usize], ker: Kernel) -> Result<Vec<f64>, String> {
    let n = x.len();
    let k = n / 4;
    if k < 1 {
        return Err("kdeb: needs at least 4 observations".to_string());
    }
    let mut sorted = x.to_vec();
    sorted.sort_by(|a, b| a.total_cmp(b));
    // kordstat(x, n+1-k) - kordstat(x, k), 1-based ranks.
    let scale = sorted[n - k] - sorted[k - 1];
    let c = widthsj(x, scale)?;
    meth.iter()
        .map(|&m| esolve(x, m, h0, h1, 10, c, ker))
        .collect()
}

/// R's `kdeb(x, h0, h1, meth, kern, gf)` after the R-side scaling: `h0` and
/// `h1` are `gf * h0` and `gf * h1`. Returns one bandwidth per method.
pub fn kdeb(x: &[f64], h0: f64, h1: f64, meth: &[usize], ker: Kernel) -> Result<Vec<f64>, String> {
    for &m in meth {
        if !(1..=6).contains(&m) {
            return Err(format!("kdeb: method code {m} is not 1 to 6"));
        }
    }
    kdeselect(x, h0, h1, meth, ker)
}
