//! `TRSBOX` from minqa `trsbox.f`.

use crate::arr::{dmax1, dmin1, g, g2, s};

fn ggmult(n: i32, npt: i32, xpt: &[f64], hq: &[f64], pq: &[f64], svec: &[f64], hs: &mut [f64]) {
    let zero = 0.0;
    let mut ih = 0;
    for j in 1..=n {
        s(hs, j, zero);
        for i in 1..=j {
            ih += 1;
            if i < j {
                s(hs, j, g(hs, j) + g(hq, ih) * g(svec, i));
            }
            s(hs, i, g(hs, i) + g(hq, ih) * g(svec, j));
        }
    }
    for k in 1..=npt {
        if g(pq, k) != zero {
            let mut temp = zero;
            for j in 1..=n {
                temp = temp + g2(xpt, npt, k, j) * g(svec, j);
            }
            temp = temp * g(pq, k);
            for i in 1..=n {
                s(hs, i, g(hs, i) + temp * g2(xpt, npt, k, i));
            }
        }
    }
}

/// The product `S * H` is followed by the same branch as label 210.
fn after_gg(
    crvmin: f64,
    iterc: i32,
    itcsav: i32,
    n: i32,
    hs: &[f64],
    hred: &mut [f64],
) -> i32 {
    if crvmin != 0.0 {
        return 50;
    }
    if iterc > itcsav {
        return 150;
    }
    for i in 1..=n {
        s(hred, i, g(hs, i));
    }
    120
}

