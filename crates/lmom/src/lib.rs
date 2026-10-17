//! L-moment kernels ported from lmom 3.3: `src/samlm.f` and `src/lmoments.f`.
//!
//! Each routine returns the Fortran `IFAIL` code next to its output. Output
//! arrays are zero-filled where the Fortran leaves them untouched on an error
//! path (R allocates them as zeros).
//!
//! Not ported: `CDFWAK` (a distribution function, not an L-moment routine),
//! and `lmomc.c` with QUADPACK (the bridge that evaluates R closures).

use std::cmp::Ordering;

#[cfg(feature = "python")]
use pyo3::prelude::*;

const PI: f64 = 3.141592653589793238e0;

const ZMOM_GUMBEL: [f64; 20] = [
    0.577215664901532861e0,
    0.693147180559945309e0,
    0.169925001442312363e0,
    0.150374992788438185e0,
    0.558683500577583138e-1,
    0.581100239999710876e-1,
    0.276242584297309125e-1,
    0.305563766579053126e-1,
    0.164650282258328802e-1,
    0.187846624298170912e-1,
    0.109328215063027148e-1,
    0.126973126676329530e-1,
    0.778982818057231804e-2,
    0.914836179621999726e-2,
    0.583332389328363588e-2,
    0.690104287590348154e-2,
    0.453267970180679549e-2,
    0.538916811326595459e-2,
    0.362407767772368790e-2,
    0.432387608605538096e-2,
];

const ZMOM_NORMAL: [f64; 20] = [
    0.0,
    0.564189583547756287e0,
    0.0,
    0.122601719540890947e0,
    0.0,
    0.436611538950024944e-1,
    0.0,
    0.218431360332508776e-1,
    0.0,
    0.129635015801507746e-1,
    0.0,
    0.852962124191705402e-2,
    0.0,
    0.601389015179323333e-2,
    0.0,
    0.44555825864765015e-2,
    0.0,
    0.342643243578076985e-2,
    0.0,
    0.271267963048139365e-2,
];

/// Coefficients Z(k, m) of the generalized logistic ratios, `GLO_Z[m][k-1]`.
const GLO_Z: [&[f64]; 21] = [
    &[],
    &[],
    &[],
    &[1.0],
    &[0.166666666666666667e0, 0.833333333333333333e0],
    &[0.416666666666666667e0, 0.583333333333333333e0],
    &[0.666666666666666667e-1, 0.583333333333333333e0, 0.35e0],
    &[0.233333333333333333e0, 0.583333333333333333e0, 0.183333333333333333e0],
    &[
        0.357142857142857143e-1,
        0.420833333333333333e0,
        0.458333333333333333e0,
        0.851190476190476190e-1,
    ],
    &[
        0.150992063492063492e0,
        0.515625e0,
        0.297916666666666667e0,
        0.354662698412698413e-1,
    ],
    &[
        0.222222222222222222e-1,
        0.318893298059964727e0,
        0.479976851851851852e0,
        0.165509259259259259e0,
        0.133983686067019400e-1,
    ],
    &[
        0.106507936507936508e0,
        0.447663139329805996e0,
        0.360810185185185185e0,
        0.803902116402116402e-1,
        0.462852733686067019e-2,
    ],
    &[
        0.151515151515151515e-1,
        0.251316137566137566e0,
        0.469695216049382716e0,
        0.227650462962962963e0,
        0.347139550264550265e-1,
        0.147271324354657688e-2,
    ],
    &[
        0.795695045695045695e-1,
        0.389765946502057613e0,
        0.392917309670781893e0,
        0.123813106261022928e0,
        0.134998713991769547e-1,
        0.434261597456041900e-3,
    ],
    &[
        0.109890109890109890e-1,
        0.204132996632996633e0,
        0.447736625514403292e0,
        0.273053442827748383e0,
        0.591917438271604938e-1,
        0.477687757201646091e-2,
        0.119302636637477750e-3,
    ],
    &[
        0.619345205059490774e-1,
        0.342031759392870504e0,
        0.407013705173427396e0,
        0.162189192806752331e0,
        0.252492100235155791e-1,
        0.155093427662872107e-2,
        0.306778208563922850e-4,
    ],
    &[
        0.833333333333333333e-2,
        0.169768364902293474e0,
        0.422191282868366202e0,
        0.305427172894620811e0,
        0.840827939972285210e-1,
        0.972435791446208113e-2,
        0.465280282988616322e-3,
        0.741380670696146887e-5,
    ],
    &[
        0.497166028416028416e-1,
        0.302765838598713328e0,
        0.410473300089185506e0,
        0.194839026503251764e0,
        0.386598063704648526e-1,
        0.341399407642897226e-2,
        0.129741617371825705e-3,
        0.168991182291033482e-5,
    ],
    &[
        0.653594771241830065e-2,
        0.143874847595085690e0,
        0.396432853710259464e0,
        0.328084180720899471e0,
        0.107971393165194318e0,
        0.159653369932077769e-1,
        0.110127737569143819e-2,
        0.337982364582066963e-4,
        0.364490785333601627e-6,
    ],
    &[
        0.408784570549276431e-1,
        0.270244290725441519e0,
        0.407599524514551521e0,
        0.222111426489320008e0,
        0.528463884629533398e-1,
        0.598298239272872761e-2,
        0.328593965565898436e-3,
        0.826179113422830354e-5,
        0.746033771150646605e-7,
    ],
    &[
        0.526315789473684211e-2,
        0.123817655775305491e0,
        0.371859291444794917e0,
        0.343568747670189607e0,
        0.130198662812524058e0,
        0.231474364898477023e-1,
        0.205192519479869981e-2,
        0.912058258107571930e-4,
        0.190238611643414884e-5,
        0.145280260697757497e-7,
    ],
];

// ---------------------------------------------------------------------------
// Special functions (digamd.f, xlgama.f, xerf.f)
// ---------------------------------------------------------------------------

/// Digamma function, port of `DIGAMD`.
pub fn digamd(x: f64) -> f64 {
    const SMALL: f64 = 1e-9;
    const CRIT: f64 = 13.0;
    const VBIG: f64 = 1e300;
    const C1: f64 = 0.833333333333333333e-1;
    const C2: f64 = -0.833333333333333333e-2;
    const C3: f64 = 0.396825396825396825e-2;
    const C4: f64 = -0.416666666666666666e-2;
    const C5: f64 = 0.757575757575757575e-2;
    const C6: f64 = -0.210927960927960928e-1;
    const C7: f64 = 0.833333333333333333e-1;
    const EU: f64 = -0.577215664901532861e0;

    if x <= 0.0 {
        return VBIG;
    }
    if x <= SMALL {
        return EU - 1.0 / x;
    }
    let mut digam = 0.0;
    let mut y = x;
    while y < CRIT {
        digam -= 1.0 / y;
        y += 1.0;
    }
    digam += y.ln() - 0.5 / y;
    let y2 = 1.0 / (y * y);
    let sum = ((((((C7 * y2 + C6) * y2 + C5) * y2 + C4) * y2 + C3) * y2 + C2) * y2 + C1) * y2;
    digam - sum
}

/// Log-gamma function, port of `XLGAMA`.
pub fn xlgama(x: f64) -> f64 {
    const SMALL: f64 = 1e-5;
    const CRIT: f64 = 13.0;
    const BIG: f64 = 1e9;
    const VBIG: f64 = 1e300;
    const C0: f64 = 0.918938533204672742e0;
    const C1: f64 = 0.833333333333333333e-1;
    const C2: f64 = -0.277777777777777778e-2;
    const C3: f64 = 0.793650793650793651e-3;
    const C4: f64 = -0.595238095238095238e-3;
    const C5: f64 = 0.841750841750841751e-3;
    const C6: f64 = -0.191752691752691753e-2;
    const C7: f64 = 0.641025641025641026e-2;
    const S1: f64 = -0.577215664901532861e0;
    const S2: f64 = 0.822467033424113218e0;

    if x <= 0.0 {
        return VBIG;
    }
    if x <= SMALL {
        return -x.ln() + S1 * x;
    }
    if (x - 2.0).abs() <= SMALL {
        let xx = x - 2.0;
        return (x - 1.0).ln() + xx * (S1 + xx * S2);
    }
    if (x - 1.0).abs() <= SMALL {
        let xx = x - 1.0;
        return xx * (S1 + xx * S2);
    }
    let mut sum1 = 0.0;
    let mut y = x;
    if y < CRIT {
        let mut z = 1.0;
        loop {
            z *= y;
            y += 1.0;
            if y >= CRIT {
                break;
            }
        }
        sum1 -= z.ln();
    }
    sum1 += (y - 0.5) * y.ln() - y + C0;
    let mut sum2 = 0.0;
    if y < BIG {
        let z = 1.0 / (y * y);
        sum2 = ((((((C7 * z + C6) * z + C5) * z + C4) * z + C3) * z + C2) * z + C1) / y;
    }
    sum1 + sum2
}

