//! `PRELIM` from minqa `prelim.f`.

use crate::arr::{dmax1, dmin1, g, g2, s, s2};

pub fn prelim(
    n: i32,
    npt: i32,
    x: &mut [f64],
    xl: &[f64],
    xu: &[f64],
    rhobeg: f64,
    _iprint: i32,
    maxfun: i32,
    xbase: &mut [f64],
    xpt: &mut [f64],
    fval: &mut [f64],
    gopt: &mut [f64],
    hq: &mut [f64],
    pq: &mut [f64],
    bmat: &mut [f64],
    zmat: &mut [f64],
    ndim: i32,
    sl: &[f64],
    su: &[f64],
    calfun: &mut dyn FnMut(&[f64]) -> f64,
) -> (i32, i32) {
    let half = 0.5;
    let one = 1.0;
    let two = 2.0;
    let zero = 0.0;
    let rhosq = rhobeg * rhobeg;
    let recip = one / rhosq;
    let np = n + 1;

    for j in 1..=n {
        s(xbase, j, g(x, j));
        for k in 1..=npt {
            s2(xpt, npt, k, j, zero);
        }
        for i in 1..=ndim {
            s2(bmat, ndim, i, j, zero);
        }
    }
    let nh = (n * np) / 2;
    for ih in 1..=nh {
        s(hq, ih, zero);
    }
    for k in 1..=npt {
        s(pq, k, zero);
        for j in 1..=(npt - np) {
            s2(zmat, npt, k, j, zero);
        }
    }

    let mut nf = 0;
    let mut kopt = 0;
    let mut fbeg = zero;
    let mut stepa = zero;
    let mut stepb = zero;
    let mut ipt = 0;
    let mut jpt = 0;
    loop {
        let nfm = nf;
        let nfx = nf - n;
        nf += 1;
        if nfm <= 2 * n {
            if nfm >= 1 && nfm <= n {
                stepa = rhobeg;
                if g(su, nfm) == zero {
                    stepa = -stepa;
                }
                s2(xpt, npt, nf, nfm, stepa);
            } else if nfm > n {
                stepa = g2(xpt, npt, nf - n, nfx);
                stepb = -rhobeg;
                if g(sl, nfx) == zero {
                    stepb = dmin1(two * rhobeg, g(su, nfx));
                }
                if g(su, nfx) == zero {
                    stepb = dmax1(-two * rhobeg, g(sl, nfx));
                }
                s2(xpt, npt, nf, nfx, stepb);
            }
        } else {
            let mut itemp = (nfm - np) / n;
            jpt = nfm - itemp * n - n;
            ipt = jpt + itemp;
            if ipt > n {
                itemp = jpt;
                jpt = ipt - n;
                ipt = itemp;
            }
            s2(xpt, npt, nf, ipt, g2(xpt, npt, ipt + 1, ipt));
            s2(xpt, npt, nf, jpt, g2(xpt, npt, jpt + 1, jpt));
        }

        for j in 1..=n {
            let mut xj = dmin1(dmax1(g(xl, j), g(xbase, j) + g2(xpt, npt, nf, j)), g(xu, j));
            if g2(xpt, npt, nf, j) == g(sl, j) {
                xj = g(xl, j);
            }
            if g2(xpt, npt, nf, j) == g(su, j) {
                xj = g(xu, j);
            }
            s(x, j, xj);
        }
        let f = calfun(&x[..n as usize]);
        s(fval, nf, f);
        if nf == 1 {
            fbeg = f;
            kopt = 1;
        } else if f < g(fval, kopt) {
            kopt = nf;
        }

        if nf <= 2 * n + 1 {
            if nf >= 2 && nf <= n + 1 {
                s(gopt, nfm, (f - fbeg) / stepa);
                if npt < nf + n {
                    s2(bmat, ndim, 1, nfm, -one / stepa);
                    s2(bmat, ndim, nf, nfm, one / stepa);
                    s2(bmat, ndim, npt + nfm, nfm, -half * rhosq);
                }
            } else if nf >= n + 2 {
                let ih = (nfx * (nfx + 1)) / 2;
                let temp = (f - fbeg) / stepb;
                let diff = stepb - stepa;
                s(hq, ih, (two * (temp - g(gopt, nfx))) / diff);
                s(
                    gopt,
                    nfx,
                    (g(gopt, nfx) * stepb - temp * stepa) / diff,
                );
                if stepa * stepb < zero {
                    if f < g(fval, nf - n) {
                        s(fval, nf, g(fval, nf - n));
                        s(fval, nf - n, f);
                        if kopt == nf {
                            kopt = nf - n;
                        }
                        s2(xpt, npt, nf - n, nfx, stepb);
                        s2(xpt, npt, nf, nfx, stepa);
                    }
                }
                s2(bmat, ndim, 1, nfx, -(stepa + stepb) / (stepa * stepb));
                s2(bmat, ndim, nf, nfx, -half / g2(xpt, npt, nf - n, nfx));
                s2(
                    bmat,
                    ndim,
                    nf - n,
                    nfx,
                    -g2(bmat, ndim, 1, nfx) - g2(bmat, ndim, nf, nfx),
                );
                s2(zmat, npt, 1, nfx, two.sqrt() / (stepa * stepb));
                s2(zmat, npt, nf, nfx, half.sqrt() / rhosq);
                s2(
                    zmat,
                    npt,
                    nf - n,
                    nfx,
                    -g2(zmat, npt, 1, nfx) - g2(zmat, npt, nf, nfx),
                );
            }
        } else {
            let ih = (ipt * (ipt - 1)) / 2 + jpt;
            s2(zmat, npt, 1, nfx, recip);
            s2(zmat, npt, nf, nfx, recip);
            s2(zmat, npt, ipt + 1, nfx, -recip);
            s2(zmat, npt, jpt + 1, nfx, -recip);
            let temp = g2(xpt, npt, nf, ipt) * g2(xpt, npt, nf, jpt);
            s(
                hq,
                ih,
                (((fbeg - g(fval, ipt + 1)) - g(fval, jpt + 1)) + f) / temp,
            );
        }
        if !(nf < npt && nf < maxfun) {
            break;
        }
    }
    (nf, kopt)
}
