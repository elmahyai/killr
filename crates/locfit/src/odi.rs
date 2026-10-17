//! Port of locfit 1.5-9.12 `dens_odi.c` (one-dimensional integrals of the
//! density likelihood `int W(u) u^j exp(P(u)) du`), with the helpers it calls
//! from `weight.c` (`wtaylor`), `math.c` (`lf_exp`, `lfdaws`, `ptail`) and
//! `prob.c` (`mut_pnorm`).
//!
//! The series truncations (`1e-8` in `explint1` and `explinfbk0`, `1e-10` in
//! the Dawson and tail series) are kept, so the results carry the same
//! approximation error as R's, not the error of an exact integral.
//!
//! Convention: `cf` is `[a, b, c]` for `P(u) = a + b u + c u^2 / 2` in
//! `onedint` (as in locfit), and `[a, b, c]` for `a + b u + c u^2` inside
//! `recurint` (locfit halves `c` in `onedint`).

use crate::kernel::Kernel;

const S2PI: f64 = 2.506_628_274_631_000_5;
const SQRPI: f64 = 1.772_453_850_905_516;
const SQRT2: f64 = std::f64::consts::SQRT_2;
/// Work-array length; locfit uses fixed arrays of 50 to 150 entries.
const WORK: usize = 256;

/// locfit `lf_exp`: `exp` with the overflow value capped.
fn lf_exp(x: f64) -> f64 {
    if x > 700.0 {
        1.014_232_054_735_004e304
    } else {
        x.exp()
    }
}

/// Dawson's function table at quarter steps (locfit `lfdaws`).
const DAWS_VAL: [f64; 25] = [
    0.0,
    0.24485619356002,
    0.46034428261948,
    0.62399959848185,
    0.72477845900708,
    0.76388186132749,
    0.75213621001998,
    0.70541701910853,
    0.63998807456541,
    0.56917098836654,
    0.50187821196415,
    0.44274283060424,
    0.39316687916687,
    0.35260646480842,
    0.31964847250685,
    0.29271122077502,
    0.27039629581340,
    0.25160207761769,
    0.23551176224443,
    0.22153505358518,
    0.20924575719548,
    0.19833146819662,
    0.18855782729305,
    0.17974461154688,
    0.17175005072385,
];

/// Dawson's function (locfit `lfdaws`).
fn daws(x: f64) -> f64 {
    if x < 0.0 {
        return -daws(-x);
    }
    if x > 6.0 {
        let mut y = 1.0 / x;
        let mut z = y;
        let mut j = 0usize;
        loop {
            let f0 = (2 * j + 1) as f64 / (x * x);
            if !(f0 < 1.0 && y > 1.0e-10 * z) {
                break;
            }
            y *= f0;
            z += y;
            j += 1;
        }
        return z;
    }
    let mut m = (4.0 * x) as usize;
    let mut h = x - 0.25 * m as f64;
    if h > 0.125 {
        m += 1;
        h -= 0.25;
    }
    let xx = 0.25 * m as f64;
    let mut f0 = DAWS_VAL[m];
    let mut f1 = 1.0 - xx * f0;
    let mut z = f0 + h * f1;
    let mut y = h;
    let mut j = 2usize;
    while y.abs() > z * 1.0e-10 {
        let f2 = -((j - 1) as f64) * f0 - xx * f1;
        y *= h / j as f64;
        z += y * f2;
        f0 = f1;
        f1 = f2;
        j += 1;
    }
    z
}

/// `exp(x^2/2) * int_{-inf}^x exp(-u^2/2) du` for x < -6 (locfit `ptail`).
fn ptail(x: f64) -> f64 {
    let mut y = -1.0 / x;
    let mut z = y;
    let mut j = 0usize;
    loop {
        let f0 = -((2 * j + 1) as f64) / (x * x);
        if !(f0.abs() < 1.0 && y.abs() > 1.0e-10 * z) {
            break;
        }
        y *= f0;
        z += y;
        j += 1;
    }
    z
}

