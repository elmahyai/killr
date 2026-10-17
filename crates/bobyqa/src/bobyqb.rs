//! `BOBYQB` from minqa `bobyqb.f`.

use crate::altmov::altmov;
use crate::arr::{dmax1, dmax3, dmin1, g, g2, s, s2};
use crate::prelim::prelim;
use crate::rescue::rescue;
use crate::trsbox::trsbox;
use crate::update::update;

fn minqit(
    iprint: i32,
    _rho: f64,
    _nf: i32,
    _fopt: f64,
    _n: i32,
    _xbase: &[f64],
    _xopt: &[f64],
) {
    let _ = iprint;
}

fn minqir(iprint: i32, _f: f64, _nf: i32, _n: i32, _x: &[f64]) {
    let _ = iprint;
}

#[allow(clippy::too_many_arguments)]
pub fn bobyqb(
    n: i32,
    npt: i32,
    x: &mut [f64],
    xl: &[f64],
    xu: &[f64],
    rhobeg: f64,
    rhoend: f64,
    iprint: i32,
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
    xnew: &mut [f64],
    xalt: &mut [f64],
    d: &mut [f64],
    vlag: &mut [f64],
    w: &mut [f64],
    ierr: &mut i32,
    calfun: &mut dyn FnMut(&[f64]) -> f64,
) -> i32 {
    let half = 0.5;
    let one = 1.0;
    let ten = 10.0;
    let tenth = 0.1;
    let two = 2.0;
    let zero = 0.0;
    let np = n + 1;
    let nptm = npt - np;
    let nh = (n * np) / 2;

    let (mut nf, mut kopt) = prelim(
        n, npt, x, xl, xu, rhobeg, iprint, maxfun, xbase, xpt, fval, gopt, hq, pq, bmat,
        zmat, ndim, sl, su, calfun,
    );
    let mut xoptsq = zero;
    for i in 1..=n {
        s(xopt, i, g2(xpt, npt, kopt, i));
        xoptsq = xoptsq + g(xopt, i) * g(xopt, i);
    }
    let mut fsave = g(fval, 1);
    let mut f = zero;
    let mut rho = rhobeg;
    let mut delta = rhobeg;
    let mut nresc = nf;
    let mut ntrits = 0;
    let mut diffa = zero;
    let mut diffb = zero;
    let mut diffc = zero;
    let mut itest = 0;
    let mut nfsav = nf;
    let mut kbase = 1;
    let mut knew = 0;
    let mut denom = zero;
    let mut beta = zero;
    let mut alpha = zero;
    let mut cauchy = zero;
    let mut adelt = zero;
    let mut dsq = zero;
    let mut dnorm = zero;
    let mut ratio = zero;
    let mut distsq = zero;
    let mut label = 20i32;
    if nf < npt {
        *ierr = 390;
        label = 720;
    }

    loop {
        if label == 20 {
            if kopt != kbase {
                let mut ih = 0;
                for j in 1..=n {
                    for i in 1..=j {
                        ih += 1;
                        if i < j {
                            s(gopt, j, g(gopt, j) + g(hq, ih) * g(xopt, i));
                        }
                        s(gopt, i, g(gopt, i) + g(hq, ih) * g(xopt, j));
                    }
                }
                if nf > npt {
                    for k in 1..=npt {
                        let mut temp = zero;
                        for j in 1..=n {
                            temp = temp + g2(xpt, npt, k, j) * g(xopt, j);
                        }
                        temp = g(pq, k) * temp;
                        for i in 1..=n {
                            s(gopt, i, g(gopt, i) + temp * g2(xpt, npt, k, i));
                        }
                    }
                }
            }
            label = 60;
        }
        if label == 60 {
            let crvmin;
            {
                let nu = n as usize;
                let (gnew, rest) = w.split_at_mut(nu);
                let (xbdi, rest) = rest.split_at_mut(nu);
                let (svec, rest) = rest.split_at_mut(nu);
                let (hs, rest) = rest.split_at_mut(nu);
                let (hred, _) = rest.split_at_mut(nu);
                let (dsq_out, crv) = trsbox(
                    n, npt, xpt, xopt, gopt, hq, pq, sl, su, delta, xnew, d, gnew, xbdi,
                    svec, hs, hred,
                );
                dsq = dsq_out;
                crvmin = crv;
            }
            dnorm = dmin1(delta, dsq.sqrt());
            if dnorm < half * rho {
                ntrits = -1;
                distsq = (ten * rho) * (ten * rho);
                if nf <= nfsav + 2 {
                    label = 650;
                    continue;
                }
                let errbig = dmax3(diffa, diffb, diffc);
                let frhosq = (0.125 * rho) * rho;
                if crvmin > zero && errbig > frhosq * crvmin {
                    label = 650;
                    continue;
                }
                let bdtol = errbig / rho;
                let mut to_650 = false;
                for j in 1..=n {
                    let mut bdtest = bdtol;
                    if g(xnew, j) == g(sl, j) {
                        bdtest = g(w, j);
                    }
                    if g(xnew, j) == g(su, j) {
                        bdtest = -g(w, j);
                    }
                    if bdtest < bdtol {
                        let mut curv = g(hq, (j + j * j) / 2);
                        for k in 1..=npt {
                            let xp = g2(xpt, npt, k, j);
                            curv = curv + g(pq, k) * (xp * xp);
                        }
                        bdtest = bdtest + (half * curv) * rho;
                        if bdtest < bdtol {
                            to_650 = true;
                            break;
                        }
                    }
                }
                if to_650 {
                    label = 650;
                } else {
                    label = 680;
                }
                continue;
            }
            ntrits += 1;
            label = 90;
        }
        if label == 90 {
            if dsq <= 1.0e-3 * xoptsq {
                let fracsq = 0.25 * xoptsq;
                let mut sumpq = zero;
                for k in 1..=npt {
                    sumpq = sumpq + g(pq, k);
                    let mut sum = -half * xoptsq;
                    for i in 1..=n {
                        sum = sum + g2(xpt, npt, k, i) * g(xopt, i);
                    }
                    s(w, npt + k, sum);
                    let temp = fracsq - half * sum;
                    for i in 1..=n {
                        s(w, i, g2(bmat, ndim, k, i));
                        s(
                            vlag,
                            i,
                            g2(xpt, npt, k, i) * sum + temp * g(xopt, i),
                        );
                        let ip = npt + i;
                        for j in 1..=i {
                            let updated = (g2(bmat, ndim, ip, j) + g(w, i) * g(vlag, j))
                                + g(vlag, i) * g(w, j);
                            s2(bmat, ndim, ip, j, updated);
                        }
                    }
                }
                for jj in 1..=nptm {
                    let mut sumz = zero;
                    let mut sumw = zero;
                    for k in 1..=npt {
                        sumz = sumz + g2(zmat, npt, k, jj);
                        s(vlag, k, g(w, npt + k) * g2(zmat, npt, k, jj));
                        sumw = sumw + g(vlag, k);
                    }
                    for j in 1..=n {
                        let mut sum = (fracsq * sumz - half * sumw) * g(xopt, j);
                        for k in 1..=npt {
                            sum = sum + g(vlag, k) * g2(xpt, npt, k, j);
                        }
                        s(w, j, sum);
                        for k in 1..=npt {
                            s2(
                                bmat,
                                ndim,
                                k,
                                j,
                                g2(bmat, ndim, k, j) + sum * g2(zmat, npt, k, jj),
                            );
                        }
                    }
                    for i in 1..=n {
                        let ip = i + npt;
                        let temp = g(w, i);
                        for j in 1..=i {
                            s2(
                                bmat,
                                ndim,
                                ip,
                                j,
                                g2(bmat, ndim, ip, j) + temp * g(w, j),
                            );
                        }
                    }
                }
                let mut ih = 0;
                for j in 1..=n {
                    s(w, j, -half * sumpq * g(xopt, j));
                    for k in 1..=npt {
                        s(w, j, g(w, j) + g(pq, k) * g2(xpt, npt, k, j));
                        s2(xpt, npt, k, j, g2(xpt, npt, k, j) - g(xopt, j));
                    }
                    for i in 1..=j {
                        ih += 1;
                        s(
                            hq,
                            ih,
                            (g(hq, ih) + g(w, i) * g(xopt, j)) + g(xopt, i) * g(w, j),
                        );
                        s2(bmat, ndim, npt + i, j, g2(bmat, ndim, npt + j, i));
                    }
                }
                for i in 1..=n {
                    s(xbase, i, g(xbase, i) + g(xopt, i));
                    s(xnew, i, g(xnew, i) - g(xopt, i));
                    s(sl, i, g(sl, i) - g(xopt, i));
                    s(su, i, g(su, i) - g(xopt, i));
                    s(xopt, i, zero);
                }
                xoptsq = zero;
            }
            if ntrits == 0 {
                label = 210;
            } else {
                label = 230;
            }
        }
        if label == 190 {
            nfsav = nf;
            kbase = kopt;
            {
                let (ptsaux, rest) = w.split_at_mut((2 * n) as usize);
                let (ptsid, wres) = rest.split_at_mut(npt as usize);
                rescue(
                    n, npt, xl, xu, iprint, maxfun, xbase, xpt, fval, xopt, gopt, hq, pq,
                    bmat, zmat, ndim, sl, su, &mut nf, delta, &mut kopt, vlag, ptsaux, ptsid,
                    wres, calfun,
                );
            }
            xoptsq = zero;
            if kopt != kbase {
                for i in 1..=n {
                    s(xopt, i, g2(xpt, npt, kopt, i));
                    xoptsq = xoptsq + g(xopt, i) * g(xopt, i);
                }
            }
            if nf < 0 {
                nf = maxfun;
                *ierr = 390;
                label = 720;
            } else {
                nresc = nf;
                if nfsav < nf {
                    nfsav = nf;
                    label = 20;
                    continue;
                }
                if ntrits > 0 {
                    label = 60;
                    continue;
                }
                label = 210;
            }
        }
        if label == 210 {
            {
                let (glag, rest) = w.split_at_mut(n as usize);
                let (hcol, walt) = rest.split_at_mut(npt as usize);
                let (a, c) = altmov(
                    n, npt, xpt, xopt, bmat, zmat, ndim, sl, su, kopt, knew, adelt, xnew,
                    xalt, glag, hcol, walt,
                );
                alpha = a;
                cauchy = c;
            }
            for i in 1..=n {
                s(d, i, g(xnew, i) - g(xopt, i));
            }
            label = 230;
        }
        if label == 230 {
            let mut redo = false;
            let mut leave = 0i32;
            for k in 1..=npt {
                let mut suma = zero;
                let mut sumb = zero;
                let mut sum = zero;
                for j in 1..=n {
                    suma = suma + g2(xpt, npt, k, j) * g(d, j);
                    sumb = sumb + g2(xpt, npt, k, j) * g(xopt, j);
                    sum = sum + g2(bmat, ndim, k, j) * g(d, j);
                }
                s(w, k, suma * (half * suma + sumb));
                s(vlag, k, sum);
                s(w, npt + k, suma);
            }
            beta = zero;
            for jj in 1..=nptm {
                let mut sum = zero;
                for k in 1..=npt {
                    sum = sum + g2(zmat, npt, k, jj) * g(w, k);
                }
                beta = beta - sum * sum;
                for k in 1..=npt {
                    s(vlag, k, g(vlag, k) + sum * g2(zmat, npt, k, jj));
                }
            }
            dsq = zero;
            let mut bsum = zero;
            let mut dx = zero;
            for j in 1..=n {
                dsq = dsq + g(d, j) * g(d, j);
                let mut sum = zero;
                for k in 1..=npt {
                    sum = sum + g(w, k) * g2(bmat, ndim, k, j);
                }
                bsum = bsum + sum * g(d, j);
                let jp = npt + j;
                for i in 1..=n {
                    sum = sum + g2(bmat, ndim, jp, i) * g(d, i);
                }
                s(vlag, jp, sum);
                bsum = bsum + sum * g(d, j);
                dx = dx + g(d, j) * g(xopt, j);
            }
            let quad = ((xoptsq + dx) + dx) + half * dsq;
            beta = ((dx * dx + dsq * quad) + beta) - bsum;
            s(vlag, kopt, g(vlag, kopt) + one);

            if ntrits == 0 {
                denom = g(vlag, knew) * g(vlag, knew) + alpha * beta;
                if denom < cauchy && cauchy > zero {
                    for i in 1..=n {
                        s(xnew, i, g(xalt, i));
                        s(d, i, g(xnew, i) - g(xopt, i));
                    }
                    cauchy = zero;
                    redo = true;
                } else if denom <= half * (g(vlag, knew) * g(vlag, knew)) {
                    if nf > nresc {
                        leave = 190;
                    } else {
                        *ierr = 320;
                        leave = 720;
                    }
                }
            } else {
                let delsq = delta * delta;
                let mut scaden = zero;
                let mut biglsq = zero;
                knew = 0;
                for k in 1..=npt {
                    if k == kopt {
                        continue;
                    }
                    let mut hdiag = zero;
                    for jj in 1..=nptm {
                        hdiag = hdiag + g2(zmat, npt, k, jj) * g2(zmat, npt, k, jj);
                    }
                    let den = beta * hdiag + g(vlag, k) * g(vlag, k);
                    let mut dist = zero;
                    for j in 1..=n {
                        let gap = g2(xpt, npt, k, j) - g(xopt, j);
                        dist = dist + gap * gap;
                    }
                    let temp = dmax1(one, (dist / delsq) * (dist / delsq));
                    if temp * den > scaden {
                        scaden = temp * den;
                        knew = k;
                        denom = den;
                    }
                    biglsq = dmax1(biglsq, temp * (g(vlag, k) * g(vlag, k)));
                }
                if scaden <= half * biglsq {
                    if nf > nresc {
                        leave = 190;
                    } else {
                        *ierr = 320;
                        leave = 720;
                    }
                }
            }
            if redo {
                continue;
            }
            if leave != 0 {
                label = leave;
                if leave == 720 {
                    // fall through only if 720 is later; 190 is earlier
                }
                if leave == 190 {
                    continue;
                }
            } else {
                label = 360;
            }
        }
        if label == 360 {
            for i in 1..=n {
                let mut xi = dmin1(dmax1(g(xl, i), g(xbase, i) + g(xnew, i)), g(xu, i));
                if g(xnew, i) == g(sl, i) {
                    xi = g(xl, i);
                }
                if g(xnew, i) == g(su, i) {
                    xi = g(xu, i);
                }
                s(x, i, xi);
            }
            if nf >= maxfun {
                *ierr = 390;
                label = 720;
            } else {
                nf += 1;
                f = calfun(&x[..n as usize]);
                if ntrits == -1 {
                    fsave = f;
                    label = 720;
                } else {
                    let fopt = g(fval, kopt);
                    let mut vquad = zero;
                    let mut ih = 0;
                    for j in 1..=n {
                        vquad = vquad + g(d, j) * g(gopt, j);
                        for i in 1..=j {
                            ih += 1;
                            let mut temp = g(d, i) * g(d, j);
                            if i == j {
                                temp = half * temp;
                            }
                            vquad = vquad + g(hq, ih) * temp;
                        }
                    }
                    for k in 1..=npt {
                        let wk = g(w, npt + k);
                        vquad = vquad + (half * g(pq, k)) * (wk * wk);
                    }
                    let diff = (f - fopt) - vquad;
                    diffc = diffb;
                    diffb = diffa;
                    diffa = diff.abs();
                    if dnorm > rho {
                        nfsav = nf;
                    }
                    if ntrits > 0 {
                        if vquad >= zero {
                            *ierr = 430;
                            label = 720;
                        } else {
                            ratio = (f - fopt) / vquad;
                            if ratio <= tenth {
                                delta = dmin1(half * delta, dnorm);
                            } else if ratio <= 0.7 {
                                delta = dmax1(half * delta, dnorm);
                            } else {
                                delta = dmax1(half * delta, dnorm + dnorm);
                            }
                            if delta <= 1.5 * rho {
                                delta = rho;
                            }
                            if f < fopt {
                                let ksav = knew;
                                let densav = denom;
                                let delsq = delta * delta;
                                let mut scaden = zero;
                                let mut biglsq = zero;
                                knew = 0;
                                for k in 1..=npt {
                                    let mut hdiag = zero;
                                    for jj in 1..=nptm {
                                        hdiag = hdiag
                                            + g2(zmat, npt, k, jj) * g2(zmat, npt, k, jj);
                                    }
                                    let den = beta * hdiag + g(vlag, k) * g(vlag, k);
                                    let mut dist = zero;
                                    for j in 1..=n {
                                        let gap = g2(xpt, npt, k, j) - g(xnew, j);
                                        dist = dist + gap * gap;
                                    }
                                    let temp = dmax1(one, (dist / delsq) * (dist / delsq));
                                    if temp * den > scaden {
                                        scaden = temp * den;
                                        knew = k;
                                        denom = den;
                                    }
                                    biglsq = dmax1(biglsq, temp * (g(vlag, k) * g(vlag, k)));
                                }
                                if scaden <= half * biglsq {
                                    knew = ksav;
                                    denom = densav;
                                }
                            }
                        }
                    }
                    if label != 720 {
                        update(n, npt, bmat, zmat, ndim, vlag, beta, denom, knew, w);
                        let mut ih = 0;
                        let pqold = g(pq, knew);
                        s(pq, knew, zero);
                        for i in 1..=n {
                            let temp = pqold * g2(xpt, npt, knew, i);
                            for j in 1..=i {
                                ih += 1;
                                s(
                                    hq,
                                    ih,
                                    g(hq, ih) + temp * g2(xpt, npt, knew, j),
                                );
                            }
                        }
                        for jj in 1..=nptm {
                            let temp = diff * g2(zmat, npt, knew, jj);
                            for k in 1..=npt {
                                s(pq, k, g(pq, k) + temp * g2(zmat, npt, k, jj));
                            }
                        }
                        s(fval, knew, f);
                        for i in 1..=n {
                            s2(xpt, npt, knew, i, g(xnew, i));
                            s(w, i, g2(bmat, ndim, knew, i));
                        }
                        for k in 1..=npt {
                            let mut suma = zero;
                            for jj in 1..=nptm {
                                suma = suma + g2(zmat, npt, knew, jj) * g2(zmat, npt, k, jj);
                            }
                            let mut sumb = zero;
                            for j in 1..=n {
                                sumb = sumb + g2(xpt, npt, k, j) * g(xopt, j);
                            }
                            let temp = suma * sumb;
                            for i in 1..=n {
                                s(w, i, g(w, i) + temp * g2(xpt, npt, k, i));
                            }
                        }
                        for i in 1..=n {
                            s(gopt, i, g(gopt, i) + diff * g(w, i));
                        }
                        if f < fopt {
                            kopt = knew;
                            xoptsq = zero;
                            let mut ih = 0;
                            for j in 1..=n {
                                s(xopt, j, g(xnew, j));
                                xoptsq = xoptsq + g(xopt, j) * g(xopt, j);
                                for i in 1..=j {
                                    ih += 1;
                                    if i < j {
                                        s(gopt, j, g(gopt, j) + g(hq, ih) * g(d, i));
                                    }
                                    s(gopt, i, g(gopt, i) + g(hq, ih) * g(d, j));
                                }
                            }
                            for k in 1..=npt {
                                let mut temp = zero;
                                for j in 1..=n {
                                    temp = temp + g2(xpt, npt, k, j) * g(d, j);
                                }
                                temp = g(pq, k) * temp;
                                for i in 1..=n {
                                    s(gopt, i, g(gopt, i) + temp * g2(xpt, npt, k, i));
                                }
                            }
                        }
                        if ntrits > 0 {
                            for k in 1..=npt {
                                s(vlag, k, g(fval, k) - g(fval, kopt));
                                s(w, k, zero);
                            }
                            for j in 1..=nptm {
                                let mut sum = zero;
                                for k in 1..=npt {
                                    sum = sum + g2(zmat, npt, k, j) * g(vlag, k);
                                }
                                for k in 1..=npt {
                                    s(w, k, g(w, k) + sum * g2(zmat, npt, k, j));
                                }
                            }
                            for k in 1..=npt {
                                let mut sum = zero;
                                for j in 1..=n {
                                    sum = sum + g2(xpt, npt, k, j) * g(xopt, j);
                                }
                                s(w, k + npt, g(w, k));
                                s(w, k, sum * g(w, k));
                            }
                            let mut gqsq = zero;
                            let mut gisq = zero;
                            for i in 1..=n {
                                let mut sum = zero;
                                for k in 1..=npt {
                                    sum = sum
                                        + g2(bmat, ndim, k, i) * g(vlag, k)
                                        + g2(xpt, npt, k, i) * g(w, k);
                                }
                                if g(xopt, i) == g(sl, i) {
                                    let t = dmin1(zero, g(gopt, i));
                                    gqsq = gqsq + t * t;
                                    let t = dmin1(zero, sum);
                                    gisq = gisq + t * t;
                                } else if g(xopt, i) == g(su, i) {
                                    let t = dmax1(zero, g(gopt, i));
                                    gqsq = gqsq + t * t;
                                    let t = dmax1(zero, sum);
                                    gisq = gisq + t * t;
                                } else {
                                    gqsq = gqsq + g(gopt, i) * g(gopt, i);
                                    gisq = gisq + sum * sum;
                                }
                                s(vlag, npt + i, sum);
                            }
                            itest += 1;
                            if gqsq < ten * gisq {
                                itest = 0;
                            }
                            if itest >= 3 {
                                let lim = npt.max(nh);
                                for i in 1..=lim {
                                    if i <= n {
                                        s(gopt, i, g(vlag, npt + i));
                                    }
                                    if i <= npt {
                                        s(pq, i, g(w, npt + i));
                                    }
                                    if i <= nh {
                                        s(hq, i, zero);
                                    }
                                    itest = 0;
                                }
                            }
                        }
                        if ntrits == 0 {
                            label = 60;
                            continue;
                        }
                        if f <= fopt + tenth * vquad {
                            label = 60;
                            continue;
                        }
                        distsq = dmax1((two * delta) * (two * delta), (ten * rho) * (ten * rho));
                        label = 650;
                    }
                }
            }
        }
        if label == 650 {
            knew = 0;
            for k in 1..=npt {
                let mut sum = zero;
                for j in 1..=n {
                    let gap = g2(xpt, npt, k, j) - g(xopt, j);
                    sum = sum + gap * gap;
                }
                if sum > distsq {
                    knew = k;
                    distsq = sum;
                }
            }
            if knew > 0 {
                let dist = distsq.sqrt();
                if ntrits == -1 {
                    delta = dmin1(tenth * delta, half * dist);
                    if delta <= 1.5 * rho {
                        delta = rho;
                    }
                }
                ntrits = 0;
                adelt = dmax1(dmin1(tenth * dist, delta), rho);
                dsq = adelt * adelt;
                label = 90;
                continue;
            }
            if ntrits == -1 {
                label = 680;
            } else if ratio > zero {
                label = 60;
                continue;
            } else if dmax1(delta, dnorm) > rho {
                label = 60;
                continue;
            } else {
                label = 680;
            }
        }
        if label == 680 {
            if rho > rhoend {
                delta = half * rho;
                ratio = rho / rhoend;
                if ratio <= 16.0 {
                    rho = rhoend;
                } else if ratio <= 250.0 {
                    rho = ratio.sqrt() * rhoend;
                } else {
                    rho = tenth * rho;
                }
                delta = dmax1(delta, rho);
                minqit(iprint, rho, nf, g(fval, kopt), n, xbase, xopt);
                ntrits = 0;
                nfsav = nf;
                label = 60;
                continue;
            }
            if ntrits == -1 {
                label = 360;
                continue;
            }
            label = 720;
        }
        if label == 720 {
            break;
        }
    }

    if g(fval, kopt) <= fsave {
        for i in 1..=n {
            let mut xi = dmin1(dmax1(g(xl, i), g(xbase, i) + g(xopt, i)), g(xu, i));
            if g(xopt, i) == g(sl, i) {
                xi = g(xl, i);
            }
            if g(xopt, i) == g(su, i) {
                xi = g(xu, i);
            }
            s(x, i, xi);
        }
        f = g(fval, kopt);
    }
    minqir(iprint, f, nf, n, x);
    nf
}
