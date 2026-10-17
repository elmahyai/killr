//! Lagrange step, from minqa `biglag.f`.

use crate::fortran::{get, get2, set};

#[allow(clippy::too_many_arguments)]
pub(crate) fn biglag(
    n: i32,
    npt: i32,
    xopt: &[f64],
    xpt: &[f64],
    bmat: &[f64],
    zmat: &[f64],
    idz: i32,
    ndim: i32,
    knew: i32,
    delta: f64,
    d: &mut [f64],
    alpha: &mut f64,
    hcol: &mut [f64],
    gc: &mut [f64],
    gd: &mut [f64],
    s: &mut [f64],
    w: &mut [f64],
) {
    let half = 0.5;
    let one = 1.0;
    let twopi = 8.0 * 1.0_f64.atan();
    let delsq = delta * delta;
    let nptm = npt - n - 1;

    let mut iterc = 0;
    for k in 1..=npt {
        set(hcol, k, 0.0);
    }
    for j in 1..=nptm {
        let mut temp = get2(zmat, npt, knew, j);
        if j < idz {
            temp = -temp;
        }
        for k in 1..=npt {
            set(hcol, k, get(hcol, k) + temp * get2(zmat, npt, k, j));
        }
    }
    *alpha = get(hcol, knew);

    let mut dd = 0.0;
    for i in 1..=n {
        set(d, i, get2(xpt, npt, knew, i) - get(xopt, i));
        set(gc, i, get2(bmat, ndim, knew, i));
        set(gd, i, 0.0);
        dd = dd + get(d, i) * get(d, i);
    }
    for k in 1..=npt {
        let mut temp = 0.0;
        let mut sum = 0.0;
        for j in 1..=n {
            temp = temp + get2(xpt, npt, k, j) * get(xopt, j);
            sum = sum + get2(xpt, npt, k, j) * get(d, j);
        }
        temp = get(hcol, k) * temp;
        sum = get(hcol, k) * sum;
        for i in 1..=n {
            set(gc, i, get(gc, i) + temp * get2(xpt, npt, k, i));
            set(gd, i, get(gd, i) + sum * get2(xpt, npt, k, i));
        }
    }

    let mut gg = 0.0;
    let mut sp = 0.0;
    let mut dhd = 0.0;
    for i in 1..=n {
        gg = gg + get(gc, i) * get(gc, i);
        sp = sp + get(d, i) * get(gc, i);
        dhd = dhd + get(d, i) * get(gd, i);
    }
    let mut scale = delta / dd.sqrt();
    if sp * dhd < 0.0 {
        scale = -scale;
    }
    let mut temp = 0.0;
    if sp * sp > 0.99 * dd * gg {
        temp = one;
    }
    let tau = scale * (sp.abs() + half * scale * dhd.abs());
    if gg * delsq < 0.01 * tau * tau {
        temp = one;
    }
    for i in 1..=n {
        set(d, i, scale * get(d, i));
        set(gd, i, scale * get(gd, i));
        set(s, i, get(gc, i) + temp * get(gd, i));
    }

    loop {
        iterc += 1;
        dd = 0.0;
        sp = 0.0;
        let mut ss = 0.0;
        for i in 1..=n {
            dd = dd + get(d, i) * get(d, i);
            sp = sp + get(d, i) * get(s, i);
            ss = ss + get(s, i) * get(s, i);
        }
        temp = dd * ss - sp * sp;
        if temp <= 1.0e-8 * dd * ss {
            return;
        }
        let denom = temp.sqrt();
        for i in 1..=n {
            set(s, i, (dd * get(s, i) - sp * get(d, i)) / denom);
            set(w, i, 0.0);
        }
        for k in 1..=npt {
            let mut sum = 0.0;
            for j in 1..=n {
                sum = sum + get2(xpt, npt, k, j) * get(s, j);
            }
            sum = get(hcol, k) * sum;
            for i in 1..=n {
                set(w, i, get(w, i) + sum * get2(xpt, npt, k, i));
            }
        }
        let mut cf1 = 0.0;
        let mut cf2 = 0.0;
        let mut cf3 = 0.0;
        let mut cf4 = 0.0;
        let mut cf5 = 0.0;
        for i in 1..=n {
            cf1 = cf1 + get(s, i) * get(w, i);
            cf2 = cf2 + get(d, i) * get(gc, i);
            cf3 = cf3 + get(s, i) * get(gc, i);
            cf4 = cf4 + get(d, i) * get(gd, i);
            cf5 = cf5 + get(s, i) * get(gd, i);
        }
        cf1 = half * cf1;
        cf4 = half * cf4 - cf1;

        let taubeg = cf1 + cf2 + cf4;
        let mut taumax = taubeg;
        let mut tauold = taubeg;
        let mut isave = 0;
        let iu = 49;
        temp = twopi / ((iu + 1) as f64);
        let mut tempa = 0.0;
        let mut tempb = 0.0;
        let mut tau = 0.0;
        for i in 1..=iu {
            let angle = (i as f64) * temp;
            let cth = angle.cos();
            let sth = angle.sin();
            tau = cf1 + (cf2 + cf4 * cth) * cth + (cf3 + cf5 * cth) * sth;
            if tau.abs() > taumax.abs() {
                taumax = tau;
                isave = i;
                tempa = tauold;
            } else if i == isave + 1 {
                tempb = tau;
            }
            tauold = tau;
        }
        if isave == 0 {
            tempa = tau;
        }
        if isave == iu {
            tempb = taubeg;
        }
        let mut step = 0.0;
        if tempa != tempb {
            tempa = tempa - taumax;
            tempb = tempb - taumax;
            step = half * (tempa - tempb) / (tempa + tempb);
        }
        let angle = temp * ((isave as f64) + step);
        let cth = angle.cos();
        let sth = angle.sin();
        tau = cf1 + (cf2 + cf4 * cth) * cth + (cf3 + cf5 * cth) * sth;
        for i in 1..=n {
            set(d, i, cth * get(d, i) + sth * get(s, i));
            set(gd, i, cth * get(gd, i) + sth * get(w, i));
            set(s, i, get(gc, i) + get(gd, i));
        }
        if tau.abs() <= 1.1 * taubeg.abs() {
            return;
        }
        if iterc >= n {
            return;
        }
    }
}