/// Complementary error function for x >= 0: Taylor series below 2, and a
/// continued fraction above.
fn erfc_pos(x: f64) -> f64 {
    if x < 2.0 {
        let mut sum = 0.0;
        let mut term = x;
        for n in 0..120 {
            sum += term / (2 * n + 1) as f64;
            term *= -x * x / (n + 1) as f64;
        }
        1.0 - 2.0 / SQRPI * sum
    } else {
        let mut t = x;
        for n in (1..=120).rev() {
            t = x + (n as f64 / 2.0) / t;
        }
        (-x * x).exp() / (SQRPI * t)
    }
}

/// Standard normal distribution function (locfit `mut_pnorm(x, 0, 1)`).
fn pnorm(x: f64) -> f64 {
    // pnorm(x) = erfc(-x / sqrt 2) / 2.
    let y = -x / SQRT2;
    if y >= 0.0 {
        0.5 * erfc_pos(y)
    } else {
        1.0 - 0.5 * erfc_pos(-y)
    }
}

/// Taylor coefficients of the weight `W(x + v) = sum_j f[j] v^j` for the
/// kernel (locfit `wtaylor`).
fn wtaylor(x: f64, ker: Kernel) -> Result<Vec<f64>, String> {
    Ok(match ker {
        Kernel::Rect => vec![1.0],
        Kernel::Epan => vec![1.0 - x * x, -2.0 * x, -1.0],
        Kernel::Bisq => {
            let v = 1.0 - x * x;
            vec![v * v, -4.0 * x * v, 4.0 - 6.0 * v, 4.0 * x, 1.0]
        }
        Kernel::Tcub => {
            if x == 1.0 {
                vec![0.0, 0.0, 0.0, -27.0, -81.0, -108.0, -81.0, -36.0, -9.0, -1.0]
            } else if x == 0.0 {
                vec![1.0, 0.0, 0.0, -3.0, 0.0, 0.0, 3.0, 0.0, 0.0, -1.0]
            } else {
                let v = 1.0 - x * x * x;
                vec![
                    v * v * v,
                    -9.0 * v * v * x * x,
                    x * v * (27.0 - 36.0 * v),
                    -27.0 + v * (108.0 - 84.0 * v),
                    -3.0 * x * x * (27.0 - 42.0 * v),
                    x * (-108.0 + 126.0 * v),
                    -81.0 + 84.0 * v,
                    -36.0 * x * x,
                    -9.0 * x,
                    -1.0,
                ]
            }
        }
        Kernel::Trwt => {
            let v = 1.0 - x * x;
            vec![
                v * v * v,
                -6.0 * x * v * v,
                v * (12.0 - 15.0 * v),
                x * (20.0 * v - 8.0),
                15.0 * v - 12.0,
                -6.0,
                -1.0,
            ]
        }
        Kernel::Tria => vec![1.0 - x, -1.0],
        Kernel::Ququ => {
            let v = 1.0 - x * x;
            vec![
                v * v * v * v,
                -8.0 * x * v * v * v,
                v * v * (24.0 - 28.0 * v),
                v * x * (56.0 * v - 32.0),
                (70.0 * v - 80.0) * v + 16.0,
                x * (32.0 - 56.0 * v),
                24.0 - 28.0 * v,
                8.0 * x,
                1.0,
            ]
        }
        Kernel::Cub6 => {
            let v = 1.0 - x * x * x;
            vec![
                v * v * v * v * v * v,
                -18.0 * x * x * v * v * v * v * v,
                x * v * v * v * v * (135.0 - 153.0 * v),
                v * v * v * (-540.0 + v * (1350.0 - 816.0 * v)),
                x * x * v * v * (1215.0 - v * (4050.0 - v * 3060.0)),
                x * v * (-1458.0 + v * (9234.0 + v * (-16254.0 + v * 8568.0))),
                729.0 - v * (10206.0 - v * (35154.0 - v * (44226.0 - v * 18564.0))),
                x * x * (4374.0 - v * (30132.0 - v * (56862.0 - v * 31824.0))),
                x * (12393.0 - v * (61479.0 - v * (92664.0 - v * 43758.0))),
                21870.0 - v * (89100.0 - v * (115830.0 - v * 48620.0)),
                x * x * (26730.0 - v * (69498.0 - v * 43758.0)),
                x * (23814.0 - v * (55458.0 - v * 31824.0)),
                15849.0 - v * (34398.0 - v * 18564.0),
                x * x * (7938.0 - 8568.0 * v),
                x * (2970.0 - 3060.0 * v),
                810.0 - 816.0 * v,
                153.0 * x * x,
                18.0 * x,
                1.0,
            ]
        }
        _ => return Err("dens_odi: kernel not ported".to_string()),
    })
}

