//! Weight functions and local polynomial basis, ported from locfit
//! `weight.c` (`W`) and `lf_fitfun.c` (`calcp`, `fitfun`) for the
//! spherical and product kernel types with non-angular variables.

/// Weight functions (locfit `WRECT`..`WPARM`) that this crate implements.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Kernel {
    Rect,
    Epan,
    Bisq,
    Tcub,
    Trwt,
    Tria,
    Ququ,
    Cub6,
    Gaus,
    Expl,
    Parm,
}

/// Multivariate kernel type (locfit `KSPH`, `KPROD`).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Kt {
    Sph,
    Prod,
}

const GFACT: f64 = 2.5;
const EFACT: f64 = 3.0;

/// Parse the kernel names accepted by R's `locfit.raw(kern = ...)`.
pub fn kernel_from_str(s: &str) -> Result<Kernel, String> {
    Ok(match s {
        "rectangular" | "rect" => Kernel::Rect,
        "epanechnikov" | "epan" => Kernel::Epan,
        "bisquare" | "bisq" => Kernel::Bisq,
        "tricube" | "tcub" => Kernel::Tcub,
        "triweight" | "trwt" => Kernel::Trwt,
        "triangular" | "tria" => Kernel::Tria,
        "ququ" => Kernel::Ququ,
        "6cub" => Kernel::Cub6,
        "gaussian" | "gaus" => Kernel::Gaus,
        "exponential" | "expl" => Kernel::Expl,
        "parametric" | "parm" => Kernel::Parm,
        other => return Err(format!("kernel '{other}' is not ported yet")),
    })
}

/// Parse the kernel-type names accepted by R's `locfit.raw(kt = ...)`.
pub fn kt_from_str(s: &str) -> Result<Kt, String> {
    match s {
        "sph" | "spherical" => Ok(Kt::Sph),
        "prod" | "product" => Ok(Kt::Prod),
        other => Err(format!("kernel type '{other}' is not ported yet")),
    }
}

/// `W(u, ker)` from locfit `weight.c`.
pub fn w_fn(u: f64, ker: Kernel) -> f64 {
    let u = u.abs();
    match ker {
        Kernel::Rect => {
            if u > 1.0 {
                0.0
            } else {
                1.0
            }
        }
        Kernel::Epan => {
            if u > 1.0 {
                0.0
            } else {
                1.0 - u * u
            }
        }
        Kernel::Bisq => {
            if u > 1.0 {
                0.0
            } else {
                let v = 1.0 - u * u;
                v * v
            }
        }
        Kernel::Tcub => {
            if u > 1.0 {
                0.0
            } else {
                let v = 1.0 - u * u * u;
                v * v * v
            }
        }
        Kernel::Trwt => {
            if u > 1.0 {
                0.0
            } else {
                let v = 1.0 - u * u;
                v * v * v
            }
        }
        Kernel::Tria => {
            if u > 1.0 {
                0.0
            } else {
                1.0 - u
            }
        }
        Kernel::Ququ => {
            if u > 1.0 {
                0.0
            } else {
                let v = 1.0 - u * u;
                v * v * v * v
            }
        }
        Kernel::Cub6 => {
            if u > 1.0 {
                0.0
            } else {
                let v = 1.0 - u * u * u;
                let v = v * v * v;
                v * v
            }
        }
        Kernel::Gaus => (-(GFACT * u) * (GFACT * u) / 2.0).exp(),
        Kernel::Expl => (-EFACT * u).exp(),
        Kernel::Parm => 1.0,
    }
}

/// Number of local fitting functions `p` (locfit `calcp`).
pub fn calcp(kt: Kt, d: usize, deg: usize) -> usize {
    match kt {
        Kt::Sph => {
            let mut k = 1usize;
            for i in 1..=deg {
                k = k * (d + i) / i;
            }
            k
        }
        Kt::Prod => d * deg + 1,
    }
}

