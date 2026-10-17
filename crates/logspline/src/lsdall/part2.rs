//! The main iteration loop `liter` and the integration bounds `setbounds`,
//! remade from `src/lsdall.c`.

use super::part3::numbertester;
use super::{rprintf, Lsd, NC};
use crate::linpack::{dsidi, dsifa, dsisl};

/// Copy `cbound[1..5]` back into `bound[1..5]`, as the C code does before
/// each early return.
fn restore(bound: &mut [f64], cbound: &[f64; 7]) {
    for i in 1..5 {
        bound[i] = cbound[i];
    }
}

impl Lsd {
    /// `liter`: iterate to the maximum likelihood `zheta`.
    ///
    /// Returns the log-likelihood. `itrouble` records the convergence status
    /// and `sorc[0]` the error code, as in the C source.
    #[allow(clippy::too_many_arguments)]
    pub fn liter(
        &mut self,
        info: &mut [[f64; NC]; NC],
        sufficient: &[[f64; 2]; NC],
        bound: &mut [f64],
        sorc: &mut [i32],
        nsample: &[i32],
        sample: &[f64],
        accuracy_in: i32,
        itrouble: &mut i32,
    ) -> f64 {
        let mut counter: i32 = 0;
        let mut nrc: i32 = 0;
        let mut nrc2: i32 = 0;
        let mut zerror: f64 = 0.0;
        let mut oldlikelihood: f64 = 0.0;
        let mut cbound = [0.0f64; 7];
        let mut shift = [0.0f64; NC];
        let mut dd = [0.0f64; 2];
        let mut candidate = [0.0f64; NC];
        let mut newlikelihood: f64 = 0.0;
        let mut work = [[0.0f64; NC]; NC];
        let one: f64 = 0.99999;
        let mut rvr = [0.0f64; 100];
        let mut zerrorx: f64;
        let mut accuracy = accuracy_in;
        let mut kpvt = [0i32; NC];
        let mut iii = [0i32; 4];
        let mut infol: i32 = 0;
        let mut i2: i32;
        let mut i7: i32;
        let mut jaja1: i32;
        let nk = self.nknots as usize;
        let nki = self.nknots;

        // sets integration bounds
        self.setbounds(bound, &mut cbound, nsample);

        // accuracy = 0 means that we approximate censoring
        if accuracy == 0 && nsample[0] == nsample[1] {
            accuracy = 1;
        }

        // start of the iteration
        if sorc[0] == 0 {
            rprintf(&format!("{} \n", nki));
        }
        let mut i1: i32 = 1;
        while i1 < 500 {
            // if we go extremely far out in the tails, and zheta[first] or
            // zheta[last] still doesn't have the right sign, we fix the bounds at
            // the max value
            let mut ithere: i32 = 0;
            if bound[3] < 0.5 || bound[3] > 1.5 {
                ithere = 5;
            } else if bound[4] >= 25.0 * self.knots[nk - 1] - 24.0 * self.knots[0] {
                if sorc[0] == 0 && sorc[24] == 0 {
                    rprintf("a very long right tail");
                }
                sorc[24] = nki;
                *itrouble = 17;
                restore(bound, &cbound);
                return 0.0;
            }
            if bound[1] < 0.5 || bound[1] > 1.5 {
                ithere += 5;
            } else if bound[2] <= -24.0 * self.knots[nk - 1] + 25.0 * self.knots[0] {
                if sorc[0] == 0 && sorc[23] == 0 {
                    rprintf("a very long left tail");
                }
                sorc[23] = nki;
                *itrouble = 17;
                restore(bound, &cbound);
                return 0.0;
            }

            // after 250 iterations we do the censoring exact
            if accuracy == 0 && i1 == 250 {
                accuracy = 1;
                counter = 0;
            }
            jaja1 = 0;
            counter += 1;

            // if something changed in the bounds since last time counter = 0, and
            // we have to recompute czheta and the loglikelihood
            i7 = 0;
            loop {
                if counter == 1 {
                    loop {
                        let v = self.middle(
                            info,
                            &mut shift,
                            sufficient,
                            bound,
                            accuracy,
                            nsample,
                            sample,
                            &self.zheta.clone(),
                            0,
                        );
                        self.czheta = v;
                        // check against overflow and NAs
                        i2 = -1;
                        if self.czheta > 0.0 {
                            i2 += 1;
                        }
                        if self.czheta < 2.0 {
                            i2 += 1;
                        }
                        if numbertester(self.czheta) == 1 {
                            i2 -= 4;
                        }
                        if i2 < 0 {
                            for i in 0..nk - 1 {
                                self.zheta[i] /= 10.0;
                            }
                            if i7 > 7 && *itrouble == 0 {
                                *itrouble = 2;
                                restore(bound, &cbound);
                                return 0.0;
                            }
                            i2 = -6;
                            i7 += 1;
                            if i7 == 200 {
                                *itrouble = 5;
                                return 1.0;
                            }
                        }
                        if i2 >= 0 {
                            break;
                        }
                    }
                    newlikelihood = self.likeli_now(nsample, sample, bound, accuracy);
                }

                // compute score (stored in shift), info and czheta
                let v = self.middle(
                    info,
                    &mut shift,
                    sufficient,
                    bound,
                    accuracy,
                    nsample,
                    sample,
                    &self.zheta.clone(),
                    2,
                );
                self.czheta = v;

                // store the loglikelihood of the previous iteration
                oldlikelihood = newlikelihood;

                // copy info and solve the system
                for a in 0..nk - 1 {
                    for b in 0..nk - 1 {
                        work[a][b] = info[a][b];
                    }
                }
                dsifa(work.as_flattened_mut(), NC, nk - 1, &mut kpvt, &mut infol);
                // check for underflows overflows and NA
                if infol != 0 {
                    for a in 0..nk - 1 {
                        self.zheta[a] /= 100.0;
                    }
                    if i7 > 7 && *itrouble == 0 {
                        *itrouble = 2;
                        restore(bound, &cbound);
                        return 0.0;
                    }
                    i7 += 1;
                    if i7 == 200 {
                        *itrouble = 5;
                        return 1.0;
                    }
                }
                if infol == 0 {
                    break;
                }
            }
            iii[1] = 0;
            iii[2] = 0;
            if nsample[2] + nsample[3] + nsample[4] > 0 {
                dsidi(
                    work.as_flattened_mut(),
                    NC,
                    nk - 1,
                    &kpvt,
                    &mut dd,
                    &mut iii[..],
                    &mut rvr[..],
                    100,
                );
            }
            for a in 0..nk - 1 {
                rvr[a] = shift[a];
            }
            iii[3] = iii[1] + iii[2];
            if iii[2] + iii[1] == 0 {
                nrc = 0;
            }
            if iii[2] + iii[1] == 0 {
                nrc2 = 0;
            }
            if iii[1] + iii[2] > 0 && nrc + nrc2 >= 5 && nrc >= 2 {
                nrc2 += 1;
                if nrc2 == 15 && *itrouble == 0 {
                    *itrouble = 2;
                    restore(bound, &cbound);
                    return 0.0;
                }
                if nrc2 == 48 && *itrouble != 0 {
                    *itrouble = 5;
                    restore(bound, &cbound);
                    return 1.0;
                }
                iii[2] = 0;
                iii[1] = 0;
                nrc = 0;
            }
            if iii[2] + iii[1] == 0 {
                dsisl(work.as_flattened(), NC, nk - 1, &kpvt, &mut shift);

                // compute the stop criterion and adjust stepsize, if too large
                i7 = 0;
                loop {
                    zerrorx = self.error2(&shift, &rvr);
                    zerrorx *= 100.0;
                    zerror = self.erroradjust(&mut shift);
                    if iii[3] == 0 {
                        zerror = zerrorx;
                    }
                    i2 = -1;
                    if zerror > 0.0 {
                        i2 += 2;
                    }
                    if zerror < 2.0 {
                        i2 += 2;
                    }
                    if numbertester(zerror) == 1 {
                        i2 -= 4;
                    }
                    if i2 < 0 {
                        for a in 0..nk - 1 {
                            shift[a] /= 10.0;
                        }
                        if i7 > 7 && *itrouble == 0 {
                            *itrouble = 2;
                            restore(bound, &cbound);
                            return 0.0;
                        }
                        i7 += 1;
                        if i7 == 200 {
                            *itrouble = 5;
                            return 1.0;
                        }
                        i2 = -7;
                    }
                    if i2 >= 0 {
                        break;
                    }
                }

                // counter is the number of iterations since the last adjustment of
                // integration boundaries. Thus if we find an zerror, we put it to 0
                // and start all over. Temporarily we deduct 10000 from it if we have
                // to half the step size first
                i7 = 0;
                loop {
                    if counter < -1000 {
                        counter += 10000;
                    }

                    // We should check whether zheta's that should be negative (the
                    // ones for tail basis functions if we are integrating to
                    // plus/minus infinity) stay negative.
                    if self.zheta[0] + shift[0] >= 0.0 && bound[1] < 0.5 {
                        cbound[5] = -cbound[5];
                        bound[2] = cbound[5] * (self.knots[0] - self.knots[1]) + self.knots[0];
                        bound[1] = 1.0;
                        counter = 0;
                    }
                    if self.zheta[nk - 2] + shift[nk - 2] >= 0.0 && bound[3] < 0.5 {
                        cbound[6] = -cbound[6];
                        bound[4] = cbound[6] * (self.knots[nk - 1] - self.knots[nk - 2])
                            + self.knots[nk - 1];
                        bound[3] = 1.0;
                        counter = 0;
                    }

                    // Compute the C(zheta) for the candidate zheta-hat. We can then
                    // compute the new log-likelihood.
                    if counter > 0 {
                        for a in 0..nk - 1 {
                            candidate[a] = shift[a] + self.zheta[a];
                        }
                        let v = self.middle(
                            info,
                            &mut shift,
                            sufficient,
                            bound,
                            accuracy,
                            nsample,
                            sample,
                            &candidate,
                            0,
                        );
                        self.czheta = v;
                        i2 = 0;
                        if self.czheta > 0.0 {
                            i2 += 1;
                        }
                        if self.czheta < 2.0 {
                            i2 += 1;
                        }
                        if numbertester(self.czheta) == 1 {
                            i2 -= 4;
                        }
                        if i2 > 0 {
                            newlikelihood =
                                self.likeli(&candidate, nsample, sample, bound, accuracy);

                            // If the loglikelihood really decreases, we step size and go
                            // back a bit
                            if newlikelihood < oldlikelihood
                                && ((newlikelihood / oldlikelihood < one)
                                    || (oldlikelihood / newlikelihood < one))
                                && zerror > 0.00001
                            {
                                jaja1 += 1;
                                if jaja1 < 12 || i1 < 3 {
                                    for a in 0..nk - 1 {
                                        shift[a] /= 2.0;
                                    }
                                    counter -= 10000;
                                }
                            }
                        } else {
                            if i7 > 7 && *itrouble == 0 {
                                *itrouble = 2;
                                restore(bound, &cbound);
                                return 0.0;
                            }
                            i7 += 1;
                            if i7 == 200 {
                                *itrouble = 5;
                                return 1.0;
                            }
                            for a in 0..nk - 1 {
                                shift[a] /= 10.0;
                            }
                            counter -= 10000;
                        }
                    }
                    if counter >= 0 {
                        break;
                    }
                }
                // Only if the counter is negative we have to go back.
            }
            if jaja1 == 25 {
                restore(bound, &cbound);
                return newlikelihood;
            }
            if iii[2] + iii[1] > 0 {
                nrc += 1;
                for a in 0..nk - 1 {
                    shift[a] = rvr[a];
                }
                for a in 0..nk - 1 {
                    rvr[a] = self.zheta[a];
                }
                self.erroradjust(&mut shift);
                if cbound[5] < 0.0
                    && bound[1] < 0.5
                    && (cbound[5] > -6.0 || self.zheta[0] + shift[0] > 0.0)
                {
                    cbound[5] = -cbound[5];
                    bound[2] = cbound[5] * (self.knots[0] - self.knots[1]) + self.knots[0];
                    bound[1] = 1.0;
                    counter = 0;
                }
                if cbound[6] < 0.0
                    && bound[3] < 0.5
                    && (cbound[6] > -6.0 || self.zheta[nk - 2] + shift[nk - 2] > 0.0)
                {
                    cbound[6] = -cbound[6];
                    bound[4] = cbound[6] * (self.knots[nk - 1] - self.knots[nk - 2])
                        + self.knots[nk - 1];
                    bound[3] = 1.0;
                    counter = 0;
                }
                if counter == 0 {
                    let v = self.middle(
                        info,
                        &mut shift,
                        sufficient,
                        bound,
                        accuracy,
                        nsample,
                        sample,
                        &self.zheta.clone(),
                        0,
                    );
                    self.czheta = v;
                    self.middle(
                        info,
                        &mut shift,
                        sufficient,
                        bound,
                        accuracy,
                        nsample,
                        sample,
                        &self.zheta.clone(),
                        1,
                    );
                    oldlikelihood = self.likeli_now(nsample, sample, bound, accuracy);
                    for a in 0..nk - 1 {
                        shift[a] = rvr[a];
                    }
                    for a in 0..nk - 1 {
                        rvr[a] = self.zheta[a];
                    }
                    self.erroradjust(&mut shift);
                }
                oldlikelihood =
                    self.linsearch(&mut shift, oldlikelihood, bound, nsample, sample, accuracy);
                let v = self.middle(
                    info,
                    &mut shift,
                    sufficient,
                    bound,
                    accuracy,
                    nsample,
                    sample,
                    &self.zheta.clone(),
                    0,
                );
                self.czheta = v;
                self.middle(
                    info,
                    &mut shift,
                    sufficient,
                    bound,
                    accuracy,
                    nsample,
                    sample,
                    &self.zheta.clone(),
                    1,
                );
                self.erroradjust(&mut shift);
                oldlikelihood =
                    self.linsearch(&mut shift, oldlikelihood, bound, nsample, sample, accuracy);
                for a in 0..nk - 1 {
                    shift[a] = self.zheta[a] - rvr[a];
                }
                oldlikelihood =
                    self.linsearch(&mut shift, oldlikelihood, bound, nsample, sample, accuracy);
                let v = self.middle(
                    info,
                    &mut shift,
                    sufficient,
                    bound,
                    accuracy,
                    nsample,
                    sample,
                    &self.zheta.clone(),
                    0,
                );
                self.czheta = v;
                for a in 0..nk - 1 {
                    shift[a] = 0.0;
                }
                for a in 0..nk - 1 {
                    rvr[a] = self.zheta[a] - rvr[a];
                }
                zerror = 100.0 * self.erroradjust(&mut rvr[..]);
                newlikelihood = oldlikelihood;
            }

            // O.K. the new zheta is good, let's store it.
            if counter > 0 {
                for a in 0..nk - 1 {
                    self.zheta[a] += shift[a];
                }

                // Is there convergence? If this is not the final iteration, we're not picky.
                if ithere < 10 {
                    zerror /= 100.0;
                }
                if zerror < 0.000001 {
                    // If we were integrating to +/-infinity or if we exceeded the
                    // bounds, done.
                    if ithere > 9 {
                        if accuracy == 5 {
                            restore(bound, &cbound);
                            let v = self.middle(
                                info,
                                &mut shift,
                                sufficient,
                                bound,
                                5,
                                nsample,
                                sample,
                                &self.zheta.clone(),
                                0,
                            );
                            rvr[99] = v;
                            if iii[1] + iii[2] != 0 {
                                let v = self.middle(
                                    info,
                                    &mut shift,
                                    sufficient,
                                    bound,
                                    5,
                                    nsample,
                                    sample,
                                    &self.zheta.clone(),
                                    0,
                                );
                                rvr[99] = v;
                            }
                            i2 = 0;
                            if rvr[99] > 0.0 {
                                i2 += 1;
                            }
                            if rvr[99] < 2.0 {
                                i2 += 1;
                            }
                            if numbertester(rvr[99]) == 1 {
                                i2 -= 4;
                            }
                            if i2 > 0 {
                                self.czheta = rvr[99];
                                newlikelihood = self.likeli_now(nsample, sample, bound, 5);
                            }
                            return newlikelihood;
                        } else {
                            accuracy = 5;
                            counter = 0;
                        }
                    } else {
                        // If we were not integrating to +/- infinity, we either double
                        // the integration tails (if a tail zheta was possitive) or we go
                        // for it: +/- infinity (That means cbound[5] and cbound[6]
                        // become negative.)
                        counter = 0;
                        // Left tail
                        if cbound[5] < 0.0 {
                            // case A
                            cbound[5] = 2.0 * cbound[5];
                        } else {
                            if cbound[1] < 0.5 && self.zheta[0] >= 0.0 {
                                // case B
                                cbound[5] = 2.0 * cbound[5];
                                bound[2] =
                                    cbound[5] * (self.knots[0] - self.knots[1]) + self.knots[0];
                            }
                            if cbound[1] < 0.5 && self.zheta[0] < 0.0 {
                                // case B to A
                                cbound[5] = -2.0 * cbound[5];
                                bound[1] = 0.0;
                            }
                            if cbound[1] > 0.5 && bound[1] > 0.5 && bound[1] < 1.5 {
                                // case E
                                cbound[5] = 2.0 * cbound[5];
                                bound[2] =
                                    cbound[5] * (self.knots[0] - self.knots[1]) + self.knots[0];
                                if bound[2] < cbound[2] {
                                    // goto C/D
                                    bound[2] = cbound[2];
                                    bound[1] = 2.0;
                                }
                            }
                        }
                        // Right tail
                        if cbound[6] < 0.0 {
                            // case A
                            cbound[6] = 2.0 * cbound[6];
                        } else {
                            if cbound[3] < 0.5 && self.zheta[nk - 2] >= 0.0 {
                                // case B
                                cbound[6] = 2.0 * cbound[6];
                                bound[4] = cbound[6] * (self.knots[nk - 1] - self.knots[nk - 2])
                                    + self.knots[nk - 1];
                            }
                            if cbound[3] < 0.5 && self.zheta[nk - 2] < 0.0 {
                                // case B to A
                                cbound[6] = -2.0 * cbound[6];
                                bound[3] = 0.0;
                            }
                            if cbound[3] > 0.5 && bound[3] > 0.5 && bound[3] < 1.5 {
                                // case E
                                cbound[6] = 2.0 * cbound[6];
                                bound[4] = cbound[6] * (self.knots[nk - 1] - self.knots[nk - 2])
                                    + self.knots[nk - 1];
                                if bound[4] > cbound[4] {
                                    // goto C/D
                                    bound[4] = cbound[4];
                                    bound[3] = 2.0;
                                }
                            }
                        }
                    }
                }
            }
            i1 += 1;
        }

        // If we ended up here, there was no convergence in 300 iterations.
        if sorc[0] == 0 {
            rprintf(&format!("no convergence was achieved with {} knots\n", nki));
            sorc[0] = -647;
        } else {
            sorc[0] = -sorc[0];
        }
        newlikelihood
    }