/// locfit `explint1`: `I[j] = int_l0^l1 x^j exp(a + b x) dx`, j = 0..p-1.
fn explint1(l0: f64, l1: f64, cf: &[f64], i: &mut [f64], p: usize) {
    let mut y0 = lf_exp(cf[0] + l0 * cf[1]);
    let mut y1 = lf_exp(cf[0] + l1 * cf[1]);
    let mut k: usize = if (p as f64) < 2.0 * cf[1].abs() {
        p
    } else {
        cf[1].abs() as usize
    };
    let k1 = k;
    if k > 0 {
        i[0] = (y1 - y0) / cf[1];
        for j in 1..k {
            y1 *= l1;
            y0 *= l0;
            i[j] = (y1 - y0 - j as f64 * i[j - 1]) / cf[1];
        }
        if k == p {
            return;
        }
        y1 *= l1;
        y0 *= l0;
    }
    let mut f = 1.0;
    while k < 50 && f > 1.0e-8 {
        y1 *= l1;
        y0 *= l0;
        i[k] = y1 - y0;
        if k >= p {
            f *= cf[1].abs() / (k + 1) as f64;
        }
        k += 1;
    }
    i[k] = 0.0;
    for j in (k1..k).rev() {
        i[j] = (i[j] - cf[1] * i[j + 1]) / (j + 1) as f64;
    }
}

/// locfit `explintyl`: small c, Taylor series in c around `explint1`.
fn explintyl(l0: f64, l1: f64, cf: &[f64], i: &mut [f64], p: usize) {
    explint1(l0, l1, cf, i, p + 8);
    let c = cf[2];
    for k in 0..p {
        i[k] = (((i[k + 8] * c / 4.0 + i[k + 6]) * c / 3.0 + i[k + 4]) * c / 2.0 + i[k + 2]) * c
            + i[k];
    }
}

/// locfit `solvetrid`: tridiagonal solve on the 3-banded system `x` with
/// right-hand side `y` (`x` holds sub, diagonal and super entries in triples).
fn solvetrid(x: &mut [f64], y: &mut [f64], m: usize) {
    for i in 1..m {
        let s = x[3 * i] / x[3 * i - 2];
        x[3 * i] = 0.0;
        x[3 * i + 1] -= s * x[3 * i - 1];
        y[i] -= s * y[i - 1];
    }
    for i in (0..m.saturating_sub(1)).rev() {
        let s = x[3 * i + 2] / x[3 * i + 4];
        x[3 * i + 2] = 0.0;
        y[i] -= s * y[i + 1];
    }
    for i in 0..m {
        y[i] /= x[3 * i + 1];
    }
}

/// locfit `initi0i1`: the first two integrals of the Gaussian-type weight.
fn initi0i1(i: &mut [f64], cf: &[f64], y0: f64, y1: f64, l0: f64, l1: f64) {
    let d = -cf[1] / (2.0 * cf[2]);
    let c = (2.0 * cf[2].abs()).sqrt();
    let a0 = c * (l0 - d);
    let a1 = c * (l1 - d);
    if cf[2] < 0.0 {
        let bi = lf_exp(cf[0] + cf[1] * d + cf[2] * d * d) / c;
        if a0 > 0.0 {
            i[0] = if a0 > 6.0 {
                (y0 * ptail(-a0) - y1 * ptail(-a1)) / c
            } else {
                S2PI * (pnorm(-a0) - pnorm(-a1)) * bi
            };
        } else if a1 < -6.0 {
            i[0] = (y1 * ptail(a1) - y0 * ptail(a0)) / c;
        } else {
            i[0] = S2PI * (pnorm(a1) - pnorm(a0)) * bi;
        }
    } else {
        i[0] = (y1 * daws(a1) - y0 * daws(a0)) / c;
    }
    i[1] = (y1 - y0) / (2.0 * cf[2]) + d * i[0];
}

