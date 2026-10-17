//! `UOBYQA` and `UOBYQB` from minqa `src/uobyqa.f` and `src/uobyqb.f`.
//!
//! The working array is partitioned as in `UOBYQA`. `VLAG` starts at the same
//! address as `H`, so both live in `region`. `minqit` and `minqir` do not
//! change the numbers.

use crate::fortran::{ix, ix2, pow15};
use crate::lagmax::lagmax;
use crate::trstep::trstep;

enum Lab {
    At30,
    At50,
    At60,
    At70,
    At100,
    At120,
    At240,
    At290,
    At310,
    At420,
}

pub(crate) fn uobyqa(
    n: i32,
    x: &mut [f64],
    rhobeg: f64,
    rhoend: f64,
    iprint: i32,
    maxfun: i32,
    w: &mut [f64],
    ierr: &mut i32,
    calfun: &mut dyn FnMut(&[f64]) -> f64,
) -> i32 {
    let npt = (n * n + 3 * n + 2) / 2;
    let n_us = n as usize;
    let npt_us = npt as usize;
    let (xbase, rest) = w.split_at_mut(n_us);
    let (xopt, rest) = rest.split_at_mut(n_us);
    let (xnew, rest) = rest.split_at_mut(n_us);
    let (xpt, rest) = rest.split_at_mut(n_us * npt_us);
    let (pq, rest) = rest.split_at_mut(npt_us - 1);
    let (pl, region) = rest.split_at_mut((npt_us - 1) * npt_us);
    *ierr = 0;
    uobyqb(
        n, npt, x, rhobeg, rhoend, iprint, maxfun, xbase, xopt, xnew, xpt, pq, pl, region,
        ierr, calfun,
    )
}

