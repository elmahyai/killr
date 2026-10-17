//! Standard bivariate normal CDF.
//!
//! Ports `PBIVNORM`, `MVBVN`, `MVBVU`, and `MVPHI` from pbivnorm 0.6.0
//! (`src/pbivnorm.f`). `MVBVU` is Alan Genz's and Yihong Ge's routine from
//! MVTDSTPACK, after Drezner and Wesolowsky (1989). The R wrapper that
//! replaces infinite limits, recycles arguments, and calls `.Fortran` is not
//! ported; the Python entry point takes the same `x`, `y`, `rho` vectors that
//! the R call passes to the kernel, with `lower = (0, 0)` and `infin = (0, 0)`.

#[cfg(feature = "python")]
mod python;

/// Gauss-Legendre weights and abscissae for `NG = 1` (6 points, 3 used pairs).
const GW1: [f64; 3] = [0.1713244923791705, 0.3607615730481384, 0.4679139345726904];
const GX1: [f64; 3] = [-0.9324695142031522, -0.6612093864662647, -0.2386191860831970];

/// Gauss-Legendre rule for `NG = 2` (12 points).
const GW2: [f64; 6] = [
    0.4717533638651177e-1,
    0.1069393259953183,
    0.1600783285433464,
    0.2031674267230659,
    0.2334925365383547,
    0.2491470458134029,
];
const GX2: [f64; 6] = [
    -0.9815606342467191,
    -0.9041172563704750,
    -0.7699026741943050,
    -0.5873179542866171,
    -0.3678314989981802,
    -0.1252334085114692,
];

/// Gauss-Legendre rule for `NG = 3` (20 points).
const GW3: [f64; 10] = [
    0.1761400713915212e-1,
    0.4060142980038694e-1,
    0.6267204833410906e-1,
    0.8327674157670475e-1,
    0.1019301198172404,
    0.1181945319615184,
    0.1316886384491766,
    0.1420961093183821,
    0.1491729864726037,
    0.1527533871307259,
];
const GX3: [f64; 10] = [
    -0.9931285991850949,
    -0.9639719272779138,
    -0.9122344282513259,
    -0.8391169718222188,
    -0.7463319064601508,
    -0.6360536807265150,
    -0.5108670019508271,
    -0.3737060887154196,
    -0.2277858511416451,
    -0.7652652113349733e-1,
];

const TWOPI: f64 = 6.283185307179586;
const RTWO: f64 = 1.414213562373095048801688724209;
/// Highest index used in the `MVPHI` polynomial (`IM` in the Fortran).
const IM: usize = 24;

/// Chebyshev-type coefficients `A(0:43)` from Schonfelder (1978), used by `MVPHI`.
const A: [f64; 44] = [
    6.10143081923200417926465815756e-1,
    -4.34841272712577471828182820888e-1,
    1.76351193643605501125840298123e-1,
    -6.0710795609249414860051215825e-2,
    1.7712068995694114486147141191e-2,
    -4.321119385567293818599864968e-3,
    8.54216676887098678819832055e-4,
    -1.27155090609162742628893940e-4,
    1.1248167243671189468847072e-5,
    3.13063885421820972630152e-7,
    -2.70988068537762022009086e-7,
    3.0737622701407688440959e-8,
    2.515620384817622937314e-9,
    -1.028929921320319127590e-9,
    2.9944052119949939363e-11,
    2.6051789687266936290e-11,
    -2.634839924171969386e-12,
    -6.43404509890636443e-13,
    1.12457401801663447e-13,
    1.7281533389986098e-14,
    -4.264101694942375e-15,
    -5.45371977880191e-16,
    1.58697607761671e-16,
    2.0899837844334e-17,
    -5.900526869409e-18,
    -9.41893387554e-19,
    2.14977356470e-19,
    4.6660985008e-20,
    -7.243011862e-21,
    -2.387966824e-21,
    1.91177535e-22,
    1.20482568e-22,
    -6.72377e-25,
    -5.747997e-24,
    -4.28493e-25,
    2.44856e-25,
    4.3793e-26,
    -8.151e-27,
    -3.089e-27,
    9.3e-29,
    1.74e-28,
    1.6e-29,
    -8.0e-30,
    -2.0e-30,
];