/// locfit `explinsid`: large b; expansion around the peak-free end.
fn explinsid(l0: f64, l1: f64, cf: &[f64], i: &mut [f64], p: usize) {
    let k0 = 2usize;
    let mut k1 = (cf[1].abs() + (2.0 * cf[2]).abs()) as usize;
    if k1 < 2 {
        k1 = 2;
    }
    if k1 > p + 20 {
        k1 = p + 20;
    }
    let k2 = p + 20;
    let mut z = vec![0.0; 3 * (k2 + 4)];
    let mut y0 = lf_exp(cf[0] + l0 * (cf[1] + l0 * cf[2]));
    let mut y1 = lf_exp(cf[0] + l1 * (cf[1] + l1 * cf[2]));
    initi0i1(i, cf, y0, y1, l0, l1);
    y1 *= l1;
    y0 *= l0;
    if k0 < k1 {
        for k in k0..k1 {
            y1 *= l1;
            y0 *= l0;
            i[k] = y1 - y0;
            z[3 * k] = k as f64;
            z[3 * k + 1] = cf[1];
            z[3 * k + 2] = 2.0 * cf[2];
        }
    }
    y1 *= l1;
    y0 *= l0;
    for k in k1..k2 {
        y1 *= l1;
        y0 *= l0;
        i[k] = y1 - y0;
    }
    i[k2] = 0.0;
    i[k2 + 1] = 0.0;
    for k in (k1..k2).rev() {
        i[k] = (i[k] - cf[1] * i[k + 1] - 2.0 * cf[2] * i[k + 2]) / (k + 1) as f64;
    }
    if k0 < k1 {
        i[k0] -= k0 as f64 * i[k0 - 1];
        i[k1 - 1] -= 2.0 * cf[2] * i[k1];
        z[3 * k0] = 0.0;
        z[3 * k1 - 1] = 0.0;
        solvetrid(&mut z[3 * k0..], &mut i[k0..], k1 - k0);
    }
}

/// locfit `explinbkr`: small b and c; backward recursion.
fn explinbkr(l0: f64, l1: f64, cf: &[f64], i: &mut [f64], p: usize) {
    let mut y0 = lf_exp(cf[0] + l0 * (cf[1] + cf[2] * l0));
    let mut y1 = lf_exp(cf[0] + l1 * (cf[1] + cf[2] * l1));
    let km = p + 10;
    for k in 0..=km {
        y1 *= l1;
        y0 *= l0;
        i[k] = y1 - y0;
    }
    i[km + 1] = 0.0;
    i[km + 2] = 0.0;
    for k in (0..=km).rev() {
        i[k] = (i[k] - cf[1] * i[k + 1] - 2.0 * cf[2] * i[k + 2]) / (k + 1) as f64;
    }
}