/// Returns `(dsq, crvmin)`.
pub fn trsbox(
    n: i32,
    npt: i32,
    xpt: &[f64],
    xopt: &[f64],
    gopt: &[f64],
    hq: &[f64],
    pq: &[f64],
    sl: &[f64],
    su: &[f64],
    delta: f64,
    xnew: &mut [f64],
    d: &mut [f64],
    gnew: &mut [f64],
    xbdi: &mut [f64],
    svec: &mut [f64],
    hs: &mut [f64],
    hred: &mut [f64],
) -> (f64, f64) {
    let half = 0.5;
    let one = 1.0;
    let onemin = -1.0;
    let zero = 0.0;

    let mut iterc = 0;
    let mut nact = 0;
    for i in 1..=n {
        s(xbdi, i, zero);
        if g(xopt, i) <= g(sl, i) {
            if g(gopt, i) >= zero {
                s(xbdi, i, onemin);
            }
        } else if g(xopt, i) >= g(su, i) && g(gopt, i) <= zero {
            s(xbdi, i, one);
        }
        if g(xbdi, i) != zero {
            nact += 1;
        }
        s(d, i, zero);
        s(gnew, i, g(gopt, i));
    }
    let mut delsq = delta * delta;
    let mut qred = zero;
    let mut crvmin = onemin;
    let mut beta = zero;
    let mut gredsq = zero;
    let mut itermax = 0;
    let mut ggsav = zero;
    let mut itcsav = 0;
    let mut stepsq = zero;
    let mut label = 20i32;

    loop {
        if label == 20 {
            beta = zero;
            label = 30;
        }
        if label == 30 {
            stepsq = zero;
            for i in 1..=n {
                if g(xbdi, i) != zero {
                    s(svec, i, zero);
                } else if beta == zero {
                    s(svec, i, -g(gnew, i));
                } else {
                    s(svec, i, beta * g(svec, i) - g(gnew, i));
                }
                stepsq = stepsq + g(svec, i) * g(svec, i);
            }
            if stepsq == zero {
                label = 190;
            } else {
                if beta == zero {
                    gredsq = stepsq;
                    itermax = iterc + n - nact;
                }
                if gredsq * delsq <= 1.0e-4 * qred * qred {
                    label = 190;
                } else {
                    ggmult(n, npt, xpt, hq, pq, svec, hs);
                    label = after_gg(crvmin, iterc, itcsav, n, hs, hred);
                }
            }
        }
        if label == 50 {
            let mut resid = delsq;
            let mut ds = zero;
            let mut shs = zero;
            for i in 1..=n {
                if g(xbdi, i) == zero {
                    resid = resid - g(d, i) * g(d, i);
                    ds = ds + g(svec, i) * g(d, i);
                    shs = shs + g(svec, i) * g(hs, i);
                }
            }
            if resid <= zero {
                label = 90;
            } else {
                let temp = (stepsq * resid + ds * ds).sqrt();
                let blen = if ds < zero {
                    (temp - ds) / stepsq
                } else {
                    resid / (temp + ds)
                };
                let mut stplen = blen;
                if shs > zero {
                    stplen = dmin1(blen, gredsq / shs);
                }
                let mut iact = 0;
                for i in 1..=n {
                    if g(svec, i) != zero {
                        let xsum = g(xopt, i) + g(d, i);
                        let temp = if g(svec, i) > zero {
                            (g(su, i) - xsum) / g(svec, i)
                        } else {
                            (g(sl, i) - xsum) / g(svec, i)
                        };
                        if temp < stplen {
                            stplen = temp;
                            iact = i;
                        }
                    }
                }
                let mut sdec = zero;
                if stplen > zero {
                    iterc += 1;
                    let temp = shs / stepsq;
                    if iact == 0 && temp > zero {
                        crvmin = dmin1(crvmin, temp);
                        if crvmin == onemin {
                            crvmin = temp;
                        }
                    }
                    ggsav = gredsq;
                    gredsq = zero;
                    for i in 1..=n {
                        s(gnew, i, g(gnew, i) + stplen * g(hs, i));
                        if g(xbdi, i) == zero {
                            gredsq = gredsq + g(gnew, i) * g(gnew, i);
                        }
                        s(d, i, g(d, i) + stplen * g(svec, i));
                    }
                    sdec = dmax1(stplen * (ggsav - (half * stplen) * shs), zero);
                    qred = qred + sdec;
                }
                if iact > 0 {
                    nact += 1;
                    s(xbdi, iact, one);
                    if g(svec, iact) < zero {
                        s(xbdi, iact, onemin);
                    }
                    delsq = delsq - g(d, iact) * g(d, iact);
                    if delsq <= zero {
                        label = 90;
                    } else {
                        label = 20;
                        continue;
                    }
                } else if stplen < blen {
                    if iterc == itermax || sdec <= 0.01 * qred {
                        label = 190;
                    } else {
                        beta = gredsq / ggsav;
                        label = 30;
                        continue;
                    }
                } else {
                    label = 90;
                }
            }
        }
        if label == 90 {
            crvmin = zero;
            label = 100;
        }
        if label == 100 {
            if nact >= n - 1 {
                label = 190;
            } else {
                let mut dredsq = zero;
                let mut dredg = zero;
                gredsq = zero;
                for i in 1..=n {
                    if g(xbdi, i) == zero {
                        dredsq = dredsq + g(d, i) * g(d, i);
                        dredg = dredg + g(d, i) * g(gnew, i);
                        gredsq = gredsq + g(gnew, i) * g(gnew, i);
                        s(svec, i, g(d, i));
                    } else {
                        s(svec, i, zero);
                    }
                }
                itcsav = iterc;
                ggmult(n, npt, xpt, hq, pq, svec, hs);
                label = after_gg(crvmin, iterc, itcsav, n, hs, hred);
                // Label 120 uses DREDSQ, DREDG and the search that follows.
                if label == 120 {
                    label = alt_search(
                        n,
                        npt,
                        xpt,
                        xopt,
                        hq,
                        pq,
                        sl,
                        su,
                        d,
                        gnew,
                        xbdi,
                        svec,
                        hs,
                        hred,
                        &mut iterc,
                        &mut nact,
                        &mut qred,
                        &mut gredsq,
                        itcsav,
                        dredsq,
                        dredg,
                        half,
                        one,
                        onemin,
                        zero,
                    );
                }
            }
        }
        if label == 190 {
            break;
        }
        if label != 20 && label != 30 && label != 50 && label != 90 && label != 100 {
            break;
        }
    }

    let mut dsq = zero;
    for i in 1..=n {
        let mut xn = dmax1(dmin1(g(xopt, i) + g(d, i), g(su, i)), g(sl, i));
        if g(xbdi, i) == onemin {
            xn = g(sl, i);
        }
        if g(xbdi, i) == one {
            xn = g(su, i);
        }
        s(xnew, i, xn);
        s(d, i, g(xnew, i) - g(xopt, i));
        dsq = dsq + g(d, i) * g(d, i);
    }
    (dsq, crvmin)
}

