//! Oldlogspline density fit (the `logcensor` entry point), remade from
//! `src/lsdall.c` in logspline 2.1.22.
//!
//! Copyright [1993-2018] Charles Kooperberg. Licensed under the Apache License,
//! Version 2.0, as stated in the header of the original file. That header also
//! keeps a leftover line with the Free Software Foundation address from an
//! earlier GPL notice; the licence it grants is Apache-2.0.
//!
//! The C file keeps its working state in file-scope statics (`knots`, `coef`,
//! `zheta`, `czheta`, `xg`, `dfunpar`, `nknots`, `ng3`, `ng4`). Those are the
//! fields of [`Lsd`]. The functions are methods on `Lsd`, and each keeps the C
//! name in snake case.

mod part2;
mod part3;
mod part4;
mod part5;
mod part6;
pub(crate) mod tables;

use crate::linpack::{dsidi, dsifa};

/// Maximum number of knots and the width of every square work matrix.
pub const NC: usize = 50;

/// Print text the way R's `Rprintf` does: to standard output.
pub(crate) fn rprintf(text: &str) {
    print!("{text}");
}

/// The file-scope state of `lsdall.c`.
pub struct Lsd {
    pub knots: [f64; NC],
    /// `coef[NC][4][NC]` in the C source.
    pub coef: Box<[[[f64; NC]; 4]; NC]>,
    pub zheta: [f64; NC],
    pub czheta: f64,
    pub xg: [f64; NC],
    pub dfunpar: [f64; 6],
    pub nknots: i32,
    pub ng3: [i32; NC],
    pub ng4: [i32; NC],
}

impl Default for Lsd {
    fn default() -> Self {
        Lsd {
            knots: [0.0; NC],
            coef: Box::new([[[0.0; NC]; 4]; NC]),
            zheta: [0.0; NC],
            czheta: 0.0,
            xg: [0.0; NC],
            dfunpar: [0.0; 6],
            nknots: 0,
            ng3: [0; NC],
            ng4: [0; NC],
        }
    }
}

