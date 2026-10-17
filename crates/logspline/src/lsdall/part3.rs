//! Likelihood, step-size search, density evaluation, Gauss-Legendre
//! integration, the basis coefficients, and the first starting-value
//! statistics, remade from `src/lsdall.c`.

use super::tables::{GL12_W, GL12_Y, GL3_W, GL3_Y};
use super::{Lsd, NC};

/// `numbertester`: classify a value as -Inf (0), +Inf (1), NaN (2), or finite (3).
pub fn numbertester(aa: f64) -> i32 {
    let mut i1 = 0;
    let mut i2 = 0;
    let mut i3 = 0;
    let mut i4 = 0;
    if aa < 2.0 {
        i1 = 1;
    }
    if aa > 0.0 {
        i2 = 1;
    }
    if aa < 10f64.powf(200.0) {
        i3 = 1;
    }
    if aa > -10f64.powf(200.0) {
        i4 = 1;
    }
    if i1 + i2 + i3 + i4 >= 3 {
        return 3;
    }
    if i2 == 1 && i4 == 1 {
        return 1;
    }
    if i1 == 1 && i3 == 1 {
        return 0;
    }
    2
}

/// `expin`: analytic integral of `(a1 x^2 + a2 x + a3) exp(a4 x + a5)` between
/// `t1` and `t2`, with the sign and the version selected as in the C source.
pub fn expin(version: i32, t1: f64, t2: f64, a: &[f64]) -> f64 {
    if a[4] != 0.0 || version == 1 || version == 3 {
        let a1 = a[1] / a[4];
        let b1 = (a[2] - 2.0 * a1) / a[4];
        let c1 = (a[3] - b1) / a[4];
        let mut f1 = a1 * t1 * t1 + b1 * t1 + c1;
        let mut i1: i32 = 1;
        if f1 < 0.0 {
            i1 = -1;
        }
        f1 = f1.abs().ln() + a[4] * t1 + a[5];
        if f1 > 2000.0 {
            f1 = 2000.0;
        }
        if version == 2 || version == 4 {
            let mut f2 = a1 * t2 * t2 + b1 * t2 + c1;
            let mut i2: i32 = 1;
            if f2 < 0.0 {
                i2 = -1;
            }
            f2 = f2.abs().ln() + a[4] * t2 + a[5];
            if f2 > 2000.0 {
                f2 = 2000.0;
            }
            if version == 2 {
                return i1 as f64 * f1.exp() - i2 as f64 * f2.exp();
            }
            return i2 as f64 * f2.exp() - i1 as f64 * f1.exp();
        }
        if version == 1 {
            return i1 as f64 * f1.exp();
        }
        return -(i1 as f64) * f1.exp();
    }
    let a1 = (((a[1] / 3.0) * (t2 - t1) + a[2] / 2.0) * (t2 - t1) + a[3]) * (t2 - t1) * a[5].exp();
    if version == 4 {
        return a1;
    }
    -a1
}

/// `expin2`: the same integral with a higher-order leading polynomial.
pub fn expin2(version: i32, t1: f64, t2: f64, aa: &[f64], b1: f64, b0: f64) -> f64 {
    if b1 != 0.0 || version == 1 || version == 3 {
        let u6 = aa[6] / b1;
        let u5 = (aa[5] - 6.0 * u6) / b1;
        let u4 = (aa[4] - 5.0 * u5) / b1;
        let u3 = (aa[3] - 4.0 * u4) / b1;
        let u2 = (aa[2] - 3.0 * u3) / b1;
        let u1 = (aa[1] - 2.0 * u2) / b1;
        let u0 = (aa[0] - u1) / b1;
        let mut f1 = (((((u6 * t1 + u5) * t1 + u4) * t1 + u3) * t1 + u2) * t1 + u1) * t1 + u0;
        let mut i1: i32 = 1;
        if f1 < 0.0 {
            i1 = -1;
        }
        f1 = f1.abs().ln() + b1 * t1 + b0;
        if f1 > 2000.0 {
            f1 = 2000.0;
        }
        if version == 2 || version == 4 {
            let mut f2 = (((((u6 * t2 + u5) * t2 + u4) * t2 + u3) * t2 + u2) * t2 + u1) * t2 + u0;
            let mut i2: i32 = 1;
            if f2 < 0.0 {
                i2 = -1;
            }
            f2 = f2.abs().ln() + b1 * t2 + b0;
            if f2 > 2000.0 {
                f2 = 2000.0;
            }
            if version == 2 {
                return i1 as f64 * f1.exp() - i2 as f64 * f2.exp();
            }
            return i2 as f64 * f2.exp() - i1 as f64 * f1.exp();
        }
        if version == 1 {
            return i1 as f64 * f1.exp();
        }
        return -(i1 as f64) * f1.exp();
    }
    let mut u6 = (((aa[6] / 7.0 * (t2 - t1) + aa[5] / 6.0) * (t2 - t1) + aa[4] / 5.0)
        * (t2 - t1)
        + aa[3] / 4.0)
        * (t2 - t1);
    u6 = (((u6 + aa[2] / 3.0) * (t2 - t1) + aa[1] / 2.0) * (t2 - t1) + aa[0])
        * (t2 - t1)
        * b0.exp();
    if version == 4 {
        return u6;
    }
    -u6
}