/// Error function, port of `XERF` (Hart et al. 1968, algorithm 5666).
pub fn xerf(x: f64) -> f64 {
    const P0: f64 = 0.220206867912376100e3;
    const P1: f64 = 0.221213596169931100e3;
    const P2: f64 = 0.112079291497870900e3;
    const P3: f64 = 0.339128660783830000e2;
    const P4: f64 = 0.637396220353165000e1;
    const P5: f64 = 0.700383064443688100e0;
    const P6: f64 = 0.352624965998910900e-1;
    const Q0: f64 = 0.440413735824752200e3;
    const Q1: f64 = 0.793826512519948400e3;
    const Q2: f64 = 0.637333633378831100e3;
    const Q3: f64 = 0.296564248779673700e3;
    const Q4: f64 = 0.867807322029460800e2;
    const Q5: f64 = 0.160641775792069500e2;
    const Q6: f64 = 0.175566716318264200e1;
    const Q7: f64 = 0.883883476483184400e-1;
    const C1: f64 = 1.414213562373095e0;
    const C2: f64 = 0.797884560802865400e0;
    const BIG: f64 = 6.25;
    const CRIT: f64 = 5.0;
    const P65: f64 = 0.65;

    if x == 0.0 {
        return 0.0;
    }
    let xx = x.abs();
    if xx > BIG {
        return if x < 0.0 { -1.0 } else { 1.0 };
    }
    let expntl = (-x * x).exp();
    let zz = (x * C1).abs();
    if xx > CRIT {
        let mut d = zz + P65;
        d = zz + 4.0 / d;
        d = zz + 3.0 / d;
        d = zz + 2.0 / d;
        d = zz + 1.0 / d;
        let r = expntl * C2 / d;
        if x < 0.0 {
            r - 1.0
        } else {
            1.0 - r
        }
    } else {
        let mut num = P6;
        for c in [P5, P4, P3, P2, P1, P0] {
            num = num * zz + c;
        }
        let mut den = Q7;
        for c in [Q6, Q5, Q4, Q3, Q2, Q1, Q0] {
            den = den * zz + c;
        }
        let r = expntl * num / den;
        if x < 0.0 {
            2.0 * r - 1.0
        } else {
            1.0 - 2.0 * r
        }
    }
}

// ---------------------------------------------------------------------------
// Sample L-moments (samlm.f)
// ---------------------------------------------------------------------------

/// Sample L-moments, port of `SAMLM`. `isort` sorts a copy of the data first.
/// `iratio` returns L-moment ratios (tau_r, r >= 3) instead of L-moments.
pub fn samlm(x_in: &[f64], nmom: usize, isort: bool, iratio: bool) -> Vec<f64> {
    let mut xmom = vec![0.0; nmom];
    if nmom == 0 {
        return xmom;
    }
    let mut x = x_in.to_vec();
    if isort {
        x.sort_by(|a, b| a.partial_cmp(b).unwrap_or(Ordering::Equal));
    }
    let n = x.len();
    let dn = n as f64;

    if nmom <= 2 {
        let mut sum1 = 0.0;
        let mut sum2 = 0.0;
        let mut temp = -dn + 1.0;
        for &xi in &x {
            sum1 += xi;
            sum2 += xi * temp;
            temp += 2.0;
        }
        xmom[0] = sum1 / dn;
        if nmom == 1 {
            return xmom;
        }
        xmom[1] = sum2 / (dn * (dn - 1.0));
        if isort && x.first().map_or(false, |&v| v >= 0.0) && xmom[1] > xmom[0] {
            xmom[1] = xmom[0];
        }
        return xmom;
    }

    let mut coef1 = vec![0.0; nmom + 1];
    let mut coef2 = vec![0.0; nmom + 1];
    for j in 3..=nmom {
        let ji = j as i64;
        let ni = n as i64;
        let temp = 1.0 / (((ji - 1) * (ni - ji + 1)) as f64);
        coef1[j] = ((2 * ji - 3) as f64) * temp;
        coef2[j] = (((ji - 2) * (ni + ji - 2)) as f64) * temp;
    }
    let mut temp = -dn - 1.0;
    let konst = 1.0 / (dn - 1.0);
    let nhalf = n / 2;
    for i in 1..=nhalf {
        temp += 2.0;
        let xi = x[i - 1];
        let xii = x[n - i];
        let termp = xi + xii;
        let termn = xi - xii;
        xmom[0] += termp;
        let mut s1 = 1.0;
        let mut s = temp * konst;
        xmom[1] += s * termn;
        let mut j = 3;
        while j <= nmom {
            let s2 = s1;
            s1 = s;
            s = coef1[j] * temp * s1 - coef2[j] * s2;
            xmom[j - 1] += s * termp;
            if j != nmom {
                let jj = j + 1;
                let s2 = s1;
                s1 = s;
                s = coef1[jj] * temp * s1 - coef2[jj] * s2;
                xmom[jj - 1] += s * termn;
            }
            j += 2;
        }
    }
    if 2 * nhalf != n {
        let term = x[nhalf];
        let mut s = 1.0;
        xmom[0] += term;
        let mut j = 3;
        while j <= nmom {
            s = -coef2[j] * s;
            xmom[j - 1] += s * term;
            j += 2;
        }
    }

    let rn = 1.0 / dn;
    let amult = if iratio {
        if xmom[1] == 0.0 {
            0.0
        } else {
            1.0 / xmom[1]
        }
    } else {
        rn
    };
    for xm in xmom.iter_mut().skip(2) {
        *xm *= amult;
    }
    xmom[0] *= rn;
    xmom[1] *= rn;
    xmom
}

// ---------------------------------------------------------------------------
// L-moments of distributions from parameters (lmr*.f)
// Each returns (xmom, ifail). `para` must hold the distribution's parameters.
// ---------------------------------------------------------------------------

/// Exponential, port of `LMREXP`.
pub fn lmr_exp(para: &[f64], nmom: usize) -> (Vec<f64>, i32) {
    let mut xmom = vec![0.0; nmom];
    if nmom == 0 {
        return (xmom, 0);
    }
    let a = para[1];
    if a <= 0.0 {
        return (xmom, 7000);
    }
    if nmom > 20 {
        return (xmom, 7010);
    }
    xmom[0] = para[0] + a;
    if nmom == 1 {
        return (xmom, 0);
    }
    xmom[1] = 0.5 * a;
    if nmom == 2 {
        return (xmom, 0);
    }
    for j in 3..=nmom {
        xmom[j - 1] = 2.0 / ((j * (j - 1)) as f64);
    }
    (xmom, 0)
}

