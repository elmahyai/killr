//! Trust-region step, from minqa `trsapp.f`.

use crate::fortran::{dmin1, get, get2, set};

fn set_hd(n: i32, npt: i32, xpt: &[f64], pq: &[f64], hq: &[f64], d: &[f64], hd: &mut [f64]) {
    for i in 1..=n {
        set(hd, i, 0.0);
    }
    for k in 1..=npt {
        let mut temp = 0.0;
        for j in 1..=n {
            temp = temp + get2(xpt, npt, k, j) * get(d, j);
        }
        temp = temp * get(pq, k);
        for i in 1..=n {
            set(hd, i, get(hd, i) + temp * get2(xpt, npt, k, i));
        }
    }
    let mut ih = 0;
    for j in 1..=n {
        for i in 1..=j {
            ih += 1;
            if i < j {
                set(hd, j, get(hd, j) + get(hq, ih) * get(d, i));
            }
            set(hd, i, get(hd, i) + get(hq, ih) * get(d, j));
        }
    }
}

pub(crate) fn trsapp(
    n: i32,
    npt: i32,
    xopt: &[f64],
    xpt: &[f64],
    gq: &[f64],
    hq: &[f64],
    pq: &[f64],
    delta: f64,
    step: &mut [f64],
    d: &mut [f64],
    g: &mut [f64],
    hd: &mut [f64],
    hs: &mut [f64],
    crvmin: &mut f64,
) {
    let half = 0.5;
    let twopi = 8.0 * 1.0_f64.atan();
    let delsq = delta * delta;
    let mut iterc = 0;
    let itermax = n;
    let mut itersw = itermax;
    for i in 1..=n {
        set(d, i, get(xopt, i));
    }

    let mut qred = 0.0;
    let mut dd = 0.0;
    let mut ds = 0.0;
    let mut ss = 0.0;
    let mut gg = 0.0;
    let mut ggbeg = 0.0;
    let mut bstep = 0.0;
    let mut qadd;
    let mut label = 170;
    loop {
        match label {
            20 => {
                qred = 0.0;
                dd = 0.0;
                for i in 1..=n {
                    set(step, i, 0.0);
                    set(hs, i, 0.0);
                    set(g, i, get(gq, i) + get(hd, i));
                    set(d, i, -get(g, i));
                    dd = dd + get(d, i) * get(d, i);
                }
                *crvmin = 0.0;
                if dd == 0.0 {
                    return;
                }
                ds = 0.0;
                ss = 0.0;
                gg = dd;
                ggbeg = gg;
                label = 40;
            }
            40 => {
                iterc += 1;
                let temp = delsq - ss;
                bstep = temp / (ds + (ds * ds + dd * temp).sqrt());
                label = 170;
            }
            50 => {
                let mut dhd = 0.0;
                for j in 1..=n {
                    dhd = dhd + get(d, j) * get(hd, j);
                }
                let mut alpha = bstep;
                if dhd > 0.0 {
                    let temp = dhd / dd;
                    if iterc == 1 {
                        *crvmin = temp;
                    }
                    *crvmin = dmin1(*crvmin, temp);
                    alpha = dmin1(alpha, gg / dhd);
                }
                qadd = alpha * (gg - half * alpha * dhd);
                qred = qred + qadd;
                let ggsav = gg;
                gg = 0.0;
                for i in 1..=n {
                    set(step, i, get(step, i) + alpha * get(d, i));
                    set(hs, i, get(hs, i) + alpha * get(hd, i));
                    let gi = get(g, i) + get(hs, i);
                    gg = gg + gi * gi;
                }
                if alpha < bstep {
                    if qadd <= 0.01 * qred {
                        return;
                    }
                    if gg <= 1.0e-4 * ggbeg {
                        return;
                    }
                    if iterc == itermax {
                        return;
                    }
                    let temp = gg / ggsav;
                    dd = 0.0;
                    ds = 0.0;
                    ss = 0.0;
                    for i in 1..=n {
                        set(d, i, temp * get(d, i) - get(g, i) - get(hs, i));
                        dd = dd + get(d, i) * get(d, i);
                        ds = ds + get(d, i) * get(step, i);
                        ss = ss + get(step, i) * get(step, i);
                    }
                    if ds <= 0.0 {
                        return;
                    }
                    if ss < delsq {
                        label = 40;
                        continue;
                    }
                }
                *crvmin = 0.0;
                itersw = iterc;
                label = 90;
            }
            90 => {
                if gg <= 1.0e-4 * ggbeg {
                    return;
                }
                let mut sg = 0.0;
                let mut shs = 0.0;
                for i in 1..=n {
                    sg = sg + get(step, i) * get(g, i);
                    shs = shs + get(step, i) * get(hs, i);
                }
                let sgk = sg + shs;
                let angtest = sgk / (gg * delsq).sqrt();
                if angtest <= -0.99 {
                    return;
                }
                iterc += 1;
                let temp = (delsq * gg - sgk * sgk).sqrt();
                let tempa = delsq / temp;
                let tempb = sgk / temp;
                for i in 1..=n {
                    set(
                        d,
                        i,
                        tempa * (get(g, i) + get(hs, i)) - tempb * get(step, i),
                    );
                }
                label = 170;
                // Carry sg, shs into label 120 through the outer variables.
                // They are recomputed there from the arrays, so nothing else is kept.
                let _ = (sg, shs);
            }
            120 => {
                let mut sg = 0.0;
                let mut shs = 0.0;
                for i in 1..=n {
                    sg = sg + get(step, i) * get(g, i);
                    shs = shs + get(step, i) * get(hs, i);
                }
                let mut dg = 0.0;
                let mut dhd = 0.0;
                let mut dhs = 0.0;
                for i in 1..=n {
                    dg = dg + get(d, i) * get(g, i);
                    dhd = dhd + get(hd, i) * get(d, i);
                    dhs = dhs + get(hd, i) * get(step, i);
                }
                let cf = half * (shs - dhd);
                let qbeg = sg + cf;
                let mut qsav = qbeg;
                let mut qmin = qbeg;
                let mut isave = 0;
                let iu = 49;
                let temp = twopi / ((iu + 1) as f64);
                let mut qnew = 0.0;
                let mut tempa = 0.0;
                let mut tempb = 0.0;
                for i in 1..=iu {
                    let angle = (i as f64) * temp;
                    let cth = angle.cos();
                    let sth = angle.sin();
                    qnew = (sg + cf * cth) * cth + (dg + dhs * cth) * sth;
                    if qnew < qmin {
                        qmin = qnew;
                        isave = i;
                        tempa = qsav;
                    } else if i == isave + 1 {
                        tempb = qnew;
                    }
                    qsav = qnew;
                }
                if isave == 0 {
                    tempa = qnew;
                }
                if isave == iu {
                    tempb = qbeg;
                }
                let mut angle = 0.0;
                if tempa != tempb {
                    tempa = tempa - qmin;
                    tempb = tempb - qmin;
                    angle = half * (tempa - tempb) / (tempa + tempb);
                }
                angle = temp * ((isave as f64) + angle);
                let cth = angle.cos();
                let sth = angle.sin();
                let reduc = qbeg - (sg + cf * cth) * cth - (dg + dhs * cth) * sth;
                gg = 0.0;
                for i in 1..=n {
                    set(step, i, cth * get(step, i) + sth * get(d, i));
                    set(hs, i, cth * get(hs, i) + sth * get(hd, i));
                    let gi = get(g, i) + get(hs, i);
                    gg = gg + gi * gi;
                }
                qred = qred + reduc;
                let ratio = reduc / qred;
                if iterc < itermax && ratio > 0.01 {
                    label = 90;
                } else {
                    return;
                }
            }
            170 => {
                set_hd(n, npt, xpt, pq, hq, d, hd);
                if iterc == 0 {
                    label = 20;
                } else if iterc <= itersw {
                    label = 50;
                } else {
                    label = 120;
                }
            }
            _ => return,
        }
    }
}