fn uobyqb(
    n: i32,
    npt: i32,
    x: &mut [f64],
    rhobeg: f64,
    rhoend: f64,
    iprint: i32,
    maxfun: i32,
    xbase: &mut [f64],
    xopt: &mut [f64],
    xnew: &mut [f64],
    xpt: &mut [f64],
    pq: &mut [f64],
    pl: &mut [f64],
    region: &mut [f64],
    ierr: &mut i32,
    calfun: &mut dyn FnMut(&[f64]) -> f64,
) -> i32 {
    let one = 1.0;
    let two = 2.0;
    let zero = 0.0;
    let half = 0.5;
    let tol = 0.01;
    let nnp = n + n + 1;
    let nptm = npt - 1;
    let nftest = maxfun.max(1);
    let n_us = n as usize;
    let g_off = n_us * n_us;
    let d_off = g_off + n_us;
    let w_off = d_off + n_us;

    let mut rho = rhobeg;
    let mut rhosq = rho * rho;
    let mut nf = 0;
    for i in 1..=n {
        xbase[ix(i)] = x[ix(i)];
        for k in 1..=npt {
            xpt[ix2(npt, k, i)] = zero;
        }
    }
    for k in 1..=npt {
        for j in 1..=nptm {
            pl[ix2(npt, k, j)] = zero;
        }
    }

    let mut f = zero;
    let mut fopt = zero;
    let mut fbase = zero;
    let mut fsave = zero;
    let mut diff = zero;
    let mut vquad;
    let mut sixthm = zero;
    let mut delta = zero;
    let mut tworsq = zero;
    let mut dnorm = zero;
    let mut errtol = zero;
    let mut ddknew = zero;
    let mut j = 0;
    let mut jswitch = 0;
    let mut ih = 0;
    let mut ip = 0;
    let mut iq = 0;
    let mut kopt = 0;
    let mut knew = 0;
    let mut ksave = 0;
    let mut label = Lab::At30;

    loop {
        match label {
            Lab::At30 => {
                for i in 1..=n {
                    x[ix(i)] = xbase[ix(i)] + xpt[ix2(npt, nf + 1, i)];
                }
                label = Lab::At120;
            }
            Lab::At50 => {
                if nf == 1 {
                    fopt = f;
                    kopt = nf;
                    fbase = f;
                    j = 0;
                    jswitch = -1;
                    ih = n;
                } else if f < fopt {
                    fopt = f;
                    kopt = nf;
                }
                if nf <= nnp {
                    jswitch = -jswitch;
                    if jswitch > 0 {
                        if j >= 1 {
                            ih += j;
                            if region[w_off + ix(j)] < zero {
                                region[d_off + ix(j)] = (fsave + f - two * fbase) / rhosq;
                                pq[ix(j)] = (fsave - f) / (two * rho);
                                pl[ix2(npt, 1, ih)] = -two / rhosq;
                                pl[ix2(npt, nf - 1, j)] = half / rho;
                                pl[ix2(npt, nf - 1, ih)] = one / rhosq;
                            } else {
                                pq[ix(j)] = (4.0 * fsave - 3.0 * fbase - f) / (two * rho);
                                region[d_off + ix(j)] = (fbase + f - two * fsave) / rhosq;
                                pl[ix2(npt, 1, j)] = -1.5 / rho;
                                pl[ix2(npt, 1, ih)] = one / rhosq;
                                pl[ix2(npt, nf - 1, j)] = two / rho;
                                pl[ix2(npt, nf - 1, ih)] = -two / rhosq;
                            }
                            pq[ix(ih)] = region[d_off + ix(j)];
                            pl[ix2(npt, nf, j)] = -half / rho;
                            pl[ix2(npt, nf, ih)] = one / rhosq;
                        }
                        if j < n {
                            j += 1;
                            xpt[ix2(npt, nf + 1, j)] = rho;
                        }
                    } else {
                        fsave = f;
                        if f < fbase {
                            region[w_off + ix(j)] = rho;
                            xpt[ix2(npt, nf + 1, j)] = two * rho;
                        } else {
                            region[w_off + ix(j)] = -rho;
                            xpt[ix2(npt, nf + 1, j)] = -rho;
                        }
                    }
                    if nf < nnp {
                        label = Lab::At30;
                        continue;
                    }
                    ih = n;
                    ip = 1;
                    iq = 2;
                }
                ih += 1;
                if nf > nnp {
                    let temp = one / (region[w_off + ix(ip)] * region[w_off + ix(iq)]);
                    let tempa = f
                        - fbase
                        - region[w_off + ix(ip)] * pq[ix(ip)]
                        - region[w_off + ix(iq)] * pq[ix(iq)];
                    pq[ix(ih)] = (tempa
                        - half * rhosq * (region[d_off + ix(ip)] + region[d_off + ix(iq)]))
                        * temp;
                    pl[ix2(npt, 1, ih)] = temp;
                    let mut iw = ip + ip;
                    if region[w_off + ix(ip)] < zero {
                        iw += 1;
                    }
                    pl[ix2(npt, iw, ih)] = -temp;
                    iw = iq + iq;
                    if region[w_off + ix(iq)] < zero {
                        iw += 1;
                    }
                    pl[ix2(npt, iw, ih)] = -temp;
                    pl[ix2(npt, nf, ih)] = temp;
                    ip += 1;
                }
                if ip == iq {
                    ih += 1;
                    ip = 1;
                    iq += 1;
                }
                if nf < npt {
                    xpt[ix2(npt, nf + 1, ip)] = region[w_off + ix(ip)];
                    xpt[ix2(npt, nf + 1, iq)] = region[w_off + ix(iq)];
                    label = Lab::At30;
                    continue;
                }
                sixthm = zero;
                delta = rho;
                label = Lab::At60;
            }
            Lab::At60 => {
                tworsq = (two * rho) * (two * rho);
                rhosq = rho * rho;
                label = Lab::At70;
            }
            Lab::At70 => {
                knew = 0;
                let mut ihg = n;
                for jg in 1..=n {
                    xopt[ix(jg)] = xpt[ix2(npt, kopt, jg)];
                    region[g_off + ix(jg)] = pq[ix(jg)];
                    for ig in 1..=jg {
                        ihg += 1;
                        let pqih = pq[ix(ihg)];
                        region[g_off + ix(ig)] = region[g_off + ix(ig)] + pqih * xopt[ix(jg)];
                        if ig < jg {
                            region[g_off + ix(jg)] =
                                region[g_off + ix(jg)] + pqih * xopt[ix(ig)];
                        }
                        region[ix2(n, ig, jg)] = pqih;
                    }
                }
                let evalue = trust_step(region, n, delta, tol);
                let mut temp = zero;
                for i in 1..=n {
                    let di = region[d_off + ix(i)];
                    temp = temp + di * di;
                }
                dnorm = delta.min(temp.sqrt());
                errtol = -one;
                if dnorm < half * rho {
                    knew = -1;
                    errtol = half * evalue * rho * rho;
                    if nf <= npt + 9 {
                        errtol = zero;
                    }
                    label = Lab::At290;
                    continue;
                }
                label = Lab::At100;
            }
            Lab::At100 => {
                for i in 1..=n {
                    xnew[ix(i)] = xopt[ix(i)] + region[d_off + ix(i)];
                    x[ix(i)] = xbase[ix(i)] + xnew[ix(i)];
                }
                label = Lab::At120;
            }
            Lab::At120 => {
                if nf >= nftest {
                    *ierr = 390;
                    label = Lab::At420;
                    continue;
                }
                nf += 1;
                f = calfun(x);
                if nf <= npt {
                    label = Lab::At50;
                    continue;
                }
                if knew == -1 {
                    label = Lab::At420;
                    continue;
                }
                vquad = zero;
                let mut ihq = n;
                for jq in 1..=n {
                    region[w_off + ix(jq)] = region[d_off + ix(jq)];
                    vquad = vquad + region[w_off + ix(jq)] * pq[ix(jq)];
                    for iq_ in 1..=jq {
                        ihq += 1;
                        region[w_off + ix(ihq)] = region[d_off + ix(iq_)] * xnew[ix(jq)]
                            + region[d_off + ix(jq)] * xopt[ix(iq_)];
                        if iq_ == jq {
                            region[w_off + ix(ihq)] = half * region[w_off + ix(ihq)];
                        }
                        vquad = vquad + region[w_off + ix(ihq)] * pq[ix(ihq)];
                    }
                }
                for k in 1..=npt {
                    let mut temp = zero;
                    for jv in 1..=nptm {
                        temp = temp + region[w_off + ix(jv)] * pl[ix2(npt, k, jv)];
                    }
                    region[ix(k)] = temp;
                }
                region[ix(kopt)] = region[ix(kopt)] + one;
                diff = f - fopt - vquad;
                let mut sum = zero;
                for k in 1..=npt {
                    let mut temp = zero;
                    for i in 1..=n {
                        let gap = xpt[ix2(npt, k, i)] - xnew[ix(i)];
                        temp = temp + gap * gap;
                    }
                    temp = temp.sqrt();
                    sum = sum + (temp * temp * temp * region[ix(k)]).abs();
                }
                sixthm = sixthm.max(diff.abs() / sum);
                fsave = fopt;
                if f < fopt {
                    fopt = f;
                    for i in 1..=n {
                        xopt[ix(i)] = xnew[ix(i)];
                    }
                }
                ksave = knew;
                if knew > 0 {
                    label = Lab::At240;
                    continue;
                }
                if vquad >= zero {
                    *ierr = 2101;
                    label = Lab::At420;
                    continue;
                }
                let ratio = (f - fsave) / vquad;
                if ratio <= 0.1 {
                    delta = half * dnorm;
                } else if ratio <= 0.7 {
                    delta = (half * delta).max(dnorm);
                } else {
                    delta = delta.max(1.25 * dnorm).max(dnorm + rho);
                }
                if delta <= 1.5 * rho {
                    delta = rho;
                }
                let mut ktemp = 0;
                let mut detrat = zero;
                if f >= fsave {
                    ktemp = kopt;
                    detrat = one;
                }
                for k in 1..=npt {
                    let mut sumk = zero;
                    for i in 1..=n {
                        let gap = xpt[ix2(npt, k, i)] - xopt[ix(i)];
                        sumk = sumk + gap * gap;
                    }
                    let mut temp = region[ix(k)].abs();
                    if sumk > rhosq {
                        temp = temp * pow15(sumk / rhosq);
                    }
                    if temp > detrat && k != ktemp {
                        detrat = temp;
                        ddknew = sumk;
                        knew = k;
                    }
                }
                if knew == 0 {
                    label = Lab::At290;
                    continue;
                }
                label = Lab::At240;
            }
            Lab::At240 => {
                for i in 1..=n {
                    xpt[ix2(npt, knew, i)] = xnew[ix(i)];
                }
                let temp = one / region[ix(knew)];
                for jv in 1..=nptm {
                    pl[ix2(npt, knew, jv)] = temp * pl[ix2(npt, knew, jv)];
                    pq[ix(jv)] = pq[ix(jv)] + diff * pl[ix2(npt, knew, jv)];
                }
                for k in 1..=npt {
                    if k != knew {
                        let tempk = region[ix(k)];
                        for jv in 1..=nptm {
                            pl[ix2(npt, k, jv)] =
                                pl[ix2(npt, k, jv)] - tempk * pl[ix2(npt, knew, jv)];
                        }
                    }
                }
                if f < fsave {
                    kopt = knew;
                    label = Lab::At70;
                    continue;
                }
                if ksave > 0 {
                    label = Lab::At70;
                    continue;
                }
                if dnorm > two * rho {
                    label = Lab::At70;
                    continue;
                }
                if ddknew > tworsq {
                    label = Lab::At70;
                    continue;
                }
                label = Lab::At290;
            }
            Lab::At290 => {
                for k in 1..=npt {
                    region[w_off + ix(k)] = zero;
                    for i in 1..=n {
                        let gap = xpt[ix2(npt, k, i)] - xopt[ix(i)];
                        region[w_off + ix(k)] = region[w_off + ix(k)] + gap * gap;
                    }
                }
                label = Lab::At310;
            }
            Lab::At310 => {
                knew = -1;
                let mut distest = tworsq;
                for k in 1..=npt {
                    if region[w_off + ix(k)] > distest {
                        knew = k;
                        distest = region[w_off + ix(k)];
                    }
                }
                if knew > 0 {
                    let mut ihl = n;
                    let mut sumh = zero;
                    for jl in 1..=n {
                        region[g_off + ix(jl)] = pl[ix2(npt, knew, jl)];
                        let mut temp = zero;
                        for il in 1..=jl {
                            ihl += 1;
                            temp = pl[ix2(npt, knew, ihl)];
                            region[g_off + ix(jl)] =
                                region[g_off + ix(jl)] + temp * xopt[ix(il)];
                            if il < jl {
                                region[g_off + ix(il)] =
                                    region[g_off + ix(il)] + temp * xopt[ix(jl)];
                                sumh = sumh + temp * temp;
                            }
                            region[ix2(n, il, jl)] = temp;
                        }
                        sumh = sumh + half * temp * temp;
                    }
                    let mut wmult = zero;
                    if errtol > zero {
                        region[w_off + ix(knew)] = zero;
                        let mut sumg = zero;
                        for i in 1..=n {
                            let gi = region[g_off + ix(i)];
                            sumg = sumg + gi * gi;
                        }
                        let estim = rho * (sumg.sqrt() + rho * (half * sumh).sqrt());
                        wmult = sixthm * pow15(distest);
                        if wmult * estim <= errtol {
                            label = Lab::At310;
                            continue;
                        }
                    }
                    let vmax = lagrange_step(region, xnew, n, rho);
                    if errtol > zero && wmult * vmax <= errtol {
                        label = Lab::At310;
                        continue;
                    }
                    label = Lab::At100;
                    continue;
                }
                if dnorm > rho {
                    label = Lab::At70;
                    continue;
                }
                if rho > rhoend {
                    let mut ihs = n;
                    for js in 1..=n {
                        xbase[ix(js)] = xbase[ix(js)] + xopt[ix(js)];
                        for k in 1..=npt {
                            xpt[ix2(npt, k, js)] = xpt[ix2(npt, k, js)] - xopt[ix(js)];
                        }
                        for is_ in 1..=js {
                            ihs += 1;
                            pq[ix(is_)] = pq[ix(is_)] + pq[ix(ihs)] * xopt[ix(js)];
                            if is_ < js {
                                pq[ix(js)] = pq[ix(js)] + pq[ix(ihs)] * xopt[ix(is_)];
                                for k in 1..=npt {
                                    pl[ix2(npt, k, js)] = pl[ix2(npt, k, js)]
                                        + pl[ix2(npt, k, ihs)] * xopt[ix(is_)];
                                }
                            }
                            for k in 1..=npt {
                                pl[ix2(npt, k, is_)] = pl[ix2(npt, k, is_)]
                                    + pl[ix2(npt, k, ihs)] * xopt[ix(js)];
                            }
                        }
                    }
                    delta = half * rho;
                    let ratio = rho / rhoend;
                    if ratio <= 16.0 {
                        rho = rhoend;
                    } else if ratio <= 250.0 {
                        rho = ratio.sqrt() * rhoend;
                    } else {
                        rho = 0.1 * rho;
                    }
                    delta = delta.max(rho);
                    if iprint >= 2 {
                        minqit(iprint, rho, nf, fopt, n, xbase, xopt);
                    }
                    label = Lab::At60;
                    continue;
                }
                if errtol >= zero {
                    label = Lab::At100;
                    continue;
                }
                label = Lab::At420;
            }
            Lab::At420 => {
                if fopt <= f {
                    for i in 1..=n {
                        x[ix(i)] = xbase[ix(i)] + xopt[ix(i)];
                    }
                    f = fopt;
                }
                if iprint >= 1 {
                    minqir(iprint, f, nf, n, x);
                }
                return nf;
            }
        }
    }
}