/// Local polynomial basis `f` at `x` relative to `t` (locfit `fitfun`), with
/// the derivative multi-index given by `derivs` (one entry per derivative).
/// Only the non-angular, spherical and product cases are implemented.
pub fn fitfun(
    x: &[f64],
    t: Option<&[f64]>,
    d: usize,
    kt: Kt,
    deg: usize,
    derivs: &[usize],
    f: &mut [f64],
) {
    let nd = derivs.len();
    let mut m = 0usize;
    f[m] = if nd == 0 { 1.0 } else { 0.0 };
    m += 1;
    if deg == 0 {
        return;
    }

    let mut ct = vec![0usize; d];
    for &k in derivs {
        ct[k] += 1;
    }
    let mut dx = vec![0.0; d];
    for i in 0..d {
        dx[i] = match t {
            None => x[i],
            Some(tt) => x[i] - tt[i],
        };
    }
    // ff[i][j] = d^j/dx^j derivative of the basis for dimension i, scaled.
    let mut ff = vec![vec![0.0; deg + 1]; d];
    for i in 0..d {
        if ct[i] <= deg {
            ff[i][ct[i]] = 1.0;
        }
        for j in (ct[i] + 1)..=deg {
            ff[i][j] = ff[i][j - 1] * dx[i] / ((j - ct[i]) as f64);
        }
    }
    let sel = |cond: bool, v: f64| if cond { v } else { 0.0 };

    if d == 1 || kt == Kt::Prod {
        for j in 1..=deg {
            for i in 0..d {
                f[m] = sel(ct[i] == nd, ff[i][j]);
                m += 1;
            }
        }
        return;
    }

    for i in 0..d {
        f[m] = sel(ct[i] == nd, ff[i][1]);
        m += 1;
    }
    if deg == 1 {
        return;
    }
    for i in 0..d {
        f[m] = sel(ct[i] == nd, ff[i][2]);
        m += 1;
        for j in (i + 1)..d {
            f[m] = sel(ct[i] + ct[j] == nd, ff[i][1] * ff[j][1]);
            m += 1;
        }
    }
    if deg == 2 {
        return;
    }
    for i in 0..d {
        f[m] = sel(ct[i] == nd, ff[i][3]);
        m += 1;
        for k in (i + 1)..d {
            f[m] = sel(ct[i] + ct[k] == nd, ff[i][2] * ff[k][1]);
            m += 1;
        }
        for j in (i + 1)..d {
            f[m] = sel(ct[i] + ct[j] == nd, ff[i][1] * ff[j][2]);
            m += 1;
            for k in (j + 1)..d {
                f[m] = sel(
                    ct[i] + ct[j] + ct[k] == nd,
                    ff[i][1] * ff[j][1] * ff[k][1],
                );
                m += 1;
            }
        }
    }
}

/// `sqrt(pi)`, locfit `SQRPI`.
const SQRPI: f64 = 1.772_453_850_905_516;
/// `sqrt(2 pi)`, locfit `S2PI`.
const S2PI: f64 = 2.506_628_274_631_000_5;

/// `W'(u)` from locfit `weight.c` (`Wd`).
pub fn wd_fn(u: f64, ker: Kernel) -> Result<f64, String> {
    if ker == Kernel::Gaus {
        return Ok(-(GFACT * GFACT) * (-(GFACT * u) * (GFACT * u) / 2.0).exp());
    }
    if ker == Kernel::Parm {
        return Ok(0.0);
    }
    if u.abs() > 1.0 {
        return Ok(0.0);
    }
    Ok(match ker {
        Kernel::Epan => -2.0,
        Kernel::Bisq => -4.0 * (1.0 - u * u),
        Kernel::Tcub => {
            let v = 1.0 - u * u * u;
            -9.0 * v * v * u
        }
        Kernel::Trwt => {
            let v = 1.0 - u * u;
            -6.0 * v * v
        }
        _ => return Err(format!("Invalid kernel {ker:?} in Wd")),
    })
}

/// `Wconv(v, ker)` from locfit `weight.c`: the Taylor expansion of the
/// kernel convolution `int W(x) W(x + v) dx`.
pub fn wconv_fn(v: f64, ker: Kernel) -> Result<f64, String> {
    match ker {
        Kernel::Gaus => Ok(SQRPI / GFACT * (-(GFACT * v) * (GFACT * v) / 4.0).exp()),
        Kernel::Rect => {
            let v = v.abs();
            Ok(if v > 2.0 { 0.0 } else { 2.0 - v })
        }
        Kernel::Epan => {
            let v = v.abs();
            Ok(if v > 2.0 {
                0.0
            } else {
                (2.0 - v) * (16.0 + v * (8.0 - v * (16.0 - v * (2.0 + v)))) / 30.0
            })
        }
        Kernel::Bisq => {
            let v = v.abs();
            if v > 2.0 {
                return Ok(0.0);
            }
            let v2 = 2.0 - v;
            Ok(v2 * v2 * v2 * v2 * v2 * (16.0 + v * (40.0 + v * (36.0 + v * (10.0 + v)))) / 630.0)
        }
        _ => Err(format!("Wconv not implemented for kernel {ker:?}")),
    }
}

