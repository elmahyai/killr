//! Anderson-Darling kernels from goftest 1.2-3, ported from `src/AnDarl.c`
//! and `src/ADinf.c` (original C by G. and J. Marsaglia).
//!
//! The Cramer-von Mises distribution (`R/cramer.R`) is R code that calls
//! `besselK`; goftest has no C for it, so it is not a kernel here.
//!
//! Floating-point operations keep the C evaluation order so results match
//! the compiled R package to rounding error.

#[cfg(feature = "python")]
mod python;

/// Short asymptotic approximation to `Pr[A_n < z]`, `adinf()` in AnDarl.c.
pub fn adinf(z: f64) -> f64 {
    if z < 2.0 {
        let s1 = 0.011672 - 0.00168691 * z;
        let s2 = 0.0347962 - s1 * z;
        let s3 = 0.0649821 - s2 * z;
        let s4 = 0.247105 - s3 * z;
        let poly = 2.00012 + s4 * z;
        return (-1.2337141 / z).exp() / z.sqrt() * poly;
    }
    let u1 = 0.008056 - 0.0003146 * z;
    let u2 = 0.082433 - u1 * z;
    let u3 = 0.43424 - u2 * z;
    let u4 = 2.30695 - u3 * z;
    let u5 = 1.0776 - u4 * z;
    (-(u5.exp())).exp()
}

/// Finite-sample correction to `adinf(x)`, `errfix()` in AnDarl.c.
pub fn errfix(n: i32, x: f64) -> f64 {
    let nf = n as f64;
    if x > 0.8 {
        return (-130.2137
            + (745.2337 - (1705.091 - (1950.646 - (1116.360 - 255.7844 * x) * x) * x) * x) * x)
            / nf;
    }
    let c = 0.01265 + 0.1757 / nf;
    if x < c {
        let t = x / c;
        let t = t.sqrt() * (1.0 - t) * (49.0 * t - 102.0);
        return t * (0.0037 / (nf * nf) + 0.00078 / nf + 0.00006) / nf;
    }
    let t = (x - c) / (0.8 - c);
    let t = -0.00022633 + (6.54034 - (14.6538 - (14.458 - (8.259 - 1.91864 * t) * t) * t) * t) * t;
    t * (0.04213 + 0.01365 / nf) / nf
}

/// `Pr[A_n < z]` for sample size `n`, `AD()` in AnDarl.c.
///
/// The C computes `x + v` where `v` is the same correction `errfix` applies,
/// so this is `adinf(z) + errfix(n, adinf(z))`.
pub fn ad_prob(n: i32, z: f64) -> f64 {
    let x = adinf(z);
    x + errfix(n, x)
}

/// Anderson-Darling statistic `A_n` for sorted `x` in `[0, 1]`, `ADstat()`.
///
/// The caller sorts `x`, as the R wrapper `simpleADtest` does.
pub fn ad_statistic(x: &[f64]) -> f64 {
    let n = x.len();
    let mut z = 0.0;
    for i in 0..n {
        let t = x[i] * (1.0 - x[n - 1 - i]);
        z = z - ((i + i + 1) as f64) * t.ln();
    }
    -(n as f64) + z / (n as f64)
}

/// `ADtestR()` in AnDarl.c: returns `(statistic, p-value)` with
/// `p-value = 1 - Pr[A_n < statistic]`. `x` must be sorted.
pub fn ad_test(x: &[f64]) -> (f64, f64) {
    let a = ad_statistic(x);
    let p = ad_prob(x.len() as i32, a);
    (a, 1.0 - p)
}

/// Standard normal upper tail `cPhi(x) = P[N(0,1) > x]`, `cPhi()` in ADinf.c.
///
/// The C reads `v[j]` past the end of its 9-entry table when `|x| >= 17`
/// (undefined behaviour). Here `j` is capped at 8, so `|x| > 16` uses the
/// last Taylor base point. ADinf only reaches that range for `z < 0.0086`,
/// where the terms it affects are below `1e-60`.
pub fn c_phi(x: f64) -> f64 {
    const V: [f64; 9] = [
        1.25331413731550025,
        0.421369229288054473,
        0.236652382913560671,
        0.162377660896867462,
        0.123131963257932296,
        0.0990285964717319214,
        0.0827662865013691773,
        0.0710695805388521071,
        0.0622586659950261958,
    ];
    let j = (((x.abs() + 1.0) / 2.0) as usize).min(8);
    let mut a = V[j];
    let z = (2 * j) as f64;
    let h = x.abs() - z;
    let mut b = z * a - 1.0;
    let mut pwr = 1.0;
    let mut s = a + h * b;
    let mut i = 2;
    while i < 100 {
        a = (a + z * b) / i as f64;
        b = (b + z * a) / (i + 1) as f64;
        pwr = pwr * h * h;
        let t = s;
        s = s + pwr * (a + h * b);
        if s == t {
            s *= (-0.5 * x * x - 0.91893853320467274178).exp();
            return if x > 0.0 { s } else { 1.0 - s };
        }
        i += 2;
    }
    if x > 0.0 {
        s
    } else {
        1.0 - s
    }
}

/// Term `j` of the exact limiting series, `ADf()` in ADinf.c.
fn ad_f(z: f64, j: i32) -> f64 {
    let t = ((4 * j + 1) * (4 * j + 1)) as f64 * 1.23370055013617 / z;
    if t > 150.0 {
        return 0.0;
    }
    let mut a = 2.22144146907918 * (-t).exp() / t.sqrt();
    let mut b = 3.93740248643060 * 2.0 * c_phi((2.0 * t).sqrt());
    let mut r = z * 0.125;
    let mut f = a + b * r;
    for i in 1..200 {
        let fi = i as f64;
        let c = ((fi - 0.5 - t) * b + t * a) / fi;
        a = b;
        b = c;
        r *= z / ((8 * i + 8) as f64);
        if r.abs() < 1e-40 || c.abs() < 1e-40 {
            return f;
        }
        let fnew = f + c * r;
        if f == fnew {
            return f;
        }
        f = fnew;
    }
    f
}

/// Exact limiting distribution `lim_n Pr[A_n < z]`, `ADinf()` in ADinf.c.
pub fn ad_inf(z: f64) -> f64 {
    if z < 0.01 {
        return 0.0;
    }
    let mut r = 1.0 / z;
    let mut ad = r * ad_f(z, 0);
    for j in 1..100 {
        let jf = j as f64;
        r *= (0.5 - jf) / jf;
        let adnew = ad + (4 * j + 1) as f64 * r * ad_f(z, j);
        if ad == adnew {
            return ad;
        }
        ad = adnew;
    }
    ad
}