/// Alternative iteration, labels 120 and 150, until it returns 100 or 190.
fn alt_search(
    n: i32,
    npt: i32,
    xpt: &[f64],
    xopt: &[f64],
    hq: &[f64],
    pq: &[f64],
    sl: &[f64],
    su: &[f64],
    d: &mut [f64],
    gnew: &mut [f64],
    xbdi: &mut [f64],
    svec: &mut [f64],
    hs: &mut [f64],
    hred: &mut [f64],
    iterc: &mut i32,
    nact: &mut i32,
    qred: &mut f64,
    gredsq: &mut f64,
    itcsav: i32,
    dredsq: f64,
    mut dredg: f64,
    half: f64,
    one: f64,
    onemin: f64,
    zero: f64,
) -> i32 {
    loop {
        *iterc += 1;
        let mut temp = (*gredsq) * dredsq - dredg * dredg;
        if temp <= 1.0e-4 * (*qred) * (*qred) {
            return 190;
        }
        temp = temp.sqrt();
        for i in 1..=n {
            if g(xbdi, i) == zero {
                s(svec, i, (dredg * g(d, i) - dredsq * g(gnew, i)) / temp);
            } else {
                s(svec, i, zero);
            }
        }
        let sredg = -temp;

        let mut angbd = one;
        let mut iact = 0;
        let mut xsav = zero;
        let mut hit_bound = false;
        for i in 1..=n {
            if g(xbdi, i) == zero {
                let tempa = (g(xopt, i) + g(d, i)) - g(sl, i);
                let tempb = (g(su, i) - g(xopt, i)) - g(d, i);
                if tempa <= zero {
                    *nact += 1;
                    s(xbdi, i, onemin);
                    hit_bound = true;
                    break;
                } else if tempb <= zero {
                    *nact += 1;
                    s(xbdi, i, one);
                    hit_bound = true;
                    break;
                }
                let ssq = g(d, i) * g(d, i) + g(svec, i) * g(svec, i);
                let mut temp = ssq - (g(xopt, i) - g(sl, i)) * (g(xopt, i) - g(sl, i));
                if temp > zero {
                    temp = temp.sqrt() - g(svec, i);
                    if angbd * temp > tempa {
                        angbd = tempa / temp;
                        iact = i;
                        xsav = onemin;
                    }
                }
                temp = ssq - (g(su, i) - g(xopt, i)) * (g(su, i) - g(xopt, i));
                if temp > zero {
                    temp = temp.sqrt() + g(svec, i);
                    if angbd * temp > tempb {
                        angbd = tempb / temp;
                        iact = i;
                        xsav = one;
                    }
                }
            }
        }
        if hit_bound {
            return 100;
        }

        ggmult(n, npt, xpt, hq, pq, svec, hs);
        let branch = after_gg(zero, *iterc, itcsav, n, hs, hred);
        if branch != 150 {
            // crvmin is zero here and iterc > itcsav, so the branch is 150.
        }

        let mut shs = zero;
        let mut dhs = zero;
        let mut dhd = zero;
        for i in 1..=n {
            if g(xbdi, i) == zero {
                shs = shs + g(svec, i) * g(hs, i);
                dhs = dhs + g(d, i) * g(hs, i);
                dhd = dhd + g(d, i) * g(hred, i);
            }
        }

        let mut redmax = zero;
        let mut isav = 0;
        let mut redsav = zero;
        let mut rdprev = zero;
        let mut rdnext = zero;
        let iu = (17.0 * angbd + 3.1) as i32;
        for i in 1..=iu {
            let angt = (angbd * (i as f64)) / (iu as f64);
            let sth = (angt + angt) / (one + angt * angt);
            let temp = shs + angt * ((angt * dhd - dhs) - dhs);
            let rednew = sth * ((angt * dredg - sredg) - half * sth * temp);
            if rednew > redmax {
                redmax = rednew;
                isav = i;
                rdprev = redsav;
            } else if i == isav + 1 {
                rdnext = rednew;
            }
            redsav = rednew;
        }
        if isav == 0 {
            return 190;
        }
        let mut angt = (angbd * (isav as f64)) / (iu as f64);
        if isav < iu {
            let temp = (rdnext - rdprev) / ((redmax + redmax - rdprev) - rdnext);
            angt = (angbd * ((isav as f64) + half * temp)) / (iu as f64);
        }
        let cth = (one - angt * angt) / (one + angt * angt);
        let sth = (angt + angt) / (one + angt * angt);
        let temp = shs + angt * ((angt * dhd - dhs) - dhs);
        let sdec = sth * ((angt * dredg - sredg) - half * sth * temp);
        if sdec <= zero {
            return 190;
        }

        dredg = zero;
        *gredsq = zero;
        for i in 1..=n {
            s(
                gnew,
                i,
                (g(gnew, i) + (cth - one) * g(hred, i)) + sth * g(hs, i),
            );
            if g(xbdi, i) == zero {
                s(d, i, cth * g(d, i) + sth * g(svec, i));
                dredg = dredg + g(d, i) * g(gnew, i);
                *gredsq = *gredsq + g(gnew, i) * g(gnew, i);
            }
            s(hred, i, cth * g(hred, i) + sth * g(hs, i));
        }
        *qred = *qred + sdec;
        if iact > 0 && isav == iu {
            *nact += 1;
            s(xbdi, iact, xsav);
            return 100;
        }
        if sdec > 0.01 * *qred {
            continue;
        }
        return 190;
    }
}
