//! `RESCUE` from minqa `rescue.f`.

use crate::arr::{dmax1, dmin1, g, g2, s, s2};
use crate::update::update;

pub fn rescue(
    n: i32,
    npt: i32,
    xl: &[f64],
    xu: &[f64],
    _iprint: i32,
    maxfun: i32,
    xbase: &mut [f64],
    xpt: &mut [f64],
    fval: &mut [f64],
    xopt: &mut [f64],
    gopt: &mut [f64],
    hq: &mut [f64],
    pq: &mut [f64],
    bmat: &mut [f64],
    zmat: &mut [f64],
    ndim: i32,
    sl: &mut [f64],
    su: &mut [f64],
    nf: &mut i32,
    delta: f64,
    kopt: &mut i32,
    vlag: &mut [f64],
    ptsaux: &mut [f64],
    ptsid: &mut [f64],
    w: &mut [f64],
    calfun: &mut dyn FnMut(&[f64]) -> f64,
) {
    let half = 0.5;
    let one = 1.0;
    let zero = 0.0;
    let np = n + 1;
    let sfrac = half / (np as f64);
    let nptm = npt - np;

    let mut sumpq = zero;
    let mut winc = zero;
    for k in 1..=npt {
        let mut distsq = zero;
        for j in 1..=n {
            s2(xpt, npt, k, j, g2(xpt, npt, k, j) - g(xopt, j));
            distsq = distsq + g2(xpt, npt, k, j) * g2(xpt, npt, k, j);
        }
        sumpq = sumpq + g(pq, k);
        s(w, ndim + k, distsq);
        winc = dmax1(winc, distsq);
        for j in 1..=nptm {
            s2(zmat, npt, k, j, zero);
        }
    }

    let mut ih = 0;
    for j in 1..=n {
        s(w, j, half * sumpq * g(xopt, j));
        for k in 1..=npt {
            s(w, j, g(w, j) + g(pq, k) * g2(xpt, npt, k, j));
        }
        for i in 1..=j {
            ih += 1;
            s(
                hq,
                ih,
                (g(hq, ih) + g(w, i) * g(xopt, j)) + g(w, j) * g(xopt, i),
            );
        }
    }

    for j in 1..=n {
        s(xbase, j, g(xbase, j) + g(xopt, j));
        s(sl, j, g(sl, j) - g(xopt, j));
        s(su, j, g(su, j) - g(xopt, j));
        s(xopt, j, zero);
        s2(ptsaux, 2, 1, j, dmin1(delta, g(su, j)));
        s2(ptsaux, 2, 2, j, dmax1(-delta, g(sl, j)));
        if g2(ptsaux, 2, 1, j) + g2(ptsaux, 2, 2, j) < zero {
            let temp = g2(ptsaux, 2, 1, j);
            s2(ptsaux, 2, 1, j, g2(ptsaux, 2, 2, j));
            s2(ptsaux, 2, 2, j, temp);
        }
        if g2(ptsaux, 2, 2, j).abs() < half * g2(ptsaux, 2, 1, j).abs() {
            s2(ptsaux, 2, 2, j, half * g2(ptsaux, 2, 1, j));
        }
        for i in 1..=ndim {
            s2(bmat, ndim, i, j, zero);
        }
    }
    let fbase = g(fval, *kopt);

    s(ptsid, 1, sfrac);
    for j in 1..=n {
        let jp = j + 1;
        let jpn = jp + n;
        s(ptsid, jp, (j as f64) + sfrac);
        if jpn <= npt {
            s(ptsid, jpn, (j as f64) / (np as f64) + sfrac);
            let temp = one / (g2(ptsaux, 2, 1, j) - g2(ptsaux, 2, 2, j));
            s2(
                bmat,
                ndim,
                jp,
                j,
                -temp + one / g2(ptsaux, 2, 1, j),
            );
            s2(
                bmat,
                ndim,
                jpn,
                j,
                temp + one / g2(ptsaux, 2, 2, j),
            );
            s2(
                bmat,
                ndim,
                1,
                j,
                -g2(bmat, ndim, jp, j) - g2(bmat, ndim, jpn, j),
            );
            s2(
                zmat,
                npt,
                1,
                j,
                2.0_f64.sqrt() / (g2(ptsaux, 2, 1, j) * g2(ptsaux, 2, 2, j)).abs(),
            );
            s2(
                zmat,
                npt,
                jp,
                j,
                g2(zmat, npt, 1, j) * g2(ptsaux, 2, 2, j) * temp,
            );
            s2(
                zmat,
                npt,
                jpn,
                j,
                -g2(zmat, npt, 1, j) * g2(ptsaux, 2, 1, j) * temp,
            );
        } else {
            s2(bmat, ndim, 1, j, -one / g2(ptsaux, 2, 1, j));
            s2(bmat, ndim, jp, j, one / g2(ptsaux, 2, 1, j));
            s2(
                bmat,
                ndim,
                j + npt,
                j,
                -half * (g2(ptsaux, 2, 1, j) * g2(ptsaux, 2, 1, j)),
            );
        }
    }

    if npt >= n + np {
        for k in (2 * np)..=npt {
            let iw = (((k - np) as f64 - half) / (n as f64)) as i32;
            let ip = k - np - iw * n;
            let mut iq = ip + iw;
            if iq > n {
                iq -= n;
            }
            s(
                ptsid,
                k,
                (ip as f64) + (iq as f64) / (np as f64) + sfrac,
            );
            let temp = one / (g2(ptsaux, 2, 1, ip) * g2(ptsaux, 2, 1, iq));
            s2(zmat, npt, 1, k - np, temp);
            s2(zmat, npt, ip + 1, k - np, -temp);
            s2(zmat, npt, iq + 1, k - np, -temp);
            s2(zmat, npt, k, k - np, temp);
        }
    }

    let mut nrem = npt;
    let mut kold = 1;
    let mut knew = *kopt;
    let mut beta = zero;
    let mut denom = zero;
    let mut label = 80i32;

    loop {
        if label == 80 {
            for j in 1..=n {
                let temp = g2(bmat, ndim, kold, j);
                s2(bmat, ndim, kold, j, g2(bmat, ndim, knew, j));
                s2(bmat, ndim, knew, j, temp);
            }
            for j in 1..=nptm {
                let temp = g2(zmat, npt, kold, j);
                s2(zmat, npt, kold, j, g2(zmat, npt, knew, j));
                s2(zmat, npt, knew, j, temp);
            }
            s(ptsid, kold, g(ptsid, knew));
            s(ptsid, knew, zero);
            s(w, ndim + knew, zero);
            nrem -= 1;
            if knew != *kopt {
                let temp = g(vlag, kold);
                s(vlag, kold, g(vlag, knew));
                s(vlag, knew, temp);
                update(n, npt, bmat, zmat, ndim, vlag, beta, denom, knew, w);
                if nrem == 0 {
                    label = 350;
                } else {
                    for k in 1..=npt {
                        s(w, ndim + k, g(w, ndim + k).abs());
                    }
                    label = 120;
                }
            } else {
                label = 120;
            }
        }
        if label == 120 {
            let mut dsqmin = zero;
            for k in 1..=npt {
                if g(w, ndim + k) > zero && (dsqmin == zero || g(w, ndim + k) < dsqmin) {
                    knew = k;
                    dsqmin = g(w, ndim + k);
                }
            }
            if dsqmin == zero {
                label = 260;
            } else {
                for j in 1..=n {
                    s(w, npt + j, g2(xpt, npt, knew, j));
                }
                for k in 1..=npt {
                    let mut sum = zero;
                    if k == *kopt {
                    } else if g(ptsid, k) == zero {
                        for j in 1..=n {
                            sum = sum + g(w, npt + j) * g2(xpt, npt, k, j);
                        }
                    } else {
                        let ip = g(ptsid, k) as i32;
                        if ip > 0 {
                            sum = g(w, npt + ip) * g2(ptsaux, 2, 1, ip);
                        }
                        let iq = ((np as f64) * g(ptsid, k) - (ip * np) as f64) as i32;
                        if iq > 0 {
                            let mut iw = 1;
                            if ip == 0 {
                                iw = 2;
                            }
                            sum = sum + g(w, npt + iq) * g2(ptsaux, 2, iw, iq);
                        }
                    }
                    s(w, k, (half * sum) * sum);
                }

                for k in 1..=npt {
                    let mut sum = zero;
                    for j in 1..=n {
                        sum = sum + g2(bmat, ndim, k, j) * g(w, npt + j);
                    }
                    s(vlag, k, sum);
                }
                beta = zero;
                for j in 1..=nptm {
                    let mut sum = zero;
                    for k in 1..=npt {
                        sum = sum + g2(zmat, npt, k, j) * g(w, k);
                    }
                    beta = beta - sum * sum;
                    for k in 1..=npt {
                        s(vlag, k, g(vlag, k) + sum * g2(zmat, npt, k, j));
                    }
                }
                let mut bsum = zero;
                let mut distsq = zero;
                for j in 1..=n {
                    let mut sum = zero;
                    for k in 1..=npt {
                        sum = sum + g2(bmat, ndim, k, j) * g(w, k);
                    }
                    let jp = j + npt;
                    bsum = bsum + sum * g(w, jp);
                    for ip in (npt + 1)..=ndim {
                        sum = sum + g2(bmat, ndim, ip, j) * g(w, ip);
                    }
                    bsum = bsum + sum * g(w, jp);
                    s(vlag, jp, sum);
                    distsq = distsq + g2(xpt, npt, knew, j) * g2(xpt, npt, knew, j);
                }
                beta = ((half * distsq) * distsq + beta) - bsum;
                s(vlag, *kopt, g(vlag, *kopt) + one);

                denom = zero;
                let mut vlmssq = zero;
                for k in 1..=npt {
                    if g(ptsid, k) != zero {
                        let mut hdiag = zero;
                        for j in 1..=nptm {
                            hdiag = hdiag + g2(zmat, npt, k, j) * g2(zmat, npt, k, j);
                        }
                        let den = beta * hdiag + g(vlag, k) * g(vlag, k);
                        if den > denom {
                            kold = k;
                            denom = den;
                        }
                    }
                    vlmssq = dmax1(vlmssq, g(vlag, k) * g(vlag, k));
                }
                if denom <= 1.0e-2 * vlmssq {
                    s(w, ndim + knew, -g(w, ndim + knew) - winc);
                    label = 120;
                    continue;
                }
                label = 80;
                continue;
            }
        }
        if label == 260 {
            let mut stop = false;
            for kpt in 1..=npt {
                if g(ptsid, kpt) == zero {
                    continue;
                }
                if *nf >= maxfun {
                    *nf = -1;
                    stop = true;
                    break;
                }
                let mut ih = 0;
                for j in 1..=n {
                    s(w, j, g2(xpt, npt, kpt, j));
                    s2(xpt, npt, kpt, j, zero);
                    let temp = g(pq, kpt) * g(w, j);
                    for i in 1..=j {
                        ih += 1;
                        s(hq, ih, g(hq, ih) + temp * g(w, i));
                    }
                }
                s(pq, kpt, zero);
                let ip = g(ptsid, kpt) as i32;
                let iq = ((np as f64) * g(ptsid, kpt) - (ip * np) as f64) as i32;
                let mut xp = zero;
                let mut xq = zero;
                if ip > 0 {
                    xp = g2(ptsaux, 2, 1, ip);
                    s2(xpt, npt, kpt, ip, xp);
                }
                if iq > 0 {
                    xq = g2(ptsaux, 2, 1, iq);
                    if ip == 0 {
                        xq = g2(ptsaux, 2, 2, iq);
                    }
                    s2(xpt, npt, kpt, iq, xq);
                }

                let mut vquad = fbase;
                let mut ihp = 0;
                if ip > 0 {
                    ihp = (ip + ip * ip) / 2;
                    vquad = vquad + xp * (g(gopt, ip) + (half * xp) * g(hq, ihp));
                }
                if iq > 0 {
                    let ihq = (iq + iq * iq) / 2;
                    vquad = vquad + xq * (g(gopt, iq) + (half * xq) * g(hq, ihq));
                    if ip > 0 {
                        let iw = ihp.max(ihq) - (ip - iq).abs();
                        vquad = vquad + (xp * xq) * g(hq, iw);
                    }
                }
                for k in 1..=npt {
                    let mut temp = zero;
                    if ip > 0 {
                        temp = temp + xp * g2(xpt, npt, k, ip);
                    }
                    if iq > 0 {
                        temp = temp + xq * g2(xpt, npt, k, iq);
                    }
                    vquad = vquad + ((half * g(pq, k)) * temp) * temp;
                }

                for i in 1..=n {
                    let mut wi = dmin1(
                        dmax1(g(xl, i), g(xbase, i) + g2(xpt, npt, kpt, i)),
                        g(xu, i),
                    );
                    if g2(xpt, npt, kpt, i) == g(sl, i) {
                        wi = g(xl, i);
                    }
                    if g2(xpt, npt, kpt, i) == g(su, i) {
                        wi = g(xu, i);
                    }
                    s(w, i, wi);
                }
                *nf += 1;
                let point: Vec<f64> = (1..=n).map(|i| g(w, i)).collect();
                let f = calfun(&point);
                s(fval, kpt, f);
                if f < g(fval, *kopt) {
                    *kopt = kpt;
                }
                let diff = f - vquad;

                for i in 1..=n {
                    s(gopt, i, g(gopt, i) + diff * g2(bmat, ndim, kpt, i));
                }
                for k in 1..=npt {
                    let mut sum = zero;
                    for j in 1..=nptm {
                        sum = sum + g2(zmat, npt, k, j) * g2(zmat, npt, kpt, j);
                    }
                    let temp = diff * sum;
                    if g(ptsid, k) == zero {
                        s(pq, k, g(pq, k) + temp);
                    } else {
                        let ip = g(ptsid, k) as i32;
                        let iq = ((np as f64) * g(ptsid, k) - (ip * np) as f64) as i32;
                        let ihq = (iq * iq + iq) / 2;
                        if ip == 0 {
                            let p2 = g2(ptsaux, 2, 2, iq);
                            s(hq, ihq, g(hq, ihq) + temp * (p2 * p2));
                        } else {
                            let ihp = (ip * ip + ip) / 2;
                            let p1 = g2(ptsaux, 2, 1, ip);
                            s(hq, ihp, g(hq, ihp) + temp * (p1 * p1));
                            if iq > 0 {
                                let q1 = g2(ptsaux, 2, 1, iq);
                                s(hq, ihq, g(hq, ihq) + temp * (q1 * q1));
                                let iw = ihp.max(ihq) - (iq - ip).abs();
                                s(hq, iw, g(hq, iw) + temp * p1 * q1);
                            }
                        }
                    }
                }
                s(ptsid, kpt, zero);
            }
            let _ = stop;
            break;
        }
        if label == 350 {
            break;
        }
    }
}