/// `Wconv1(v, ker)` from locfit `weight.c`: `(1/v) d/dv` of `Wconv`.
pub fn wconv1_fn(v: f64, ker: Kernel) -> Result<f64, String> {
    let v = v.abs();
    match ker {
        Kernel::Gaus => Ok(-0.5 * SQRPI * GFACT * (-(GFACT * v) * (GFACT * v) / 4.0).exp()),
        Kernel::Rect => Ok(if v > 2.0 { 0.0 } else { 1.0 }),
        Kernel::Epan => Ok(if v > 2.0 {
            0.0
        } else {
            (-16.0 + v * (12.0 - v * v)) / 6.0
        }),
        Kernel::Bisq => {
            if v > 2.0 {
                return Ok(0.0);
            }
            let v2 = 2.0 - v;
            Ok(-v2 * v2 * v2 * v2 * (32.0 + v * (64.0 + v * (24.0 + v * 3.0))) / 210.0)
        }
        _ => Err(format!("Wconv1 not implemented for kernel {ker:?}")),
    }
}

/// `Wconv4(v, ker)` from locfit `weight.c`: 4th derivative of `Wconv`.
pub fn wconv4_fn(v: f64, ker: Kernel) -> Result<f64, String> {
    match ker {
        Kernel::Gaus => {
            let gv = GFACT * v;
            Ok((-(gv * gv) / 4.0).exp() * GFACT * GFACT * GFACT
                * (12.0 - gv * gv * (12.0 - gv * gv))
                * SQRPI
                / 16.0)
        }
        _ => Err(format!("Wconv4 not implemented for kernel {ker:?}")),
    }
}

/// `Wconv5(v, ker)` from locfit `weight.c`: 5th derivative of `Wconv`.
pub fn wconv5_fn(v: f64, ker: Kernel) -> Result<f64, String> {
    match ker {
        Kernel::Gaus => {
            let gv = GFACT * v;
            Ok(-(-(gv * gv) / 4.0).exp()
                * GFACT * GFACT * GFACT * GFACT
                * gv
                * (60.0 - gv * gv * (20.0 - gv * gv))
                * SQRPI
                / 32.0)
        }
        _ => Err(format!("Wconv5 not implemented for kernel {ker:?}")),
    }
}

/// `Wconv6(v, ker)` from locfit `weight.c`: 6th derivative of `Wconv`, used by
/// the SJPI bandwidth (`widthsj`). Only the Gaussian kernel is implemented.
pub fn wconv6_fn(v: f64, ker: Kernel) -> Result<f64, String> {
    match ker {
        Kernel::Gaus => {
            let gv = GFACT * v;
            let gv = gv * gv;
            let z = (-gv / 4.0).exp() * (-120.0 + gv * (180.0 - gv * (30.0 - gv)))
                * 0.027_694_591_42;
            let g2 = GFACT * GFACT;
            Ok(z * g2 * g2 * GFACT)
        }
        _ => Err(format!("Wconv6 not implemented for kernel {ker:?}")),
    }
}

/// Natural log of the gamma function (Lanczos approximation, g = 7).
pub fn lgamma(x: f64) -> f64 {
    const G: [f64; 9] = [
        0.999_999_999_999_809_9,
        676.520_368_121_885_1,
        -1_259.139_216_722_402_8,
        771.323_428_777_653_1,
        -176.615_029_162_140_6,
        12.507_343_278_686_905,
        -0.138_571_095_265_720_12,
        9.984_369_578_019_572e-6,
        1.505_632_735_149_311_6e-7,
    ];
    if x < 0.5 {
        let s = (std::f64::consts::PI * x).sin();
        return (std::f64::consts::PI / s.abs()).ln() - lgamma(1.0 - x);
    }
    let x = x - 1.0;
    let mut a = G[0];
    let t = x + 7.5;
    for (i, g) in G.iter().enumerate().skip(1) {
        a += g / (x + i as f64);
    }
    0.5 * (2.0 * std::f64::consts::PI).ln() + (x + 0.5) * t.ln() - t + a.ln()
}