/// `fun2`: `exp(p1 + x p2 + x^2 p3 + x^3 p4)` with `dfunpar` as the parameters.
fn fun2(dfunpar: &[f64; 6], x: f64) -> f64 {
    (dfunpar[1] + x * (dfunpar[2] + x * (dfunpar[3] + x * dfunpar[4]))).exp()
}

impl Lsd {
    /// `dens3`: a logspline density at one point.
    pub fn dens3(&self, x: f64) -> f64 {
        self.dens33(x).exp()
    }

    /// `dens33`: the log of a logspline density at one point.
    pub fn dens33(&self, x: f64) -> f64 {
        let nk = self.nknots as usize;
        let mut j = 0usize;
        while j < nk && x > self.knots[j] {
            j += 1;
        }
        let mut f = -self.czheta.ln();

        // find in between which knots the point is, and compute the spline
        for k in (j as i64 - 3)..(j as i64 + 1) {
            if k >= 0 && k <= nk as i64 {
                let k = k as usize;
                f = f
                    + self.zheta[k]
                        * (self.coef[k][0][j]
                            + x * (self.coef[k][1][j]
                                + x * (self.coef[k][2][j] + x * self.coef[k][3][j])));
            }
        }
        f
    }

    /// `numint`: Gauss-Legendre integral of the density from `k1` to `k2`.
    pub fn numint(&self, k1: f64, k2: f64, accuracy: i32) -> f64 {
        let mut r1 = (k2 - k1) / 2.0;
        let r2 = (k2 + k1) / 2.0;
        if accuracy == 0 || accuracy == 1 {
            let mut w = [0.0f64; 4];
            let mut y = [0.0f64; 4];
            for i in 1..4 {
                w[i] = GL3_W[i] * r1;
                y[i] = GL3_Y[i] * r1;
            }
            r1 = 0.0;
            for i in 1..4 {
                r1 = r1 + w[i] * (self.dens3(r2 - y[i]) + self.dens3(r2 + y[i]));
            }
            return r1;
        }
        let mut w = [0.0f64; 33];
        let mut y = [0.0f64; 33];
        for i in 1..33 {
            w[i] = GL12_W[i] * r1;
            y[i] = GL12_Y[i] * r1;
        }
        r1 = 0.0;
        for i in 1..33 {
            r1 = r1 + w[i] * (self.dens3(r2 - y[i]) + self.dens3(r2 + y[i]));
        }
        r1
    }

    /// `numint2`: the same quadrature with `fun2` as the integrand.
    pub fn numint2(&self, k1: f64, k2: f64, accuracy: i32) -> f64 {
        let mut r1 = (k2 - k1) / 2.0;
        let r2 = (k2 + k1) / 2.0;
        if accuracy == 0 || accuracy == 1 {
            let mut w = [0.0f64; 4];
            let mut y = [0.0f64; 4];
            for i in 1..4 {
                w[i] = GL3_W[i] * r1;
                y[i] = GL3_Y[i] * r1;
            }
            r1 = 0.0;
            for i in 1..4 {
                r1 = r1
                    + w[i] * (fun2(&self.dfunpar, r2 - y[i]) + fun2(&self.dfunpar, r2 + y[i]));
            }
            return r1;
        }
        let mut w = [0.0f64; 33];
        let mut y = [0.0f64; 33];
        for i in 1..33 {
            w[i] = GL12_W[i] * r1;
            y[i] = GL12_Y[i] * r1;
        }
        r1 = 0.0;
        for i in 1..33 {
            r1 = r1 + w[i] * (fun2(&self.dfunpar, r2 - y[i]) + fun2(&self.dfunpar, r2 + y[i]));
        }
        r1
    }

