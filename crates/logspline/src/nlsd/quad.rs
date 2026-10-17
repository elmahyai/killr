//! Integrals of x^i times exp(polynomial) and the small polynomial helpers from
//! `src/nlsd.c` (`m1int`, `l1int`, `l2int`, `fctf1`, `fctf2`, `pol3`, `inp3`,
//! `mat3`). The Gauss-Legendre nodes come from the lsdall tables.

use super::base::{mylog, myexp};
use crate::lsdall::tables::{GL12_W, GL12_Y, GL3_W, GL3_Y};

/// `m1int`: integrals of x^i times exp(coef polynomial) over (k1, k2) by
/// Gauss-Legendre quadrature. `what == 0` keeps only the first integral.
/// `accuracy == 1` uses the 3-point rule, otherwise the 32-point rule.
pub fn m1int(vv: &mut [f64], k1: f64, k2: f64, what: i32, coef: &[f64], accuracy: i32) {
    let r1 = (k2 - k1) / 2.0;
    let r2 = (k2 + k1) / 2.0;
    for i1 in 0..7 {
        vv[i1] = 0.0;
    }
    if k2 == k1 {
        return;
    }
    let mut j: usize = 7;
    if what == 0 {
        j = 1;
    }
    if accuracy == 1 {
        for i1 in 1..4 {
            let y = GL3_Y[i1] * r1;
            let v = r1 * GL3_W[i1];
            let mut x = r2 - y;
            let mut z = v * myexp(coef[0] + x * (coef[1] + x * (coef[2] + x * coef[3])));
            vv[0] += z;
            for i2 in 1..j {
                z *= x;
                vv[i2] += z;
            }
            x = r2 + y;
            z = v * myexp(coef[0] + x * (coef[1] + x * (coef[2] + x * coef[3])));
            vv[0] += z;
            for i2 in 1..j {
                z *= x;
                vv[i2] += z;
            }
        }
    } else {
        for i1 in 1..33 {
            let y = GL12_Y[i1] * r1;
            let v = r1 * GL12_W[i1];
            let mut x = r2 - y;
            let mut z = v * myexp(coef[0] + x * (coef[1] + x * (coef[2] + x * coef[3])));
            vv[0] += z;
            for i2 in 1..j {
                z *= x;
                vv[i2] += z;
            }
            x = r2 + y;
            z = v * myexp(coef[0] + x * (coef[1] + x * (coef[2] + x * coef[3])));
            vv[0] += z;
            for i2 in 1..j {
                z *= x;
                vv[i2] += z;
            }
        }
    }
}

/// `fctf1`: one term of the one-sided integral.
fn fctf1(b0: f64, b1: f64, t1: f64, f1_in: f64, j_in: i32) -> f64 {
    let mut j = j_in;
    if f1_in < 0.0 {
        j = -j;
    }
    let mut f1 = mylog(f1_in.abs()) + b1 * t1 + b0;
    if f1 > 600.0 {
        f1 = 600.0;
    }
    (j as f64) * myexp(f1)
}

/// `fctf2`: one two-sided term of the exact integral.
fn fctf2(b0: f64, b1: f64, t1: f64, t2: f64, f1_in: f64, f2_in: f64) -> f64 {
    let mut i1: i32 = 1;
    let mut i2: i32 = 1;
    if f1_in < 0.0 {
        i1 = -1;
    }
    let mut f1 = mylog(f1_in.abs()) + b1 * t1 + b0;
    if f1 > 600.0 {
        f1 = 600.0;
    }
    if f2_in < 0.0 {
        i2 = -1;
    }
    let mut f2 = mylog(f2_in.abs()) + b1 * t2 + b0;
    if f2 > 600.0 {
        f2 = 600.0;
    }
    (i2 as f64) * myexp(f2) - (i1 as f64) * myexp(f1)
}

/// `l1int`: integrals from -inf to t1 (`j == 1`) or from t1 to inf (`j == -1`).
pub fn l1int(results: &mut [f64], t1: f64, coef: &[f64], j: i32, what: i32) {
    let b1 = coef[1];
    let b0 = coef[0];
    let mut b3 = [0.0f64; 7];
    b3[0] = 1.0 / b1;
    let mut f1 = b3[0];
    results[0] = fctf1(b0, b1, t1, f1, j);
    if what == 0 {
        return;
    }
    b3[1] = b3[0] * b3[0];
    b3[2] = b3[1] * b3[0];
    b3[3] = b3[2] * b3[0];
    b3[4] = b3[3] * b3[0];
    b3[5] = b3[4] * b3[0];
    b3[6] = b3[5] * b3[0];

    let u1 = b3[0];
    let u0 = -b3[1];
    f1 = u1 * t1 + u0;
    results[1] = fctf1(b0, b1, t1, f1, j);

    let u2 = b3[0];
    let u1 = -2.0 * b3[1];
    let u0 = 2.0 * b3[2];
    f1 = (u2 * t1 + u1) * t1 + u0;
    results[2] = fctf1(b0, b1, t1, f1, j);

    let u3 = b3[0];
    let u2 = -3.0 * b3[1];
    let u1 = 6.0 * b3[2];
    let u0 = -6.0 * b3[3];
    f1 = ((u3 * t1 + u2) * t1 + u1) * t1 + u0;
    results[3] = fctf1(b0, b1, t1, f1, j);

    let u4 = b3[0];
    let u3 = -4.0 * b3[1];
    let u2 = 12.0 * b3[2];
    let u1 = -24.0 * b3[3];
    let u0 = 24.0 * b3[4];
    f1 = (((u4 * t1 + u3) * t1 + u2) * t1 + u1) * t1 + u0;
    results[4] = fctf1(b0, b1, t1, f1, j);

    let u5 = b3[0];
    let u4 = -5.0 * b3[1];
    let u3 = 20.0 * b3[2];
    let u2 = -60.0 * b3[3];
    let u1 = 120.0 * b3[4];
    let u0 = -120.0 * b3[5];
    f1 = ((((u5 * t1 + u4) * t1 + u3) * t1 + u2) * t1 + u1) * t1 + u0;
    results[5] = fctf1(b0, b1, t1, f1, j);

    let u6 = b3[0];
    let u5 = -6.0 * b3[1];
    let u4 = 30.0 * b3[2];
    let u3 = -120.0 * b3[3];
    let u2 = 360.0 * b3[4];
    let u1 = -720.0 * b3[5];
    let u0 = 720.0 * b3[6];
    f1 = (((((u6 * t1 + u5) * t1 + u4) * t1 + u3) * t1 + u2) * t1 + u1) * t1 + u0;
    results[6] = fctf1(b0, b1, t1, f1, j);
}