/// Gamma, port of `LMRGAM`.
pub fn lmr_gam(para: &[f64], nmom: usize) -> (Vec<f64>, i32) {
    const CONST: f64 = 0.564189583547756287e0;
    const A0: f64 = 0.32573501e0;
    const A1: f64 = 0.16869150e0;
    const A2: f64 = 0.78327243e-1;
    const A3: f64 = -0.29120539e-2;
    const B1: f64 = 0.46697102e0;
    const B2: f64 = 0.24255406e0;
    const C0: f64 = 0.12260172e0;
    const C1: f64 = 0.53730130e-1;
    const C2: f64 = 0.43384378e-1;
    const C3: f64 = 0.11101277e-1;
    const D1: f64 = 0.18324466e0;
    const D2: f64 = 0.20166036e0;
    const E1: f64 = 0.23807576e1;
    const E2: f64 = 0.15931792e1;
    const E3: f64 = 0.11618371e0;
    const F1: f64 = 0.51533299e1;
    const F2: f64 = 0.71425260e1;
    const F3: f64 = 0.19745056e1;
    const G1: f64 = 0.21235833e1;
    const G2: f64 = 0.41670213e1;
    const G3: f64 = 0.31925299e1;
    const H1: f64 = 0.90551443e1;
    const H2: f64 = 0.26649995e2;
    const H3: f64 = 0.26193668e2;

    let mut xmom = vec![0.0; nmom];
    if nmom == 0 {
        return (xmom, 0);
    }
    let alpha = para[0];
    let beta = para[1];
    if alpha <= 0.0 || beta <= 0.0 {
        return (xmom, 7000);
    }
    if nmom > 4 {
        return (xmom, 7010);
    }
    xmom[0] = alpha * beta;
    if nmom == 1 {
        return (xmom, 0);
    }
    xmom[1] = beta * CONST * (xlgama(alpha + 0.5) - xlgama(alpha)).exp();
    if nmom == 2 {
        return (xmom, 0);
    }
    if alpha < 1.0 {
        let z = alpha;
        xmom[2] = (((E3 * z + E2) * z + E1) * z + 1.0) / (((F3 * z + F2) * z + F1) * z + 1.0);
        if nmom == 3 {
            return (xmom, 0);
        }
        xmom[3] = (((G3 * z + G2) * z + G1) * z + 1.0) / (((H3 * z + H2) * z + H1) * z + 1.0);
    } else {
        let z = 1.0 / alpha;
        xmom[2] = z.sqrt() * (((A3 * z + A2) * z + A1) * z + A0) / ((B2 * z + B1) * z + 1.0);
        if nmom == 3 {
            return (xmom, 0);
        }
        xmom[3] = (((C3 * z + C2) * z + C1) * z + C0) / ((D2 * z + D1) * z + 1.0);
    }
    (xmom, 0)
}

/// Generalized extreme value, port of `LMRGEV`.
pub fn lmr_gev(para: &[f64], nmom: usize) -> (Vec<f64>, i32) {
    let mut xmom = vec![0.0; nmom];
    if nmom == 0 {
        return (xmom, 0);
    }
    let (u, a, g) = (para[0], para[1], para[2]);
    if a <= 0.0 || g <= -1.0 {
        return (xmom, 7000);
    }
    if nmom > 20 {
        return (xmom, 7010);
    }
    if g.abs() <= 1e-6 {
        xmom[0] = u + a * ZMOM_GUMBEL[0];
        if nmom == 1 {
            return (xmom, 0);
        }
        xmom[1] = a * ZMOM_GUMBEL[1];
        if nmom == 2 {
            return (xmom, 0);
        }
        for i in 3..=nmom {
            xmom[i - 1] = ZMOM_GUMBEL[i - 1];
        }
        return (xmom, 0);
    }
    let gam = xlgama(1.0 + g).exp();
    xmom[0] = u + a * (1.0 - gam) / g;
    if nmom == 1 {
        return (xmom, 0);
    }
    let xx2 = 1.0 - 2f64.powf(-g);
    xmom[1] = a * xx2 * gam / g;
    if nmom == 2 {
        return (xmom, 0);
    }
    let mut z0 = 1.0;
    for j in 3..=nmom {
        let dj = j as f64;
        let beta = (1.0 - dj.powf(-g)) / xx2;
        z0 = z0 * (4.0 * dj - 6.0) / dj;
        let mut z = z0 * 3.0 * (dj - 1.0) / (dj + 1.0);
        let mut sum = z0 * beta - z;
        for i in 2..=(j - 2) {
            let di = i as f64;
            z = z * (2.0 * di + 1.0) * (dj - di) / ((2.0 * di - 1.0) * (dj + di));
            sum -= z * xmom[i];
        }
        xmom[j - 1] = sum;
    }
    (xmom, 0)
}

/// Generalized logistic, port of `LMRGLO`.
pub fn lmr_glo(para: &[f64], nmom: usize) -> (Vec<f64>, i32) {
    const SMALL: f64 = 1e-4;
    const C1: f64 = 0.164493406684822644e1;
    const C2: f64 = 0.189406565899449184e1;

    let mut xmom = vec![0.0; nmom];
    if nmom == 0 {
        return (xmom, 0);
    }
    let (u, a, g) = (para[0], para[1], para[2]);
    if a <= 0.0 || g.abs() >= 1.0 {
        return (xmom, 7000);
    }
    if nmom > 20 {
        return (xmom, 7010);
    }
    let gg = g * g;
    let mut alam1 = -g * (C1 + gg * C2);
    let mut alam2 = 1.0 + gg * (C1 + gg * C2);
    if g.abs() > SMALL {
        alam2 = g * PI / (g * PI).sin();
        alam1 = (1.0 - alam2) / g;
    }
    xmom[0] = u + a * alam1;
    if nmom == 1 {
        return (xmom, 0);
    }
    xmom[1] = a * alam2;
    if nmom == 2 {
        return (xmom, 0);
    }
    for m in 3..=nmom {
        let kmax = m / 2;
        let zm = GLO_Z[m];
        let mut sum = zm[kmax - 1];
        for k in (1..kmax).rev() {
            sum = sum * gg + zm[k - 1];
        }
        if m != (m / 2) * 2 {
            sum = -g * sum;
        }
        xmom[m - 1] = sum;
    }
    (xmom, 0)
}

/// Generalized normal, port of `LMRGNO`. Uses trapezium-rule integration
/// with doubling, as in the Fortran.
pub fn lmr_gno(para: &[f64], nmom: usize) -> (Vec<f64>, i32) {
    const EPS: f64 = 1e-8;
    const RANGE: f64 = 5.0;
    const MAXIT: usize = 10;
    const RRT2: f64 = 0.707106781186547524e0;
    const RRTPI: f64 = 0.564189583547756287e0;

    let mut xmom = vec![0.0; nmom];
    if nmom == 0 {
        return (xmom, 0);
    }
    let (u, a, g) = (para[0], para[1], para[2]);
    if a <= 0.0 {
        return (xmom, 7000);
    }
    if nmom > 20 {
        return (xmom, 7010);
    }
    if g.abs() <= EPS {
        xmom[0] = u;
        if nmom == 1 {
            return (xmom, 0);
        }
        xmom[1] = a * ZMOM_NORMAL[1];
        if nmom == 2 {
            return (xmom, 0);
        }
        for i in 3..=nmom {
            xmom[i - 1] = ZMOM_NORMAL[i - 1];
        }
        return (xmom, 0);
    }
    let egg = (0.5 * g * g).exp();
    let alam1 = (1.0 - egg) / g;
    xmom[0] = u + a * alam1;
    if nmom == 1 {
        return (xmom, 0);
    }
    let alam2 = egg * xerf(0.5 * g) / g;
    xmom[1] = a * alam2;
    if nmom == 2 {
        return (xmom, 0);
    }

    let cc = -g * RRT2;
    let xmin = cc - RANGE;
    let xmax = cc + RANGE;
    let mut sum = [0.0f64; 21];
    let mut est = [0.0f64; 21];
    let mut estx = [0.0f64; 21];
    let mut n: usize = 16;
    let mut xinc = (xmax - xmin) / (n as f64);

    // Accumulate the integrand at the given abscissa indices.
    let accumulate = |i: usize, xinc: f64, sum: &mut [f64; 21]| {
        let x = xmin + (i as f64) * xinc;
        let e = (-((x - cc) * (x - cc))).exp();
        let d = xerf(x);
        let mut p1 = 1.0;
        let mut p = d;
        for m in 3..=nmom {
            let c1 = (m + m - 3) as f64;
            let c2 = (m - 2) as f64;
            let c3 = (m - 1) as f64;
            let p2 = p1;
            p1 = p;
            p = (c1 * d * p1 - c2 * p2) / c3;
            sum[m] += e * p;
        }
    };

    for i in 1..=(n - 1) {
        accumulate(i, xinc, &mut sum);
    }
    for m in 3..=nmom {
        est[m] = sum[m] * xinc;
    }

    let mut converged = false;
    let mut notcgd = 0usize;
    for _it in 1..=MAXIT {
        for m in 3..=nmom {
            estx[m] = est[m];
        }
        n *= 2;
        xinc = (xmax - xmin) / (n as f64);
        let mut i = 1;
        while i <= n - 1 {
            accumulate(i, xinc, &mut sum);
            i += 2;
        }
        notcgd = 0;
        for m in (3..=nmom).rev() {
            est[m] = sum[m] * xinc;
            if (est[m] - estx[m]).abs() > EPS * est[m].abs() {
                notcgd = m;
            }
        }
        if notcgd == 0 {
            converged = true;
            break;
        }
    }
    let ifail = if converged { 0 } else { 7100 + (notcgd as i32 - 1) };

    let konst = -(cc * cc).exp() * RRTPI / (alam2 * g);
    for m in 3..=nmom {
        xmom[m - 1] = konst * est[m];
    }
    (xmom, ifail)
}