    /// `fun48`: add `w * x^i * dens3(x)` for `i < ip` into `vv`.
    fn fun48(&self, w: f64, x: f64, vv: &mut [f64], ip: usize) {
        let mut vx = w * self.dens3(x);
        vv[0] = vv[0] + vx;
        for i1 in 1..ip {
            vx = vx * x;
            vv[i1] = vv[i1] + vx;
        }
    }

    /// `numints`: vector of Gauss-Legendre integrals of `x^i * dens3(x)`.
    pub fn numints(&self, vv: &mut [f64], k1: f64, k2: f64, accuracy: i32, ip: usize) -> f64 {
        let r1 = (k2 - k1) / 2.0;
        let r2 = (k2 + k1) / 2.0;
        if accuracy == 0 || accuracy == 1 {
            let mut w = [0.0f64; 4];
            let mut y = [0.0f64; 4];
            for i in 1..4 {
                w[i] = GL3_W[i] * r1;
                y[i] = GL3_Y[i] * r1;
            }
            for i1 in 0..ip {
                vv[i1] = 0.0;
            }
            for i1 in 1..4 {
                self.fun48(w[i1], r2 - y[i1], vv, ip);
                self.fun48(w[i1], r2 + y[i1], vv, ip);
            }
            return 0.0;
        }
        let mut w = [0.0f64; 33];
        let mut y = [0.0f64; 33];
        for i in 1..33 {
            w[i] = GL12_W[i] * r1;
            y[i] = GL12_Y[i] * r1;
        }
        for i1 in 0..ip {
            vv[i1] = 0.0;
        }
        for i1 in 1..33 {
            self.fun48(w[i1], r2 - y[i1], vv, ip);
            self.fun48(w[i1], r2 + y[i1], vv, ip);
        }
        0.0
    }

    /// `erroradjust`: the stopping criterion `zerror`. It scales `shift` down
    /// when the criterion is larger than 1000.
    pub fn erroradjust(&self, shift: &mut [f64]) -> f64 {
        let nk = self.nknots as usize;
        let zheta = &self.zheta;
        let mut r1 = 0.0f64;
        let mut r2: f64;
        // the zerror is the sum of (shift/zheta)^2, except where zheta is very small
        for i in 0..nk - 1 {
            r2 = zheta[i] * zheta[i];
            if r2 < 0.0000001 {
                r2 = 0.0000001;
            }
            r1 = r1 + shift[i] * shift[i] / r2;
        }
        if numbertester(r1) != 1 {
            r2 = r1.sqrt();
        } else {
            // if the zerror is infinity we compute an alternate zerror criterion
            r1 = 0.0;
            for i in 0..nk - 1 {
                r2 = zheta[i].abs();
                if r2 < 0.00001 {
                    r2 = 0.00001;
                }
                r1 = r1 + shift[i].abs() / r2;
            }
            r2 = r1;
        }

        // If the zerror would be too big, we only take a smaller step: this is to
        // prevent overshoot.
        let mut i = 0usize;
        while i < nk - 1 && r1 > 1000.0 {
            shift[i] = shift[i] * 3.0 / r2;
            i += 1;
        }
        r1
    }

    /// `error2`: the inner product of `shift` and `rvr`, halved, with a guard.
    pub fn error2(&self, shift: &[f64], rvr: &[f64]) -> f64 {
        let nk = self.nknots as usize;
        let mut r = 0.0f64;
        for i in 0..nk - 1 {
            r = r + shift[i] * rvr[i] / 2.0;
        }
        let mut j: i32 = -1;
        if r >= 0.0 {
            j += 1;
        }
        if numbertester(r) == 1 {
            j -= 2;
        }
        if j < 0 {
            r = 1000.0;
        }
        r
    }

