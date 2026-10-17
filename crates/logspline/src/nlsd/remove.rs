//! Removing a knot in `src/nlsd.c`: `remdim` picks the knot with the smallest
//! Wald ratio, and `betarem` gives the new coefficients under the restrictions
//! that keep the tails in place (`redo1`, `redo2`, `solver`).

use super::base::{luinverse, mat, swapspace, DataS, Mat, Space, MAXKNOTS};
use super::setup::setupspace;
use crate::lsdall::rprintf;

/// `remdim`: remove the knot whose removal costs least. `spc2` receives a copy
/// of the model before the knot is removed.
pub fn remdim(spc: &mut Space, data: &mut DataS, spc2: &mut Space, silent: i32) {
    let mut ratmax = 0.0f64;
    let mut irmax: i32 = 1;
    let ndim = spc.ndim as usize;

    // invert the Hessian
    luinverse(&mut spc.info, ndim);
    // copy for later use
    swapspace(spc2, spc);

    for i in 0..spc.nk as usize {
        // compute the coefficient
        let mut phi = 0.0f64;
        for j in 0..ndim {
            phi += spc.basis[j].beta * spc.basis[j].c1[i + 2];
        }
        phi = phi.abs();
        // the standard error
        let mut se = 0.0f64;
        for j in 0..ndim {
            for k in 0..ndim {
                se -= spc.basis[j].c1[i + 2] * spc.basis[k].c1[i + 2] * spc.info[j][k];
            }
        }
        se = se.abs().sqrt();
        // Select for which knot se/phi takes it maximal value
        if se > phi * ratmax {
            ratmax = se / phi;
            irmax = i as i32;
        }
    }
    if silent == 1 {
        rprintf(&format!(
            "rem({:.2}), wald={:.2} ",
            spc.knots[irmax as usize],
            1.0 / (ratmax * ratmax)
        ));
    }

    // get nk and ndim
    spc.nk -= 1;
    spc.ndim -= 1;
    // remove the knot
    for i in irmax as usize..spc.nk as usize {
        spc.iknots[i] = spc.iknots[i + 1];
        spc.knots[i] = spc.knots[i + 1];
    }
    setupspace(spc, data);
    // get the new starting values
    betarem(spc2, spc, irmax);
}

/// Power-basis values `r1[i] = sum_j beta_j c1_j[i]` for `i < nk + 2`.
fn power_values(spc: &Space, r1: &mut [f64]) {
    for i in 0..(spc.nk + 2) as usize {
        r1[i] = 0.0;
        for j in 0..spc.ndim as usize {
            r1[i] += spc.basis[j].beta * spc.basis[j].c1[i];
        }
    }
}

/// Fill the (k+3) x (k+3) restriction matrix `mm2` from the basis `c1` rows,
/// with the identity block and the `mm2[k][0] = 1` entry, and invert it.
fn restriction_inverse(mm2: &mut Mat, spc: &Space, k: usize) {
    for i in 0..k + 3 {
        for j in 0..k + 3 {
            mm2[i][j] = 0.0;
        }
    }
    for j in 0..k + 3 {
        for i in 0..k {
            mm2[i][j] = spc.basis[i].c1[j];
        }
    }
    for i in k + 1..k + 3 {
        mm2[i][i] = 1.0;
    }
    mm2[k][0] = 1.0;
    luinverse(mm2, k + 3);
}