    /// `setbounds`: set the integration boundaries in each tail.
    ///
    /// `cbound` is the copy of the boundaries used while iterating. See the C
    /// source for the five cases A to E.
    pub fn setbounds(&self, bound: &mut [f64], cbound: &mut [f64; 7], nsample: &[i32]) {
        let nk = self.nknots as usize;
        let knots = &self.knots;
        let zheta = &self.zheta;

        // the lower tail
        cbound[2] = bound[2];
        cbound[1] = bound[1];
        cbound[5] = 1.0;
        if nsample[3] * 3 > nsample[1] {
            cbound[5] = 0.5;
        }
        bound[2] = cbound[5] * (knots[0] - knots[1]) + knots[0];

        if zheta[0] < 0.0 && cbound[1] < 0.5 && nsample[0] == nsample[1] {
            cbound[5] = -1.0;
        }
        if cbound[1] < 0.5 && (zheta[0] >= 0.0 || nsample[0] != nsample[1]) {
            bound[1] = 1.0;
        }
        if cbound[1] > 0.5 {
            bound[1] = 2.0;
        }
        if cbound[1] > 0.5 && zheta[1] >= 0.0 && bound[2] >= cbound[2] {
            bound[1] = 1.0;
        }
        if cbound[1] > 0.5 && (zheta[0] < 0.0 || (zheta[0] >= 0.0 && bound[2] < cbound[2])) {
            bound[2] = cbound[2];
        }

        // the upper tail almost similar
        cbound[4] = bound[4];
        cbound[3] = bound[3];
        cbound[6] = 1.0;
        if nsample[4] * 3 > nsample[1] {
            cbound[6] = 0.5;
        }
        bound[4] = cbound[6] * (knots[nk - 1] - knots[nk - 2]) + knots[nk - 1];
        if zheta[nk - 2] < 0.0 && cbound[3] < 0.5 && nsample[0] == nsample[1] {
            cbound[6] = -cbound[6];
        }
        if cbound[3] < 0.5 && (zheta[nk - 2] >= 0.0 || nsample[0] != nsample[1]) {
            bound[3] = 1.0;
        }
        if cbound[3] > 0.5 {
            bound[3] = 2.0;
        }
        if cbound[3] > 0.5 && zheta[nk - 2] >= 0.0 && cbound[4] >= bound[4] {
            bound[3] = 1.0;
        }
        if cbound[3] > 0.5
            && (zheta[nk - 2] < 0.0 || (zheta[nk - 2] >= 0.0 && bound[4] > cbound[4]))
        {
            bound[4] = cbound[4];
        }
    }
}