impl Lsd {
    /// `logcensor`: the main program of the old logspline fit.
    ///
    /// The R wrapper passes vectors padded with zeros. `sample` has length at
    /// least `nsample[0] + nsample[2] + 1`. `yknots`, `ycoef`, and `wk`/`wk2`
    /// have length at least `NC`. `logl` has length at least `nsample[0] + 11`.
    /// `sorc` has length 35, `bound` has length 5, and `nsample` has length 5
    /// (the C source indexes these by fixed positions).
    #[allow(clippy::too_many_arguments)]
    pub fn logcensor(
        &mut self,
        idelete: i32,
        iknotauto: i32,
        sample: &mut [f64],
        nsample: &mut [i32],
        bound: &mut [f64],
        sorc: &mut [i32],
        ynknots: &mut i32,
        yknots: &mut [f64],
        ycoef: &mut [f64],
        alpha: f64,
        wk: &mut [f64],
        wk2: &mut [f64],
        logl: &mut [f64],
    ) {
        let accuracy: i32 = 0;
        let mut xnknots: i32 = 0;
        let mut qt = [0.0f64; 2];
        let mut info = [[0.0f64; NC]; NC];
        let mut loglikelihood: f64 = 0.0;
        let mut sufficient = [[0.0f64; 2]; NC];
        let mut coef2 = [[0.0f64; NC]; NC];
        let mut xczheta: f64 = 0.0;
        let mut derivatives = [0.0f64; NC];
        let mut crossprods = [[0.0f64; NC]; NC];
        let mut suffcombine = [[0.0f64; 2]; NC];
        let mut xzheta = [0.0f64; NC];
        let mut aic: f64;
        let mut aicmin: f64;
        let mut r1: f64;
        let mut xcoef2 = [[0.0f64; NC]; NC];
        let mut nkstart: i32;
        let mut iremove: i32 = 0;
        let mut iknots = [0i32; NC];
        let mut xiknots = [0i32; NC];
        let mut itrouble: i32;

        // compute the number of knots (to start)
        for i in 0..NC {
            self.ng3[i] = 0;
        }
        for i in 0..NC {
            self.ng4[i] = 0;
        }
        self.nknots = *ynknots;
        for i in 0..NC {
            self.knots[i] = yknots[i];
        }

        // 14 is the minimum sample size
        if nsample[0] < 14 {
            if sorc[0] == 0 {
                rprintf("sample is too small\n");
            } else {
                sorc[0] = 2;
            }
            return;
        }

        // determine the number of starting knots
        self.nknots = part5::knotnumber(idelete, nsample, self.nknots, sorc);

        // place the knots
        let mut rknots = [0.0f64; NC];
        self.knotplace(
            &mut iknots,
            &mut rknots,
            iknotauto,
            bound,
            sample,
            nsample,
            sorc,
            wk,
            wk2,
            &mut qt,
        );
        bound[2] = qt[0] + qt[1] * bound[2];
        bound[4] = qt[0] + qt[1] * bound[4];

        // initialize aicmin to a very large value
        aicmin = 10f64.powf(100.0);

        nkstart = self.nknots;
        for i in 0..self.nknots as usize {
            self.xg[i] = self.knots[i];
        }
        let nk = self.nknots as usize;
        let mut i = nsample[1] + 2 * nsample[2];
        while i < nsample[0] + nsample[2] - nsample[4] {
            let iu = i as usize;
            let mut j = 0usize;
            while self.knots[j] < sample[iu] && j < nk {
                j += 1;
            }
            if j != 0 && j != nk && sample[iu] - self.knots[j - 1] < self.knots[j] - sample[iu] {
                j -= 1;
            }
            if j == nk {
                j -= 1;
            }
            self.ng3[j] += 1;
            i += 1;
        }
        let mut i = nsample[1] + 2 * nsample[2] + nsample[3];
        while i < nsample[0] + nsample[2] {
            let iu = i as usize;
            let mut j = 0usize;
            while self.knots[j] < sample[iu] && j < nk {
                j += 1;
            }
            if j != 0 && j != nk && sample[iu] - self.knots[j - 1] < self.knots[j] - sample[iu] {
                j -= 1;
            }
            if j == nk {
                j -= 1;
            }
            self.ng4[j] += 1;
            i += 1;
        }
        for i in 0..nk {
            yknots[i] = self.knots[i];
        }

        // some possible errors
        if sorc[0] == -2 {
            return;
        }
        if sorc[0] == 647 {
            return;
        }
        if sorc[0] == 23 {
            return;
        }

        // Compute stuff later used for computing sufficient statistics.
        self.suffstat1(&mut suffcombine, sample, nsample);

        // Compute stuff later used for computing the starting values.
        self.start1(&mut crossprods, &mut derivatives, sample, nsample);

        // Compute coefficient matrix.
        itrouble = 0;
        loop {
            self.coeff(&mut coef2);

            // Compute sufficient statistics.
            self.suffstat2(&suffcombine, &coef2, &mut sufficient);

            // Compute starting values
            self.start2(&mut crossprods, &mut derivatives, &coef2, nkstart, iremove);

            // Compute zheta-hat (main iteration loop).
            if itrouble == 1 {
                for i in 0..(self.nknots - 1) as usize {
                    self.zheta[i] = 0.0;
                }
                loglikelihood = self.liter(
                    &mut info,
                    &sufficient,
                    bound,
                    sorc,
                    nsample,
                    sample,
                    5,
                    &mut itrouble,
                );
            } else {
                loglikelihood = self.liter(
                    &mut info,
                    &sufficient,
                    bound,
                    sorc,
                    nsample,
                    sample,
                    accuracy,
                    &mut itrouble,
                );
                if itrouble == 2 {
                    for i in 0..(self.nknots - 1) as usize {
                        self.zheta[i] = 0.0;
                    }
                    itrouble = 1;
                    loglikelihood = self.liter(
                        &mut info,
                        &sufficient,
                        bound,
                        sorc,
                        nsample,
                        sample,
                        5,
                        &mut itrouble,
                    );
                }
            }

            // this means that there were problems (like no convergence)
            sorc[27] = 0;
            if sorc[0] < 0 || itrouble == 5 || itrouble == 17 {
                if self.nknots == nkstart {
                    sorc[0] = -1;
                    sorc[27] = 0;
                    return;
                }
                if sorc[0] == -647 {
                    rprintf(&format!(
                        "Smallest number of knots tried is {}\n",
                        self.nknots + 1
                    ));
                }
                sorc[27] = self.nknots;
                self.nknots = 0;
            }

            // If we have a fixed number of knots we are done now.
            // Copy the solution in the x-arrays
            if self.nknots > 0 {
                if idelete == 0 {
                    xczheta = self.czheta;
                    xnknots = self.nknots;
                    for i in 0..NC {
                        xzheta[i] = self.zheta[i];
                        xiknots[i] = iknots[i];
                        for j in 0..NC {
                            xcoef2[i][j] = coef2[i][j];
                        }
                    }
                    logl[0] = loglikelihood * nsample[0] as f64
                        + qt[1].ln() * nsample[1] as f64;
                } else {
                    // We are deleting knots. Compute aic. Is it an improvement?
                    aic = -2.0 * loglikelihood * nsample[0] as f64
                        + alpha * (self.nknots - 1) as f64;
                    logl[(self.nknots - 1) as usize] = loglikelihood * nsample[0] as f64
                        + qt[1].ln() * nsample[1] as f64;
                    if aic <= aicmin {
                        // Then we mark the solution
                        aicmin = aic;
                        xczheta = self.czheta;
                        xnknots = self.nknots;
                        for i in 0..NC {
                            xzheta[i] = self.zheta[i];
                            xiknots[i] = iknots[i];
                            for j in 0..NC {
                                xcoef2[i][j] = coef2[i][j];
                            }
                        }
                        // that is we fill it here, iknots contains the rank numbers of
                        // the remaining knots
                    } else {
                        r1 = -2.0 * loglikelihood * nsample[0] as f64 + alpha * 2.0;
                        if r1 >= aicmin {
                            self.nknots = 0;
                        }
                    }

                    // If there were more than 4 knots, we should remove one.
                    if self.nknots >= 4 {
                        // Select the one to remove.
                        iremove = self.removeknot(&mut info, &coef2);

                        // Remove its remainders from all sort of arrays. That is, shift
                        // the ends of the array 1 closer to 0, crossprods gets shifted in
                        // 2 directions
                        let nk = self.nknots as usize;
                        let ir = iremove as usize;
                        for i in ir..nk {
                            self.knots[i] = self.knots[i + 1];
                            iknots[i] = iknots[i + 1];
                            derivatives[i + 1] = derivatives[i + 2];
                            suffcombine[i + 2][0] = suffcombine[i + 3][0];
                            suffcombine[i + 2][1] = suffcombine[i + 3][1];
                            crossprods[0][i + 1] = crossprods[0][i + 2];
                            crossprods[i + 1][0] = crossprods[i + 2][0];
                        }
                        for j in 0..nk {
                            for i in ir..nk {
                                if j >= ir {
                                    crossprods[i + 1][j + 1] = crossprods[i + 2][j + 2];
                                }
                            }
                            for i in ir..nk {
                                if j < ir {
                                    crossprods[i + 1][j + 1] = crossprods[i + 2][j + 1];
                                }
                            }
                            for i in 0..ir {
                                if j >= ir {
                                    crossprods[i + 1][j + 1] = crossprods[i + 1][j + 2];
                                }
                            }
                        }
                    } else if self.nknots == 3 {
                        self.nknots = 2;
                    }
                }
            }
            if !(self.nknots >= 3 && idelete > 0) {
                break;
            }
        }

        // Now write the solution down. This prints the density
        self.nknots = nkstart;
        fits(&xcoef2, &xzheta, xczheta, ycoef, &xiknots, xnknots);
        *ynknots = nkstart;
        let nks = nkstart as usize;
        bound[2] = (bound[2] - qt[0]) / qt[1];
        bound[4] = (bound[4] - qt[0]) / qt[1];
        for i in 0..nks {
            yknots[i] = (yknots[i] - qt[0]) / qt[1];
        }
        for i in 0..nks {
            ycoef[i + 2] = ycoef[i + 2] * qt[1] * qt[1] * qt[1];
        }
        ycoef[0] = ycoef[0] + ycoef[1] * qt[0] + qt[1].ln();
        ycoef[1] = ycoef[1] * qt[1];
    }