/// `betarem`: new coefficients for the model after knot `irmax` is removed.
fn betarem(spc2: &mut Space, spc: &mut Space, irmax: i32) {
    let mut k = spc2.ndim as usize;
    let mut mm2: Mat = mat(MAXKNOTS + 6, MAXKNOTS + 6);
    let mut r1 = vec![0.0f64; MAXKNOTS + 6];

    // find A, the restriction
    for i in 0..k {
        mm2[0][i] = spc2.basis[i].c1[(irmax + 2) as usize];
    }
    // solve the quadratic problem
    solver(&mm2, k, 1, &mut r1, spc2);
    // problems, a coefficient needing to be <0 is >=0
    if (spc.ilow == 1 && r1[0] >= 0.0) || (spc.iupp == 1 && r1[1] >= 0.0) {
        // only restrictions on the lower tail
        if spc.ilow == 1 && spc.iupp == 0 {
            if irmax <= 2 {
                power_values(spc2, &mut r1);
                redo1(spc2, irmax, k as i32);
                restriction_inverse(&mut mm2, spc2, k);
                for i in 0..k {
                    spc2.basis[i].beta = 0.0;
                    for j in 0..k + 3 {
                        spc2.basis[i].beta += mm2[j][i] * r1[j];
                    }
                }
            }
            for i in 0..k {
                mm2[0][i] = spc2.basis[i].c1[(irmax + 2) as usize];
            }
            for i in 0..k {
                mm2[1][i] = 0.0;
            }
            mm2[1][0] = 1.0;
            let x = spc2.basis[0].beta;
            spc2.basis[0].beta = 0.0;
            solver(&mm2, k, 2, &mut r1, spc2);
            r1[0] += x;
        }
        // only restrictions on the upper tail
        if spc.ilow == 0 && spc.iupp == 1 {
            if irmax >= k as i32 - 2 {
                power_values(spc2, &mut r1);
                let nk2 = spc2.nk;
                redo2(spc2, irmax, nk2);
                restriction_inverse(&mut mm2, spc2, k);
                for i in 0..k {
                    spc2.basis[i].beta = 0.0;
                    for j in 0..k + 3 {
                        spc2.basis[i].beta += mm2[j][i] * r1[j];
                    }
                }
                power_values(spc2, &mut r1);
            }
            for i in 0..k {
                mm2[0][i] = spc2.basis[i].c1[(irmax + 2) as usize];
            }
            for i in 0..k {
                mm2[1][i] = 0.0;
            }
            mm2[1][1] = 1.0;
            let x = spc2.basis[1].beta;
            spc2.basis[1].beta = 0.0;
            solver(&mm2, k, 2, &mut r1, spc2);
            r1[1] += x;
        }
        // restrictions on both tails
        if spc.ilow == 1 && spc.iupp == 1 {
            if irmax > k as i32 - 3 || irmax <= 2 {
                power_values(spc2, &mut r1);
                if irmax <= 2 {
                    redo1(spc2, irmax, k as i32);
                }
                if irmax > k as i32 - 3 {
                    let nk2 = spc2.nk;
                    redo2(spc2, irmax, nk2);
                }
                restriction_inverse(&mut mm2, spc2, k);
                for i in 0..k {
                    spc2.basis[i].beta = 0.0;
                    for j in 0..k + 3 {
                        spc2.basis[i].beta += mm2[j][i] * r1[j];
                    }
                }
            }
            for i in 0..k {
                mm2[0][i] = spc2.basis[i].c1[(irmax + 2) as usize];
            }
            for i in 0..k {
                mm2[1][i] = 0.0;
            }
            mm2[1][0] = 1.0;
            for i in 0..k {
                mm2[2][i] = 0.0;
            }
            mm2[2][1] = 1.0;
            let x = spc2.basis[0].beta;
            spc2.basis[0].beta = 0.0;
            let y = spc2.basis[1].beta;
            spc2.basis[1].beta = 0.0;
            solver(&mm2, k, 3, &mut r1, spc2);
            r1[0] += x;
            r1[1] += y;
        }
    }
    // record beta
    for i in 0..spc2.ndim as usize {
        spc2.basis[i].beta = r1[i];
    }
    // get it to be a power basis
    power_values(spc2, &mut r1);
    let mut i = irmax as usize;
    while i < spc2.nk as usize {
        r1[i + 2] = r1[i + 3];
        i += 1;
    }
    k -= 1;
    restriction_inverse(&mut mm2, spc, k);
    for i in 0..k {
        spc.basis[i].beta = 0.0;
        for j in 0..k + 3 {
            spc.basis[i].beta += mm2[j][i] * r1[j];
        }
    }
}