    /// `likeli`: the average log-likelihood with `zheta` set to `candidate`.
    ///
    /// The C source swaps `zheta` and `candidate` around the computation and
    /// swaps them back, so this copies `candidate` into `zheta` and restores it.
    pub fn likeli(
        &mut self,
        candidate: &[f64],
        nsample: &[i32],
        sample: &[f64],
        bound: &[f64],
        accuracy: i32,
    ) -> f64 {
        let nk = self.nknots as usize;
        let saved = self.zheta;
        for i in 0..nk - 1 {
            self.zheta[i] = candidate[i];
        }
        let r = self.likeli_now(nsample, sample, bound, accuracy);
        self.zheta = saved;
        r
    }

    /// `likeli` evaluated at the current `zheta`.
    pub fn likeli_now(&self, nsample: &[i32], sample: &[f64], bound: &[f64], accuracy: i32) -> f64 {
        let nk = self.nknots as usize;
        let knots = &self.knots;
        let zheta = &self.zheta;
        let coef = &self.coef;
        let czheta = self.czheta;
        let r0 = (-740.0f64).exp();

        // the stuff for the exact data is easy
        let mut likl = 0.0f64;
        for i1 in 0..nsample[1] as usize {
            likl = likl + self.dens33(sample[i1]);
        }

        // compute the integral of the density between each two knots in r3
        let iv: i32 = if bound[3] > 0.5 { 4 } else { 3 };
        let iw: i32 = if bound[1] > 0.5 { 2 } else { 1 };
        let mut aa = [0.0f64; 7];
        aa[1] = 0.0;
        aa[2] = 0.0;
        aa[3] = 1.0;
        aa[4] = zheta[nk - 2] * coef[nk - 2][1][nk];
        aa[5] = zheta[nk - 2] * coef[nk - 2][0][nk] + zheta[nk - 3] * coef[nk - 3][0][nk]
            - czheta.ln();
        if nk < 4 {
            aa[5] = zheta[nk - 2] * coef[nk - 2][0][nk] - czheta.ln();
        }
        let mut r3 = [0.0f64; NC + 1];
        r3[nk] = expin(iv, knots[nk - 1], bound[4], &aa);
        let mut bb = [0.0f64; 7];
        bb[1] = 0.0;
        bb[2] = 0.0;
        bb[3] = 1.0;
        bb[4] = zheta[0] * coef[0][1][0];
        bb[5] = zheta[0] * coef[0][0][0] - czheta.ln();
        r3[0] = expin(iw, knots[0], bound[2], &bb);
        for i1 in 1..nk {
            r3[i1] = self.numint(knots[i1 - 1], knots[i1], accuracy);
        }

        // depending on the accuracy we either deal with the censored data
        // approximate or exact
        if accuracy != 0 {
            // exact first the rounded data
            for i1 in 0..nsample[2] as usize {
                let i2 = i1 * 2 + nsample[1] as usize;
                // between which knots are the two endpoints
                let mut i3 = 0usize;
                while knots[i3] < sample[i2] && i3 < nk {
                    i3 += 1;
                }
                let mut i4 = 0usize;
                while knots[i4] < sample[i2 + 1] && i4 < nk {
                    i4 += 1;
                }
                // is it the same interval
                if i3 == i4 {
                    likl = likl + self.numint(sample[i2], sample[i2 + 1], 0).ln();
                } else {
                    // or a different interval
                    let mut r1 = self.numint(sample[i2], knots[i3], 0);
                    r1 = r1 + self.numint(knots[i4 - 1], sample[i2 + 1], 0);
                    i3 += 1;
                    while i3 < i4 {
                        r1 = r1 + r3[i3];
                        i3 += 1;
                    }
                    likl = likl + r1.ln();
                }
            }
            // the right censored data
            for i1 in 0..nsample[3] as usize {
                let i2 = i1 + nsample[1] as usize + 2 * nsample[2] as usize;
                // in which interval is the datapoint
                let mut i3 = 0usize;
                while knots[i3] < sample[i2] && i3 < nk {
                    i3 += 1;
                }
                // somewhere in the middle
                if i3 < nk {
                    let mut r1 = self.numint(sample[i2], knots[i3], 0);
                    i3 += 1;
                    while i3 <= nk {
                        r1 = r1 + r3[i3];
                        i3 += 1;
                    }
                    // if r1<=r0 the likl is effectively -infinity
                    if r1 > r0 {
                        likl = likl + r1.ln();
                    } else {
                        likl = likl - 1000.0;
                    }
                } else {
                    // in the tail
                    likl = likl + expin(iv, sample[i2], bound[4], &aa).ln();
                }
            }
            // the left censored data
            for i1 in 0..nsample[4] as usize {
                let i2 = i1 + nsample[1] as usize + 2 * nsample[2] as usize + nsample[3] as usize;
                // in which interval is the datapoint
                let mut i3 = 0usize;
                while knots[i3] < sample[i2] && i3 < nk {
                    i3 += 1;
                }
                // somewhere in the middle
                if i3 > 0 {
                    let mut r1 = self.numint(knots[i3 - 1], sample[i2], 0);
                    for i4 in 0..i3 {
                        r1 = r1 + r3[i4];
                    }
                    // if r1<=r0 the likl is effectively -infinity
                    if r1 > r0 {
                        likl = likl + r1.ln();
                    } else {
                        likl = likl - 1000.0;
                    }
                } else {
                    // in the tail
                    likl = likl + expin(iw, sample[i2], bound[2], &bb).ln();
                }
            }
        } else {
            // approximate, first right censored - essentially as above
            // there are ng3 points at xg
            if nsample[3] > 0 {
                let mut i1: i32 = 0;
                for i2 in 0..NC {
                    if self.ng3[i2] > 0 {
                        i1 += self.ng3[i2];
                        let mut i3 = 0usize;
                        while knots[i3] < self.xg[i2] && i3 < nk {
                            i3 += 1;
                        }
                        if i3 < nk {
                            let mut r1 = self.numint(self.xg[i2], knots[i3], 0);
                            i3 += 1;
                            while i3 <= nk {
                                r1 = r1 + r3[i3];
                                i3 += 1;
                            }
                            if r1 > r0 {
                                likl = likl + self.ng3[i2] as f64 * r1.ln();
                            } else {
                                likl = likl - 1000.0 * self.ng3[i2] as f64;
                            }
                        } else {
                            likl = likl
                                + self.ng3[i2] as f64 * expin(iv, self.xg[i2], bound[4], &aa).ln();
                        }
                        if i1 == nsample[3] {
                            break;
                        }
                    }
                }
            }
            // approximate, now left censored - essentially as above
            // there are ng4 points at xg
            if nsample[4] > 0 {
                let mut i1: i32 = 0;
                for i2 in 0..NC {
                    if self.ng4[i2] > 0 {
                        i1 += self.ng4[i2];
                        let mut i3 = 0usize;
                        while knots[i3] < self.xg[i2] && i3 < nk {
                            i3 += 1;
                        }
                        if i3 > 0 {
                            let mut r1 = self.numint(knots[i3 - 1], self.xg[i2], 0);
                            for i4 in 0..i3 {
                                r1 = r1 + r3[i4];
                            }
                            if r1 > r0 {
                                likl = likl + self.ng4[i2] as f64 * r1.ln();
                            } else {
                                likl = likl - 1000.0 * self.ng4[i2] as f64;
                            }
                        } else {
                            likl = likl
                                + self.ng4[i2] as f64 * expin(iw, self.xg[i2], bound[2], &bb).ln();
                        }
                        if i1 == nsample[4] {
                            break;
                        }
                    }
                }
            }
            // the interval censored stuff is easy
            if nsample[2] > 0 {
                for i1 in 0..nsample[2] as usize {
                    let r1 = (sample[nsample[1] as usize + i1 * 2]
                        + sample[nsample[1] as usize + i1 * 2 + 1])
                        / 2.0;
                    likl = likl + self.dens33(r1);
                }
            }
        }
        likl / nsample[0] as f64
    }

