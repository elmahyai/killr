//! Knot placement and the number of starting knots, remade from `src/lsdall.c`.

use super::{rprintf, Lsd, NC};
use crate::linpack::xssort;

/// `knotnumber`: the number of starting knots.
pub fn knotnumber(idelete: i32, nsample: &[i32], nknots_in: i32, sorc: &mut [i32]) -> i32 {
    let mut nknots = nknots_in;
    let nn = nsample[1] + nsample[2] + (nsample[3] + nsample[4]) / 2;
    if nknots >= NC as i32 || (nknots > nsample[5] + 1 && nsample[5] > 1) {
        if sorc[0] == 0 {
            rprintf("can not run with that many knots\n");
        } else {
            sorc[20] = 1;
        }
        nknots = NC as i32 - 1;
        if nknots > nsample[5] + 1 {
            nknots = nsample[5] + 1;
        }
    }
    if nknots > 0 {
        return nknots;
    }
    let mut r = 2.5 * (nn as f64).powf(0.2);
    if idelete > 0 {
        r = 1.6 * r;
    }
    if idelete > 0 && nn < 51 {
        r = nn as f64 / 6.0;
    }
    if r > NC as f64 - 1.1 {
        r = NC as f64 - 1.1;
    }
    if r < 2.5 {
        r = 2.5;
    }
    if nsample[5] != 0 && r > (nsample[5] + 1) as f64 {
        r = nsample[5] as f64 + 0.1;
    }
    r.ceil() as i32
}

/// `piecedens`: sort the data and build the piecewise-constant density used to
/// place the knots. Returns the number of distinct points `il`.
pub fn piecedens(
    sample: &mut [f64],
    smp2: &mut [f64],
    smp3: &mut [f64],
    nsample: &[i32],
) -> i32 {
    let n0 = nsample[0] as usize;
    let n1 = nsample[1] as usize;
    let n2 = nsample[2] as usize;
    let n3 = nsample[3] as usize;
    let n4 = nsample[4] as usize;
    let il: i32;

    if n1 > 0 {
        xssort(sample, smp3, n1, 1);
    }
    if n2 > 0 {
        for i in 0..n2 {
            smp2[i] = sample[n1 + 2 * i];
            smp3[i] = sample[n1 + 2 * i + 1];
        }
        xssort(smp2, smp3, n2, 2);
        for i in 0..n2 {
            sample[n1 + 2 * i] = smp2[i];
            sample[n1 + 2 * i + 1] = smp3[i];
        }
    }
    if n3 > 0 {
        for i in 0..n3 {
            smp2[i] = sample[i + n1 + 2 * n2];
        }
        xssort(smp2, smp3, n3, 1);
        for i in 0..n3 {
            sample[i + n1 + 2 * n2] = smp2[i];
        }
    }
    if n4 > 0 {
        for i in 0..n4 {
            smp2[i] = sample[i + n1 + 2 * n2 + n3];
        }
        xssort(smp2, smp3, n4, 1);
        for i in 0..n4 {
            sample[i + n1 + 2 * n2 + n3] = smp2[i];
        }
    }
    for i in 0..n1 {
        smp2[i] = sample[i];
        smp3[i] = 1.0;
    }
    for i in 0..(n3 + n4) {
        let j = n1 + 2 * n2 + i;
        smp2[j] = sample[j];
        smp3[j] = 1.0;
    }
    if n2 > 0 {
        for i in 0..n2 {
            let j = n1 + i * 2;
            smp2[j] = sample[j];
            smp3[j] = 0.0;
            smp2[j + 1] = sample[j + 1];
            smp3[j + 1] = 0.0;
        }
    }
    xssort(smp2, smp3, n0 + n2, 2);
    let mut i: usize = 0;
    for j in 1..(n0 + n2) {
        if smp2[j] == smp2[i] {
            smp3[i] = smp3[i] + smp3[j];
        } else {
            i += 1;
            smp2[i] = smp2[j];
            smp3[i] = smp3[j];
        }
    }
    il = i as i32;

    // for(i=il-1;i>=0;i=i-1)
    let mut ii = il - 1;
    while ii >= 0 {
        let u = ii as usize;
        if smp3[u] > 0.0 {
            smp3[u + 1] = smp3[u + 1] + 0.5 * smp3[u];
            smp3[u] = 0.5 * smp3[u];
        }
        ii -= 1;
    }
    if n2 > 0 {
        let mut k: i32 = 0;
        for i in 0..n2 {
            let j = n1 + i * 2;
            let mut m = k;
            while m <= il {
                if sample[j] < smp2[m as usize] {
                    k = m;
                    m = 2 * il + 1;
                    let mut nn = k;
                    while nn <= il {
                        if sample[j + 1] < smp2[nn as usize] {
                            nn = 2 * il + 1;
                        } else {
                            let u = nn as usize;
                            smp3[u] = smp3[u] + (smp2[u] - smp2[u - 1]) / (sample[j + 1] - sample[j]);
                        }
                        nn += 1;
                    }
                }
                m += 1;
            }
        }
    }
    for i in 1..=(il.max(0) as usize) {
        smp3[i] = smp3[i] + smp3[i - 1];
    }
    il
}