/// Generalized Pareto, port of `LMRGPA`.
pub fn lmr_gpa(para: &[f64], nmom: usize) -> (Vec<f64>, i32) {
    let mut xmom = vec![0.0; nmom];
    if nmom == 0 {
        return (xmom, 0);
    }
    let (u, a, g) = (para[0], para[1], para[2]);
    if a <= 0.0 || g < -1.0 {
        return (xmom, 7000);
    }
    if nmom > 20 {
        return (xmom, 7010);
    }
    let mut y = 1.0 / (1.0 + g);
    xmom[0] = u + a * y;
    if nmom == 1 {
        return (xmom, 0);
    }
    y /= 2.0 + g;
    xmom[1] = a * y;
    if nmom == 2 {
        return (xmom, 0);
    }
    y = 1.0;
    for m in 3..=nmom {
        let am = (m as f64) - 2.0;
        y = y * (am - g) / ((m as f64) + g);
        xmom[m - 1] = y;
    }
    (xmom, 0)
}

/// Gumbel, port of `LMRGUM`.
pub fn lmr_gum(para: &[f64], nmom: usize) -> (Vec<f64>, i32) {
    let mut xmom = vec![0.0; nmom];
    if nmom == 0 {
        return (xmom, 0);
    }
    let a = para[1];
    if a <= 0.0 {
        return (xmom, 7000);
    }
    if nmom > 20 {
        return (xmom, 7010);
    }
    xmom[0] = para[0] + a * ZMOM_GUMBEL[0];
    if nmom == 1 {
        return (xmom, 0);
    }
    xmom[1] = a * ZMOM_GUMBEL[1];
    if nmom == 2 {
        return (xmom, 0);
    }
    for j in 3..=nmom {
        xmom[j - 1] = ZMOM_GUMBEL[j - 1];
    }
    (xmom, 0)
}

/// Kappa, port of `LMRKAP`.
pub fn lmr_kap(para: &[f64], nmom: usize) -> (Vec<f64>, i32) {
    const EU: f64 = 0.577215664901532861e0;
    const SMALL: f64 = 1e-8;
    const OFL: f64 = 170.0;

    let mut xmom = vec![0.0; nmom];
    if nmom == 0 {
        return (xmom, 0);
    }
    let (u, a, g, h) = (para[0], para[1], para[2], para[3]);
    if a <= 0.0 || g <= -1.0 {
        return (xmom, 7000);
    }
    if h < 0.0 && g * h <= -1.0 {
        return (xmom, 7000);
    }
    if nmom > 20 {
        return (xmom, 7010);
    }
    let mut beta = [0.0f64; 21];
    let xlgam = xlgama(1.0 + g);
    if g == 0.0 {
        if h < 0.0 {
            for ir in 1..=nmom {
                let r = ir as f64;
                beta[ir] = EU + (-h).ln() + digamd(-r / h);
            }
        } else if h.abs() < SMALL {
            for ir in 1..=nmom {
                beta[ir] = EU + (ir as f64).ln();
            }
        } else {
            for ir in 1..=nmom {
                let r = ir as f64;
                beta[ir] = EU + h.ln() + digamd(1.0 + r / h);
            }
        }
    } else if h < 0.0 {
        for ir in 1..=nmom {
            let r = ir as f64;
            let arg = xlgam + xlgama(-r / h - g) - xlgama(-r / h) - g * (-h).ln();
            if arg.abs() > OFL {
                return (xmom, 7020);
            }
            beta[ir] = arg.exp();
        }
    } else if h.abs() < SMALL {
        for ir in 1..=nmom {
            let r = ir as f64;
            beta[ir] = (xlgam - g * r.ln()).exp() * (1.0 - 0.5 * h * g * (1.0 + g) / r);
        }
    } else {
        for ir in 1..=nmom {
            let r = ir as f64;
            let arg = xlgam + xlgama(1.0 + r / h) - xlgama(1.0 + g + r / h) - g * h.ln();
            if arg.abs() > OFL {
                return (xmom, 7020);
            }
            beta[ir] = arg.exp();
        }
    }

    xmom[0] = if g == 0.0 {
        u + a * beta[1]
    } else {
        u + a * (1.0 - beta[1]) / g
    };
    if nmom == 1 {
        return (xmom, 0);
    }
    let alam2 = beta[2] - beta[1];
    xmom[1] = if g == 0.0 {
        a * alam2
    } else {
        a * alam2 / (-g)
    };
    if nmom == 2 {
        return (xmom, 0);
    }
    let mut z0 = 1.0;
    for j in 3..=nmom {
        let dj = j as f64;
        z0 = z0 * (4.0 * dj - 6.0) / dj;
        let mut z = z0 * 3.0 * (dj - 1.0) / (dj + 1.0);
        let mut sum = z0 * (beta[j] - beta[1]) / alam2 - z;
        for i in 2..=(j - 2) {
            let di = i as f64;
            z = z * (2.0 * di + 1.0) * (dj - di) / ((2.0 * di - 1.0) * (dj + di));
            sum -= z * xmom[i];
        }
        xmom[j - 1] = sum;
    }
    (xmom, 0)
}

/// Normal, port of `LMRNOR`.
pub fn lmr_nor(para: &[f64], nmom: usize) -> (Vec<f64>, i32) {
    let mut xmom = vec![0.0; nmom];
    if nmom == 0 {
        return (xmom, 0);
    }
    if para[1] <= 0.0 {
        return (xmom, 7000);
    }
    if nmom > 20 {
        return (xmom, 7010);
    }
    xmom[0] = para[0];
    if nmom == 1 {
        return (xmom, 0);
    }
    xmom[1] = para[1] * ZMOM_NORMAL[1];
    if nmom == 2 {
        return (xmom, 0);
    }
    for m in 3..=nmom {
        xmom[m - 1] = ZMOM_NORMAL[m - 1];
    }
    (xmom, 0)
}

/// Pearson type 3, port of `LMRPE3`.
pub fn lmr_pe3(para: &[f64], nmom: usize) -> (Vec<f64>, i32) {
    const SMALL: f64 = 1e-6;
    const CONST: f64 = 0.564189583547756287e0;
    const A0: f64 = 0.32573501e0;
    const A1: f64 = 0.16869150e0;
    const A2: f64 = 0.78327243e-1;
    const A3: f64 = -0.29120539e-2;
    const B1: f64 = 0.46697102e0;
    const B2: f64 = 0.24255406e0;
    const C0: f64 = 0.12260172e0;
    const C1: f64 = 0.53730130e-1;
    const C2: f64 = 0.43384378e-1;
    const C3: f64 = 0.11101277e-1;
    const D1: f64 = 0.18324466e0;
    const D2: f64 = 0.20166036e0;
    const E1: f64 = 0.23807576e1;
    const E2: f64 = 0.15931792e1;
    const E3: f64 = 0.11618371e0;
    const F1: f64 = 0.51533299e1;
    const F2: f64 = 0.71425260e1;
    const F3: f64 = 0.19745056e1;
    const G1: f64 = 0.21235833e1;
    const G2: f64 = 0.41670213e1;
    const G3: f64 = 0.31925299e1;
    const H1: f64 = 0.90551443e1;
    const H2: f64 = 0.26649995e2;
    const H3: f64 = 0.26193668e2;

    let mut xmom = vec![0.0; nmom];
    if nmom == 0 {
        return (xmom, 0);
    }
    let sd = para[1];
    if sd <= 0.0 {
        return (xmom, 7000);
    }
    if nmom > 4 {
        return (xmom, 7010);
    }
    xmom[0] = para[0];
    if nmom == 1 {
        return (xmom, 0);
    }
    let gamma = para[2];
    if gamma.abs() < SMALL {
        xmom[0] = para[0];
        if nmom == 1 {
            return (xmom, 0);
        }
        xmom[1] = CONST * para[1];
        if nmom == 2 {
            return (xmom, 0);
        }
        xmom[2] = 0.0;
        if nmom == 3 {
            return (xmom, 0);
        }
        xmom[3] = C0;
        return (xmom, 0);
    }
    let alpha = 4.0 / (gamma * gamma);
    let beta = (0.5 * sd * gamma).abs();
    let alam2 = CONST * (xlgama(alpha + 0.5) - xlgama(alpha)).exp();
    xmom[1] = alam2 * beta;
    if nmom == 2 {
        return (xmom, 0);
    }
    if alpha < 1.0 {
        let z = alpha;
        xmom[2] = (((E3 * z + E2) * z + E1) * z + 1.0) / (((F3 * z + F2) * z + F1) * z + 1.0);
        if gamma < 0.0 {
            xmom[2] = -xmom[2];
        }
        if nmom == 3 {
            return (xmom, 0);
        }
        xmom[3] = (((G3 * z + G2) * z + G1) * z + 1.0) / (((H3 * z + H2) * z + H1) * z + 1.0);
    } else {
        let z = 1.0 / alpha;
        xmom[2] = z.sqrt() * (((A3 * z + A2) * z + A1) * z + A0) / ((B2 * z + B1) * z + 1.0);
        if gamma < 0.0 {
            xmom[2] = -xmom[2];
        }
        if nmom == 3 {
            return (xmom, 0);
        }
        xmom[3] = (((C3 * z + C2) * z + C1) * z + C0) / ((D2 * z + D1) * z + 1.0);
    }
    (xmom, 0)
}

