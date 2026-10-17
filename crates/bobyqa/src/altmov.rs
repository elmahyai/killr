//! `ALTMOV` from minqa `altmov.f`.

use crate::arr::{dmax1, dmin1, g, g2, s};

#[allow(unused_assignments)]
pub fn altmov(
    n: i32,
    npt: i32,
    xpt: &[f64],
    xopt: &[f64],
    bmat: &[f64],
    zmat: &[f64],
    ndim: i32,
    sl: &[f64],
    su: &[f64],
    kopt: i32,
    knew: i32,
    adelt: f64,
    xnew: &mut [f64],
    xalt: &mut [f64],
    glag: &mut [f64],
    hcol: &mut [f64],
    w: &mut [f64],
) -> (f64, f64) {
    let half = 0.5;
    let one = 1.0;
    let zero = 0.0;
    let const_ = one + 2.0_f64.sqrt();

    for k in 1..=npt {
        s(hcol, k, zero);
    }
    for j in 1..=(npt - n - 1) {
        let temp = g2(zmat, npt, knew, j);
        for k in 1..=npt {
            s(hcol, k, g(hcol, k) + temp * g2(zmat, npt, k, j));
        }
    }
    let alpha = g(hcol, knew);
    let ha = half * alpha;

    for i in 1..=n {
        s(glag, i, g2(bmat, ndim, knew, i));
    }
    for k in 1..=npt {
        let mut temp = zero;
        for j in 1..=n {
            temp = temp + g2(xpt, npt, k, j) * g(xopt, j);
        }
        temp = g(hcol, k) * temp;
        for i in 1..=n {
            s(glag, i, g(glag, i) + temp * g2(xpt, npt, k, i));
        }
    }

    let mut presav = zero;
    let mut ksav = 0;
    let mut stpsav = zero;
    #[allow(unused_assignments)]
    let mut ibdsav = 0;
    for k in 1..=npt {
        if k == kopt {
            continue;
        }
        let mut dderiv = zero;
        let mut distsq = zero;
        for i in 1..=n {
            let temp = g2(xpt, npt, k, i) - g(xopt, i);
            dderiv = dderiv + g(glag, i) * temp;
            distsq = distsq + temp * temp;
        }
        let mut subd = adelt / distsq.sqrt();
        let mut slbd = -subd;
        let mut ilbd = 0;
        let mut iubd = 0;
        let sumin = dmin1(one, subd);
        for i in 1..=n {
            let temp = g2(xpt, npt, k, i) - g(xopt, i);
            if temp > zero {
                if slbd * temp < g(sl, i) - g(xopt, i) {
                    slbd = (g(sl, i) - g(xopt, i)) / temp;
                    ilbd = -i;
                }
                if subd * temp > g(su, i) - g(xopt, i) {
                    subd = dmax1(sumin, (g(su, i) - g(xopt, i)) / temp);
                    iubd = i;
                }
            } else if temp < zero {
                if slbd * temp > g(su, i) - g(xopt, i) {
                    slbd = (g(su, i) - g(xopt, i)) / temp;
                    ilbd = i;
                }
                if subd * temp < g(sl, i) - g(xopt, i) {
                    subd = dmax1(sumin, (g(sl, i) - g(xopt, i)) / temp);
                    iubd = -i;
                }
            }
        }

        let mut step;
        let mut vlag;
        let mut isbd;
        if k == knew {
            let diff = dderiv - one;
            step = slbd;
            vlag = slbd * (dderiv - slbd * diff);
            isbd = ilbd;
            let temp = subd * (dderiv - subd * diff);
            if temp.abs() > vlag.abs() {
                step = subd;
                vlag = temp;
                isbd = iubd;
            }
            let tempd = half * dderiv;
            let tempa = tempd - diff * slbd;
            let tempb = tempd - diff * subd;
            if tempa * tempb < zero {
                let temp = (tempd * tempd) / diff;
                if temp.abs() > vlag.abs() {
                    step = tempd / diff;
                    vlag = temp;
                    isbd = 0;
                }
            }
        } else {
            step = slbd;
            vlag = slbd * (one - slbd);
            isbd = ilbd;
            let temp = subd * (one - subd);
            if temp.abs() > vlag.abs() {
                step = subd;
                vlag = temp;
                isbd = iubd;
            }
            if subd > half && vlag.abs() < 0.25 {
                step = half;
                vlag = 0.25;
                isbd = 0;
            }
            vlag = vlag * dderiv;
        }

        let temp = step * (one - step) * distsq;
        let predsq = (vlag * vlag) * (vlag * vlag + ha * temp * temp);
        if predsq > presav {
            presav = predsq;
            ksav = k;
            stpsav = step;
            ibdsav = isbd;
        }
    }

    // The extracted minqa source clears IBDSAV before XNEW is built.
    ibdsav = 0;
    for i in 1..=n {
        let temp = g(xopt, i) + stpsav * (g2(xpt, npt, ksav, i) - g(xopt, i));
        s(xnew, i, dmax1(g(sl, i), dmin1(g(su, i), temp)));
    }
    if ibdsav < 0 {
        s(xnew, -ibdsav, g(sl, -ibdsav));
    }
    if ibdsav > 0 {
        s(xnew, ibdsav, g(su, ibdsav));
    }

    let bigstp = adelt + adelt;
    let mut iflag = 0;
    let mut csave = zero;
    let mut cauchy;
    loop {
        let mut wfixsq = zero;
        let mut ggfree = zero;
        for i in 1..=n {
            s(w, i, zero);
            let tempa = dmin1(g(xopt, i) - g(sl, i), g(glag, i));
            let tempb = dmax1(g(xopt, i) - g(su, i), g(glag, i));
            if tempa > zero || tempb < zero {
                s(w, i, bigstp);
                ggfree = ggfree + g(glag, i) * g(glag, i);
            }
        }
        if ggfree == zero {
            cauchy = zero;
            break;
        }

        let mut step = zero;
        loop {
            let temp = adelt * adelt - wfixsq;
            if temp > zero {
                let wsqsav = wfixsq;
                step = (temp / ggfree).sqrt();
                ggfree = zero;
                for i in 1..=n {
                    if g(w, i) == bigstp {
                        let temp = g(xopt, i) - step * g(glag, i);
                        if temp <= g(sl, i) {
                            s(w, i, g(sl, i) - g(xopt, i));
                            wfixsq = wfixsq + g(w, i) * g(w, i);
                        } else if temp >= g(su, i) {
                            s(w, i, g(su, i) - g(xopt, i));
                            wfixsq = wfixsq + g(w, i) * g(w, i);
                        } else {
                            ggfree = ggfree + g(glag, i) * g(glag, i);
                        }
                    }
                }
                if wfixsq > wsqsav && ggfree > zero {
                    continue;
                }
            }
            break;
        }

        let mut gw = zero;
        for i in 1..=n {
            if g(w, i) == bigstp {
                s(w, i, -step * g(glag, i));
                s(
                    xalt,
                    i,
                    dmax1(g(sl, i), dmin1(g(su, i), g(xopt, i) + g(w, i))),
                );
            } else if g(w, i) == zero {
                s(xalt, i, g(xopt, i));
            } else if g(glag, i) > zero {
                s(xalt, i, g(sl, i));
            } else {
                s(xalt, i, g(su, i));
            }
            gw = gw + g(glag, i) * g(w, i);
        }

        let mut curv = zero;
        for k in 1..=npt {
            let mut temp = zero;
            for j in 1..=n {
                temp = temp + g2(xpt, npt, k, j) * g(w, j);
            }
            curv = curv + (g(hcol, k) * temp) * temp;
        }
        if iflag == 1 {
            curv = -curv;
        }
        if curv > -gw && curv < -const_ * gw {
            let scale = -gw / curv;
            for i in 1..=n {
                let temp = g(xopt, i) + scale * g(w, i);
                s(xalt, i, dmax1(g(sl, i), dmin1(g(su, i), temp)));
            }
            let half_scale = (half * gw) * scale;
            cauchy = half_scale * half_scale;
        } else {
            let t = gw + half * curv;
            cauchy = t * t;
        }

        if iflag == 0 {
            for i in 1..=n {
                s(glag, i, -g(glag, i));
                s(w, n + i, g(xalt, i));
            }
            csave = cauchy;
            iflag = 1;
            continue;
        }
        if csave > cauchy {
            for i in 1..=n {
                s(xalt, i, g(w, n + i));
            }
            cauchy = csave;
        }
        break;
    }
    (alpha, cauchy)
}