    /// `linsearch`: steepest-descent line search in direction `shift`.
    ///
    /// Moves `zheta` to the best step found and returns the log-likelihood there.
    pub fn linsearch(
        &mut self,
        shift: &mut [f64],
        oldll: f64,
        bound: &[f64],
        nsample: &[i32],
        sample: &[f64],
        accuracy: i32,
    ) -> f64 {
        let nk = self.nknots as usize;
        let mut rl = 1000.0f64;
        let mut rr = 1000.0f64;
        if bound[1] < 0.5 && shift[0] * self.zheta[0] < 0.0 {
            rl = -self.zheta[0] / shift[0];
        }
        if bound[3] < 0.5 && shift[nk - 2] * self.zheta[nk - 2] < 0.0 {
            rr = -self.zheta[nk - 2] / shift[nk - 2];
        }
        // rl and rr are the maximum stepsize, given the sign of zheta and
        // integration boundaries
        if rl < rr {
            rr = rl;
        }
        let mut maxll = oldll;
        let mut maxrt: f64 = -100.0;
        // rt is the first stepsize guess, on a 2log basis
        let mut rt: f64 = if rr > 0.5 {
            -2.0
        } else {
            (rr.ln() / 2f64.ln()).floor() - 2.0
        };
        // onesearch computes the loglikelihood for one rt (stepsize)
        let (mut ll, mut err) = self.onesearch(rt, shift, accuracy, bound, nsample, sample);
        // if for the basis stepsize the likelihood goes up we try more
        if err == 0 && ll > maxll {
            loop {
                maxrt = rt;
                maxll = ll;
                rt += 2.0;
                let r = self.onesearch(rt, shift, accuracy, bound, nsample, sample);
                ll = r.0;
                err = r.1;
                if !(rt < 8.5 && ll > maxll && err == 0) {
                    break;
                }
            }
        } else {
            // if for the basis stepsize the likelihood goes down we try less
            loop {
                rt -= 2.0;
                let r = self.onesearch(rt, shift, accuracy, bound, nsample, sample);
                ll = r.0;
                err = r.1;
                if !(rt > -14.1 && (ll < maxll || err == 1)) {
                    break;
                }
            }
        }
        // write down the winning combination
        if err == 0 && ll > maxll {
            maxrt = rt;
            maxll = ll;
        }
        if maxrt > -50.0 {
            rt = maxrt + 1.0;
            let r = self.onesearch(rt, shift, accuracy, bound, nsample, sample);
            ll = r.0;
            err = r.1;
            if err == 0 && ll > maxll {
                maxrt = rt;
                maxll = ll;
            }
            maxrt = 2f64.powf(maxrt);
            for i in 0..nk - 1 {
                self.zheta[i] = self.zheta[i] + maxrt * shift[i];
            }
        }
        maxll
    }