/// `redo1`: the lower-tail basis function after the knot is removed.
fn redo1(spc: &mut Space, irmax: i32, k: i32) {
    let mut i0: usize = 0;
    let mut i1: usize = 2;
    let i2: usize = 3;
    if irmax == 2 {
        i1 = 1;
    }
    if irmax == 0 {
        i0 = 1;
    }
    let t = spc.knots.clone();
    let c = &mut spc.basis[0].c1;
    for i in 0..=(k + 1) as usize {
        c[i] = 0.0;
    }
    let a = t[i2] - t[i0];
    let b = t[i2] - t[i1];
    c[i0 + 2] = 1.0;
    c[i1 + 2] = -a / b;
    c[i2 + 2] = -1.0 - c[i1 + 2];
    c[1] = -3.0 * (t[i0] * t[i0] + c[i1 + 2] * t[i1] * t[i1] + c[i2 + 2] * t[i2] * t[i2]);
    c[0] = -t[i2] * c[1] - c[i0 + 2] * a * a * a - c[i1 + 2] * b * b * b;
}

/// `redo2`: the upper-tail basis function after the knot is removed.
fn redo2(spc: &mut Space, irmax: i32, k: i32) {
    let i0: i32 = k - 4;
    let mut i1: i32 = k - 3;
    let mut i2: i32 = k - 1;
    let t = spc.knots.clone();
    let c = &mut spc.basis[1].c1;
    if irmax == k - 3 {
        i1 = k - 2;
    }
    if irmax == k - 1 {
        i2 = k - 2;
    }
    for i in 0..=(k + 1) as usize {
        c[i] = 0.0;
    }
    c[(i0 + 2) as usize] = 1.0;
    c[(i1 + 2) as usize] = (t[i0 as usize] - t[i2 as usize]) / (t[i2 as usize] - t[i1 as usize]);
    c[(i2 + 2) as usize] = -1.0 - c[(i1 + 2) as usize];
}

/// `solver`: the constrained solution of the quadratic problem with `j`
/// restrictions given by the rows of `mm2`. Writes the new coefficients to `r1`.
fn solver(mm2: &Mat, i: usize, j: usize, r1: &mut [f64], spc: &Space) {
    let mut c1: Mat = mat(MAXKNOTS + 6, MAXKNOTS + 6);
    let mut c2: Mat = mat(MAXKNOTS + 6, MAXKNOTS + 6);
    let mut c3: Mat = mat(MAXKNOTS + 6, MAXKNOTS + 6);
    if i == j {
        for k0 in 0..i {
            r1[k0] = 0.0;
        }
    }
    let mm1 = &spc.info;
    // c1 = Inv(H) t(A)   ixj
    for k0 in 0..i {
        for k1 in 0..j {
            c1[k0][k1] = 0.0;
            for k2 in 0..i {
                c1[k0][k1] += mm1[k0][k2] * mm2[k1][k2];
            }
        }
    }
    // c2 = A c1   jxj
    for k0 in 0..j {
        for k1 in 0..j {
            c2[k0][k1] = 0.0;
            for k2 in 0..i {
                c2[k0][k1] += mm2[k0][k2] * c1[k2][k1];
            }
        }
    }
    // c2 = Inv(c2)
    luinverse(&mut c2, j);
    // c3 = c1 c2   ixj
    for k0 in 0..i {
        for k1 in 0..j {
            c3[k0][k1] = 0.0;
            for k2 in 0..j {
                c3[k0][k1] += c1[k0][k2] * c2[k2][k1];
            }
        }
    }
    // c1 = c3 A   ixi
    for k0 in 0..i {
        for k1 in 0..i {
            c1[k0][k1] = 0.0;
            for k2 in 0..j {
                c1[k0][k1] += c3[k0][k2] * mm2[k2][k1];
            }
        }
    }
    // shift beta
    for k0 in 0..i {
        r1[k0] = spc.basis[k0].beta;
        for k1 in 0..i {
            r1[k0] -= c1[k0][k1] * spc.basis[k1].beta;
        }
    }
}
