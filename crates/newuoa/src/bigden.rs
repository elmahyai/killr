//! Denominator step, from minqa `bigden.f`.

use crate::fortran::{dmax1, get, get2, set, set2};

#[allow(clippy::too_many_arguments)]
pub(crate) fn bigden(
    n: i32,
    npt: i32,
    xopt: &[f64],
    xpt: &[f64],
    bmat: &[f64],
    zmat: &[f64],
    idz: i32,
    ndim: i32,
    kopt: i32,
    knew: i32,
    d: &mut [f64],
    w: &mut [f64],
    vlag: &mut [f64],
    beta: &mut f64,
    s: &mut [f64],
    wvec: &mut [f64],
    prod: &mut [f64],
) {
    let half = 0.5;
    let one = 1.0_f64;
    let quart = 0.25;
    let two = 2.0;
    let twopi = 8.0 * one.atan();
    let nptm = npt - n - 1;

    for k in 1..=npt {
        set(w, n + k, 0.0);
    }
    for j in 1..=nptm {
        let mut temp = get2(zmat, npt, knew, j);
        if j < idz {
            temp = -temp;
        }
        for k in 1..=npt {
            set(w, n + k, get(w, n + k) + temp * get2(zmat, npt, k, j));
        }
    }
    let alpha = get(w, n + knew);

    let mut dd = 0.0;
    let mut ds = 0.0;
    let mut ss = 0.0;
    let mut xoptsq = 0.0;
    for i in 1..=n {
        dd = dd + get(d, i) * get(d, i);
        set(s, i, get2(xpt, npt, knew, i) - get(xopt, i));
        ds = ds + get(d, i) * get(s, i);
        ss = ss + get(s, i) * get(s, i);
        xoptsq = xoptsq + get(xopt, i) * get(xopt, i);
    }
    if ds * ds > 0.99 * dd * ss {
        let mut ksav = knew;
        let mut dtest = ds * ds / ss;
        for k in 1..=npt {
            if k != kopt {
                let mut dstemp = 0.0;
                let mut sstemp = 0.0;
                for i in 1..=n {
                    let diff = get2(xpt, npt, k, i) - get(xopt, i);
                    dstemp = dstemp + get(d, i) * diff;
                    sstemp = sstemp + diff * diff;
                }
                if dstemp * dstemp / sstemp < dtest {
                    ksav = k;
                    dtest = dstemp * dstemp / sstemp;
                    ds = dstemp;
                    ss = sstemp;
                }
            }
        }
        for i in 1..=n {
            set(s, i, get2(xpt, npt, ksav, i) - get(xopt, i));
        }
    }
    let mut ssden = dd * ss - ds * ds;
    let mut iterc = 0;
    let mut densav = 0.0;

    let mut den = [0.0; 10];
    let mut denex = [0.0; 10];
    let mut par = [0.0; 10];
    let mut denold;
    let mut denmax;

    loop {
        iterc += 1;
        let temp = one / ssden.sqrt();
        let mut xoptd = 0.0;
        let mut xopts = 0.0;
        for i in 1..=n {
            set(s, i, temp * (dd * get(s, i) - ds * get(d, i)));
            xoptd = xoptd + get(xopt, i) * get(d, i);
            xopts = xopts + get(xopt, i) * get(s, i);
        }

        let tempa = half * xoptd * xoptd;
        let tempb = half * xopts * xopts;
        den[1] = dd * (xoptsq + half * dd) + tempa + tempb;
        den[2] = two * xoptd * dd;
        den[3] = two * xopts * dd;
        den[4] = tempa - tempb;
        den[5] = xoptd * xopts;
        for i in 6..=9 {
            den[i] = 0.0;
        }

        for k in 1..=npt {
            let mut tempa = 0.0;
            let mut tempb = 0.0;
            let mut tempc = 0.0;
            for i in 1..=n {
                tempa = tempa + get2(xpt, npt, k, i) * get(d, i);
                tempb = tempb + get2(xpt, npt, k, i) * get(s, i);
                tempc = tempc + get2(xpt, npt, k, i) * get(xopt, i);
            }
            set2(wvec, ndim, k, 1, quart * (tempa * tempa + tempb * tempb));
            set2(wvec, ndim, k, 2, tempa * tempc);
            set2(wvec, ndim, k, 3, tempb * tempc);
            set2(wvec, ndim, k, 4, quart * (tempa * tempa - tempb * tempb));
            set2(wvec, ndim, k, 5, half * tempa * tempb);
        }
        for i in 1..=n {
            let ip = i + npt;
            set2(wvec, ndim, ip, 1, 0.0);
            set2(wvec, ndim, ip, 2, get(d, i));
            set2(wvec, ndim, ip, 3, get(s, i));
            set2(wvec, ndim, ip, 4, 0.0);
            set2(wvec, ndim, ip, 5, 0.0);
        }

        for jc in 1..=5 {
            let mut nw = npt;
            if jc == 2 || jc == 3 {
                nw = ndim;
            }
            for k in 1..=npt {
                set2(prod, ndim, k, jc, 0.0);
            }
            for j in 1..=nptm {
                let mut sum = 0.0;
                for k in 1..=npt {
                    sum = sum + get2(zmat, npt, k, j) * get2(wvec, ndim, k, jc);
                }
                if j < idz {
                    sum = -sum;
                }
                for k in 1..=npt {
                    set2(
                        prod,
                        ndim,
                        k,
                        jc,
                        get2(prod, ndim, k, jc) + sum * get2(zmat, npt, k, j),
                    );
                }
            }
            if nw == ndim {
                for k in 1..=npt {
                    let mut sum = 0.0;
                    for j in 1..=n {
                        sum = sum + get2(bmat, ndim, k, j) * get2(wvec, ndim, npt + j, jc);
                    }
                    set2(prod, ndim, k, jc, get2(prod, ndim, k, jc) + sum);
                }
            }
            for j in 1..=n {
                let mut sum = 0.0;
                for i in 1..=nw {
                    sum = sum + get2(bmat, ndim, i, j) * get2(wvec, ndim, i, jc);
                }
                set2(prod, ndim, npt + j, jc, sum);
            }
        }

        for k in 1..=ndim {
            let mut sum = 0.0;
            for i in 1..=5 {
                par[i] = half * get2(prod, ndim, k, i as i32) * get2(wvec, ndim, k, i as i32);
                sum = sum + par[i];
            }
            den[1] = den[1] - par[1] - sum;
            let mut tempa = get2(prod, ndim, k, 1) * get2(wvec, ndim, k, 2)
                + get2(prod, ndim, k, 2) * get2(wvec, ndim, k, 1);
            let mut tempb = get2(prod, ndim, k, 2) * get2(wvec, ndim, k, 4)
                + get2(prod, ndim, k, 4) * get2(wvec, ndim, k, 2);
            let mut tempc = get2(prod, ndim, k, 3) * get2(wvec, ndim, k, 5)
                + get2(prod, ndim, k, 5) * get2(wvec, ndim, k, 3);
            den[2] = den[2] - tempa - half * (tempb + tempc);
            den[6] = den[6] - half * (tempb - tempc);
            tempa = get2(prod, ndim, k, 1) * get2(wvec, ndim, k, 3)
                + get2(prod, ndim, k, 3) * get2(wvec, ndim, k, 1);
            tempb = get2(prod, ndim, k, 2) * get2(wvec, ndim, k, 5)
                + get2(prod, ndim, k, 5) * get2(wvec, ndim, k, 2);
            tempc = get2(prod, ndim, k, 3) * get2(wvec, ndim, k, 4)
                + get2(prod, ndim, k, 4) * get2(wvec, ndim, k, 3);
            den[3] = den[3] - tempa - half * (tempb - tempc);
            den[7] = den[7] - half * (tempb + tempc);
            tempa = get2(prod, ndim, k, 1) * get2(wvec, ndim, k, 4)
                + get2(prod, ndim, k, 4) * get2(wvec, ndim, k, 1);
            den[4] = den[4] - tempa - par[2] + par[3];
            tempa = get2(prod, ndim, k, 1) * get2(wvec, ndim, k, 5)
                + get2(prod, ndim, k, 5) * get2(wvec, ndim, k, 1);
            tempb = get2(prod, ndim, k, 2) * get2(wvec, ndim, k, 3)
                + get2(prod, ndim, k, 3) * get2(wvec, ndim, k, 2);
            den[5] = den[5] - tempa - half * tempb;
            den[8] = den[8] - par[4] + par[5];
            tempa = get2(prod, ndim, k, 4) * get2(wvec, ndim, k, 5)
                + get2(prod, ndim, k, 5) * get2(wvec, ndim, k, 4);
            den[9] = den[9] - half * tempa;
        }

        let mut sum = 0.0;
        for i in 1..=5 {
            par[i] = half * get2(prod, ndim, knew, i as i32) * get2(prod, ndim, knew, i as i32);
            sum = sum + par[i];
        }
        denex[1] = alpha * den[1] + par[1] + sum;
        let mut tempa = two * get2(prod, ndim, knew, 1) * get2(prod, ndim, knew, 2);
        let mut tempb = get2(prod, ndim, knew, 2) * get2(prod, ndim, knew, 4);
        let mut tempc = get2(prod, ndim, knew, 3) * get2(prod, ndim, knew, 5);
        denex[2] = alpha * den[2] + tempa + tempb + tempc;
        denex[6] = alpha * den[6] + tempb - tempc;
        tempa = two * get2(prod, ndim, knew, 1) * get2(prod, ndim, knew, 3);
        tempb = get2(prod, ndim, knew, 2) * get2(prod, ndim, knew, 5);
        tempc = get2(prod, ndim, knew, 3) * get2(prod, ndim, knew, 4);
        denex[3] = alpha * den[3] + tempa + tempb - tempc;
        denex[7] = alpha * den[7] + tempb + tempc;
        tempa = two * get2(prod, ndim, knew, 1) * get2(prod, ndim, knew, 4);
        denex[4] = alpha * den[4] + tempa + par[2] - par[3];
        tempa = two * get2(prod, ndim, knew, 1) * get2(prod, ndim, knew, 5);
        denex[5] = alpha * den[5] + tempa + get2(prod, ndim, knew, 2) * get2(prod, ndim, knew, 3);
        denex[8] = alpha * den[8] + par[4] - par[5];
        denex[9] = alpha * den[9] + get2(prod, ndim, knew, 4) * get2(prod, ndim, knew, 5);

        sum = denex[1] + denex[2] + denex[4] + denex[6] + denex[8];
        denold = sum;
        denmax = sum;
        let mut isave = 0;
        let iu = 49;
        let temp = twopi / ((iu + 1) as f64);
        par[1] = one;
        let mut tempa_s = 0.0;
        let mut tempb_s = 0.0;
        for i in 1..=iu {
            let angle = (i as f64) * temp;
            par[2] = angle.cos();
            par[3] = angle.sin();
            let mut j = 4;
            while j <= 8 {
                let pjm2 = par[(j - 2) as usize];
                let pjm1 = par[(j - 1) as usize];
                par[j as usize] = par[2] * pjm2 - par[3] * pjm1;
                par[(j + 1) as usize] = par[2] * pjm1 + par[3] * pjm2;
                j += 2;
            }
            let sumold = sum;
            sum = 0.0;
            for j in 1..=9 {
                sum = sum + denex[j] * par[j];
            }
            if sum.abs() > denmax.abs() {
                denmax = sum;
                isave = i;
                tempa_s = sumold;
            } else if i == isave + 1 {
                tempb_s = sum;
            }
        }
        if isave == 0 {
            tempa_s = sum;
        }
        if isave == iu {
            tempb_s = denold;
        }
        let mut step = 0.0;
        if tempa_s != tempb_s {
            tempa_s = tempa_s - denmax;
            tempb_s = tempb_s - denmax;
            step = half * (tempa_s - tempb_s) / (tempa_s + tempb_s);
        }
        let angle = temp * ((isave as f64) + step);

        par[2] = angle.cos();
        par[3] = angle.sin();
        let mut j = 4;
        while j <= 8 {
            let pjm2 = par[(j - 2) as usize];
            let pjm1 = par[(j - 1) as usize];
            par[j as usize] = par[2] * pjm2 - par[3] * pjm1;
            par[(j + 1) as usize] = par[2] * pjm1 + par[3] * pjm2;
            j += 2;
        }
        *beta = 0.0;
        denmax = 0.0;
        for j in 1..=9 {
            *beta = *beta + den[j] * par[j];
            denmax = denmax + denex[j] * par[j];
        }
        for k in 1..=ndim {
            set(vlag, k, 0.0);
            for j in 1..=5 {
                set(
                    vlag,
                    k,
                    get(vlag, k) + get2(prod, ndim, k, j) * par[j as usize],
                );
            }
        }
        let tau = get(vlag, knew);
        dd = 0.0;
        let mut tempa = 0.0;
        let mut tempb = 0.0;
        for i in 1..=n {
            set(d, i, par[2] * get(d, i) + par[3] * get(s, i));
            set(w, i, get(xopt, i) + get(d, i));
            dd = dd + get(d, i) * get(d, i);
            tempa = tempa + get(d, i) * get(w, i);
            tempb = tempb + get(w, i) * get(w, i);
        }
        if iterc >= n {
            break;
        }
        if iterc > 1 {
            densav = dmax1(densav, denold);
        }
        if denmax.abs() <= 1.1 * densav.abs() {
            break;
        }
        densav = denmax;

        for i in 1..=n {
            let temp = tempa * get(xopt, i) + tempb * get(d, i) - get(vlag, npt + i);
            set(s, i, tau * get2(bmat, ndim, knew, i) + alpha * temp);
        }
        for k in 1..=npt {
            let mut sum = 0.0;
            for j in 1..=n {
                sum = sum + get2(xpt, npt, k, j) * get(w, j);
            }
            let temp = (tau * get(w, n + k) - alpha * get(vlag, k)) * sum;
            for i in 1..=n {
                set(s, i, get(s, i) + temp * get2(xpt, npt, k, i));
            }
        }
        ss = 0.0;
        ds = 0.0;
        for i in 1..=n {
            ss = ss + get(s, i) * get(s, i);
            ds = ds + get(d, i) * get(s, i);
        }
        ssden = dd * ss - ds * ds;
        if ssden < 1.0e-8 * dd * ss {
            break;
        }
    }

    for k in 1..=ndim {
        set(w, k, 0.0);
        for j in 1..=5 {
            set(w, k, get(w, k) + get2(wvec, ndim, k, j) * par[j as usize]);
        }
    }
    set(vlag, kopt, get(vlag, kopt) + one);
}