/// Wakeby, port of `LMRWAK`.
pub fn lmr_wak(para: &[f64], nmom: usize) -> (Vec<f64>, i32) {
    let mut xmom = vec![0.0; nmom];
    if nmom == 0 {
        return (xmom, 0);
    }
    let (xi, a, b, c, d) = (para[0], para[1], para[2], para[3], para[4]);
    if d >= 1.0 {
        return (xmom, 7000);
    }
    if b + d <= 0.0 && (b != 0.0 || c != 0.0 || d != 0.0) {
        return (xmom, 7000);
    }
    if a == 0.0 && b != 0.0 {
        return (xmom, 7000);
    }
    if c == 0.0 && d != 0.0 {
        return (xmom, 7000);
    }
    if c < 0.0 {
        return (xmom, 7000);
    }
    if a + c < 0.0 {
        return (xmom, 7000);
    }
    if a == 0.0 && c == 0.0 {
        return (xmom, 7000);
    }
    if nmom > 20 {
        return (xmom, 7010);
    }
    let mut y = a / (1.0 + b);
    let mut z = c / (1.0 - d);
    xmom[0] = xi + y + z;
    if nmom == 1 {
        return (xmom, 0);
    }
    y /= 2.0 + b;
    z /= 2.0 - d;
    let alam2 = y + z;
    xmom[1] = alam2;
    if nmom == 2 {
        return (xmom, 0);
    }
    for m in 3..=nmom {
        let am = m as f64;
        y = y * (am - 2.0 - b) / (am + b);
        z = z * (am - 2.0 + d) / (am - d);
        xmom[m - 1] = (y + z) / alam2;
    }
    (xmom, 0)
}

// ---------------------------------------------------------------------------
// Parameters from L-moments (pel*.f). Each takes L-moments and returns
// (para, ifail). Output is zero-filled where the Fortran leaves it unset.
// ---------------------------------------------------------------------------

/// Exponential, port of `PELEXP`.
pub fn pel_exp(xmom: &[f64]) -> (Vec<f64>, i32) {
    let mut para = vec![0.0; 2];
    if xmom[1] <= 0.0 {
        return (para, 7000);
    }
    para[1] = 2.0 * xmom[1];
    para[0] = xmom[0] - para[1];
    (para, 0)
}

/// Gamma, port of `PELGAM`.
pub fn pel_gam(xmom: &[f64]) -> (Vec<f64>, i32) {
    const A1: f64 = -0.3080;
    const A2: f64 = -0.05812;
    const A3: f64 = 0.01765;
    const B1: f64 = 0.7213;
    const B2: f64 = -0.5947;
    const B3: f64 = -2.1817;
    const B4: f64 = 1.2113;
    const PI_GAM: f64 = 3.1415927;

    let mut para = vec![0.0; 2];
    if xmom[0] <= xmom[1] || xmom[1] <= 0.0 {
        return (para, 7000);
    }
    let cv = xmom[1] / xmom[0];
    let alpha = if cv >= 0.5 {
        let t = 1.0 - cv;
        t * (B1 + t * B2) / (1.0 + t * (B3 + t * B4))
    } else {
        let t = PI_GAM * cv * cv;
        (1.0 + A1 * t) / (t * (1.0 + t * (A2 + t * A3)))
    };
    para[0] = alpha;
    para[1] = xmom[0] / alpha;
    (para, 0)
}

/// Generalized extreme value, port of `PELGEV`.
pub fn pel_gev(xmom: &[f64]) -> (Vec<f64>, i32) {
    const SMALL: f64 = 1e-5;
    const EPS: f64 = 1e-6;
    const MAXIT: usize = 20;
    const EU: f64 = 0.57721566e0;
    const DL2: f64 = 0.69314718e0;
    const DL3: f64 = 1.0986123e0;
    const A0: f64 = 0.28377530e0;
    const A1: f64 = -1.21096399e0;
    const A2: f64 = -2.50728214e0;
    const A3: f64 = -1.13455566e0;
    const A4: f64 = -0.07138022e0;
    const B1: f64 = 2.06189696e0;
    const B2: f64 = 1.31912239e0;
    const B3: f64 = 0.25077104e0;
    const C1: f64 = 1.59921491e0;
    const C2: f64 = -0.48832213e0;
    const C3: f64 = 0.01573152e0;
    const D1: f64 = -0.64363929e0;
    const D2: f64 = 0.08985247e0;

    let mut para = vec![0.0; 3];
    let t3 = xmom[2];
    if xmom[1] <= 0.0 || t3.abs() >= 1.0 {
        return (para, 7000);
    }
    let mut ifail = 0;
    let mut g;
    if t3 > 0.0 {
        let z = 1.0 - t3;
        g = (-1.0 + z * (C1 + z * (C2 + z * C3))) / (1.0 + z * (D1 + z * D2));
        if g.abs() < SMALL {
            // Shape effectively zero: Gumbel limit.
            para[2] = 0.0;
            para[1] = xmom[1] / DL2;
            para[0] = xmom[0] - EU * para[1];
            return (para, ifail);
        }
    } else {
        g = (A0 + t3 * (A1 + t3 * (A2 + t3 * (A3 + t3 * A4))))
            / (1.0 + t3 * (B1 + t3 * (B2 + t3 * B3)));
        if t3 < -0.8 {
            if t3 <= -0.97 {
                g = 1.0 - (1.0 + t3).ln() / DL2;
            }
            let t0 = (t3 + 3.0) * 0.5;
            let mut converged = false;
            for _it in 1..=MAXIT {
                let x2 = 2f64.powf(-g);
                let x3 = 3f64.powf(-g);
                let xx2 = 1.0 - x2;
                let xx3 = 1.0 - x3;
                let t = xx3 / xx2;
                let deriv = (xx2 * x3 * DL3 - xx3 * x2 * DL2) / (xx2 * xx2);
                let gold = g;
                g -= (t - t0) / deriv;
                if (g - gold).abs() <= EPS * g {
                    converged = true;
                    break;
                }
            }
            if !converged {
                ifail = 7020;
            }
        }
    }
    para[2] = g;
    let gam = xlgama(1.0 + g).exp();
    para[1] = xmom[1] * g / (gam * (1.0 - 2f64.powf(-g)));
    para[0] = xmom[0] - para[1] * (1.0 - gam) / g;
    (para, ifail)
}

/// Generalized logistic, port of `PELGLO`.
pub fn pel_glo(xmom: &[f64]) -> (Vec<f64>, i32) {
    const SMALL: f64 = 1e-6;
    let mut para = vec![0.0; 3];
    let g = -xmom[2];
    if xmom[1] <= 0.0 || g.abs() >= 1.0 {
        return (para, 7000);
    }
    if g.abs() <= SMALL {
        para[2] = 0.0;
        para[1] = xmom[1];
        para[0] = xmom[0];
        return (para, 0);
    }
    let gg = g * PI / (g * PI).sin();
    let a = xmom[1] / gg;
    para[0] = xmom[0] - a * (1.0 - gg) / g;
    para[1] = a;
    para[2] = g;
    (para, 0)
}

