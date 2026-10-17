//! NEWUOA driver and main iteration, from minqa `newuoa.f` and `newuob.f`.

use crate::bigden::bigden;
use crate::biglag::biglag;
use crate::fortran::{dmax1, dmax3, dmin1, get, get2, set, set2};
use crate::trsapp::trsapp;
use crate::update::update;

#[allow(clippy::too_many_arguments)]
pub(crate) fn newuob(
    n: i32,
    npt: i32,
    x: &mut [f64],
    rhobeg: f64,
    rhoend: f64,
    iprint: i32,
    maxfun: i32,
    w: &mut [f64],
    ierr: &mut i32,
    calfun: &mut dyn FnMut(&[f64]) -> f64,
) -> i32 {
    let nu = n as usize;
    let npt_u = npt as usize;
    let np = n + 1;
    let nh = (n * np) / 2;
    let ndim = npt + n;
    let nptm = npt - np;
    let (xbase, w) = w.split_at_mut(nu);
    let (xopt, w) = w.split_at_mut(nu);
    let (xnew, w) = w.split_at_mut(nu);
    let (xpt, w) = w.split_at_mut(nu * npt_u);
    let (fval, w) = w.split_at_mut(npt_u);
    let (gq, w) = w.split_at_mut(nu);
    let (hq, w) = w.split_at_mut(nh as usize);
    let (pq, w) = w.split_at_mut(npt_u);
    let (bmat, w) = w.split_at_mut((ndim as usize) * nu);
    let (zmat, w) = w.split_at_mut(npt_u * (nptm as usize));
    let (d, w) = w.split_at_mut(nu);
    let (vlag, wwork) = w.split_at_mut(ndim as usize);

    let half = 0.5_f64;
    let one = 1.0;
    let tenth = 0.1;
    let nftest = maxfun.max(1);

    for j in 1..=n {
        set(xbase, j, get(x, j));
        for k in 1..=npt {
            set2(xpt, npt, k, j, 0.0);
        }
        for i in 1..=ndim {
            set2(bmat, ndim, i, j, 0.0);
        }
    }
    for ih in 1..=nh {
        set(hq, ih, 0.0);
    }
    for k in 1..=npt {
        set(pq, k, 0.0);
        for j in 1..=nptm {
            set2(zmat, npt, k, j, 0.0);
        }
    }

    let mut rhosq = rhobeg * rhobeg;
    let recip = one / rhosq;
    let reciq = half.sqrt() / rhosq;
    let mut nf = 0;
    let mut nfm = 0;
    let mut nfmm = 0;
    let mut ipt = 0;
    let mut jpt = 0;
    let mut xipt = 0.0;
    let mut xjpt = 0.0;
    let mut f = 0.0;
    let mut fbeg = 0.0;
    let mut fopt = 0.0;
    let mut kopt = 1;
    let mut rho = rhobeg;
    let mut delta = rhobeg;
    let mut idz = 1;
    let mut diffa = 0.0;
    let mut diffb = 0.0;
    let mut diffc = 0.0;
    let mut itest = 0;
    let mut xoptsq = 0.0;
    let mut nfsav = 0;
    let mut knew = 0;
    let mut dsq = 0.0;
    let mut dnorm = 0.0;
    let mut ratio = 0.0;
    let mut crvmin = 0.0;
    let mut alpha = 0.0;
    let mut beta = 0.0;
    let mut dstep = 0.0;
    let mut vquad = 0.0;
    let mut fsave = 0.0;
    let mut ksave = 0;
    let mut diff = 0.0;

    let mut label = 50;
    loop {
        match label {
            50 => {
                nfm = nf;
                nfmm = nf - n;
                nf += 1;
                if nfm <= 2 * n {
                    if nfm >= 1 && nfm <= n {
                        set2(xpt, npt, nf, nfm, rhobeg);
                    } else if nfm > n {
                        set2(xpt, npt, nf, nfmm, -rhobeg);
                    }
                } else {
                    let mut itemp = (nfmm - 1) / n;
                    jpt = nfm - itemp * n - n;
                    ipt = jpt + itemp;
                    if ipt > n {
                        itemp = jpt;
                        jpt = ipt - n;
                        ipt = itemp;
                    }
                    xipt = rhobeg;
                    if get(fval, ipt + np) < get(fval, ipt + 1) {
                        xipt = -xipt;
                    }
                    xjpt = rhobeg;
                    if get(fval, jpt + np) < get(fval, jpt + 1) {
                        xjpt = -xjpt;
                    }
                    set2(xpt, npt, nf, ipt, xipt);
                    set2(xpt, npt, nf, jpt, xjpt);
                }
                for j in 1..=n {
                    set(x, j, get2(xpt, npt, nf, j) + get(xbase, j));
                }
                label = 310;
            }
            70 => {
                set(fval, nf, f);
                if nf == 1 {
                    fbeg = f;
                    fopt = f;
                    kopt = 1;
                } else if f < fopt {
                    fopt = f;
                    kopt = nf;
                }
                if nfm <= 2 * n {
                    if nfm >= 1 && nfm <= n {
                        set(gq, nfm, (f - fbeg) / rhobeg);
                        if npt < nf + n {
                            set2(bmat, ndim, 1, nfm, -one / rhobeg);
                            set2(bmat, ndim, nf, nfm, one / rhobeg);
                            set2(bmat, ndim, npt + nfm, nfm, -half * rhosq);
                        }
                    } else if nfm > n {
                        set2(bmat, ndim, nf - n, nfmm, half / rhobeg);
                        set2(bmat, ndim, nf, nfmm, -half / rhobeg);
                        set2(zmat, npt, 1, nfmm, -reciq - reciq);
                        set2(zmat, npt, nf - n, nfmm, reciq);
                        set2(zmat, npt, nf, nfmm, reciq);
                        let ih = (nfmm * (nfmm + 1)) / 2;
                        let temp = (fbeg - f) / rhobeg;
                        set(hq, ih, (get(gq, nfmm) - temp) / rhobeg);
                        set(gq, nfmm, half * (get(gq, nfmm) + temp));
                    }
                } else {
                    let ih = (ipt * (ipt - 1)) / 2 + jpt;
                    if xipt < 0.0 {
                        ipt += n;
                    }
                    if xjpt < 0.0 {
                        jpt += n;
                    }
                    set2(zmat, npt, 1, nfmm, recip);
                    set2(zmat, npt, nf, nfmm, recip);
                    set2(zmat, npt, ipt + 1, nfmm, -recip);
                    set2(zmat, npt, jpt + 1, nfmm, -recip);
                    set(
                        hq,
                        ih,
                        (fbeg - get(fval, ipt + 1) - get(fval, jpt + 1) + f) / (xipt * xjpt),
                    );
                }
                if nf < npt {
                    label = 50;
                } else {
                    rho = rhobeg;
                    delta = rho;
                    idz = 1;
                    diffa = 0.0;
                    diffb = 0.0;
                    itest = 0;
                    xoptsq = 0.0;
                    for i in 1..=n {
                        let xi = get2(xpt, npt, kopt, i);
                        set(xopt, i, xi);
                        xoptsq = xoptsq + xi * xi;
                    }
                    label = 90;
                }
            }
            90 => {
                nfsav = nf;
                label = 100;
            }
            100 => {
                knew = 0;
                {
                    let n_u = n as usize;
                    let (dw, rest) = wwork.split_at_mut(n_u);
                    let (g, rest) = rest.split_at_mut(n_u);
                    let (hd, rest) = rest.split_at_mut(n_u);
                    let (hs, _) = rest.split_at_mut(n_u);
                    trsapp(
                        n,
                        npt,
                        xopt,
                        xpt,
                        gq,
                        hq,
                        pq,
                        delta,
                        d,
                        dw,
                        g,
                        hd,
                        hs,
                        &mut crvmin,
                    );
                }
                dsq = 0.0;
                for i in 1..=n {
                    dsq = dsq + get(d, i) * get(d, i);
                }
                dnorm = dmin1(delta, dsq.sqrt());
                if dnorm < half * rho {
                    knew = -1;
                    delta = tenth * delta;
                    ratio = -1.0;
                    if delta <= 1.5 * rho {
                        delta = rho;
                    }
                    if nf <= nfsav + 2 {
                        label = 460;
                        continue;
                    }
                    let temp = ((0.125 * crvmin) * rho) * rho;
                    if temp <= dmax3(diffa, diffb, diffc) {
                        label = 460;
                        continue;
                    }
                    label = 490;
                    continue;
                }
                label = 120;
            }
            120 => {
                if dsq <= 1.0e-3 * xoptsq {
                    let tempq = 0.25 * xoptsq;
                    for k in 1..=npt {
                        let mut sum = 0.0;
                        for i in 1..=n {
                            sum = sum + get2(xpt, npt, k, i) * get(xopt, i);
                        }
                        let temp = get(pq, k) * sum;
                        sum = sum - half * xoptsq;
                        set(wwork, npt + k, sum);
                        for i in 1..=n {
                            set(gq, i, get(gq, i) + temp * get2(xpt, npt, k, i));
                            set2(xpt, npt, k, i, get2(xpt, npt, k, i) - half * get(xopt, i));
                            set(vlag, i, get2(bmat, ndim, k, i));
                            set(wwork, i, sum * get2(xpt, npt, k, i) + tempq * get(xopt, i));
                            let ip = npt + i;
                            for j in 1..=i {
                                set2(
                                    bmat,
                                    ndim,
                                    ip,
                                    j,
                                    get2(bmat, ndim, ip, j)
                                        + get(vlag, i) * get(wwork, j)
                                        + get(wwork, i) * get(vlag, j),
                                );
                            }
                        }
                    }
                    for k in 1..=nptm {
                        let mut sumz = 0.0;
                        for i in 1..=npt {
                            sumz = sumz + get2(zmat, npt, i, k);
                            set(wwork, i, get(wwork, npt + i) * get2(zmat, npt, i, k));
                        }
                        for j in 1..=n {
                            let mut sum = tempq * sumz * get(xopt, j);
                            for i in 1..=npt {
                                sum = sum + get(wwork, i) * get2(xpt, npt, i, j);
                            }
                            set(vlag, j, sum);
                            if k < idz {
                                sum = -sum;
                            }
                            for i in 1..=npt {
                                set2(
                                    bmat,
                                    ndim,
                                    i,
                                    j,
                                    get2(bmat, ndim, i, j) + sum * get2(zmat, npt, i, k),
                                );
                            }
                        }
                        for i in 1..=n {
                            let ip = i + npt;
                            let mut temp = get(vlag, i);
                            if k < idz {
                                temp = -temp;
                            }
                            for j in 1..=i {
                                set2(
                                    bmat,
                                    ndim,
                                    ip,
                                    j,
                                    get2(bmat, ndim, ip, j) + temp * get(vlag, j),
                                );
                            }
                        }
                    }
                    let mut ih = 0;
                    for j in 1..=n {
                        set(wwork, j, 0.0);
                        for k in 1..=npt {
                            set(wwork, j, get(wwork, j) + get(pq, k) * get2(xpt, npt, k, j));
                            set2(xpt, npt, k, j, get2(xpt, npt, k, j) - half * get(xopt, j));
                        }
                        for i in 1..=j {
                            ih += 1;
                            if i < j {
                                set(gq, j, get(gq, j) + get(hq, ih) * get(xopt, i));
                            }
                            set(gq, i, get(gq, i) + get(hq, ih) * get(xopt, j));
                            set(
                                hq,
                                ih,
                                get(hq, ih)
                                    + get(wwork, i) * get(xopt, j)
                                    + get(xopt, i) * get(wwork, j),
                            );
                            set2(bmat, ndim, npt + i, j, get2(bmat, ndim, npt + j, i));
                        }
                    }
                    for j in 1..=n {
                        set(xbase, j, get(xbase, j) + get(xopt, j));
                        set(xopt, j, 0.0);
                    }
                    xoptsq = 0.0;
                }
                if knew > 0 {
                    let (hcol, gc) = vlag.split_at_mut(npt_u);
                    let n_u = n as usize;
                    let (gd, rest) = wwork.split_at_mut(n_u);
                    let (s, rest) = rest.split_at_mut(n_u);
                    let (wb, _) = rest.split_at_mut(n_u);
                    biglag(
                        n, npt, xopt, xpt, bmat, zmat, idz, ndim, knew, dstep, d, &mut alpha, hcol,
                        gc, gd, s, wb,
                    );
                }
                for k in 1..=npt {
                    let mut suma = 0.0;
                    let mut sumb = 0.0;
                    let mut sum = 0.0;
                    for j in 1..=n {
                        suma = suma + get2(xpt, npt, k, j) * get(d, j);
                        sumb = sumb + get2(xpt, npt, k, j) * get(xopt, j);
                        sum = sum + get2(bmat, ndim, k, j) * get(d, j);
                    }
                    set(wwork, k, suma * (half * suma + sumb));
                    set(vlag, k, sum);
                }
                beta = 0.0;
                for k in 1..=nptm {
                    let mut sum = 0.0;
                    for i in 1..=npt {
                        sum = sum + get2(zmat, npt, i, k) * get(wwork, i);
                    }
                    if k < idz {
                        beta = beta + sum * sum;
                        sum = -sum;
                    } else {
                        beta = beta - sum * sum;
                    }
                    for i in 1..=npt {
                        set(vlag, i, get(vlag, i) + sum * get2(zmat, npt, i, k));
                    }
                }
                let mut bsum = 0.0;
                let mut dx = 0.0;
                for j in 1..=n {
                    let mut sum = 0.0;
                    for i in 1..=npt {
                        sum = sum + get(wwork, i) * get2(bmat, ndim, i, j);
                    }
                    bsum = bsum + sum * get(d, j);
                    let jp = npt + j;
                    for k in 1..=n {
                        sum = sum + get2(bmat, ndim, jp, k) * get(d, k);
                    }
                    set(vlag, jp, sum);
                    bsum = bsum + sum * get(d, j);
                    dx = dx + get(d, j) * get(xopt, j);
                }
                beta = dx * dx + dsq * (xoptsq + dx + dx + half * dsq) + beta - bsum;
                set(vlag, kopt, get(vlag, kopt) + one);
                if knew > 0 {
                    let temp = one + alpha * beta / (get(vlag, knew) * get(vlag, knew));
                    if temp.abs() <= 0.8 {
                        let ndim_u = ndim as usize;
                        let (w_head, rest) = wwork.split_at_mut(ndim_u);
                        let (wvec, rest) = rest.split_at_mut(5 * ndim_u);
                        let (prod, _) = rest.split_at_mut(5 * ndim_u);
                        bigden(
                            n, npt, xopt, xpt, bmat, zmat, idz, ndim, kopt, knew, d, w_head, vlag,
                            &mut beta, xnew, wvec, prod,
                        );
                    }
                }
                label = 290;
            }
            290 => {
                for i in 1..=n {
                    set(xnew, i, get(xopt, i) + get(d, i));
                    set(x, i, get(xbase, i) + get(xnew, i));
                }
                nf += 1;
                label = 310;
            }
            310 => {
                if nf > nftest {
                    nf -= 1;
                    *ierr = 390;
                    label = 530;
                    continue;
                }
                f = calfun(&x[..nu]);
                if nf <= npt {
                    label = 70;
                    continue;
                }
                if knew == -1 {
                    label = 530;
                    continue;
                }
                vquad = 0.0;
                let mut ih = 0;
                for j in 1..=n {
                    vquad = vquad + get(d, j) * get(gq, j);
                    for i in 1..=j {
                        ih += 1;
                        let mut temp = get(d, i) * get(xnew, j) + get(d, j) * get(xopt, i);
                        if i == j {
                            temp = half * temp;
                        }
                        vquad = vquad + temp * get(hq, ih);
                    }
                }
                for k in 1..=npt {
                    vquad = vquad + get(pq, k) * get(wwork, k);
                }
                diff = f - fopt - vquad;
                diffc = diffb;
                diffb = diffa;
                diffa = diff.abs();
                if dnorm > rho {
                    nfsav = nf;
                }
                fsave = fopt;
                if f < fopt {
                    fopt = f;
                    xoptsq = 0.0;
                    for i in 1..=n {
                        set(xopt, i, get(xnew, i));
                        xoptsq = xoptsq + get(xopt, i) * get(xopt, i);
                    }
                }
                ksave = knew;
                if knew > 0 {
                    label = 410;
                    continue;
                }
                if vquad >= 0.0 {
                    *ierr = 3701;
                    label = 530;
                    continue;
                }
                ratio = (f - fsave) / vquad;
                if ratio <= tenth {
                    delta = half * dnorm;
                } else if ratio <= 0.7 {
                    delta = dmax1(half * delta, dnorm);
                } else {
                    delta = dmax1(half * delta, dnorm + dnorm);
                }
                if delta <= 1.5 * rho {
                    delta = rho;
                }
                rhosq = dmax1(tenth * delta, rho);
                rhosq = rhosq * rhosq;
                let mut ktemp = 0;
                let mut detrat = 0.0;
                if f >= fsave {
                    ktemp = kopt;
                    detrat = one;
                }
                for k in 1..=npt {
                    let mut hdiag = 0.0;
                    for j in 1..=nptm {
                        let mut temp = one;
                        if j < idz {
                            temp = -one;
                        }
                        let zij = get2(zmat, npt, k, j);
                        hdiag = hdiag + temp * zij * zij;
                    }
                    let mut temp = (beta * hdiag + get(vlag, k) * get(vlag, k)).abs();
                    let mut distsq = 0.0;
                    for j in 1..=n {
                        let gap = get2(xpt, npt, k, j) - get(xopt, j);
                        distsq = distsq + gap * gap;
                    }
                    if distsq > rhosq {
                        let ratio_d = distsq / rhosq;
                        temp = temp * (ratio_d * ratio_d * ratio_d);
                    }
                    if temp > detrat && k != ktemp {
                        detrat = temp;
                        knew = k;
                    }
                }
                if knew == 0 {
                    label = 460;
                } else {
                    label = 410;
                }
            }
            410 => {
                update(n, npt, bmat, zmat, &mut idz, ndim, vlag, beta, knew, wwork);
                set(fval, knew, f);
                let mut ih = 0;
                for i in 1..=n {
                    let temp = get(pq, knew) * get2(xpt, npt, knew, i);
                    for j in 1..=i {
                        ih += 1;
                        set(hq, ih, get(hq, ih) + temp * get2(xpt, npt, knew, j));
                    }
                }
                set(pq, knew, 0.0);
                for j in 1..=nptm {
                    let mut temp = diff * get2(zmat, npt, knew, j);
                    if j < idz {
                        temp = -temp;
                    }
                    for k in 1..=npt {
                        set(pq, k, get(pq, k) + temp * get2(zmat, npt, k, j));
                    }
                }
                let mut gqsq = 0.0;
                for i in 1..=n {
                    set(gq, i, get(gq, i) + diff * get2(bmat, ndim, knew, i));
                    gqsq = gqsq + get(gq, i) * get(gq, i);
                    set2(xpt, npt, knew, i, get(xnew, i));
                }
                if ksave == 0 && delta == rho {
                    if ratio.abs() > 1.0e-2 {
                        itest = 0;
                    } else {
                        for k in 1..=npt {
                            set(vlag, k, get(fval, k) - get(fval, kopt));
                        }
                        let mut gisq = 0.0;
                        for i in 1..=n {
                            let mut sum = 0.0;
                            for k in 1..=npt {
                                sum = sum + get2(bmat, ndim, k, i) * get(vlag, k);
                            }
                            gisq = gisq + sum * sum;
                            set(wwork, i, sum);
                        }
                        itest += 1;
                        if gqsq < 100.0 * gisq {
                            itest = 0;
                        }
                        if itest >= 3 {
                            for i in 1..=n {
                                set(gq, i, get(wwork, i));
                            }
                            for ih in 1..=nh {
                                set(hq, ih, 0.0);
                            }
                            for j in 1..=nptm {
                                set(wwork, j, 0.0);
                                for k in 1..=npt {
                                    set(
                                        wwork,
                                        j,
                                        get(wwork, j) + get(vlag, k) * get2(zmat, npt, k, j),
                                    );
                                }
                                if j < idz {
                                    set(wwork, j, -get(wwork, j));
                                }
                            }
                            for k in 1..=npt {
                                set(pq, k, 0.0);
                                for j in 1..=nptm {
                                    set(pq, k, get(pq, k) + get2(zmat, npt, k, j) * get(wwork, j));
                                }
                            }
                            itest = 0;
                        }
                    }
                }
                if f < fsave {
                    kopt = knew;
                }
                if f <= fsave + tenth * vquad {
                    label = 100;
                    continue;
                }
                if ksave > 0 {
                    label = 100;
                    continue;
                }
                knew = 0;
                label = 460;
            }
            460 => {
                let mut distsq = (4.0 * delta) * delta;
                for k in 1..=npt {
                    let mut sum = 0.0;
                    for j in 1..=n {
                        let gap = get2(xpt, npt, k, j) - get(xopt, j);
                        sum = sum + gap * gap;
                    }
                    if sum > distsq {
                        knew = k;
                        distsq = sum;
                    }
                }
                if knew > 0 {
                    dstep = dmax1(dmin1(tenth * distsq.sqrt(), half * delta), rho);
                    dsq = dstep * dstep;
                    label = 120;
                    continue;
                }
                if ratio > 0.0 {
                    label = 100;
                    continue;
                }
                if dmax1(delta, dnorm) > rho {
                    label = 100;
                    continue;
                }
                label = 490;
            }
            490 => {
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
                    if iprint >= 2 {
                        // minqit prints and does not change the iteration variables.
                    }
                    label = 90;
                    continue;
                }
                if knew == -1 {
                    label = 290;
                    continue;
                }
                label = 530;
            }
            530 => {
                if fopt <= f {
                    for i in 1..=n {
                        set(x, i, get(xbase, i) + get(xopt, i));
                    }
                    f = fopt;
                }
                if iprint >= 1 {
                    // minqir prints and does not change the iteration variables.
                }
                let _ = f;
                return nf;
            }
            _ => return nf,
        }
    }
}