/// locfit `explinfbk0`: b = 0, c < 0; forward and backward recursion.
fn explinfbk0(l0: f64, l1: f64, cf: &[f64], i: &mut [f64], p: usize) {
    let mut y0 = lf_exp(cf[0] + l0 * l0 * cf[2]);
    let mut y1 = lf_exp(cf[0] + l1 * l1 * cf[2]);
    initi0i1(i, cf, y0, y1, l0, l1);
    let ml2 = (l0 * l0).max(l1 * l1);
    let mut ks: i64 = 1 + (2.0 * cf[2].abs() * ml2) as i64;
    if ks < 2 {
        ks = 2;
    }
    if ks > p as i64 - 3 {
        ks = p as i64;
    }
    let ks = ks as usize;
    for k in 2..ks {
        y1 *= l1;
        y0 *= l0;
        i[k] = (y1 - y0 - (k as f64 - 1.0) * i[k - 2]) / (2.0 * cf[2]);
    }
    if ks == p {
        return;
    }
    y1 *= l1 * l1;
    y0 *= l0 * l0;
    for k in ks..p {
        y1 *= l1;
        y0 *= l0;
        i[k] = y1 - y0;
    }
    let mut f1 = 1.0 / p as f64;
    let mut f2 = 1.0 / (p as f64 - 1.0);
    i[p - 1] *= f1;
    i[p - 2] *= f2;
    let mut k = p;
    let mut f = 1.0;
    while f > 1.0e-8 {
        y1 *= l1;
        y0 *= l0;
        if (k - p) % 2 == 0 {
            f2 *= -2.0 * cf[2] / (k as f64 + 1.0);
            i[p - 2] += (y1 - y0) * f2;
        } else {
            f1 *= -2.0 * cf[2] / (k as f64 + 1.0);
            i[p - 1] += (y1 - y0) * f1;
            f *= 2.0 * cf[2].abs() * ml2 / (k as f64 + 1.0);
        }
        k += 1;
    }
    for k in (ks..p.saturating_sub(2)).rev() {
        i[k] = (i[k] - 2.0 * cf[2] * i[k + 2]) / (k + 1) as f64;
    }
}

/// locfit `explinfbk`: b not too large; forward and backward recursion.
fn explinfbk(l0: f64, l1: f64, cf: &[f64], i: &mut [f64], p: usize) {
    let mut y0 = lf_exp(cf[0] + l0 * (cf[1] + l0 * cf[2]));
    let mut y1 = lf_exp(cf[0] + l1 * (cf[1] + l1 * cf[2]));
    initi0i1(i, cf, y0, y1, l0, l1);
    let mut ks: usize = (3.0 * cf[2].abs()) as usize;
    if ks < 3 {
        ks = 3;
    }
    if ks as f64 > 0.75 * p as f64 {
        ks = p;
    }
    for k in 2..ks {
        y1 *= l1;
        y0 *= l0;
        i[k] = (y1 - y0 - cf[1] * i[k - 1] - (k as f64 - 1.0) * i[k - 2]) / (2.0 * cf[2]);
    }
    if ks == p {
        return;
    }
    let km = p + 15;
    y1 *= l1 * l1;
    y0 *= l0 * l0;
    for k in ks..=km {
        y1 *= l1;
        y0 *= l0;
        i[k] = y1 - y0;
    }
    i[km + 1] = 0.0;
    i[km + 2] = 0.0;
    for k in (ks..=km).rev() {
        i[k] = (i[k] - cf[1] * i[k + 1] - 2.0 * cf[2] * i[k + 2]) / (k + 1) as f64;
    }
}

/// locfit `recent`: applies the weight Taylor series `wt` (centred at `x`)
/// to the integrals `I`, giving `resp[i] = int W(u) u^i exp(..)` for i <= p.
fn recent(i: &[f64], resp: &mut [f64], wt: &[f64], p: usize, x: f64) {
    let s = wt.len();
    for k in 0..=p {
        resp[k] = 0.0;
        for j in 0..s {
            resp[k] += wt[j] * i[k + j];
        }
    }
    if x == 0.0 {
        return;
    }
    for j in 0..=p {
        for k in ((j + 1)..=p).rev() {
            resp[k] += x * resp[k - 1];
        }
    }
}