/// Generalized normal, port of `PELGNO`.
pub fn pel_gno(xmom: &[f64]) -> (Vec<f64>, i32) {
    const A0: f64 = 0.20466534e1;
    const A1: f64 = -0.36544371e1;
    const A2: f64 = 0.18396733e1;
    const A3: f64 = -0.20360244e0;
    const B1: f64 = -0.20182173e1;
    const B2: f64 = 0.12420401e1;
    const B3: f64 = -0.21741801e0;
    const SMALL: f64 = 1e-8;
    const ROOTPI: f64 = 1.772453850905516027e0;

    let mut para = vec![0.0; 3];
    let t3 = xmom[2];
    if xmom[1] <= 0.0 || t3.abs() >= 1.0 {
        return (para, 7000);
    }
    if t3.abs() >= 0.95 {
        return (vec![0.0, -1.0, 0.0], 7010);
    }
    if t3.abs() <= SMALL {
        return (vec![xmom[0], xmom[1] * ROOTPI, 0.0], 0);
    }
    let tt = t3 * t3;
    let g = -t3 * (A0 + tt * (A1 + tt * (A2 + tt * A3))) / (1.0 + tt * (B1 + tt * (B2 + tt * B3)));
    let e = (0.5 * g * g).exp();
    let a = xmom[1] * g / (e * xerf(0.5 * g));
    let u = xmom[0] + a * (e - 1.0) / g;
    para[0] = u;
    para[1] = a;
    para[2] = g;
    (para, 0)
}

/// Generalized Pareto, port of `PELGPA`.
pub fn pel_gpa(xmom: &[f64]) -> (Vec<f64>, i32) {
    let mut para = vec![0.0; 3];
    let t3 = xmom[2];
    if xmom[1] <= 0.0 || t3.abs() >= 1.0 {
        return (para, 7000);
    }
    let g = (1.0 - 3.0 * t3) / (1.0 + t3);
    para[2] = g;
    para[1] = (1.0 + g) * (2.0 + g) * xmom[1];
    para[0] = xmom[0] - para[1] / (1.0 + g);
    (para, 0)
}

/// Gumbel, port of `PELGUM`.
pub fn pel_gum(xmom: &[f64]) -> (Vec<f64>, i32) {
    const EU: f64 = 0.577215664901532861e0;
    const DL2: f64 = 0.693147180559945309e0;
    let mut para = vec![0.0; 2];
    if xmom[1] <= 0.0 {
        return (para, 7000);
    }
    para[1] = xmom[1] / DL2;
    para[0] = xmom[0] - EU * para[1];
    (para, 0)
}

/// Kappa, port of `PELKAP`. Newton-Raphson on (tau3, tau4) with step
/// reduction. Returns the Fortran IFAIL codes 0, 2, 3, 4, 5, 6, 7000.
pub fn pel_kap(xmom: &[f64]) -> (Vec<f64>, i32) {
    const EPS: f64 = 1e-6;
    const MAXIT: usize = 20;
    const MAXSR: usize = 10;
    const HSTART: f64 = 1.001;
    const BIG: f64 = 10.0;
    const OFLEXP: f64 = 170.0;
    const OFLGAM: f64 = 53.0;
    const P725: f64 = 0.725;
    const P8: f64 = 0.8;

    let mut para = vec![0.0; 4];
    let t3 = xmom[2];
    let t4 = xmom[3];
    if xmom[1] <= 0.0 {
        return (para, 7000);
    }
    if t3.abs() >= 1.0 || t4.abs() >= 1.0 {
        return (para, 7000);
    }
    if t4 <= (5.0 * t3 * t3 - 1.0) / 4.0 {
        return (para, 7000);
    }
    if t4 >= (5.0 * t3 * t3 + 1.0) / 6.0 {
        return (para, 2);
    }

    let mut g = (1.0 - 3.0 * t3) / (1.0 + t3);
    let mut h = HSTART;
    let mut z = g + h * P725;
    let mut xdist = BIG;
    let mut del1 = 0.0;
    let mut del2 = 0.0;
    let mut xg = 0.0;
    let mut xh = 0.0;
    let mut u1 = 0.0;
    let mut u2 = 0.0;
    let mut u3 = 0.0;
    let mut u4 = 0.0;
    let mut alam2 = 0.0;
    let mut tau3;
    let mut tau4;
    let mut e1;
    let mut e2;
    let mut dist;
    let mut converged = false;

    'newton: for _it in 1..=MAXIT {
        // Reduce the step length until closer to the target (tau3, tau4).
        let mut improved = false;
        for _i in 1..=MAXSR {
            if g > OFLGAM {
                return (para, 5);
            }
            if h > 0.0 {
                u1 = (xlgama(1.0 / h) - xlgama(1.0 / h + 1.0 + g)).exp();
                u2 = (xlgama(2.0 / h) - xlgama(2.0 / h + 1.0 + g)).exp();
                u3 = (xlgama(3.0 / h) - xlgama(3.0 / h + 1.0 + g)).exp();
                u4 = (xlgama(4.0 / h) - xlgama(4.0 / h + 1.0 + g)).exp();
            } else {
                u1 = (xlgama(-1.0 / h - g) - xlgama(-1.0 / h + 1.0)).exp();
                u2 = (xlgama(-2.0 / h - g) - xlgama(-2.0 / h + 1.0)).exp();
                u3 = (xlgama(-3.0 / h - g) - xlgama(-3.0 / h + 1.0)).exp();
                u4 = (xlgama(-4.0 / h - g) - xlgama(-4.0 / h + 1.0)).exp();
            }
            alam2 = u1 - 2.0 * u2;
            let alam3 = -u1 + 6.0 * u2 - 6.0 * u3;
            let alam4 = u1 - 12.0 * u2 + 30.0 * u3 - 20.0 * u4;
            if alam2 == 0.0 {
                return (para, 5);
            }
            tau3 = alam3 / alam2;
            tau4 = alam4 / alam2;
            e1 = tau3 - t3;
            e2 = tau4 - t4;
            dist = e1.abs().max(e2.abs());
            if dist < xdist {
                improved = true;
                break;
            }
            del1 *= 0.5;
            del2 *= 0.5;
            g = xg - del1;
            h = xh - del2;
        }
        if !improved {
            return (para, 4);
        }
        // Recompute the final residuals for the accepted (g, h).
        tau3 = (-u1 + 6.0 * u2 - 6.0 * u3) / alam2;
        tau4 = (u1 - 12.0 * u2 + 30.0 * u3 - 20.0 * u4) / alam2;
        e1 = tau3 - t3;
        e2 = tau4 - t4;
        dist = e1.abs().max(e2.abs());
        if dist < EPS {
            converged = true;
            break 'newton;
        }

        xg = g;
        xh = h;
        let xz = z;
        xdist = dist;
        let rhh = 1.0 / (h * h);
        let (u1g, u2g, u3g, u4g, u1h, u2h, u3h, u4h);
        if h > 0.0 {
            u1g = -u1 * digamd(1.0 / h + 1.0 + g);
            u2g = -u2 * digamd(2.0 / h + 1.0 + g);
            u3g = -u3 * digamd(3.0 / h + 1.0 + g);
            u4g = -u4 * digamd(4.0 / h + 1.0 + g);
            u1h = rhh * (-u1g - u1 * digamd(1.0 / h));
            u2h = 2.0 * rhh * (-u2g - u2 * digamd(2.0 / h));
            u3h = 3.0 * rhh * (-u3g - u3 * digamd(3.0 / h));
            u4h = 4.0 * rhh * (-u4g - u4 * digamd(4.0 / h));
        } else {
            u1g = -u1 * digamd(-1.0 / h - g);
            u2g = -u2 * digamd(-2.0 / h - g);
            u3g = -u3 * digamd(-3.0 / h - g);
            u4g = -u4 * digamd(-4.0 / h - g);
            u1h = rhh * (-u1g - u1 * digamd(-1.0 / h + 1.0));
            u2h = 2.0 * rhh * (-u2g - u2 * digamd(-2.0 / h + 1.0));
            u3h = 3.0 * rhh * (-u3g - u3 * digamd(-3.0 / h + 1.0));
            u4h = 4.0 * rhh * (-u4g - u4 * digamd(-4.0 / h + 1.0));
        }
        let dl2g = u1g - 2.0 * u2g;
        let dl2h = u1h - 2.0 * u2h;
        let dl3g = -u1g + 6.0 * u2g - 6.0 * u3g;
        let dl3h = -u1h + 6.0 * u2h - 6.0 * u3h;
        let dl4g = u1g - 12.0 * u2g + 30.0 * u3g - 20.0 * u4g;
        let dl4h = u1h - 12.0 * u2h + 30.0 * u3h - 20.0 * u4h;
        let d11 = (dl3g - tau3 * dl2g) / alam2;
        let d12 = (dl3h - tau3 * dl2h) / alam2;
        let d21 = (dl4g - tau4 * dl2g) / alam2;
        let d22 = (dl4h - tau4 * dl2h) / alam2;
        let det = d11 * d22 - d12 * d21;
        let h11 = d22 / det;
        let h12 = -d12 / det;
        let h21 = -d21 / det;
        let h22 = d11 / det;
        del1 = e1 * h11 + e2 * h12;
        del2 = e1 * h21 + e2 * h22;

        g = xg - del1;
        h = xh - del2;
        z = g + h * P725;

        // Keep (g, h) inside the parameter space.
        let mut factor = 1.0;
        if g <= -1.0 {
            factor = P8 * (xg + 1.0) / del1;
        }
        if h <= -1.0 {
            factor = factor.min(P8 * (xh + 1.0) / del2);
        }
        if z <= -1.0 {
            factor = factor.min(P8 * (xz + 1.0) / (xz - z));
        }
        if h <= 0.0 && g * h <= -1.0 {
            factor = factor.min(P8 * (xg * xh + 1.0) / (xg * xh - g * h));
        }
        if factor != 1.0 {
            del1 *= factor;
            del2 *= factor;
            g = xg - del1;
            h = xh - del2;
            z = g + h * P725;
        }
    }

    if !converged {
        return (para, 3);
    }
    para[3] = h;
    para[2] = g;
    let temp = xlgama(1.0 + g);
    if temp > OFLEXP {
        return (para, 6);
    }
    let gam = temp.exp();
    let temp = (1.0 + g) * h.abs().ln();
    if temp > OFLEXP {
        return (para, 6);
    }
    let hh = temp.exp();
    para[1] = xmom[1] * g * hh / (alam2 * gam);
    para[0] = xmom[0] - para[1] / g * (1.0 - gam * u1 / hh);
    (para, 0)
}