/// `wint(d, j, nj, ker)` from locfit `weight.c`: `int u^(j1)...u^(jd) W(u) du`
/// over R^d, for a 1-d kernel of order `ker`. Used with `d = 1` in `kdecri`.
pub fn wint(d: usize, j: &[usize], ker: Kernel) -> Result<f64, String> {
    let nj = j.len();
    let dj = d + j.iter().sum::<usize>();
    let dj_d = dj as f64;
    let mut i_val = match ker {
        Kernel::Rect => 1.0 / dj_d,
        Kernel::Epan => 2.0 / (dj_d * (dj_d + 2.0)),
        Kernel::Bisq => 8.0 / (dj_d * (dj_d + 2.0) * (dj_d + 4.0)),
        Kernel::Tcub => 162.0 / (dj_d * (dj_d + 3.0) * (dj_d + 6.0) * (dj_d + 9.0)),
        Kernel::Trwt => 48.0 / (dj_d * (dj_d + 2.0) * (dj_d + 4.0) * (dj_d + 6.0)),
        Kernel::Tria => 1.0 / (dj_d * (dj_d + 1.0)),
        Kernel::Ququ => {
            384.0 / (dj_d * (dj_d + 2.0) * (dj_d + 4.0) * (dj_d + 6.0) * (dj_d + 8.0))
        }
        Kernel::Cub6 => {
            524_880.0
                / (dj_d * (dj_d + 3.0) * (dj_d + 6.0) * (dj_d + 9.0) * (dj_d + 12.0)
                    * (dj_d + 15.0)
                    * (dj_d + 18.0))
        }
        Kernel::Gaus => {
            let mut v = match d {
                1 => S2PI / GFACT,
                2 => 2.0 * std::f64::consts::PI / (GFACT * GFACT),
                _ => (d as f64 * (S2PI / GFACT).ln()).exp(),
            };
            // locfit drops the fall-through from case 4 to case 2 on purpose.
            for &jk in j {
                match jk {
                    4 => {
                        v *= 3.0 / (GFACT * GFACT);
                        v /= GFACT * GFACT;
                    }
                    2 => v /= GFACT * GFACT,
                    _ => {}
                }
            }
            return Ok(v);
        }
        Kernel::Expl => {
            let fact = (1..dj).fold(1.0_f64, |a, k| a * k as f64);
            fact / EFACT.powi(dj as i32)
        }
        Kernel::Parm => return Err("Unknown kernel in wint".to_string()),
    };
    if d == 1 && nj == 0 {
        return Ok(2.0 * i_val);
    }
    let mut z = (d as f64 - nj as f64) * LOGPI_HALF - lgamma(dj_d / 2.0);
    for &jk in j {
        z += lgamma((jk as f64 + 1.0) / 2.0);
    }
    i_val *= 2.0 * z.exp();
    Ok(i_val)
}

/// `LOGPI / 2`, with locfit `LOGPI = log(pi)`.
const LOGPI_HALF: f64 = 1.144_729_885_849_400_2 / 2.0;

/// `Wikk(ker, deg)` from locfit `weight.c`, for `deg` 0 to 3.
pub fn wikk_fn(ker: Kernel, deg: usize) -> Result<f64, String> {
    let v = match deg {
        0 | 1 => match ker {
            Kernel::Rect => 4.5,
            Kernel::Epan => 15.0,
            Kernel::Bisq => 35.0,
            Kernel::Gaus => 0.282_094_791_8 * GFACT * GFACT * GFACT * GFACT * GFACT,
            Kernel::Tcub => 34.152_111_05,
            Kernel::Trwt => 66.083_916_08,
            _ => return Err(format!("Wikk not implemented for kernel {ker:?}")),
        },
        _ => match ker {
            Kernel::Rect => 11025.0,
            Kernel::Epan => 39690.0,
            Kernel::Bisq => 110_346.923_1,
            Kernel::Gaus => 14527.434_12,
            Kernel::Tcub => 126_500.590_4,
            Kernel::Trwt => 254_371.764_7,
            _ => return Err(format!("Wikk not implemented for kernel {ker:?}")),
        },
    };
    Ok(v)
}
