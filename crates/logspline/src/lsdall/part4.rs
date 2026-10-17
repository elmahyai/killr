//! Starting values and the sufficient statistics, remade from `src/lsdall.c`.

use super::{Lsd, NC};
use crate::linpack::{dsifa, dsisl};

impl Lsd {
    /// `start2`: combine the derivatives and cross-products into the starting
    /// values `zheta`. It solves a linear system with the LINPACK routines.
    pub fn start2(
        &mut self,
        crossprods: &[[f64; NC]; NC],
        derivatives: &[f64; NC],
        coef2: &[[f64; NC]; NC],
        nkstart: i32,
        iremove: i32,
    ) {
        let nk = self.nknots as usize;
        let nki = self.nknots;
        let mut work = [[0.0f64; NC]; NC];

        // Initializations
        let r1 = self.zheta[0];
        let r2 = self.zheta[1];
        let r3 = self.zheta[nk - 2];
        let r4 = self.zheta[nk - 1];
        if nk > 4 {
            for i in 0..nk {
                self.zheta[i] = 0.0;
                for j in 0..nk {
                    work[i][j] = 0.0;
                }
            }

            // The left hand side is a matrix with sums of crossproducts of derivatives
            // of basis functions. The right hand side is a vector with second
            // derivatives of the basis functions.
            for i in 0..nk - 1 {
                // these are the only combinations for which coef2 is not equal to 0
                for j2 in (i + 1)..(i + 6).min(nk + 2) {
                    let mut j = j2;
                    if i == 0 && j == 5 {
                        j = 1;
                    }
                    self.zheta[i] = self.zheta[i] - coef2[i][j] * derivatives[j - 1];
                    for k in i..nk - 1 {
                        // these are the only combinations for which coef2 is not equal to 0
                        for l2 in (k + 1)..(k + 6).min(nk + 2) {
                            let mut l = l2;
                            if k == 0 && l == 5 {
                                l = 1;
                            }
                            work[i][k] =
                                work[i][k] + coef2[i][j] * coef2[k][l] * crossprods[j - 1][l - 1];
                        }
                    }
                }
            }

            // Make symmetric
            for i in 1..nk - 1 {
                for j in 0..i {
                    work[i][j] = work[j][i];
                }
            }

            // Solving the system finishes the job.
            let mut kpvt = [0i32; 200];
            let mut infox: i32 = 0;
            dsifa(work.as_flattened_mut(), NC, nk - 1, &mut kpvt, &mut infox);
            dsisl(work.as_flattened(), NC, nk - 1, &kpvt, &mut self.zheta);

            // If we had previous iterations - we're sometimes better of using that
            if nkstart != nki {
                if iremove > 2 {
                    self.zheta[0] = r1;
                    self.zheta[1] = r2;
                }
                if iremove < 3 {
                    self.zheta[0] = r1 / 25.0;
                    self.zheta[1] = r2 / 25.0;
                }
                if (iremove as i64) < nk as i64 - 2 {
                    self.zheta[nk - 3] = r3;
                    self.zheta[nk - 2] = r4;
                }
                if (iremove as i64) > nk as i64 - 3 {
                    self.zheta[nk - 3] = r3 / 25.0;
                    if nk == 4 && iremove == 3 {
                        self.zheta[1] = (r2 + r3) / 50.0;
                    }
                    self.zheta[nk - 2] = r4 / 25.0;
                }
            } else {
                // If the zhetas are too large, we are better of if we make them smaller
                let mut r1s = 0.0f64;
                for i in 0..nk - 2 {
                    r1s = r1s + self.zheta[i].abs();
                }
                if r1s > 10000.0 {
                    for i in 0..nk - 2 {
                        self.zheta[i] = self.zheta[i] * 10000.0 / r1s;
                    }
                }
            }
        } else {
            for i in 0..3 {
                self.zheta[i] = 0.0;
            }
        }
    }

    /// `suffstat1`: statistics of the data used by `suffstat2`.
    pub fn suffstat1(
        &self,
        suffcombine: &mut [[f64; 2]; NC],
        sample: &[f64],
        nsample: &[i32],
    ) {
        let nk = self.nknots as usize;
        let knots = &self.knots;
        let n0 = nsample[0] as f64;

        // initialization
        for i in 1..nk + 2 {
            suffcombine[i][0] = 0.0;
            suffcombine[i][1] = 0.0;
        }

        suffcombine[0][0] = nsample[1] as f64 / nsample[0] as f64;
        suffcombine[0][1] = nsample[2] as f64 / nsample[0] as f64;

        // for the complete observations
        for j in 0..nsample[1] as usize {
            suffcombine[1][0] = suffcombine[1][0] + sample[j] / n0;
            for i in 2..nk + 2 {
                if sample[j] > knots[i - 2] {
                    suffcombine[i][0] =
                        suffcombine[i][0] + (sample[j] - knots[i - 2]).powf(3.0) / n0;
                }
            }
        }
        // for the interval censored observations
        for j in 0..nsample[2] as usize {
            let rr = (sample[nsample[1] as usize + 2 * j]
                + sample[nsample[1] as usize + 2 * j + 1])
                / 2.0;
            suffcombine[1][1] = suffcombine[1][1] + rr / n0;
            for i in 2..nk + 2 {
                if rr > knots[i - 2] {
                    suffcombine[i][1] = suffcombine[i][1] + (rr - knots[i - 2]).powf(3.0) / n0;
                }
            }
        }
    }

    /// `suffstat2`: sufficient statistics for the current basis `coef2`.
    pub fn suffstat2(
        &self,
        suffcombine: &[[f64; 2]; NC],
        coef2: &[[f64; NC]; NC],
        sufficient: &mut [[f64; 2]; NC],
    ) {
        let nk = self.nknots as usize;
        // over the basisfunctions
        for i in 0..nk {
            sufficient[i][0] = 0.0;
            sufficient[i][1] = 0.0;
            // over the intervals
            for j in 0..nk + 2 {
                sufficient[i][0] = sufficient[i][0] + suffcombine[j][0] * coef2[i][j];
                sufficient[i][1] = sufficient[i][1] + suffcombine[j][1] * coef2[i][j];
            }
        }
    }
}