/// Normal, port of `PELNOR`.
pub fn pel_nor(xmom: &[f64]) -> (Vec<f64>, i32) {
    const ROOTPI: f64 = 1.77245385090551603e0;
    let mut para = vec![0.0; 2];
    if xmom[1] <= 0.0 {
        return (para, 7000);
    }
    para[1] = xmom[1] * ROOTPI;
    para[0] = xmom[0];
    (para, 0)
}

/// Pearson type 3, port of `PELPE3`.
pub fn pel_pe3(xmom: &[f64]) -> (Vec<f64>, i32) {
    const SMALL: f64 = 1e-6;
    const THIRD: f64 = 0.33333333e0;
    const C1: f64 = 0.2906e0;
    const C2: f64 = 0.1882e0;
    const C3: f64 = 0.0442e0;
    const D1: f64 = 0.36067e0;
    const D2: f64 = -0.59567e0;
    const D3: f64 = 0.25361e0;
    const D4: f64 = -2.78861e0;
    const D5: f64 = 2.56096e0;
    const D6: f64 = -0.77045e0;
    const PI3: f64 = 9.4247780e0;
    const ROOTPI: f64 = 1.7724539e0;

    let mut para = vec![0.0; 3];
    let t3 = xmom[2].abs();
    if xmom[1] <= 0.0 || t3 >= 1.0 {
        return (para, 7000);
    }
    if t3 <= SMALL {
        para[0] = xmom[0];
        para[1] = xmom[1] * ROOTPI;
        para[2] = 0.0;
        return (para, 0);
    }
    let alpha = if t3 >= THIRD {
        let t = 1.0 - t3;
        t * (D1 + t * (D2 + t * D3)) / (1.0 + t * (D4 + t * (D5 + t * D6)))
    } else {
        let t = PI3 * t3 * t3;
        (1.0 + C1 * t) / (t * (1.0 + t * (C2 + t * C3)))
    };
    let rtalph = alpha.sqrt();
    let beta = ROOTPI * xmom[1] * (xlgama(alpha) - xlgama(alpha + 0.5)).exp();
    para[0] = xmom[0];
    para[1] = beta * rtalph;
    para[2] = 2.0 / rtalph;
    if xmom[2] < 0.0 {
        para[2] = -para[2];
    }
    (para, 0)
}

/// Wakeby, port of `PELWAK`. Falls back to a generalized Pareto fit (IFAIL 1).
pub fn pel_wak(xmom: &[f64]) -> (Vec<f64>, i32) {
    let mut para = vec![0.0; 5];
    if xmom[1] <= 0.0 || xmom[2].abs() >= 1.0 || xmom[3].abs() >= 1.0 || xmom[4].abs() >= 1.0 {
        return (para, 7000);
    }
    let mut ifail = 0;
    let alam1 = xmom[0];
    let alam2 = xmom[1];
    let alam3 = xmom[2] * alam2;
    let alam4 = xmom[3] * alam2;
    let alam5 = xmom[4] * alam2;

    let xn1 = 3.0 * alam2 - 25.0 * alam3 + 32.0 * alam4;
    let xn2 = -3.0 * alam2 + 5.0 * alam3 + 8.0 * alam4;
    let xn3 = 3.0 * alam2 + 5.0 * alam3 + 2.0 * alam4;
    let xc1 = 7.0 * alam2 - 85.0 * alam3 + 203.0 * alam4 - 125.0 * alam5;
    let xc2 = -7.0 * alam2 + 25.0 * alam3 + 7.0 * alam4 - 25.0 * alam5;
    let xc3 = 7.0 * alam2 + 5.0 * alam3 - 7.0 * alam4 - 5.0 * alam5;

    let xa = xn2 * xc3 - xc2 * xn3;
    let xb = xn1 * xc3 - xc1 * xn3;
    let xc = xn1 * xc2 - xc1 * xn2;
    let disc = xb * xb - 4.0 * xa * xc;

    let mut xi = 0.0;
    let mut a = 0.0;
    let mut b = 0.0;
    let mut c = 0.0;
    let mut d = 0.0;
    let mut valid = false;
    if disc >= 0.0 {
        let disc = disc.sqrt();
        let root1 = 0.5 * (-xb + disc) / xa;
        let root2 = 0.5 * (-xb - disc) / xa;
        b = root1.max(root2);
        d = -root1.min(root2);
        if d < 1.0 {
            a = (1.0 + b) * (2.0 + b) * (3.0 + b) / (4.0 * (b + d))
                * ((1.0 + d) * alam2 - (3.0 - d) * alam3);
            c = -(1.0 - d) * (2.0 - d) * (3.0 - d) / (4.0 * (b + d))
                * ((1.0 - b) * alam2 - (3.0 + b) * alam3);
            xi = alam1 - a / (1.0 + b) - c / (1.0 - d);
            valid = c >= 0.0 && a + c >= 0.0;
        }
    }
    if !valid {
        ifail = 1;
        d = -(1.0 - 3.0 * xmom[2]) / (1.0 + xmom[2]);
        c = (1.0 - d) * (2.0 - d) * xmom[1];
        b = 0.0;
        a = 0.0;
        xi = xmom[0] - c / (1.0 - d);
        if d <= 0.0 {
            a = c;
            b = -d;
            c = 0.0;
            d = 0.0;
        }
    }
    para[0] = xi;
    para[1] = a;
    para[2] = b;
    para[3] = c;
    para[4] = d;
    (para, ifail)
}