fn trust_step(region: &mut [f64], n: i32, delta: f64, tol: f64) -> f64 {
    let n_us = n as usize;
    let (h, rest) = region.split_at_mut(n_us * n_us);
    let (g, rest) = rest.split_at_mut(n_us);
    let (d, rest) = rest.split_at_mut(n_us);
    let (gg, rest) = rest.split_at_mut(n_us);
    let (td, rest) = rest.split_at_mut(n_us);
    let (tn, rest) = rest.split_at_mut(n_us);
    let (w, rest) = rest.split_at_mut(n_us);
    let (piv, rest) = rest.split_at_mut(n_us);
    let (z, _) = rest.split_at_mut(n_us);
    trstep(n, g, h, delta, tol, d, gg, td, tn, w, piv, z)
}

fn lagrange_step(region: &mut [f64], xnew: &mut [f64], n: i32, rho: f64) -> f64 {
    let n_us = n as usize;
    let (h, rest) = region.split_at_mut(n_us * n_us);
    let (g, rest) = rest.split_at_mut(n_us);
    let (d, _) = rest.split_at_mut(n_us);
    lagmax(n, g, h, rho, d, xnew)
}

fn minqit(
    iprint: i32,
    rho: f64,
    nf: i32,
    fopt: f64,
    n: i32,
    xbase: &[f64],
    xopt: &[f64],
) {
    let _ = (iprint, rho, nf, fopt, n, xbase, xopt);
}

fn minqir(iprint: i32, f: f64, nf: i32, n: i32, x: &[f64]) {
    let _ = (iprint, f, nf, n, x);
}
