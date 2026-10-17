//! `TRSTEP` from minqa `src/trstep.f`.
//!
//! `H` is column-major with leading dimension `N`. The lower triangle is
//! overwritten with Householder vectors. The return value is `EVALUE`.

use crate::fortran::{dsign, ix, ix2};

pub(crate) fn trstep(
    n: i32,
    g: &[f64],
    h: &mut [f64],
    delta: f64,
    tol: f64,
    d: &mut [f64],
    gg: &mut [f64],
    td: &mut [f64],
    tn: &mut [f64],
    w: &mut [f64],
    piv: &mut [f64],
    z: &mut [f64],
) -> f64 {
    let one = 1.0;
    let two = 2.0;
    let zero = 0.0;
    let delsq = delta * delta;
    let mut evalue = zero;
    let nm = n - 1;

    for i in 1..=n {
        d[ix(i)] = zero;
        td[ix(i)] = h[ix2(n, i, i)];
        for j in 1..=i {
            h[ix2(n, i, j)] = h[ix2(n, j, i)];
        }
    }

    for k in 1..=nm {
        let kp = k + 1;
        let mut sum = zero;
        if kp < n {
            let kpp = kp + 1;
            for i in kpp..=n {
                let hik = h[ix2(n, i, k)];
                sum = sum + hik * hik;
            }
        }
        if sum == zero {
            tn[ix(k)] = h[ix2(n, kp, k)];
            h[ix2(n, kp, k)] = zero;
        } else {
            let mut temp = h[ix2(n, kp, k)];
            tn[ix(k)] = dsign((sum + temp * temp).sqrt(), temp);
            h[ix2(n, kp, k)] = -sum / (temp + tn[ix(k)]);
            temp = (two / (sum + h[ix2(n, kp, k)] * h[ix2(n, kp, k)])).sqrt();
            for i in kp..=n {
                w[ix(i)] = temp * h[ix2(n, i, k)];
                h[ix2(n, i, k)] = w[ix(i)];
                z[ix(i)] = td[ix(i)] * w[ix(i)];
            }
            let mut wz = zero;
            for j in kp..=nm {
                let jp = j + 1;
                for i in jp..=n {
                    z[ix(i)] = z[ix(i)] + h[ix2(n, i, j)] * w[ix(j)];
                    z[ix(j)] = z[ix(j)] + h[ix2(n, i, j)] * w[ix(i)];
                }
                wz = wz + w[ix(j)] * z[ix(j)];
            }
            wz = wz + w[ix(n)] * z[ix(n)];
            for j in kp..=n {
                td[ix(j)] = td[ix(j)] + w[ix(j)] * (wz * w[ix(j)] - two * z[ix(j)]);
                if j < n {
                    let jp = j + 1;
                    for i in jp..=n {
                        h[ix2(n, i, j)] = h[ix2(n, i, j)]
                            - w[ix(i)] * z[ix(j)]
                            - w[ix(j)] * (z[ix(i)] - wz * w[ix(i)]);
                    }
                }
            }
        }
    }

    let mut gsq = zero;
    for i in 1..=n {
        gg[ix(i)] = g[ix(i)];
        gsq = gsq + g[ix(i)] * g[ix(i)];
    }
    let gnorm = gsq.sqrt();
    for k in 1..=nm {
        let kp = k + 1;
        let mut sum = zero;
        for i in kp..=n {
            sum = sum + gg[ix(i)] * h[ix2(n, i, k)];
        }
        for i in kp..=n {
            gg[ix(i)] = gg[ix(i)] - sum * h[ix2(n, i, k)];
        }
    }

    let mut hnorm = td[ix(1)].abs() + tn[ix(1)].abs();
    let mut tdmin = td[ix(1)];
    tn[ix(n)] = zero;
    for i in 2..=n {
        let temp = tn[ix(i - 1)].abs() + td[ix(i)].abs() + tn[ix(i)].abs();
        hnorm = hnorm.max(temp);
        tdmin = tdmin.min(td[ix(i)]);
    }
    if hnorm == zero {
        if gnorm == zero {
            return evalue;
        }
        let scale = delta / gnorm;
        for i in 1..=n {
            d[ix(i)] = -scale * gg[ix(i)];
        }
        inverse_householder(n, h, d);
        return evalue;
    }

    let mut parl = zero.max(-tdmin).max(gnorm / delta - hnorm);
    let mut parlest = parl;
    let mut par = parl;
    let mut paru = zero;
    let mut paruest = zero;
    let mut posdef = zero;
    let mut iterc = 0;
    let mut phil = zero;
    let mut phiu = zero;
    let mut ksav;
    let mut k;
    // `DSQ` is the sum of squares built in the curvature direction, not a
    // fresh sum over every component of `D` (higher components can be stale).
    let mut dsq = zero;

    loop {
        iterc += 1;
        ksav = 0;
        piv[ix(1)] = td[ix(1)] + par;
        k = 1;
        let mut curvature = false;
        loop {
            if piv[ix(k)] > zero {
                piv[ix(k + 1)] =
                    td[ix(k + 1)] + par - (tn[ix(k)] * tn[ix(k)]) / piv[ix(k)];
            } else if piv[ix(k)] < zero || tn[ix(k)] != zero {
                curvature = true;
                break;
            } else {
                ksav = k;
                piv[ix(k + 1)] = td[ix(k + 1)] + par;
            }
            k += 1;
            if k < n {
                continue;
            }
            break;
        }
        if !curvature {
            if piv[ix(k)] < zero {
                curvature = true;
            } else if piv[ix(k)] == zero {
                ksav = k;
            }
        }

        if !curvature && ksav == 0 && gsq > zero {
            // Label 230: positive definite solve.
        } else if !curvature && gsq == zero {
            if par == zero {
                inverse_householder(n, h, d);
                return evalue;
            }
            paru = par;
            paruest = par;
            if ksav == 0 {
                if accept_curvature(n, gg, d, delta, tol, gsq, paruest, parlest, dsq) {
                    inverse_householder(n, h, d);
                    return evalue;
                }
                par = next_par(gnorm, delta, parl, paru, parlest, paruest);
                continue;
            }
            k = ksav;
            dsq = curvature_direction(td, tn, piv, d, par, k, &mut parlest);
            parl = par;
            if accept_curvature(n, gg, d, delta, tol, gsq, paruest, parlest, dsq) {
                inverse_householder(n, h, d);
                return evalue;
            }
            par = next_par(gnorm, delta, parl, paru, parlest, paruest);
            continue;
        } else if curvature || ksav != 0 {
            if !curvature {
                k = ksav;
            }
            dsq = curvature_direction(td, tn, piv, d, par, k, &mut parlest);
            parl = par;
            if accept_curvature(n, gg, d, delta, tol, gsq, paruest, parlest, dsq) {
                inverse_householder(n, h, d);
                return evalue;
            }
            par = next_par(gnorm, delta, parl, paru, parlest, paruest);
            continue;
        }

        w[ix(1)] = -gg[ix(1)] / piv[ix(1)];
        for i in 2..=n {
            w[ix(i)] = (-gg[ix(i)] - tn[ix(i - 1)] * w[ix(i - 1)]) / piv[ix(i)];
        }
        d[ix(n)] = w[ix(n)];
        let mut i = nm;
        while i >= 1 {
            d[ix(i)] = w[ix(i)] - tn[ix(i)] * d[ix(i + 1)] / piv[ix(i)];
            i -= 1;
        }

        dsq = zero;
        let mut wsq = zero;
        for i in 1..=n {
            dsq = dsq + d[ix(i)] * d[ix(i)];
            wsq = wsq + piv[ix(i)] * (w[ix(i)] * w[ix(i)]);
        }
        if par == zero && dsq <= delsq {
            evalue = least_eigenvalue(n, td, tn, piv);
            inverse_householder(n, h, d);
            return evalue;
        }

        let dnorm = dsq.sqrt();
        let phi = one / dnorm - one / delta;
        let temp = tol * (one + par * dsq / wsq) - dsq * phi * phi;
        if temp >= zero {
            let scale = delta / dnorm;
            for i in 1..=n {
                d[ix(i)] = scale * d[ix(i)];
            }
            inverse_householder(n, h, d);
            return evalue;
        }
        if iterc >= 2 && par <= parl {
            inverse_householder(n, h, d);
            return evalue;
        }
        if paru > zero && par >= paru {
            inverse_householder(n, h, d);
            return evalue;
        }

        if phi < zero {
            parlest = par;
            if posdef == one {
                if phi <= phil {
                    inverse_householder(n, h, d);
                    return evalue;
                }
                let slope = (phi - phil) / (par - parl);
                parlest = par - phi / slope;
            }
            let mut slope = one / gnorm;
            if paru > zero {
                slope = (phiu - phi) / (paru - par);
            }
            let mut temp = par - phi / slope;
            if paruest > zero {
                temp = temp.min(paruest);
            }
            paruest = temp;
            posdef = one;
            parl = par;
            phil = phi;
            par = next_par(gnorm, delta, parl, paru, parlest, paruest);
            continue;
        }

        if posdef == zero {
            w[ix(1)] = one / piv[ix(1)];
            for i in 2..=n {
                let temp = -tn[ix(i - 1)] * w[ix(i - 1)];
                w[ix(i)] = (dsign(one, temp) + temp) / piv[ix(i)];
            }
            z[ix(n)] = w[ix(n)];
            let mut i = nm;
            while i >= 1 {
                z[ix(i)] = w[ix(i)] - tn[ix(i)] * z[ix(i + 1)] / piv[ix(i)];
                i -= 1;
            }
            let mut wwsq = zero;
            let mut zsq = zero;
            let mut dtz = zero;
            for i in 1..=n {
                wwsq = wwsq + piv[ix(i)] * (w[ix(i)] * w[ix(i)]);
                zsq = zsq + z[ix(i)] * z[ix(i)];
                dtz = dtz + d[ix(i)] * z[ix(i)];
            }
            let tempa = (delsq - dsq).abs();
            let tempb = (dtz * dtz + tempa * zsq).sqrt();
            let gam = tempa / (dsign(tempb, dtz) + dtz);
            let temp = tol * (wsq + par * delsq) - gam * gam * wwsq;
            if temp >= zero {
                for i in 1..=n {
                    d[ix(i)] = d[ix(i)] + gam * z[ix(i)];
                }
                inverse_householder(n, h, d);
                return evalue;
            }
            parlest = parlest.max(par - wwsq / zsq);
        }

        let mut slope = one / gnorm;
        if paru > zero {
            if phi >= phiu {
                inverse_householder(n, h, d);
                return evalue;
            }
            slope = (phiu - phi) / (paru - par);
        }
        parlest = parlest.max(par - phi / slope);
        paruest = par;
        if posdef == one {
            slope = (phi - phil) / (par - parl);
            paruest = par - phi / slope;
        }
        paru = par;
        phiu = phi;
        par = next_par(gnorm, delta, parl, paru, parlest, paruest);
    }
}

