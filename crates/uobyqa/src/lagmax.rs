//! `LAGMAX` from minqa `src/lagmax.f`.
//!
//! `H` is column-major with leading dimension `N`. Only the upper triangle
//! needs to be set on entry. `V` is working space. The return value is `VMAX`.

use crate::fortran::{dsign, ix, ix2};

pub(crate) fn lagmax(
    n: i32,
    g: &[f64],
    h: &mut [f64],
    rho: f64,
    d: &mut [f64],
    v: &mut [f64],
) -> f64 {
    let half: f64 = 0.5;
    let halfrt = half.sqrt();
    let one = 1.0;
    let zero = 0.0;

    let mut hmax = zero;
    let mut k = 1;
    for i in 1..=n {
        let mut sum = zero;
        for j in 1..=n {
            let hij = h[ix2(n, i, j)];
            h[ix2(n, j, i)] = hij;
            sum = sum + hij * hij;
        }
        if sum > hmax {
            hmax = sum;
            k = i;
        }
    }
    for j in 1..=n {
        v[ix(j)] = h[ix2(n, k, j)];
    }

    let mut vsq = zero;
    let mut vhv = zero;
    let mut dsq = zero;
    for i in 1..=n {
        vsq = vsq + v[ix(i)] * v[ix(i)];
        d[ix(i)] = zero;
        for j in 1..=n {
            d[ix(i)] = d[ix(i)] + h[ix2(n, i, j)] * v[ix(j)];
        }
        vhv = vhv + v[ix(i)] * d[ix(i)];
        dsq = dsq + d[ix(i)] * d[ix(i)];
    }
    if vhv * vhv <= 0.9999 * dsq * vsq {
        let mut temp = vhv / vsq;
        let mut wsq = zero;
        for i in 1..=n {
            d[ix(i)] = d[ix(i)] - temp * v[ix(i)];
            wsq = wsq + d[ix(i)] * d[ix(i)];
        }
        let mut whw = zero;
        let ratio = (wsq / vsq).sqrt();
        for i in 1..=n {
            temp = zero;
            for j in 1..=n {
                temp = temp + h[ix2(n, i, j)] * d[ix(j)];
            }
            whw = whw + temp * d[ix(i)];
            v[ix(i)] = ratio * v[ix(i)];
        }
        vhv = ratio * ratio * vhv;
        let vhw = ratio * wsq;
        temp = half * (whw - vhv);
        temp = temp + dsign((temp * temp + vhw * vhw).sqrt(), whw + vhv);
        for i in 1..=n {
            d[ix(i)] = vhw * v[ix(i)] + temp * d[ix(i)];
        }
    }

    let mut gg = zero;
    let mut gd = zero;
    let mut dd = zero;
    let mut dhd = zero;
    for i in 1..=n {
        gg = gg + g[ix(i)] * g[ix(i)];
        gd = gd + g[ix(i)] * d[ix(i)];
        dd = dd + d[ix(i)] * d[ix(i)];
        let mut sum = zero;
        for j in 1..=n {
            sum = sum + h[ix2(n, i, j)] * d[ix(j)];
        }
        dhd = dhd + sum * d[ix(i)];
    }
    let temp = gd / gg;
    let mut vv = zero;
    let scale = dsign(rho / dd.sqrt(), gd * dhd);
    for i in 1..=n {
        v[ix(i)] = d[ix(i)] - temp * g[ix(i)];
        vv = vv + v[ix(i)] * v[ix(i)];
        d[ix(i)] = scale * d[ix(i)];
    }
    let gnorm = gg.sqrt();
    if gnorm * dd <= 0.5e-2 * rho * dhd.abs() || vv / dd <= 1.0e-4 {
        return (scale * (gd + half * scale * dhd)).abs();
    }

    let mut ghg = zero;
    let mut vhg = zero;
    let mut vhv = zero;
    for i in 1..=n {
        let mut sum = zero;
        let mut sumv = zero;
        for j in 1..=n {
            sum = sum + h[ix2(n, i, j)] * g[ix(j)];
            sumv = sumv + h[ix2(n, i, j)] * v[ix(j)];
        }
        ghg = ghg + sum * g[ix(i)];
        vhg = vhg + sumv * g[ix(i)];
        vhv = vhv + sumv * v[ix(i)];
    }
    let vnorm = vv.sqrt();
    ghg = ghg / gg;
    vhg = vhg / (vnorm * gnorm);
    vhv = vhv / vv;
    let (vmu, wcos, wsin) = if vhg.abs() <= 0.01 * ghg.abs().max(vhv.abs()) {
        (ghg - vhv, one, zero)
    } else {
        let mut temp = half * (ghg - vhv);
        let vmu = temp + dsign((temp * temp + vhg * vhg).sqrt(), temp);
        temp = (vmu * vmu + vhg * vhg).sqrt();
        (vmu, vmu / temp, vhg / temp)
    };
    let tempa = wcos / gnorm;
    let tempb = wsin / vnorm;
    let tempc = wcos / vnorm;
    let tempd = wsin / gnorm;
    for i in 1..=n {
        let vi = v[ix(i)];
        let gi = g[ix(i)];
        d[ix(i)] = tempa * gi + tempb * vi;
        v[ix(i)] = tempc * vi - tempd * gi;
    }

    let dlin = wcos * gnorm / rho;
    let vlin = -wsin * gnorm / rho;
    let tempa = dlin.abs() + half * (vmu + vhv).abs();
    let tempb = vlin.abs() + half * (ghg - vmu).abs();
    let tempc = halfrt * (dlin.abs() + vlin.abs()) + 0.25 * (ghg + vhv).abs();
    let (tempd, tempv) = if tempa >= tempb && tempa >= tempc {
        (dsign(rho, dlin * (vmu + vhv)), zero)
    } else if tempb >= tempc {
        (zero, dsign(rho, vlin * (ghg - vmu)))
    } else {
        (
            dsign(halfrt * rho, dlin * (ghg + vhv)),
            dsign(halfrt * rho, vlin * (ghg + vhv)),
        )
    };
    for i in 1..=n {
        d[ix(i)] = tempd * d[ix(i)] + tempv * v[ix(i)];
    }
    rho * rho * tempa.max(tempb).max(tempc)
}