    /// `onesearch`: `czheta` and the log-likelihood at `zheta + 2^rt * shift`.
    /// Returns the log-likelihood and the error flag.
    pub fn onesearch(
        &mut self,
        rt: f64,
        shift: &[f64],
        accuracy: i32,
        bound: &[f64],
        nsample: &[i32],
        sample: &[f64],
    ) -> (f64, i32) {
        let nk = self.nknots as usize;
        let rt = 2f64.powf(rt);
        let mut rv = [0.0f64; NC];
        for i in 0..nk - 1 {
            rv[i] = self.zheta[i] + rt * shift[i];
        }
        // compute czheta
        let mut dm1 = [[0.0f64; NC]; NC];
        let mut dm2 = [0.0f64; NC];
        let dm3 = [[0.0f64; 2]; NC];
        let v = self.middle(&mut dm1, &mut dm2, &dm3, bound, accuracy, nsample, sample, &rv, 0);
        self.czheta = v;
        // zerror conditions
        if self.czheta <= 0.0 {
            return (0.0, 1);
        }
        if self.czheta.ln() > 200.0 {
            return (0.0, 1);
        }
        let mut j = 0;
        if self.czheta > -5.0 {
            j += 1;
        }
        if self.czheta < 5.0 {
            j += 1;
        }
        if j == 0 {
            return (0.0, 1);
        }
        // compute likeli
        let ll = self.likeli(&rv, nsample, sample, bound, accuracy);
        (ll, 0)
    }