/// Normal distribution function `Phi(z)` (`MVPHI` in the Fortran), accurate to about 1e-15.
pub fn mvphi(z: f64) -> f64 {
    let xa = z.abs() / RTWO;
    let mut p;
    if xa > 100.0 {
        p = 0.0;
    } else {
        let t = (8.0 * xa - 30.0) / (4.0 * xa + 15.0);
        let mut bm = 0.0;
        let mut b = 0.0;
        let mut bp = 0.0;
        for i in (0..=IM).rev() {
            bp = b;
            b = bm;
            bm = t * b - bp + A[i];
        }
        p = (-xa * xa).exp() * (bm - bp) / 4.0;
    }
    if z > 0.0 {
        p = 1.0 - p;
    }
    p
}

/// `MVBVU`: P(X > sh, Y > sk) for standard bivariate normal with correlation `r`.
pub fn mvbvu(sh: f64, sk: f64, r: f64) -> f64 {
    let (gw, gx, lg): (&[f64], &[f64], usize) = if r.abs() < 0.3 {
        (&GW1, &GX1, 3)
    } else if r.abs() < 0.75 {
        (&GW2, &GX2, 6)
    } else {
        (&GW3, &GX3, 10)
    };

    let h = sh;
    let mut k = sk;
    let mut hk = h * k;
    let mut bvn = 0.0;

    if r.abs() < 0.925 {
        let hs = (h * h + k * k) / 2.0;
        let asr = r.asin();
        for i in 0..lg {
            let mut sn = (asr * (gx[i] + 1.0) / 2.0).sin();
            bvn += gw[i] * ((sn * hk - hs) / (1.0 - sn * sn)).exp();
            sn = (asr * (-gx[i] + 1.0) / 2.0).sin();
            bvn += gw[i] * ((sn * hk - hs) / (1.0 - sn * sn)).exp();
        }
        bvn = bvn * asr / (2.0 * TWOPI) + mvphi(-h) * mvphi(-k);
    } else {
        if r < 0.0 {
            k = -k;
            hk = -hk;
        }
        if r.abs() < 1.0 {
            let as_ = (1.0 - r) * (1.0 + r);
            let a = as_.sqrt();
            let bs = (h - k) * (h - k);
            let c = (4.0 - hk) / 8.0;
            let d = (12.0 - hk) / 16.0;
            bvn = a
                * (-(bs / as_ + hk) / 2.0).exp()
                * (1.0 - c * (bs - as_) * (1.0 - d * bs / 5.0) / 3.0 + c * d * as_ * as_ / 5.0);
            if hk > -160.0 {
                let b = bs.sqrt();
                bvn -= (-hk / 2.0).exp()
                    * TWOPI.sqrt()
                    * mvphi(-b / a)
                    * b
                    * (1.0 - c * bs * (1.0 - d * bs / 5.0) / 3.0);
            }
            let a = a / 2.0;
            for i in 0..lg {
                let t = a * (gx[i] + 1.0);
                let mut xs = t * t;
                let mut rs = (1.0 - xs).sqrt();
                bvn += a
                    * gw[i]
                    * ((-bs / (2.0 * xs) - hk / (1.0 + rs)).exp() / rs
                        - (-(bs / xs + hk) / 2.0).exp() * (1.0 + c * xs * (1.0 + d * xs)));
                let t = -gx[i] + 1.0;
                xs = as_ * (t * t) / 4.0;
                rs = (1.0 - xs).sqrt();
                bvn += a
                    * gw[i]
                    * (-(bs / xs + hk) / 2.0).exp()
                    * ((-hk * (1.0 - rs) / (2.0 * (1.0 + rs))).exp() / rs
                        - (1.0 + c * xs * (1.0 + d * xs)));
            }
            bvn = -bvn / TWOPI;
        }
        if r > 0.0 {
            bvn += mvphi(-h.max(k));
        }
        if r < 0.0 {
            bvn = -bvn + (mvphi(-h) - mvphi(-k)).max(0.0);
        }
    }
    bvn
}