/// locfit `recurint`: `resp[i] = int_l0^l2 W(u) u^i exp(a + b u + c u^2)`
/// for i = 0..=p, `cf = [a, b, c]`.
pub fn recurint(l0: f64, l2: f64, cf: &[f64], p: usize, ker: Kernel) -> Result<Vec<f64>, String> {
    let mut resp = vec![0.0; p + 1];
    let mut ib = vec![0.0; WORK];
    if cf[2] == 0.0 {
        let wt = wtaylor(0.0, ker)?;
        let s = wt.len();
        explint1(l0, l2, cf, &mut ib, p + s);
        recent(&ib, &mut resp, &wt, p, 0.0);
        return Ok(resp);
    }
    let dl = l2 - l0;
    let d0 = cf[1] + 2.0 * l0 * cf[2];
    let d2 = cf[1] + 2.0 * l2 * cf[2];
    let z0 = cf[0] + l0 * (cf[1] + l0 * cf[2]);
    let z2 = cf[0] + l2 * (cf[1] + l2 * cf[2]);
    if (cf[1] * dl).abs() < 1.0 && (cf[2] * dl * dl).abs() < 1.0 {
        let ncf = [z0, d0, cf[2]];
        let wt = wtaylor(l0, ker)?;
        let s = wt.len();
        explinbkr(0.0, dl, &ncf, &mut ib, p + s);
        recent(&ib, &mut resp, &wt, p, l0);
        return Ok(resp);
    }
    if (cf[2] * dl * dl).abs() < 0.001 {
        let ncf = [z0, d0, cf[2]];
        let wt = wtaylor(l0, ker)?;
        let s = wt.len();
        explintyl(0.0, l2 - l0, &ncf, &mut ib, p + s);
        recent(&ib, &mut resp, &wt, p, l0);
        return Ok(resp);
    }
    if d0 * d2 <= 0.0 {
        let l1 = -cf[1] / (2.0 * cf[2]);
        let z1 = cf[0] + l1 * (cf[1] + l1 * cf[2]);
        if cf[2] < 0.0 {
            let wt = wtaylor(l1, ker)?;
            let s = wt.len();
            let ncf = [z1, 0.0, cf[2]];
            explinfbk0(l0 - l1, l2 - l1, &ncf, &mut ib, p + s);
            recent(&ib, &mut resp, &wt, p, l1);
            return Ok(resp);
        }
    }
    if (d0 - 2.0 * cf[2] * dl) * (d2 + 2.0 * cf[2] * dl) < 0.0 {
        let mut l1 = -cf[1] / (2.0 * cf[2]);
        let mut z1 = cf[0] + l1 * (cf[1] + l1 * cf[2]);
        if l1 < l0 {
            l1 = l0;
            z1 = z0;
        }
        if l1 > l2 {
            l1 = l2;
            z1 = z2;
        }
        if z1 >= z0 && z1 >= z2 {
            let wt = wtaylor(l1, ker)?;
            let s = wt.len();
            let d1 = cf[1] + 2.0 * l1 * cf[2];
            let ncf = [z1, d1, cf[2]];
            explinfbk(l0 - l1, l2 - l1, &ncf, &mut ib, p + s);
            recent(&ib, &mut resp, &wt, p, l1);
            return Ok(resp);
        }
        let mut r1 = vec![0.0; p + 1];
        let mut r2 = vec![0.0; p + 1];
        if l0 < l1 {
            let wt = wtaylor(l0, ker)?;
            let s = wt.len();
            let ncf = [z0, d0, cf[2]];
            explinfbk(0.0, l1 - l0, &ncf, &mut ib, p + s);
            recent(&ib, &mut r1, &wt, p, l0);
        }
        if l1 < l2 {
            let wt = wtaylor(l2, ker)?;
            let s = wt.len();
            let ncf = [z2, d2, cf[2]];
            explinfbk(l1 - l2, 0.0, &ncf, &mut ib, p + s);
            recent(&ib, &mut r2, &wt, p, l2);
        }
        for k in 0..=p {
            resp[k] = r1[k] + r2[k];
        }
        return Ok(resp);
    }
    if z2 > z0 + 3.0 {
        let wt = wtaylor(l2, ker)?;
        let s = wt.len();
        let ncf = [z2, d2, cf[2]];
        explinsid(l0 - l2, 0.0, &ncf, &mut ib, p + s);
        recent(&ib, &mut resp, &wt, p, l2);
        return Ok(resp);
    }
    let wt = wtaylor(l0, ker)?;
    let s = wt.len();
    let ncf = [z0, d0, cf[2]];
    explinsid(0.0, l2 - l0, &ncf, &mut ib, p + s);
    recent(&ib, &mut resp, &wt, p, l0);
    Ok(resp)
}