    /// `removeknot`: choose the knot whose removal is least costly.
    pub fn removeknot(&mut self, info: &mut [[f64; NC]; NC], coef2: &[[f64; NC]; NC]) -> i32 {
        let mut ratmax: f64 = 0.0;
        let mut wk1 = [0.0f64; NC];
        let mut se = [0.0f64; NC];
        let mut phi = [0.0f64; NC];
        let mut x1 = [0.0f64; 2];
        let mut x2 = [0i32; 3];
        let x3: i32 = 1;
        let mut kpvt = [0i32; NC];
        let mut irmax: i32 = 1;
        let nk = self.nknots as usize;

        // Take linear combinations of zheta such that phi is zheta(phi) for the
        // truncated power basis. (Which is not a basis.)
        for i in 0..nk - 1 {
            phi[i] = 0.0;
            for j in 0..nk - 1 {
                phi[i] = phi[i] + self.zheta[j] * coef2[j][i + 2];
            }
            phi[i] = phi[i].abs();
        }

        // Invert the information matrix, giving the approximate covariance
        // matrix for zheta
        let mut infol: i32 = 0;
        let flat = info.as_flattened_mut();
        dsifa(flat, NC, nk - 1, &mut kpvt, &mut infol);
        dsidi(flat, NC, nk - 1, &kpvt, &mut x1, &mut x2, &mut wk1, x3);

        // For convenience: symmetrize
        for i in 1..nk - 1 {
            for j in 0..i {
                info[j][i] = info[i][j];
            }
        }

        // Take linear combinations, to get the standard errors of phi we don't
        // use the tail ones
        for i in 1..nk - 1 {
            se[i] = 0.0;
            for j in 0..nk - 1 {
                for k in 0..nk - 1 {
                    se[i] = se[i] + coef2[j][i + 2] * coef2[k][i + 2] * info[j][k];
                }
            }
            if se[i] > 0.0 {
                se[i] = se[i].sqrt();

                // Select for which knot se/phi takes it maximal value
                if se[i] > phi[i] * ratmax {
                    ratmax = se[i] / phi[i];
                    irmax = i as i32;
                }
            }
        }
        self.nknots -= 1;
        irmax
    }
}

/// `fits`: write the coefficients of the chosen fit into `ycoef`.
fn fits(
    xcoef2: &[[f64; NC]; NC],
    xzheta: &[f64],
    xczheta: f64,
    ycoef: &mut [f64],
    xiknots: &[i32],
    xnknots: i32,
) {
    let xn = xnknots as usize;
    for i in 0..NC {
        ycoef[i] = 0.0;
    }
    ycoef[0] = -xczheta.ln();
    for i in 0..xn {
        let idx = (xiknots[i] + 2) as usize;
        ycoef[idx] = 0.0;
        for j in 0..xn - 1 {
            ycoef[idx] = ycoef[idx] + xzheta[j] * xcoef2[j][i + 2];
        }
    }
    for j in 0..xn - 1 {
        ycoef[0] = ycoef[0] + xzheta[j] * xcoef2[j][0];
        ycoef[1] = ycoef[1] + xzheta[j] * xcoef2[j][1];
    }
}