/// `MVBVN`: bivariate normal probability over the rectangle described by `lower`,
/// `upper`, and `infin`, with flags 0 = (-inf, upper], 1 = [lower, inf), 2 = [lower, upper].
pub fn mvbvn(lower: [f64; 2], upper: [f64; 2], infin: [i32; 2], correl: f64) -> f64 {
    match (infin[0], infin[1]) {
        (2, 2) => {
            mvbvu(lower[0], lower[1], correl) - mvbvu(upper[0], lower[1], correl)
                - mvbvu(lower[0], upper[1], correl)
                + mvbvu(upper[0], upper[1], correl)
        }
        (2, 1) => mvbvu(lower[0], lower[1], correl) - mvbvu(upper[0], lower[1], correl),
        (1, 2) => mvbvu(lower[0], lower[1], correl) - mvbvu(lower[0], upper[1], correl),
        (2, 0) => mvbvu(-upper[0], -upper[1], correl) - mvbvu(-lower[0], -upper[1], correl),
        (0, 2) => mvbvu(-upper[0], -upper[1], correl) - mvbvu(-upper[0], -lower[1], correl),
        (1, 0) => mvbvu(lower[0], -upper[1], -correl),
        (0, 1) => mvbvu(-upper[0], lower[1], -correl),
        (1, 1) => mvbvu(lower[0], lower[1], correl),
        (0, 0) => mvbvu(-upper[0], -upper[1], correl),
        _ => 1.0,
    }
}

/// `PBIVNORM`: vectorized `MVBVN`, one probability per element of `uppera`,
/// `upperb`, and `correl`. The Fortran `LENGTH` is the common length.
pub fn pbivnorm_kernel(
    lower: [f64; 2],
    uppera: &[f64],
    upperb: &[f64],
    infin: [i32; 2],
    correl: &[f64],
) -> Vec<f64> {
    let length = uppera.len().min(upperb.len()).min(correl.len());
    (0..length)
        .map(|i| mvbvn(lower, [uppera[i], upperb[i]], infin, correl[i]))
        .collect()
}

/// Standard bivariate normal CDF `P(X <= x, Y <= y)` with correlation `rho`,
/// computed the way the R call `.Fortran("PBIVNORM", ...)` does for `lower = (0, 0)`
/// and `infin = (0, 0)`.
pub fn pbivnorm(x: &[f64], y: &[f64], rho: &[f64]) -> Vec<f64> {
    pbivnorm_kernel([0.0, 0.0], x, y, [0, 0], rho)
}

#[cfg(test)]
mod tests {
    use super::{mvphi, pbivnorm};

    #[test]
    fn phi_at_zero_is_half() {
        assert!((mvphi(0.0) - 0.5).abs() < 1e-15);
    }

    #[test]
    fn independent_case_is_product() {
        let p = pbivnorm(&[0.0, 1.0], &[0.0, -0.5], &[0.0, 0.0]);
        assert!((p[0] - 0.25).abs() < 1e-15);
        assert!((p[1] - mvphi(1.0) * mvphi(-0.5)).abs() < 1e-14);
    }

    #[test]
    fn orthant_probability_matches_arcsine_formula() {
        // P(X <= 0, Y <= 0) = 1/4 + asin(rho) / (2 pi)
        let rho = 0.5;
        let p = pbivnorm(&[0.0], &[0.0], &[rho]);
        let expected = 0.25 + rho.asin() / (2.0 * std::f64::consts::PI);
        assert!((p[0] - expected).abs() < 1e-12);
    }
}