/// `l2int`: integrals from t1 to t2 (exactly, when the slope is nonzero).
pub fn l2int(results: &mut [f64], t1: f64, t2: f64, coef: &[f64], what: i32) {
    let b1 = coef[1];
    let mut b0 = coef[0];
    if b1 != 0.0 {
        let mut b3 = [0.0f64; 7];
        b3[0] = 1.0 / b1;
        let mut f1 = b3[0];
        let mut f2 = b3[0];
        results[0] = fctf2(b0, b1, t1, t2, f1, f2);
        if what == 0 {
            return;
        }
        b3[1] = b3[0] * b3[0];
        b3[2] = b3[1] * b3[0];
        b3[3] = b3[2] * b3[0];
        b3[4] = b3[3] * b3[0];
        b3[5] = b3[4] * b3[0];
        b3[6] = b3[5] * b3[0];

        let u1 = b3[0];
        let u0 = -b3[1];
        f1 = u1 * t1 + u0;
        f2 = u1 * t2 + u0;
        results[1] = fctf2(b0, b1, t1, t2, f1, f2);

        let u2 = b3[0];
        let u1 = -2.0 * b3[1];
        let u0 = 2.0 * b3[2];
        f1 = (u2 * t1 + u1) * t1 + u0;
        f2 = (u2 * t2 + u1) * t2 + u0;
        results[2] = fctf2(b0, b1, t1, t2, f1, f2);

        let u3 = b3[0];
        let u2 = -3.0 * b3[1];
        let u1 = 6.0 * b3[2];
        let u0 = -6.0 * b3[3];
        f1 = ((u3 * t1 + u2) * t1 + u1) * t1 + u0;
        f2 = ((u3 * t2 + u2) * t2 + u1) * t2 + u0;
        results[3] = fctf2(b0, b1, t1, t2, f1, f2);

        let u4 = b3[0];
        let u3 = -4.0 * b3[1];
        let u2 = 12.0 * b3[2];
        let u1 = -24.0 * b3[3];
        let u0 = 24.0 * b3[4];
        f1 = (((u4 * t1 + u3) * t1 + u2) * t1 + u1) * t1 + u0;
        f2 = (((u4 * t2 + u3) * t2 + u2) * t2 + u1) * t2 + u0;
        results[4] = fctf2(b0, b1, t1, t2, f1, f2);

        let u5 = b3[0];
        let u4 = -5.0 * b3[1];
        let u3 = 20.0 * b3[2];
        let u2 = -60.0 * b3[3];
        let u1 = 120.0 * b3[4];
        let u0 = -120.0 * b3[5];
        f1 = ((((u5 * t1 + u4) * t1 + u3) * t1 + u2) * t1 + u1) * t1 + u0;
        f2 = ((((u5 * t2 + u4) * t2 + u3) * t2 + u2) * t2 + u1) * t2 + u0;
        results[5] = fctf2(b0, b1, t1, t2, f1, f2);

        let u6 = b3[0];
        let u5 = -6.0 * b3[1];
        let u4 = 30.0 * b3[2];
        let u3 = -120.0 * b3[3];
        let u2 = 360.0 * b3[4];
        let u1 = -720.0 * b3[5];
        let u0 = 720.0 * b3[6];
        f1 = (((((u6 * t1 + u5) * t1 + u4) * t1 + u3) * t1 + u2) * t1 + u1) * t1 + u0;
        f2 = (((((u6 * t2 + u5) * t2 + u4) * t2 + u3) * t2 + u2) * t2 + u1) * t2 + u0;
        results[6] = fctf2(b0, b1, t1, t2, f1, f2);
        return;
    }
    b0 = myexp(b0);
    results[0] = (t2 - t1) * b0;
    if what == 0 {
        return;
    }
    let mut f2 = t2;
    let mut f1 = t1;
    for i in 1..7 {
        f2 *= t2;
        f1 *= t1;
        results[i] = b0 * (f2 - f1) / ((i + 1) as f64);
    }
}

/// `pol3`: cubic polynomial with coefficients `coef[0..4]` at x.
pub fn pol3(coef: &[f64], x: f64) -> f64 {
    coef[0] + x * (coef[1] + x * (coef[2] + x * coef[3]))
}

/// `inp3`: inner product of two cubic coefficient vectors.
pub fn inp3(c1: &[f64], c2: &[f64]) -> f64 {
    c1[0] * c2[0] + c1[1] * c2[1] + c1[2] * c2[2] + c1[3] * c2[3]
}

/// `mat3`: the bilinear form `sum_ij c1[i+j] c2[i] c3[j]`.
pub fn mat3(c1: &[f64], c2: &[f64], c3: &[f64]) -> f64 {
    let mut x = 0.0f64;
    for i in 0..4 {
        for j in 0..4 {
            x += c1[i + j] * c2[i] * c3[j];
        }
    }
    x
}