/// locfit `onedint` for degree <= 2: `resp[j] = int_l0^l1 W(u) u^j exp(P(u))`
/// for j = 0..=2*deg, with `P(u) = cf[0] + cf[1] u + cf[2] u^2 / 2`.
pub fn onedint(cf: &[f64], l0: f64, l1: f64, deg: usize, ker: Kernel) -> Result<Vec<f64>, String> {
    let mut ncf = [0.0_f64; 3];
    for i in 0..3 {
        ncf[i] = if i > deg { 0.0 } else { cf[i] };
    }
    ncf[2] /= 2.0;
    let top = 2 * deg;
    let pos = if l1 > 0.0 {
        recurint(l0.max(0.0), l1, &ncf, top, ker)?
    } else {
        vec![0.0; top + 1]
    };
    let rr = if l0 < 0.0 {
        let mut nn = ncf;
        nn[1] = -nn[1];
        recurint((-l1).max(0.0), -l0, &nn, top, ker)?
    } else {
        vec![0.0; top + 1]
    };
    Ok((0..=top)
        .map(|i| pos[i] + if i % 2 == 0 { rr[i] } else { -rr[i] })
        .collect())
}

/// locfit `estdiv` for the log link: integral of exp(cubic Hermite) between
/// two vertices, with a knot at the midpoint.
pub fn estdiv_log(x0: f64, x1: f64, f0: f64, f1: f64, d0: f64, d1: f64) -> Result<f64, String> {
    if x0 == x1 {
        return Ok(0.0);
    }
    let dlt = (x1 - x0) / 2.0;
    let c2a = (2.0 * (f1 - f0) - dlt * (d1 + 3.0 * d0)) / (4.0 * dlt * dlt);
    let e0 = recurint(0.0, dlt, &[f0, d0, c2a], 0, Kernel::Rect)?[0];
    let c2b = (2.0 * (f0 - f1) + dlt * (d0 + 3.0 * d1)) / (4.0 * dlt * dlt);
    let e1 = recurint(0.0, dlt, &[f1, -d1, c2b], 0, Kernel::Rect)?[0];
    Ok(e0 + e1)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn brute(cf: &[f64], l0: f64, l1: f64, j: usize, deg: usize, ker: Kernel) -> f64 {
        let n = 200_000;
        let h = (l1 - l0) / n as f64;
        let mut s = 0.0;
        for k in 0..=n {
            let u = l0 + h * k as f64;
            let w = if k == 0 || k == n { 0.5 } else { 1.0 };
            let mut p = cf[0];
            let mut uf = 1.0;
            for i in 1..=deg {
                uf *= u / i as f64;
                p += cf[i] * uf;
            }
            s += w * h * crate::kernel::w_fn(u, ker) * u.powi(j as i32) * p.exp();
        }
        s
    }

    #[test]
    fn onedint_matches_quadrature() {
        let cases: [(&[f64], usize); 4] = [
            (&[0.0, 0.0, 0.0], 0),
            (&[-0.3, 0.5, 0.0], 1),
            (&[-0.3, 0.5, -1.0], 2),
            (&[0.2, -0.7, 3.0], 2),
        ];
        for (cf, deg) in cases {
            let resp = onedint(cf, -1.0, 1.0, deg, Kernel::Tcub).unwrap();
            for j in 0..=2 * deg {
                let b = brute(cf, -1.0, 1.0, j, deg, Kernel::Tcub);
                println!("cf={cf:?} deg={deg} j={j} odi={:.12e} brute={:.12e} diff={:.3e}", resp[j], b, resp[j] - b);
                assert!((resp[j] - b).abs() < 1e-6, "j={j} cf={cf:?}");
            }
        }
    }
}

