//! Information matrix, score, and C(zheta) for the middle and the tails, remade
//! from `src/lsdall.c`. `middle` integrates numerically between the knots and
//! calls `tails` for the two ends, where the integrals are analytic.

use super::part3::{expin, expin2};
use super::{Lsd, NC};

type Qolint = [[f64; NC + 1]; 7];

impl Lsd {
    /// `middle`: score (into `shift`), information (into `info`), and C(zheta).
    ///
    /// `what == 0` computes only C(zheta) at `zheta`. `what == 1` and `what == 2`
    /// add the score and the information. The return value is the current
    /// `czheta`, as in the C source.
    #[allow(clippy::too_many_arguments)]
    pub fn middle(
        &mut self,
        info: &mut [[f64; NC]; NC],
        shift: &mut [f64],
        sufficient: &[[f64; 2]; NC],
        bound: &[f64],
        accuracy: i32,
        nsample: &[i32],
        sample: &[f64],
        zheta: &[f64],
        what: i32,
    ) -> f64 {
        let nk = self.nknots as usize;
        let nkk = self.nknots as i64;
        let mut qolint: Qolint = [[0.0f64; NC + 1]; 7];
        let mut aa = [0.0f64; 7];

        // The tails can be computed analytically
        let mut cth = self.tails(info, shift, bound, zheta, what);

        // what == 0: we are only interested in czheta
        if what == 0 {
            for i1 in 1..nk {
                for i2 in 1..5 {
                    self.dfunpar[i2] = 0.0;
                    for i3 in (i1 as i64 - 3)..(i1 as i64 + 1) {
                        if i3 >= 0 && i3 < nkk - 1 {
                            self.dfunpar[i2] =
                                self.dfunpar[i2] + self.coef[i3 as usize][i2 - 1][i1] * zheta[i3 as usize];
                        }
                    }
                }
                cth = cth + self.numint2(self.knots[i1 - 1], self.knots[i1], accuracy);
            }
            return cth;
        }

        // The integrals are computed numerically per interval between knots
        for i1 in 1..nk {
            // polint gets the result of a numerical integration of the density
            // times x^i2
            self.numints(&mut aa, self.knots[i1 - 1], self.knots[i1], accuracy, 7);
            for i2 in 0..7 {
                qolint[i2][i1] = aa[i2];
            }

            // For the scorefunction we need integrals of a basisfunction times the
            // density, this is a combination of qolint[]. Basisfunctions do not
            // exists in all intervals.
            for i2 in (i1 as i64 - 3)..=(i1 as i64) {
                if i2 >= 0 && i2 < nkk - 1 && (i2 != 0 || i1 != 3) {
                    let u2 = i2 as usize;
                    shift[u2] = shift[u2]
                        + qolint[0][i1] * self.coef[u2][0][i1]
                        + qolint[1][i1] * self.coef[u2][1][i1]
                        + qolint[2][i1] * self.coef[u2][2][i1]
                        + qolint[3][i1] * self.coef[u2][3][i1];

                    // For the information matrix we need integrals of a basisfunction
                    // times a basisfunction times the density.
                    if what == 2 {
                        for i3 in (i1 as i64 - 3)..=i2 {
                            if i3 >= 0 && i3 < nkk - 1 && (i3 != 0 || i1 != 3) {
                                let u3 = i3 as usize;
                                for i5 in 0..4 {
                                    for i4 in 0..4 {
                                        info[u2][u3] = info[u2][u3]
                                            + qolint[i5 + i4][i1]
                                                * self.coef[u2][i5][i1]
                                                * self.coef[u3][i4][i1];
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // The following lines make the informationmatrix and score function from
        // what is stored into score and info up to now.
        if what == 2 {
            for i1 in 0..nk - 1 {
                for i2 in 0..=i1 {
                    info[i1][i2] = info[i1][i2] - shift[i1] * shift[i2];
                    info[i2][i1] = info[i1][i2];
                }
            }
        }

        // if there is no censoring, we are done
        if nsample[0] != nsample[1] {
            let mut version: i32 = 3;
            if bound[3] > 0.5 {
                version = 4;
            }
            let mut version2: i32 = 1;
            if bound[1] > 0.5 {
                version2 = 2;
            }
            let czheta = self.czheta;
            let d1 = zheta[nk - 2] * self.coef[nk - 2][1][nk];
            let d2 = zheta[0] * self.coef[0][1][0];
            let e2 = zheta[0] * self.coef[0][0][0] - czheta.ln();
            let e1 = if nk > 3 {
                zheta[nk - 2] * self.coef[nk - 2][0][nk]
                    + zheta[nk - 3] * self.coef[nk - 3][0][nk]
                    - czheta.ln()
            } else {
                zheta[nk - 2] * self.coef[nk - 2][0][nk] - czheta.ln()
            };
            for i2 in 0..7 {
                aa[i2] = 0.0;
            }
            for i2 in 0..7 {
                aa[i2] = 1.0;
                if i2 != 0 {
                    aa[i2 - 1] = 0.0;
                }
                qolint[i2][nk] = expin2(version, self.knots[nk - 1], bound[4], &aa, d1, e1);
            }
            for i2 in 0..7 {
                aa[i2] = 0.0;
            }
            for i2 in 0..7 {
                aa[i2] = 1.0;
                if i2 != 0 {
                    aa[i2 - 1] = 0.0;
                }
                qolint[i2][0] = expin2(version2, self.knots[0], bound[2], &aa, d2, e2);
            }

            let n0 = nsample[0];
            let n1 = nsample[1] as usize;
            let n2 = nsample[2] as usize;
            let n3 = nsample[3] as usize;
            let n4 = nsample[4] as usize;

            if accuracy != 0 {
                if n3 > 0 {
                    let mut k0: i32 = 1;
                    for i2 in 0..n3 {
                        if i2 == n3 - 1 || sample[i2 + n1 + 2 * n2] != sample[i2 + n1 + 2 * n2 + 1] {
                            self.intnum3(
                                sample[i2 + n1 + 2 * n2],
                                &qolint,
                                d1,
                                e1,
                                version,
                                bound[4],
                                shift,
                                info,
                                k0,
                                n0,
                                what,
                            );
                            k0 = 0;
                        }
                        k0 += 1;
                    }
                }
                if n4 > 0 {
                    let mut k0: i32 = 1;
                    for i2 in 0..n4 {
                        if i2 == n4 - 1
                            || sample[i2 + n1 + 2 * n2 + n3] != sample[i2 + n1 + 2 * n2 + n3 + 1]
                        {
                            self.intnum4(
                                sample[i2 + n1 + 2 * n2 + n3],
                                &qolint,
                                d2,
                                e2,
                                version2,
                                bound[2],
                                shift,
                                info,
                                k0,
                                n0,
                                what,
                            );
                            k0 = 0;
                        }
                        k0 += 1;
                    }
                }
                if n2 > 0 {
                    let mut k0: i32 = 1;
                    for i2 in 0..n2 {
                        let i1 = n1 + 2 * i2;
                        if i2 == n2 - 1
                            || sample[i1] != sample[i1 + 2]
                            || sample[i1 + 1] != sample[i1 + 3]
                        {
                            self.intnum2(
                                sample[i1],
                                sample[i1 + 1],
                                &qolint,
                                shift,
                                info,
                                k0,
                                n0,
                                what,
                            );
                            k0 = 0;
                        }
                        k0 += 1;
                    }
                }
            } else {
                if n3 > 0 {
                    let mut i1: i32 = 0;
                    for i2 in 0..NC {
                        if self.ng3[i2] > 0 {
                            i1 += self.ng3[i2];
                            self.intnum3(
                                self.xg[i2],
                                &qolint,
                                d1,
                                e1,
                                version,
                                bound[4],
                                shift,
                                info,
                                self.ng3[i2],
                                n0,
                                what,
                            );
                            if i1 == nsample[3] {
                                break;
                            }
                        }
                    }
                }
                if n4 > 0 {
                    let mut i1: i32 = 0;
                    for i2 in 0..NC {
                        if self.ng4[i2] > 0 {
                            i1 += self.ng4[i2];
                            self.intnum4(
                                self.xg[i2],
                                &qolint,
                                d2,
                                e2,
                                version2,
                                bound[2],
                                shift,
                                info,
                                self.ng4[i2],
                                n0,
                                what,
                            );
                            if i1 == nsample[4] {
                                break;
                            }
                        }
                    }
                }
            }
        }
        for i1 in 0..nk - 1 {
            shift[i1] = sufficient[i1][0] - shift[i1];
        }
        if accuracy == 0 && nsample[2] > 0 {
            for i1 in 0..nk - 1 {
                shift[i1] = sufficient[i1][1] + shift[i1];
            }
        }
        self.czheta
    }

    /// `intnum2`: the contribution of one interval-censored observation.
    #[allow(clippy::too_many_arguments)]
    fn intnum2(
        &self,
        x1: f64,
        x2: f64,
        qolint: &Qolint,
        shift: &mut [f64],
        info: &mut [[f64; NC]; NC],
        n1: i32,
        n2: i32,
        what: i32,
    ) {
        let nk = self.nknots as usize;
        let nkk = self.nknots as i64;
        let knots = &self.knots;
        let coef = &self.coef;
        let im = (3 * what + 1) as usize;
        let mut z1 = [0.0f64; NC];
        let mut z2 = [[0.0f64; NC]; NC];
        let mut y1 = [0.0f64; 7];
        let mut y2 = [0.0f64; 7];

        // jl - in which interval is the left endpoint
        // jr - in which interval is the right endpoint
        let mut jl: usize = 0;
        while knots[jl] < x1 && jl < nk {
            jl += 1;
        }
        let mut jr: usize = 0;
        while knots[jr] < x2 && jr < nk {
            jr += 1;
        }
        let (jli, jri) = (jl as i64, jr as i64);
        if jl == jr {
            self.numints(&mut y1, x1, x2, 0, im);
        } else {
            self.numints(&mut y1, x1, knots[jl], 0, im);
            self.numints(&mut y2, knots[jr - 1], x2, 0, im);
        }

        // z1 is going to be the first order contribution, z2 the second order, z0
        // the normalizing constant.
        let mut z0 = 0.0f64;
        for i1 in 0..nk {
            z1[i1] = 0.0;
            if what == 2 {
                for i2 in 0..nk {
                    z2[i1][i2] = 0.0;
                }
            }
        }

        // for each interval strictly between jl and jr we now compute them
        for i1 in 1..nkk {
            let u1 = i1 as usize;
            if i1 > jli && i1 < jri {
                z0 = z0 + qolint[0][u1];
            }
            let mut i3 = i1 - 3;
            while i3 <= i1 && i3 < nkk - 1 {
                if i3 >= 0 {
                    let u3 = i3 as usize;
                    if i1 > jli && i1 < jri {
                        for i2 in 0..4 {
                            z1[u3] = z1[u3] + coef[u3][i2][u1] * qolint[i2][u1];
                        }
                    }
                    if what == 2 {
                        let mut i4 = i1 - 3;
                        while i4 <= i1 && i4 < nkk - 1 {
                            if i4 >= 0 && i1 > jli && i1 < jri {
                                let u4 = i4 as usize;
                                for i2 in 0..4 {
                                    for i5 in 0..4 {
                                        z2[u3][u4] = z2[u3][u4]
                                            + coef[u3][i2][u1] * qolint[i2 + i5][u1] * coef[u4][i5][u1];
                                    }
                                }
                            }
                            i4 += 1;
                        }
                    }
                }
                i3 += 1;
            }
        }
        z0 = z0 + y1[0] + y2[0];

        // we now compute them for the interval in which the left endpoint is
        let mut i3 = jli - 3;
        while i3 <= jli && i3 < nkk - 1 {
            if i3 >= 0 {
                let u3 = i3 as usize;
                for i2 in 0..4 {
                    z1[u3] = z1[u3] + coef[u3][i2][jl] * y1[i2];
                }
                if what == 2 {
                    let mut i4 = jli - 3;
                    while i4 <= jli && i4 < nkk - 1 {
                        if i4 >= 0 {
                            let u4 = i4 as usize;
                            for i2 in 0..4 {
                                for i5 in 0..4 {
                                    z2[u3][u4] = z2[u3][u4]
                                        + coef[u3][i2][jl] * y1[i2 + i5] * coef[u4][i5][jl];
                                }
                            }
                        }
                        i4 += 1;
                    }
                }
            }
            i3 += 1;
        }
        // we now compute them for the interval in which the right endpoint is
        let mut i3 = jri - 3;
        while i3 <= jri && i3 < nkk - 1 {
            if i3 >= 0 {
                let u3 = i3 as usize;
                for i2 in 0..4 {
                    z1[u3] = z1[u3] + coef[u3][i2][jr] * y2[i2];
                }
                if what == 2 {
                    let mut i4 = jri - 3;
                    while i4 <= jri && i4 < nkk - 1 {
                        if i4 >= 0 {
                            let u4 = i4 as usize;
                            for i2 in 0..4 {
                                for i5 in 0..4 {
                                    z2[u3][u4] = z2[u3][u4]
                                        + coef[u3][i2][jr] * y2[i2 + i5] * coef[u4][i5][jr];
                                }
                            }
                        }
                        i4 += 1;
                    }
                }
            }
            i3 += 1;
        }

        // now we update shift and info
        if z0 > 0.0 {
            for i3 in 0..nk {
                shift[i3] = shift[i3] - (n1 as f64) * z1[i3] / (z0 * (n2 as f64));
                if what == 2 {
                    for i4 in 0..nk {
                        info[i3][i4] = info[i3][i4]
                            + (n1 as f64) * (z1[i3] * z1[i4] / z0 - z2[i3][i4])
                                / ((n2 as f64) * z0);
                    }
                }
            }
        }
    }

    /// `intnum3`: one right-censored observation at `x`, with `vs` the version.
    #[allow(clippy::too_many_arguments)]
    fn intnum3(
        &self,
        x: f64,
        qolint: &Qolint,
        d1: f64,
        e1: f64,
        vs: i32,
        bd: f64,
        shift: &mut [f64],
        info: &mut [[f64; NC]; NC],
        n1: i32,
        n2: i32,
        what: i32,
    ) {
        let nk = self.nknots as usize;
        let nkk = self.nknots as i64;
        let knots = &self.knots;
        let coef = &self.coef;
        let im = (3 * what + 1) as usize;
        let mut aa = [0.0f64; 7];
        let mut yy = [0.0f64; 7];
        let mut z1 = [0.0f64; NC];
        let mut z2 = [[0.0f64; NC]; NC];

        // in which interval is the point
        let mut jin: usize = 0;
        while jin < nk && knots[jin] < x {
            jin += 1;
        }
        let jini = jin as i64;
        if jin < nk {
            self.numints(&mut yy, x, knots[jin], 0, im);
        } else {
            for i1 in 0..7 {
                aa[i1] = 1.0;
                if i1 != 0 {
                    aa[i1 - 1] = 0.0;
                }
                yy[i1] = expin2(vs, x, bd, &aa, d1, e1);
            }
        }

        // initialize
        let mut z0 = 0.0f64;
        for i1 in 0..nk {
            z1[i1] = 0.0;
            if what == 2 {
                for i2 in 0..nk {
                    z2[i1][i2] = 0.0;
                }
            }
        }

        // combine for the intervals which are strictly right of the observation
        for i1 in 1..=nkk {
            let u1 = i1 as usize;
            if i1 > jini {
                z0 = z0 + qolint[0][u1];
            }
            let mut i3 = i1 - 3;
            while i3 <= i1 && i3 < nkk - 1 {
                if i3 >= 0 {
                    let u3 = i3 as usize;
                    if i1 > jini {
                        for i2 in 0..4 {
                            z1[u3] = z1[u3] + coef[u3][i2][u1] * qolint[i2][u1];
                        }
                    }
                    if what == 2 {
                        let mut i4 = i1 - 3;
                        while i4 <= i1 && i4 < nkk - 1 {
                            if i4 >= 0 && i1 > jini {
                                let u4 = i4 as usize;
                                for i2 in 0..4 {
                                    for i5 in 0..4 {
                                        z2[u3][u4] = z2[u3][u4]
                                            + coef[u3][i2][u1] * qolint[i2 + i5][u1] * coef[u4][i5][u1];
                                    }
                                }
                            }
                            i4 += 1;
                        }
                    }
                }
                i3 += 1;
            }
        }

        // add the one in the interval in which the point is
        z0 = z0 + yy[0];
        let mut i3 = jini - 3;
        while i3 <= jini && i3 < nkk - 1 {
            if i3 >= 0 {
                let u3 = i3 as usize;
                for i2 in 0..4 {
                    z1[u3] = z1[u3] + coef[u3][i2][jin] * yy[i2];
                }
                if what == 2 {
                    let mut i4 = jini - 3;
                    while i4 <= jini && i4 < nkk - 1 {
                        if i4 >= 0 {
                            let u4 = i4 as usize;
                            for i2 in 0..4 {
                                for i5 in 0..4 {
                                    z2[u3][u4] = z2[u3][u4]
                                        + coef[u3][i2][jin] * yy[i2 + i5] * coef[u4][i5][jin];
                                }
                            }
                        }
                        i4 += 1;
                    }
                }
            }
            i3 += 1;
        }

        // update shift and info
        if z0 > 0.0 {
            for i3 in 0..nk - 1 {
                shift[i3] = shift[i3] - (n1 as f64) * z1[i3] / (z0 * (n2 as f64));
                if what == 2 {
                    for i4 in 0..nk - 1 {
                        info[i3][i4] = info[i3][i4]
                            + (n1 as f64) * (z1[i3] * z1[i4] / z0 - z2[i3][i4])
                                / ((n2 as f64) * z0);
                    }
                }
            }
        }
    }

    /// `intnum4`: one left-censored observation at `x`, with `vs` the version.
    #[allow(clippy::too_many_arguments)]
    fn intnum4(
        &self,
        x: f64,
        qolint: &Qolint,
        d1: f64,
        e1: f64,
        vs: i32,
        bd: f64,
        shift: &mut [f64],
        info: &mut [[f64; NC]; NC],
        n1: i32,
        n2: i32,
        what: i32,
    ) {
        let nk = self.nknots as usize;
        let nkk = self.nknots as i64;
        let knots = &self.knots;
        let coef = &self.coef;
        let im = (3 * what + 1) as usize;
        let mut aa = [0.0f64; 7];
        let mut yy = [0.0f64; 7];
        let mut z1 = [0.0f64; NC];
        let mut z2 = [[0.0f64; NC]; NC];

        // in which interval is the point
        let mut jin: usize = 0;
        while jin < nk && knots[jin] < x {
            jin += 1;
        }
        let jini = jin as i64;
        if jin > 0 {
            self.numints(&mut yy, knots[jin - 1], x, 0, im);
        } else {
            for i1 in 0..7 {
                aa[i1] = 1.0;
                if i1 != 0 {
                    aa[i1 - 1] = 0.0;
                }
                yy[i1] = expin2(vs, x, bd, &aa, d1, e1);
            }
        }

        // initialize
        let mut z0 = 0.0f64;
        for i1 in 0..nk {
            z1[i1] = 0.0;
            if what == 2 {
                for i2 in 0..nk {
                    z2[i1][i2] = 0.0;
                }
            }
        }

        // combine for the intervals which are strictly right of the observation
        for i1 in 0..nkk {
            let u1 = i1 as usize;
            if i1 < jini {
                z0 = z0 + qolint[0][u1];
            }
            let mut i3 = i1 - 3;
            while i3 <= i1 && i3 < nkk - 1 {
                if i3 >= 0 {
                    let u3 = i3 as usize;
                    if i1 < jini {
                        for i2 in 0..4 {
                            z1[u3] = z1[u3] + coef[u3][i2][u1] * qolint[i2][u1];
                        }
                    }
                    if what == 2 {
                        let mut i4 = i1 - 3;
                        while i4 <= i1 && i4 < nkk - 1 {
                            if i4 >= 0 && i1 < jini {
                                let u4 = i4 as usize;
                                for i2 in 0..4 {
                                    for i5 in 0..4 {
                                        z2[u3][u4] = z2[u3][u4]
                                            + coef[u3][i2][u1] * qolint[i2 + i5][u1] * coef[u4][i5][u1];
                                    }
                                }
                            }
                            i4 += 1;
                        }
                    }
                }
                i3 += 1;
            }
        }

        // add the one in the interval in which the point is
        z0 = z0 + yy[0];
        let mut i3 = jini - 3;
        while i3 <= jini && i3 < nkk - 1 {
            if i3 >= 0 {
                let u3 = i3 as usize;
                for i2 in 0..4 {
                    z1[u3] = z1[u3] + coef[u3][i2][jin] * yy[i2];
                }
                if what == 2 {
                    let mut i4 = jini - 3;
                    while i4 <= jini && i4 < nkk - 1 {
                        if i4 >= 0 {
                            let u4 = i4 as usize;
                            for i2 in 0..4 {
                                for i5 in 0..4 {
                                    z2[u3][u4] = z2[u3][u4]
                                        + coef[u3][i2][jin] * yy[i2 + i5] * coef[u4][i5][jin];
                                }
                            }
                        }
                        i4 += 1;
                    }
                }
            }
            i3 += 1;
        }

        // update shift and info
        if z0 > 0.0 {
            for i3 in 0..nk - 1 {
                shift[i3] = shift[i3] - (n1 as f64) * z1[i3] / (z0 * (n2 as f64));
                if what == 2 {
                    for i4 in 0..nk - 1 {
                        info[i3][i4] = info[i3][i4]
                            + (n1 as f64) * (z1[i3] * z1[i4] / z0 - z2[i3][i4])
                                / ((n2 as f64) * z0);
                    }
                }
            }
        }
    }

    /// `tails`: the exact integrals over the two tails.
    ///
    /// `shift` and `info` are cleared first when `what >= 1`, as in the C source.
    /// The divisions by `czheta` use the current value.
    fn tails(
        &self,
        info: &mut [[f64; NC]; NC],
        shift: &mut [f64],
        bound: &[f64],
        zheta: &[f64],
        what: i32,
    ) -> f64 {
        let nk = self.nknots as usize;
        let knots = &self.knots;
        let coef = &self.coef;
        let czheta = self.czheta;
        let mut a = [0.0f64; 7];
        let mut cth: f64 = 0.0;

        // Initialize cth, score and info
        if what >= 1 {
            for i in 0..nk {
                shift[i] = 0.0;
                if what == 2 {
                    for j in 0..nk {
                        info[i][j] = 0.0;
                    }
                }
            }
        }

        // Now we are going to compute the integrals, first the ones for the left
        // tail, then the right tail.
        let mut version: i32 = 1;
        if bound[1] > 0.5 {
            version = 2;
        }

        // The numbers a1,b1,c1,d1,e1 are constants in the integrals
        a[1] = 0.0;
        a[4] = zheta[0] * coef[0][1][0];
        a[5] = zheta[0] * coef[0][0][0];
        if what == 0 {
            a[2] = 0.0;
            a[3] = 1.0;
            cth = expin(version, knots[0], bound[2], &a);
        } else {
            a[2] = coef[0][1][0];
            a[3] = coef[0][0][0];
            shift[0] = expin(version, knots[0], bound[2], &a) / czheta;
            if what == 2 {
                a[1] = coef[0][1][0] * coef[0][1][0];
                a[2] = coef[0][1][0] * coef[0][0][0] * 2.0;
                a[3] = coef[0][0][0] * coef[0][0][0];
                info[0][0] = expin(version, knots[0], bound[2], &a) / czheta;
            }
        }

        // Now the right tail. Only the last 2 basisfunctions are not equal to 0 here.
        version = 3;
        if bound[3] > 0.5 {
            version = 4;
        }
        a[1] = 0.0;
        a[4] = zheta[nk - 2] * coef[nk - 2][1][nk];
        if nk > 3 {
            a[5] = zheta[nk - 2] * coef[nk - 2][0][nk] + zheta[nk - 3] * coef[nk - 3][0][nk];
        } else {
            a[5] = zheta[nk - 2] * coef[nk - 2][0][nk];
        }
        if what == 0 {
            a[2] = 0.0;
            a[3] = 1.0;
            cth = cth + expin(version, knots[nk - 1], bound[4], &a);
        } else {
            if nk > 3 {
                a[2] = 0.0;
                a[3] = coef[nk - 3][0][nk];
                shift[nk - 3] = expin(version, knots[nk - 1], bound[4], &a) / czheta;
            }
            a[2] = coef[nk - 2][1][nk];
            a[3] = coef[nk - 2][0][nk];
            shift[nk - 2] = expin(version, knots[nk - 1], bound[4], &a) / czheta;
        }
        if what == 2 && nk > 3 {
            a[2] = 0.0;
            a[3] = coef[nk - 3][0][nk] * coef[nk - 3][0][nk];
            info[nk - 3][nk - 3] = expin(version, knots[nk - 1], bound[4], &a) / czheta;
            a[2] = coef[nk - 3][0][nk] * coef[nk - 2][1][nk];
            a[3] = coef[nk - 3][0][nk] * coef[nk - 2][0][nk];
            info[nk - 2][nk - 3] = expin(version, knots[nk - 1], bound[4], &a) / czheta;
            info[nk - 3][nk - 2] = info[nk - 2][nk - 3];
        }
        if what == 2 {
            a[1] = coef[nk - 2][1][nk] * coef[nk - 2][1][nk];
            a[2] = coef[nk - 2][0][nk] * coef[nk - 2][1][nk] * 2.0;
            a[3] = coef[nk - 2][0][nk] * coef[nk - 2][0][nk];
            info[nk - 2][nk - 2] = expin(version, knots[nk - 1], bound[4], &a) / czheta;
        }
        cth
    }
}