    /// `coeff`: coefficients of the basis functions from the knots.
    ///
    /// `coef2` holds the basis coefficients in the knot index. `self.coef`
    /// holds the power coefficients in the interval index.
    pub fn coeff(&mut self, coef2: &mut [[f64; NC]; NC]) {
        let nk = self.nknots as usize;
        let knots = self.knots;

        // Initializations
        for i in 0..nk {
            for j in 0..nk + 3 {
                coef2[i][j] = 0.0;
                if j < nk + 2 {
                    for k in 0..4 {
                        self.coef[i][k][j] = 0.0;
                    }
                }
            }
        }

        // The coefficients for the two tail basis functions are easy to compute
        coef2[0][2] = 1.0;
        coef2[0][3] = (knots[0] - knots[2]) / (knots[2] - knots[1]);
        coef2[0][4] = (knots[1] - knots[0]) / (knots[2] - knots[1]);
        coef2[0][1] = -3.0
            * (knots[0].powf(2.0) + coef2[0][3] * knots[1].powf(2.0) + coef2[0][4] * knots[2].powf(2.0));
        coef2[0][0] = -knots[nk - 1] * coef2[0][1]
            - coef2[0][2] * (knots[nk - 1] - knots[0]).powf(3.0)
            - coef2[0][3] * (knots[nk - 1] - knots[1]).powf(3.0)
            - coef2[0][4] * (knots[nk - 1] - knots[2]).powf(3.0);
        coef2[0][5] = 0.0;
        coef2[nk - 2][nk - 1] = 1.0;
        coef2[nk - 2][nk] = (knots[nk - 3] - knots[nk - 1]) / (knots[nk - 1] - knots[nk - 2]);
        coef2[nk - 2][nk + 1] = (knots[nk - 2] - knots[nk - 3]) / (knots[nk - 1] - knots[nk - 2]);

        // we first create basis functions that are 0 before knot[i] and constant
        // after knot [i+3]
        if nk >= 4 {
            for i in 1..nk - 2 {
                coef2[i][i + 1] = 1.0;
                coef2[i][i + 4] = (knots[i + 1] - knots[i - 1]) * (knots[i - 1] - knots[i])
                    / ((knots[i + 1] - knots[i + 2]) * (knots[i] - knots[i + 2]));
                coef2[i][i + 3] = (coef2[i][i + 4] * (knots[i] - knots[i + 2]) + knots[i]
                    - knots[i - 1])
                    / (knots[i + 1] - knots[i]);
                coef2[i][i + 2] = -1.0 - coef2[i][i + 3] - coef2[i][i + 4];
            }

            // In the following part we subtract a number of times one basis function
            // from another - so that basis function i becomes 0 after knot[i+4]
            if nk >= 5 {
                for i in 1..nk - 3 {
                    let mut z0 = 0.0f64;
                    let mut z1 = 0.0f64;
                    for j in 2..nk + 1 {
                        z0 = z0 + coef2[i][j] * (knots[nk - 1] - knots[j - 2]).powf(3.0);
                        z1 = z1 + coef2[i + 1][j] * (knots[nk - 1] - knots[j - 2]).powf(3.0);
                    }
                    for j in 2..nk + 2 {
                        coef2[i][j] = coef2[i][j] - (z0 / z1) * coef2[i + 1][j];
                    }
                }
            }
        }

        // Now the coef matrix. First basis function 1.
        for k in 0..3 {
            self.coef[0][1][k] = coef2[0][1];
            self.coef[0][0][k] = coef2[0][0];
        }

        // The rest is a bit tricking with the correct indices
        for i in 0..nk - 1 {
            for j in i..i + 4 {
                for k in (i + 1)..(j + 2) {
                    if j > 0 && j < nk + 1 && (i != 0 || j != 3) && k != 1 {
                        self.coef[i][0][j] =
                            self.coef[i][0][j] - coef2[i][k] * knots[k - 2].powf(3.0);
                        self.coef[i][1][j] =
                            self.coef[i][1][j] + 3.0 * coef2[i][k] * knots[k - 2].powf(2.0);
                        self.coef[i][2][j] =
                            self.coef[i][2][j] - 3.0 * coef2[i][k] * knots[k - 2];
                        self.coef[i][3][j] = self.coef[i][3][j] + coef2[i][k];
                    }
                }
            }
        }
    }