impl Lsd {
    /// `knotplace`: place the knots and rescale the sample to the unit interval.
    ///
    /// `qt` receives the affine map `u4 + u3 * x` used for the data, `bound` the
    /// boundary flags, and `iknots` the knot ranks.
    #[allow(clippy::too_many_arguments)]
    pub fn knotplace(
        &mut self,
        iknots: &mut [i32],
        rknots: &mut [f64],
        iknotauto: i32,
        bound: &mut [f64],
        sample: &mut [f64],
        nsample: &mut [i32],
        sorc: &mut [i32],
        smp2: &mut [f64],
        smp3: &mut [f64],
        qt: &mut [f64],
    ) {
        let five: f64 = 4.0;
        let mut nknots = self.nknots;
        let mut j: i32 = 0;
        let mut ia: i32 = 0;
        let mut kk: i32;
        let mut ll: i32;
        let mut il: i32 = 0;
        let mut u3: f64 = 0.0;
        let mut u4: f64 = 0.0;
        let mut s: f64;
        let mut eps: f64;
        let mut eps1: f64;
        let mut eps2: f64;
        let mut v: f64;
        let mut w: f64;
        let mut u1: f64;
        let mut u2: f64;

        let w1 = nsample[0];
        let w2 = nsample[1];
        let w3 = nsample[2];
        let w4 = nsample[3];
        let w5 = nsample[4];
        let w6 = nsample[5];
        if sorc[16] == 1 {
            nsample[0] = w2;
            nsample[1] = w2;
            nsample[2] = 0;
            nsample[3] = 0;
            nsample[4] = 0;
            nsample[5] = w2 - 1;
        }

        qt[0] = -1.0;
        qt[1] = 1.0;
        if iknotauto == 0 && nknots > 12 {
            qt[0] = self.knots[4];
            qt[1] = self.knots[(nknots - 5) as usize];
        }
        if iknotauto == 0 && nknots > 9 && nknots < 13 {
            qt[0] = self.knots[3];
            qt[1] = self.knots[(nknots - 4) as usize];
        }
        if iknotauto == 0 && nknots > 6 && nknots < 10 {
            qt[0] = self.knots[2];
            qt[1] = self.knots[(nknots - 3) as usize];
        }
        if iknotauto == 0 && nknots == 3 {
            qt[0] = (self.knots[0] + self.knots[1]) / 2.0;
            qt[1] = (self.knots[2] + self.knots[1]) / 2.0;
        }
        if iknotauto == 0 && nknots > 3 && nknots < 7 {
            qt[0] = self.knots[1];
            qt[1] = self.knots[(nknots - 2) as usize];
        }
        if iknotauto == 1 {
            // compute the piecewise density
            il = piecedens(sample, smp2, smp3, nsample);
            kk = ((il as f64) / 2.0 + 2.1).floor() as i32;
            if nknots > kk && nsample[5] == 0 {
                nknots = kk;
                self.nknots = nknots;
                if sorc[0] == 0 {
                    rprintf("running with maximum number of degrees of freedom");
                } else {
                    sorc[20] = 1;
                }
            }
            if nknots == nsample[5] + 1 {
                sorc[20] = 1;
            }

            // Check whether there are not too many knots
            kk = 0;
            ll = 0;
            loop {
                ll = kk + ll;
                kk = 0;
                if bound[1] < 0.5 && bound[3] < 0.5 {
                    // all knots are a minimum of "five" apart
                    if ((nknots - 1) as f64) * five >= (nsample[0] - 1) as f64 {
                        let i = (1.0 + (nsample[0] - 1) as f64 / five).floor() as i32;
                        if sorc[0] == 0 {
                            rprintf(&format!("too many knots, at most {} knots possible\n", i));
                            sorc[0] = -647;
                        } else {
                            sorc[0] = -2;
                            sorc[1] = i;
                        }
                        self.nknots = nknots;
                        return;
                    }

                    // place the 2 extreme knots
                    rknots[0] = 1.0;
                    rknots[(nknots - 1) as usize] = nsample[0] as f64;

                    // j and j2 are this way to deal both with odd and even situations
                    j = ((nknots - 1) as f64 / 2.0).ceil() as i32;
                    let j2: i32 = ((nknots - 1) as f64 / 2.0).floor() as i32;

                    // eps1 and eps2 are lower and upper bound on eps, eps is our first guess.
                    eps1 = five - ((nsample[0] - 1) as f64 / five).powf(1.0 / ((j - 1) as f64));
                    if eps1 > 0.0 {
                        eps1 = 0.0;
                    }
                    eps2 = five - 1.0;

                    loop {
                        eps = (eps1 + eps2) / 2.0;
                        s = 1.0;
                        w = five;
                        for i in 1..=j2 {
                            v = i as f64;
                            // s is the location after adding another knot
                            s = s + w;
                            // we store the rknots - in case they are good
                            rknots[i as usize] = s;
                            rknots[(nknots - i - 1) as usize] = (nsample[0] + 1) as f64 - s;
                            v = five - v * eps;
                            // w is what is going to be the next gap
                            if v < 1.0 {
                                v = 1.0;
                            }
                            w = w * v;
                        }
                        // Are there an odd or even number of gaps?
                        if j * 2 == nknots {
                            // even - no more knots to place.
                            s = s + w / 2.0;
                        } else {
                            // odd - the last knot
                            rknots[j as usize] = (nsample[0] as f64 + 1.0) / 2.0;
                        }

                        // Is eps too large or too small?
                        if 2.0 * s >= (nsample[0] + 1) as f64 {
                            eps1 = eps;
                        } else {
                            eps2 = eps;
                        }

                        // Are eps1 and eps2 close together
                        if !(eps2 - eps1 > 0.001) {
                            break;
                        }
                    }
                } else {
                    // if both sides there are finite limits we put them equidistant
                    if bound[1] > 0.5 && bound[3] > 0.5 {
                        for i in 0..nknots as usize {
                            rknots[i] = 1.0
                                + ((nsample[0] - 1) as f64) * (i as f64) / ((nknots - 1) as f64);
                        }
                    } else {
                        // one side bounded, one side unbounded half of the five-rule
                        // which side is bounded?
                        rknots[0] = 1.0;
                        rknots[(nknots - 1) as usize] = nsample[0] as f64;
                        eps1 = 0.0;
                        eps2 = five;
                        loop {
                            eps = (eps1 + eps2) / 2.0;
                            s = 1.0;
                            w = five;
                            for i in 1..(nknots - 1) {
                                v = i as f64;
                                // s is the location after adding another knot
                                s = s + w;
                                // we store the rknots - in case they are good
                                if bound[3] > 0.5 {
                                    rknots[i as usize] = s;
                                } else {
                                    rknots[(nknots - i - 1) as usize] =
                                        (nsample[0] as f64) + 1.0 - s;
                                }
                                v = five - v * eps;
                                // w is what is going to be the next gap
                                if v < 1.0 {
                                    v = 1.0;
                                }
                                w = w * v;
                            }
                            // Is eps too large or too small?
                            if s + w > nsample[0] as f64 {
                                eps1 = eps;
                            } else {
                                eps2 = eps;
                            }
                            // Are eps1 and eps2 close together
                            if !(eps2 - eps1 > 0.001) {
                                break;
                            }
                        }
                    }
                }
                if nknots == 3 {
                    rknots[1] = nsample[0] as f64 / 2.0;
                }

                // Translate rknots in knots
                if ll == 0 {
                    // the first two knots are easy
                    self.knots[0] = smp2[0];
                    self.knots[(nknots - 1) as usize] = smp2[il as usize];

                    // cycle through the endpoints, average
                    let mut k: i32 = 0;
                    for i in 1..(nknots - 1) as usize {
                        rknots[i] = rknots[i] - 0.5;
                        let kx = k;
                        k = kx;
                        while k <= il {
                            let ku = k as usize;
                            if smp3[ku] >= rknots[i] {
                                self.knots[i] = ((rknots[i] - smp3[ku - 1]) * smp2[ku]
                                    + (smp3[ku] - rknots[i]) * smp2[ku - 1])
                                    / (smp3[ku] - smp3[ku - 1]);
                                ia = k;
                                k = k + 4 * il;
                            }
                            k += 1;
                        }
                        k = ia;
                    }
                }

                // find the first and the third quartile
                let mut i: i32 = 1;
                while i < il {
                    if smp3[i as usize] > 0.25 * nsample[0] as f64 {
                        u3 = smp2[i as usize];
                        i = i + 2 * il;
                        qt[0] = u3;
                    }
                    i += 1;
                }
                i = 1;
                while i < il + 1 {
                    if smp3[i as usize] > 0.75 * nsample[0] as f64 {
                        u4 = smp2[i as usize];
                        i = i + 2 * il;
                        qt[1] = u4;
                    }
                    i += 1;
                }

                // knots that are close together at the end, are an indicator of a
                // discontinuity. We replace the knots if this happens. kk is an
                // indicator that somthing like this is the case.
                if bound[1] < 0.5 {
                    u1 = self.knots[2] - self.knots[0];
                    u2 = u4 - u3;
                    if u1 < u2 / 30.0 {
                        if sorc[0] == 0 {
                            rprintf("possible discontinuity of the density at left end\n");
                            rprintf("considder rerunning it with lbound=min(sample)\n");
                        } else {
                            sorc[21] = 1;
                        }
                        kk = kk + 1;
                        bound[1] = 1.0;
                        bound[2] = self.knots[0];
                    }
                }
                if bound[3] < 0.5 {
                    u1 = self.knots[(nknots - 1) as usize] - self.knots[(nknots - 3) as usize];
                    u2 = u4 - u3;
                    if u1 < u2 / 30.0 {
                        if sorc[0] == 0 {
                            rprintf("possible discontinuity of the density at right end\n");
                            rprintf("considder rerunning it with ubound=max(sample)\n");
                        } else {
                            sorc[22] = 1;
                        }
                        kk = kk + 2;
                        bound[3] = 1.0;
                        bound[4] = self.knots[(nknots - 1) as usize];
                    }
                }
                if !(kk > 0) {
                    break;
                }
            }
            if ll == 1 || ll == 3 {
                bound[1] = 0.0;
            }
            if ll == 2 || ll == 3 {
                bound[3] = 0.0;
            }

            // if after previous changes these knots are still to close together, the
            // density might be real high at the end - we toss out knots in this case
            let nk = nknots as usize;
            u1 = self.knots[nk - 1] - self.knots[nk - 3];
            u2 = u4 - u3;
            if u1 < u2 / 30.0 {
                if sorc[0] == 0 {
                    rprintf("potential very high value of the density at right end\n");
                    rprintf("running program with fewer knots than usual\n");
                } else {
                    sorc[22] = 3;
                }
                self.knots[nk - 3] = (self.knots[nk - 3] + self.knots[nk - 2]) / 2.0;
                self.knots[nk - 2] = self.knots[nk - 1];
                nknots -= 1;
                self.nknots = nknots;
            }
            loop {
                let nk = nknots as usize;
                u1 = self.knots[nk - 1] - self.knots[nk - 3];
                u2 = u4 - u3;
                if !(u1 < u2 / 30.0) {
                    break;
                }
                self.knots[nk - 3] = (self.knots[nk - 3] + self.knots[nk - 2]) / 2.0;
                nknots -= 1;
                self.nknots = nknots;
            }
            u1 = self.knots[2] - self.knots[0];
            u2 = u4 - u3;
            if u1 < u2 / 30.0 {
                if sorc[0] == 0 {
                    rprintf("potential very high value of the density at left end\n");
                    rprintf("running program with fewer knots than usual\n");
                } else {
                    sorc[21] = 3;
                }
                self.knots[1] = (self.knots[1] + self.knots[2]) / 2.0;
                for i in 2..(nknots - 1) as usize {
                    self.knots[i] = self.knots[i + 1];
                }
                nknots -= 1;
                self.nknots = nknots;
            }
            loop {
                u1 = self.knots[2] - self.knots[0];
                u2 = u4 - u3;
                if !(u1 < u2 / 30.0) {
                    break;
                }
                self.knots[1] = (self.knots[1] + self.knots[2]) / 2.0;
                for i in 1..(nknots - 1) as usize {
                    self.knots[i] = self.knots[i + 1];
                }
                nknots -= 1;
                self.nknots = nknots;
            }
        }

        // Remove double knots, either store zerror messages, or print them.
        j = 0;
        let mut k: i32 = 0;
        for i in 1..nknots {
            if self.knots[i as usize] > self.knots[j as usize] {
                j += 1;
                self.knots[j as usize] = self.knots[i as usize];
            } else {
                k += 1;
                if sorc[0] == 8 {
                    rprintf(&format!(
                        "===> warning: knot {} removed - double knot\n",
                        i + 1
                    ));
                    if k == 2 {
                        rprintf("* several double knots suggests that your data is *\n");
                        rprintf("* strongly rounded: attention might be required.  *\n");
                    }
                } else {
                    sorc[0] = 2 + k;
                    if sorc[0] == 23 {
                        self.nknots = nknots;
                        return;
                    }
                    sorc[k as usize] = i + 1;
                }
            }
        }
        nknots = j + 1;
        self.nknots = nknots;
        nsample[0] = w1;
        nsample[1] = w2;
        nsample[2] = w3;
        nsample[3] = w4;
        nsample[4] = w5;
        nsample[5] = w6;
        u3 = 2.0 / (qt[1] - qt[0]);
        u4 = 1.0 - 2.0 * qt[1] / (qt[1] - qt[0]);
        qt[0] = u4;
        qt[1] = u3;
        for i in 0..nknots as usize {
            rknots[i] = u4 + u3 * self.knots[i];
            self.knots[i] = u4 + u3 * self.knots[i];
            iknots[i] = i as i32;
        }
        let lim = (nsample[0] + nsample[2]) as usize;
        for i in 0..lim {
            sample[i] = u4 + u3 * sample[i];
        }
    }
}