fn curvature_direction(
    td: &[f64],
    tn: &[f64],
    piv: &[f64],
    d: &mut [f64],
    par: f64,
    mut k: i32,
    parlest: &mut f64,
) -> f64 {
    let one = 1.0;
    let two = 2.0;
    let zero = 0.0;
    d[ix(k)] = one;
    let (mut dsq, dhd) = if tn[ix(k)].abs() <= piv[ix(k)].abs() {
        (one, piv[ix(k)])
    } else {
        let temp = td[ix(k + 1)] + par;
        let (dhd, dnext) = if temp <= piv[ix(k)].abs() {
            (
                piv[ix(k)] + temp - two * tn[ix(k)].abs(),
                dsign(one, -tn[ix(k)]),
            )
        } else {
            let dnext = -tn[ix(k)] / temp;
            (piv[ix(k)] + tn[ix(k)] * dnext, dnext)
        };
        d[ix(k + 1)] = dnext;
        (one + dnext * dnext, dhd)
    };
    loop {
        if k <= 1 {
            break;
        }
        k -= 1;
        if tn[ix(k)] != zero {
            d[ix(k)] = -tn[ix(k)] * d[ix(k + 1)] / piv[ix(k)];
            dsq = dsq + d[ix(k)] * d[ix(k)];
            continue;
        }
        for i in 1..=k {
            d[ix(i)] = zero;
        }
        break;
    }
    *parlest = par - dhd / dsq;
    dsq
}