    /// `start1`: derivatives and cross-products of the sample and the knots,
    /// used by `start2` to compute the starting values.
    pub fn start1(
        &self,
        crossprods: &mut [[f64; NC]; NC],
        derivatives: &mut [f64; NC],
        sample: &[f64],
        nsample: &[i32],
    ) {
        let nk = self.nknots as usize;
        let knots = &self.knots;

        // Initializations
        for i in 0..nk + 1 {
            derivatives[i] = 0.0;
            for j in 0..nk + 1 {
                crossprods[i][j] = 0.0;
            }
        }
        crossprods[0][0] = nsample[0] as f64;

        let mut rr = sample[0];
        let mut rs = sample[0];
        // First the uncensored part
        for i in 0..(nsample[0] + nsample[2]) as usize {
            if sample[i] > rr {
                rr = sample[i];
            }
        }
        for i in 0..(nsample[0] + nsample[2]) as usize {
            if sample[i] < rs {
                rs = sample[i];
            }
        }
        if nsample[1] > 0 {
            for j in 0..nk {
                for i in 0..nsample[1] as usize {
                    if sample[i] > knots[j] {
                        derivatives[j + 1] =
                            derivatives[j + 1] + 6.0 * (sample[i] - knots[j]);
                        crossprods[j + 1][0] =
                            crossprods[j + 1][0] + 3.0 * (sample[i] - knots[j]).powf(2.0);
                        for k in 0..=j {
                            crossprods[j + 1][k + 1] = crossprods[j + 1][k + 1]
                                + 9.0
                                    * ((sample[i] - knots[j]) * (sample[i] - knots[k])).powf(2.0);
                        }
                    }
                }
            }
        }
        // The interval censored part - we take the midpoints of the intervals
        if nsample[2] > 0 {
            for j in 0..nk {
                for i in 0..nsample[2] as usize {
                    let xs = (sample[nsample[1] as usize + 2 * i]
                        + sample[nsample[1] as usize + 2 * i + 1])
                        / 2.0;
                    if xs > knots[j] {
                        derivatives[j + 1] = derivatives[j + 1] + 6.0 * (xs - knots[j]);
                        crossprods[j + 1][0] =
                            crossprods[j + 1][0] + 3.0 * (xs - knots[j]).powf(2.0);
                        for k in 0..=j {
                            crossprods[j + 1][k + 1] = crossprods[j + 1][k + 1]
                                + 9.0 * ((xs - knots[j]) * (xs - knots[k])).powf(2.0);
                        }
                    }
                }
            }
        }
        // The right censored part
        if nsample[3] > 0 {
            for j in 0..nk {
                for i2 in 0..nsample[3] as usize {
                    let i = nsample[1] as usize + 2 * nsample[2] as usize + i2;
                    let mut uuu = 0.0f64;
                    for i3 in 0..4 {
                        uuu = (i3 as f64) * rr / 4.0 + ((4 - i3) as f64) * sample[i] / 4.0;
                    }
                    if uuu > knots[j] {
                        derivatives[j + 1] = derivatives[j + 1] + 1.5 * (uuu - knots[j]);
                        crossprods[j + 1][0] =
                            crossprods[j + 1][0] + 0.75 * (uuu - knots[j]).powf(2.0);
                        for k in 0..=j {
                            crossprods[j + 1][k + 1] = crossprods[j + 1][k + 1]
                                + 2.25 * ((uuu - knots[j]) * (uuu - knots[k])).powf(2.0);
                        }
                    }
                }
            }
        }

        // The left censored part
        if nsample[4] > 0 {
            for j in 0..nk {
                for i2 in 0..nsample[4] as usize {
                    let i = nsample[1] as usize
                        + 2 * nsample[2] as usize
                        + nsample[3] as usize
                        + i2;
                    let mut uuu = 0.0f64;
                    for i3 in 0..4 {
                        uuu = (i3 as f64) * rs / 4.0 + ((4 - i3) as f64) * sample[i] / 4.0;
                    }
                    if uuu > knots[j] {
                        derivatives[j + 1] = derivatives[j + 1] + 1.5 * (uuu - knots[j]);
                        crossprods[j + 1][0] =
                            crossprods[j + 1][0] + 0.75 * (uuu - knots[j]).powf(2.0);
                        for k in 0..=j {
                            crossprods[j + 1][k + 1] = crossprods[j + 1][k + 1]
                                + 2.25 * ((uuu - knots[j]) * (uuu - knots[k])).powf(2.0);
                        }
                    }
                }
            }
        }

        // symmetarize crossprods
        for j in 0..nk {
            for k in (j + 1)..(nk + 1) {
                crossprods[j][k] = crossprods[k][j];
            }
        }
    }
}