/// Wakeby with lower bound zero, port of `PELWA0`. Takes 4 L-moments.
pub fn pel_wa0(xmom: &[f64]) -> (Vec<f64>, i32) {
    let mut para = vec![0.0; 5];
    if xmom[0] <= 0.0 || xmom[1] <= 0.0 || xmom[2].abs() >= 1.0 || xmom[3].abs() >= 1.0 {
        return (para, 7000);
    }
    let mut ifail = 0;
    let alam1 = xmom[0];
    let alam2 = xmom[1];
    let alam3 = xmom[2] * alam2;
    let alam4 = xmom[3] * alam2;

    let zn1 = 4.0 * alam1 - 11.0 * alam2 + 9.0 * alam3;
    let zn2 = -alam2 + 3.0 * alam3;
    let zn3 = alam2 + alam3;
    let zc1 = 10.0 * alam1 - 29.0 * alam2 + 35.0 * alam3 - 16.0 * alam4;
    let zc2 = -alam2 + 5.0 * alam3 - 4.0 * alam4;
    let zc3 = alam2 - alam4;
    let za = zn2 * zc3 - zc2 * zn3;
    let zb = zn1 * zc3 - zc1 * zn3;
    let zc = zn1 * zc2 - zc1 * zn2;
    let disc = zb * zb - 4.0 * za * zc;

    let mut a = 0.0;
    let mut b = 0.0;
    let mut c = 0.0;
    let mut d = 0.0;
    let mut valid = false;
    if disc >= 0.0 {
        let disc = disc.sqrt();
        let root1 = 0.5 * (-zb + disc) / za;
        let root2 = 0.5 * (-zb - disc) / za;
        b = root1.max(root2);
        d = -root1.min(root2);
        if d < 1.0 {
            a = (1.0 + b) * (2.0 + b) / (b + d) * (alam1 - (2.0 - d) * alam2);
            c = -(1.0 - d) * (2.0 - d) / (b + d) * (alam1 - (2.0 + b) * alam2);
            valid = c >= 0.0 && a + c >= 0.0;
        }
    }
    if !valid {
        ifail = 1;
        d = 2.0 - alam1 / alam2;
        c = (1.0 - d) * alam1;
        b = 0.0;
        a = 0.0;
        if d <= 0.0 {
            a = c;
            b = -d;
            c = 0.0;
            d = 0.0;
        }
    }
    para[0] = 0.0;
    para[1] = a;
    para[2] = b;
    para[3] = c;
    para[4] = d;
    (para, ifail)
}

// ---------------------------------------------------------------------------
// PyO3 bindings (NumPy in, NumPy out)
// ---------------------------------------------------------------------------

#[cfg(feature = "python")]
mod py {
    use numpy::{IntoPyArray, PyArray1, PyReadonlyArray1};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::{
        lmr_exp as k_lmr_exp, lmr_gam as k_lmr_gam, lmr_gev as k_lmr_gev, lmr_glo as k_lmr_glo,
        lmr_gno as k_lmr_gno, lmr_gpa as k_lmr_gpa, lmr_gum as k_lmr_gum, lmr_kap as k_lmr_kap,
        lmr_nor as k_lmr_nor, lmr_pe3 as k_lmr_pe3, lmr_wak as k_lmr_wak, pel_exp as k_pel_exp,
        pel_gam as k_pel_gam, pel_gev as k_pel_gev, pel_glo as k_pel_glo, pel_gno as k_pel_gno,
        pel_gpa as k_pel_gpa, pel_gum as k_pel_gum, pel_kap as k_pel_kap, pel_nor as k_pel_nor,
        pel_pe3 as k_pel_pe3, pel_wa0 as k_pel_wa0, pel_wak as k_pel_wak, samlm as k_samlm,
    };

    fn owned(a: &PyReadonlyArray1<'_, f64>) -> Vec<f64> {
        match a.as_slice() {
            Ok(s) => s.to_vec(),
            Err(_) => a.as_array().iter().copied().collect(),
        }
    }

    type Out<'py> = PyResult<(Bound<'py, PyArray1<f64>>, i32)>;

    /// Sample L-moments (or ratios when `iratio`) of a data vector.
    #[pyfunction]
    #[pyo3(signature = (x, nmom, isort=true, iratio=false))]
    pub fn samlm<'py>(
        py: Python<'py>,
        x: PyReadonlyArray1<'py, f64>,
        nmom: usize,
        isort: bool,
        iratio: bool,
    ) -> PyResult<Bound<'py, PyArray1<f64>>> {
        let data = owned(&x);
        if data.is_empty() {
            return Err(PyValueError::new_err("x must not be empty"));
        }
        Ok(k_samlm(&data, nmom, isort, iratio).into_pyarray(py))
    }

    macro_rules! lmr_py {
        ($fname:ident, $kernel:path, $npara:expr) => {
            #[pyfunction]
            pub fn $fname<'py>(
                py: Python<'py>,
                para: PyReadonlyArray1<'py, f64>,
                nmom: usize,
            ) -> Out<'py> {
                let p = owned(&para);
                if p.len() != $npara {
                    return Err(PyValueError::new_err(format!(
                        "parameter vector must have length {}",
                        $npara
                    )));
                }
                let (xmom, ifail) = $kernel(&p, nmom);
                Ok((xmom.into_pyarray(py), ifail))
            }
        };
    }

    macro_rules! pel_py {
        ($fname:ident, $kernel:path, $himom:expr) => {
            #[pyfunction]
            pub fn $fname<'py>(py: Python<'py>, xmom: PyReadonlyArray1<'py, f64>) -> Out<'py> {
                let m = owned(&xmom);
                if m.len() < $himom {
                    return Err(PyValueError::new_err(format!(
                        "need at least {} L-moments",
                        $himom
                    )));
                }
                let (para, ifail) = $kernel(&m[..$himom]);
                Ok((para.into_pyarray(py), ifail))
            }
        };
    }

    lmr_py!(lmr_exp, k_lmr_exp, 2);
    lmr_py!(lmr_gam, k_lmr_gam, 2);
    lmr_py!(lmr_gev, k_lmr_gev, 3);
    lmr_py!(lmr_glo, k_lmr_glo, 3);
    lmr_py!(lmr_gno, k_lmr_gno, 3);
    lmr_py!(lmr_gpa, k_lmr_gpa, 3);
    lmr_py!(lmr_gum, k_lmr_gum, 2);
    lmr_py!(lmr_kap, k_lmr_kap, 4);
    lmr_py!(lmr_nor, k_lmr_nor, 2);
    lmr_py!(lmr_pe3, k_lmr_pe3, 3);
    lmr_py!(lmr_wak, k_lmr_wak, 5);

    pel_py!(pel_exp, k_pel_exp, 2);
    pel_py!(pel_gam, k_pel_gam, 2);
    pel_py!(pel_gev, k_pel_gev, 3);
    pel_py!(pel_glo, k_pel_glo, 3);
    pel_py!(pel_gno, k_pel_gno, 3);
    pel_py!(pel_gpa, k_pel_gpa, 3);
    pel_py!(pel_gum, k_pel_gum, 2);
    pel_py!(pel_kap, k_pel_kap, 4);
    pel_py!(pel_nor, k_pel_nor, 2);
    pel_py!(pel_pe3, k_pel_pe3, 3);
    pel_py!(pel_wak, k_pel_wak, 5);
    pel_py!(pel_wa0, k_pel_wa0, 4);
}

#[cfg(feature = "python")]
#[pymodule]
fn lmom_kernel(m: &Bound<'_, PyModule>) -> PyResult<()> {

    m.add_function(wrap_pyfunction!(py::samlm, m)?)?;
    m.add_function(wrap_pyfunction!(py::lmr_exp, m)?)?;
    m.add_function(wrap_pyfunction!(py::lmr_gam, m)?)?;
    m.add_function(wrap_pyfunction!(py::lmr_gev, m)?)?;
    m.add_function(wrap_pyfunction!(py::lmr_glo, m)?)?;
    m.add_function(wrap_pyfunction!(py::lmr_gno, m)?)?;
    m.add_function(wrap_pyfunction!(py::lmr_gpa, m)?)?;
    m.add_function(wrap_pyfunction!(py::lmr_gum, m)?)?;
    m.add_function(wrap_pyfunction!(py::lmr_kap, m)?)?;
    m.add_function(wrap_pyfunction!(py::lmr_nor, m)?)?;
    m.add_function(wrap_pyfunction!(py::lmr_pe3, m)?)?;
    m.add_function(wrap_pyfunction!(py::lmr_wak, m)?)?;
    m.add_function(wrap_pyfunction!(py::pel_exp, m)?)?;
    m.add_function(wrap_pyfunction!(py::pel_gam, m)?)?;
    m.add_function(wrap_pyfunction!(py::pel_gev, m)?)?;
    m.add_function(wrap_pyfunction!(py::pel_glo, m)?)?;
    m.add_function(wrap_pyfunction!(py::pel_gno, m)?)?;
    m.add_function(wrap_pyfunction!(py::pel_gpa, m)?)?;
    m.add_function(wrap_pyfunction!(py::pel_gum, m)?)?;
    m.add_function(wrap_pyfunction!(py::pel_kap, m)?)?;
    m.add_function(wrap_pyfunction!(py::pel_nor, m)?)?;
    m.add_function(wrap_pyfunction!(py::pel_pe3, m)?)?;
    m.add_function(wrap_pyfunction!(py::pel_wak, m)?)?;
    m.add_function(wrap_pyfunction!(py::pel_wa0, m)?)?;
    Ok(())
}