fn accept_curvature(
    n: i32,
    gg: &[f64],
    d: &mut [f64],
    delta: f64,
    tol: f64,
    gsq: f64,
    paruest: f64,
    parlest: f64,
    dsq: f64,
) -> bool {
    let one = 1.0;
    let zero = 0.0;
    let mut temp = paruest;
    if gsq == zero {
        temp = temp * (one - tol);
    }
    if paruest > zero && parlest >= temp {
        let mut dtg = zero;
        for i in 1..=n {
            dtg = dtg + d[ix(i)] * gg[ix(i)];
        }
        let scale = -dsign(delta / dsq.sqrt(), dtg);
        for i in 1..=n {
            d[ix(i)] = scale * d[ix(i)];
        }
        return true;
    }
    false
}

fn next_par(gnorm: f64, delta: f64, parl: f64, paru: f64, parlest: f64, paruest: f64) -> f64 {
    let mut par = if paru == 0.0 {
        2.0 * parlest + gnorm / delta
    } else {
        (0.5 * (parl + paru)).max(parlest)
    };
    if paruest > 0.0 {
        par = par.min(paruest);
    }
    par
}

fn least_eigenvalue(n: i32, td: &[f64], tn: &[f64], piv: &mut [f64]) -> f64 {
    let zero = 0.0;
    let mut shfmin = zero;
    let mut pivot = td[ix(1)];
    let mut shfmax = pivot;
    for k in 2..=n {
        pivot = td[ix(k)] - (tn[ix(k - 1)] * tn[ix(k - 1)]) / pivot;
        shfmax = shfmax.min(pivot);
    }
    let mut ksave = 0;
    let mut pivksv = zero;
    loop {
        let shift = 0.5 * (shfmin + shfmax);
        let mut k = 1;
        let mut temp = td[ix(1)] - shift;
        let mut nonpositive = false;
        loop {
            if temp > zero {
                piv[ix(k)] = temp;
                if k < n {
                    temp = td[ix(k + 1)] - shift - (tn[ix(k)] * tn[ix(k)]) / temp;
                    k += 1;
                    continue;
                }
                shfmin = shift;
                break;
            }
            nonpositive = true;
            break;
        }
        if nonpositive {
            if k < ksave || (k == ksave && pivksv == zero) {
                break;
            }
            if k == ksave {
                if piv[ix(k)] - temp < temp - pivksv {
                    pivksv = temp;
                    shfmax = shift;
                } else {
                    pivksv = zero;
                    shfmax = (shift * piv[ix(k)] - shfmin * temp) / (piv[ix(k)] - temp);
                }
            } else {
                ksave = k;
                pivksv = temp;
                shfmax = shift;
            }
        }
        if shfmin <= 0.99 * shfmax {
            continue;
        }
        break;
    }
    shfmin
}

fn inverse_householder(n: i32, h: &[f64], d: &mut [f64]) {
    let mut k = n - 1;
    while k >= 1 {
        let kp = k + 1;
        let mut sum = 0.0;
        for i in kp..=n {
            sum = sum + d[ix(i)] * h[ix2(n, i, k)];
        }
        for i in kp..=n {
            d[ix(i)] = d[ix(i)] - sum * h[ix2(n, i, k)];
        }
        k -= 1;
    }
}
