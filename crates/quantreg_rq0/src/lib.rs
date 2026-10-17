//! Dense single-tau simplex of R package quantreg 6.1, ported from its Fortran
//! `src/rq0.f` (`rq0`), a modified Koenker-D'Orey algorithm (Applied Statistics
//! AS 229) for the quantile regression linear program at one `tau`.
//!
//! R's `boot.rq.pwy` (`pwy` in `src/boot.f`) calls `rq0` once per replicate, on
//! the design with one extra row `U[, i] / tau` and the response with one extra
//! value `n * max(|y|)`. `rqs` calls it for each column of a response matrix.
//!
//! Stage 1 finds a feasible basis (`STAGE` true, the first `KL - 1` rows), and
//! stage 2 optimizes. The Fortran's parametric sweep over `t` (labels 43 to 47)
//! cannot be reached from the entry point, so it is not ported. The residual
//! vector `e` and the work arrays are not returned: R's `pwy` discards them.
//!
//! Indices follow the Fortran (1-based). `Mat` stores each matrix column-major
//! with the Fortran leading dimension, and every accessor takes 1-based
//! `(row, column)` pairs, so the loops read like the Fortran. The Fortran's
//! `goto` labels become the states of `Stage`.

#![allow(clippy::too_many_arguments, clippy::needless_range_loop)]

#[cfg(feature = "python")]
mod python;

/// `ift` value when `m` or `n` is not positive (the Fortran's `IFT = 5`).
pub const FLAG_EMPTY: i32 = 5;
/// `ift` value when `tau` is outside `[0, 1]` (the Fortran's `IFT = 6`).
pub const FLAG_TAU: i32 = 6;

/// The big value the Fortran's `BIG` takes (`1.D37`).
const BIG: f64 = 1.0e37;

/// The coefficients of one `rq0` fit and the Fortran's `IFT`.
#[derive(Clone, Debug)]
pub struct Rq0Fit {
    pub coef: Vec<f64>,
    pub ift: i32,
}

/// A column-major matrix with 1-based indices, as the Fortran arrays are.
#[derive(Clone, Debug)]
struct Mat {
    ld: usize,
    data: Vec<f64>,
}

impl Mat {
    fn new(rows: usize, cols: usize) -> Self {
        Self { ld: rows, data: vec![0.0; rows * cols] }
    }

    #[inline]
    fn at(&self, i: usize, j: usize) -> f64 {
        self.data[(j - 1) * self.ld + (i - 1)]
    }

    #[inline]
    fn set(&mut self, i: usize, j: usize, v: f64) {
        self.data[(j - 1) * self.ld + (i - 1)] = v;
    }
}

/// Fortran `SIGN(ONE, x)`: `+1` or `-1` with the sign bit of `x`, as gfortran returns it.
#[inline]
fn sign(x: f64) -> f64 {
    1.0f64.copysign(x)
}

/// The control-flow labels of `rq0` that the entry point reaches, one per Fortran `goto` target.
#[derive(Clone, Copy, Debug, PartialEq)]
enum Stage {
    /// Label 49: marginal costs at `tau`, then the stage 1 start.
    Costs,
    /// Label 70: entering column for stage 1, the largest `|reduced cost|` among structural columns.
    Enter1,
    /// Label 100: collect the ratio-test candidates.
    Candidates,
    /// Label 120: a candidate is left, or not.
    Check,
    /// Label 130: remove the smallest ratio from the candidates.
    MinRatio,
    /// Label 150: the stage 1 linear dependence check.
    Dependence,
    /// Label 170: no candidate in stage 2 is a premature end; otherwise label 180.
    PivotCheck,
    /// Label 200: pivot on `(out, inn)`.
    Pivot,
    /// Label 260: the stage 1 end test.
    AfterStage1Pivot,
    /// Label 270: entering column for stage 2.
    Enter2,
    /// Label 310: read the coefficients from the basic rows.
    Quantiles,
    /// Label 390 and the return.
    Done,
}

/// The dense simplex for the quantile regression LP at `tau`.
///
/// `a` is the `m x n` design, row-major (`a[(i - 1) * n + (j - 1)]` is `a(i, j)`).
/// `b` is the response of length `m`. `tau` must lie in `[0, 1]`, and `toler` is
/// the Fortran's `TOLER` (R's `pwy` passes `tol = 1e-4`). The coefficients are
/// returned in `coef`, of length `n`; a premature end leaves them at zero, as the
/// Fortran does, and `ift` stays 0 there, as in the Fortran.
pub fn rq0(m: usize, n: usize, a: &[f64], b: &[f64], tau: f64, toler: f64) -> Rq0Fit {
    let zeros = |ift: i32| Rq0Fit { coef: vec![0.0; n], ift };
    if m == 0 || n == 0 {
        return zeros(FLAG_EMPTY);
    }
    if !(0.0..=1.0).contains(&tau) {
        return zeros(FLAG_TAU);
    }
    debug_assert_eq!(a.len(), m * n);
    debug_assert_eq!(b.len(), m);

    let nf = n as f64;

    // Row bounds: m1..m4 are the Fortran's M+1..M+4, n1 and n2 the RHS and the row-id columns.
    // The Fortran's row M+5 holds column means that the simplex never reads, so it is not allocated.
    let (m1, m2, m3, m4) = (m + 1, m + 2, m + 3, m + 4);
    let (n1, n2) = (n + 1, n + 2);

    let mut wa = Mat::new(m4, n2);
    // WB and S are 1-based, as in the Fortran: WB(K) is a ratio, S(K) its row.
    let mut wb = vec![0.0f64; m + 1];
    let mut s = vec![0usize; m + 1];

    // Label 23016 (the copy and the sign flips): columns 1..n are the design, n1 the
    // response, n2 the row id N + i. A row with a negative response is negated.
    for i in 1..=m {
        for j in 1..=n {
            wa.set(i, j, a[(i - 1) * n + (j - 1)]);
        }
        wa.set(i, n1, b[i - 1]);
        wa.set(i, n2, (n + i) as f64);
        if wa.at(i, n1) < 0.0 {
            for j in 1..=n2 {
                wa.set(i, j, -wa.at(i, j));
            }
        }
    }
    // The ids of the structural columns, and the slopes of the reduced costs in the
    // constant (m2) and tau (m3) parts.
    let mut x = vec![0.0f64; n];
    for j in 1..=n {
        wa.set(m4, j, j as f64);
    }
    for j in 1..=n {
        wa.set(m2, j, 0.0);
        wa.set(m3, j, 0.0);
        for i in 1..=m {
            let aux = sign(wa.at(m4, j)) * wa.at(i, j);
            let v2 = wa.at(m2, j) + aux * (1.0 - sign(wa.at(i, n2)));
            wa.set(m2, j, v2);
            let v3 = wa.at(m3, j) + aux * sign(wa.at(i, n2));
            wa.set(m3, j, v3);
        }
        let v3 = 2.0 * wa.at(m3, j);
        wa.set(m3, j, v3);
    }
    // The Fortran's objective flag, cleared before the simplex and set to 2 on a premature end.
    wa.set(m2, n1, 0.0);

    // Simplex state. The Fortran's INIT is always false on this path, so it is not kept.
    let mut stage1 = true;
    let mut kr: usize = 1;
    let mut kl: usize = 1;
    let mut kount: usize = 0;
    let mut inn: usize = 1;
    let mut out: usize = 1;
    let mut k: usize = 0;
    let mut test = false;
    let mut pivot = 0.0f64;

    let mut state = Stage::Costs;
    loop {
        match state {
            Stage::Costs => {
                // Label 49: the marginal costs at tau, then stage 1 from the start.
                for j in 1..=n {
                    let v = wa.at(m2, j) + wa.at(m3, j) * tau;
                    wa.set(m1, j, v);
                }
                stage1 = true;
                kr = 1;
                kl = 1;
                state = Stage::Enter1;
            }
            Stage::Enter1 => {
                // Label 70: the largest |reduced cost| among columns that are structural.
                let mut max = -1.0f64;
                for j in kr..=n {
                    if wa.at(m4, j).abs() > nf {
                        continue;
                    }
                    let d = wa.at(m1, j).abs();
                    if d <= max {
                        continue;
                    }
                    max = d;
                    inn = j;
                }
                if wa.at(m1, inn) < 0.0 {
                    for i in 1..=m4 {
                        let v = -wa.at(i, inn);
                        wa.set(i, inn, v);
                    }
                }
                state = Stage::Candidates;
            }
            Stage::Candidates => {
                // Label 100: the ratios of the rows that can leave the basis.
                k = 0;
                for i in kl..=m {
                    let d = wa.at(i, inn);
                    if d <= toler {
                        continue;
                    }
                    k += 1;
                    wb[k] = wa.at(i, n1) / d;
                    s[k] = i;
                }
                state = Stage::Check;
            }
            Stage::Check => {
                // Label 120: TEST says whether any ratio candidate was found.
                if k > 0 {
                    test = true;
                    state = Stage::MinRatio;
                } else {
                    test = false;
                    state = Stage::Dependence;
                }
            }
            Stage::MinRatio => {
                // Label 130: the smallest ratio, then drop it from the candidates.
                let mut min = BIG;
                let mut jmin = 1usize;
                for i in 1..=k {
                    if wb[i] >= min {
                        continue;
                    }
                    jmin = i;
                    min = wb[i];
                    out = s[i];
                }
                wb[jmin] = wb[k];
                s[jmin] = s[k];
                k -= 1;
                state = Stage::Dependence;
            }
            Stage::Dependence => {
                // Label 150: in stage 1 with no candidate, swap the column into position KR.
                if test || !stage1 {
                    state = Stage::PivotCheck;
                } else {
                    for i in 1..=m4 {
                        let d = wa.at(i, kr);
                        wa.set(i, kr, wa.at(i, inn));
                        wa.set(i, inn, d);
                    }
                    kr += 1;
                    state = Stage::AfterStage1Pivot;
                }
            }
            Stage::PivotCheck => {
                if !test {
                    // Label 170: stage 2 with no candidate, a premature end.
                    wa.set(m2, n1, 2.0);
                    state = Stage::Done;
                } else {
                    // Label 180: pivot if the reduced cost allows it, else flip the column and
                    // take the next candidate (label 120).
                    pivot = wa.at(out, inn);
                    if wa.at(m1, inn) - pivot - pivot <= toler {
                        state = Stage::Pivot;
                    } else {
                        for j in kr..=n1 {
                            let d = wa.at(out, j);
                            let v1 = wa.at(m1, j) - d - d;
                            wa.set(m1, j, v1);
                            let v2 = wa.at(m2, j) - d - d;
                            wa.set(m2, j, v2);
                            wa.set(out, j, -d);
                        }
                        wa.set(out, n2, -wa.at(out, n2));
                        state = Stage::Check;
                    }
                }
            }
            Stage::Pivot => {
                // Label 200: pivot on (out, inn). The update runs column by column so that each
                // column is contiguous. Every element gets the same operands as the Fortran's
                // row-by-row loop, so the result is unchanged.
                for j in kr..=n1 {
                    if j == inn {
                        continue;
                    }
                    let v = wa.at(out, j) / pivot;
                    wa.set(out, j, v);
                }
                // Column IN is read before any update, as the Fortran reads WA(I, IN) at label 230.
                let ld = wa.ld;
                let col_in: Vec<f64> = wa.data[(inn - 1) * ld..(inn - 1) * ld + m3].to_vec();
                for j in kr..=n1 {
                    if j == inn {
                        continue;
                    }
                    let base = (j - 1) * ld;
                    let u = wa.data[base + out - 1];
                    for (i0, (c, d)) in wa.data[base..base + m3].iter_mut().zip(col_in.iter()).enumerate() {
                        if i0 + 1 == out {
                            continue;
                        }
                        *c = *c - *d * u;
                    }
                }
                for i in 1..=m3 {
                    if i == out {
                        continue;
                    }
                    let v = -wa.at(i, inn) / pivot;
                    wa.set(i, inn, v);
                }
                wa.set(out, inn, 1.0 / pivot);
                let d = wa.at(out, n2);
                wa.set(out, n2, wa.at(m4, inn));
                wa.set(m4, inn, d);
                kount += 1;
                if stage1 {
                    // Stage 1 interchanges the pivot row into position KOUNT.
                    kl += 1;
                    for j in kr..=n2 {
                        let d = wa.at(out, j);
                        wa.set(out, j, wa.at(kount, j));
                        wa.set(kount, j, d);
                    }
                    state = Stage::AfterStage1Pivot;
                } else {
                    state = Stage::Enter2;
                }
            }
            Stage::AfterStage1Pivot => {
                // Label 260: stage 1 ends when KOUNT + KR reaches N + 1.
                if kount + kr != n1 {
                    state = Stage::Enter1;
                } else {
                    stage1 = false;
                    state = Stage::Enter2;
                }
            }
            Stage::Enter2 => {
                // Label 270: the entering column for stage 2, with the reduced costs at or below -2.
                let mut max = -BIG;
                for j in kr..=n {
                    let mut d = wa.at(m1, j);
                    if d < 0.0 {
                        if d > -2.0 {
                            continue;
                        }
                        d = -d - 2.0;
                    }
                    if d <= max {
                        continue;
                    }
                    max = d;
                    inn = j;
                }
                if max <= toler {
                    state = Stage::Quantiles;
                } else {
                    if wa.at(m1, inn) <= 0.0 {
                        for i in 1..=m4 {
                            let v = -wa.at(i, inn);
                            wa.set(i, inn, v);
                        }
                        let v1 = wa.at(m1, inn) - 2.0;
                        wa.set(m1, inn, v1);
                        let v2 = wa.at(m2, inn) - 2.0;
                        wa.set(m2, inn, v2);
                    }
                    state = Stage::Candidates;
                }
            }
            Stage::Quantiles => {
                // Label 310: the basic structural columns in rows 1..KL-1 give the coefficients.
                for i in 1..kl {
                    let sg = sign(wa.at(i, n2));
                    let col = (wa.at(i, n2) * sg) as i64;
                    let value = wa.at(i, n1) * sg;
                    if col >= 1 && (col as usize) <= n {
                        x[col as usize - 1] = value;
                    }
                }
                state = Stage::Done;
            }
            Stage::Done => break,
        }
    }

    Rq0Fit { coef: x, ift: 0 }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sign_follows_gfortran() {
        assert_eq!(sign(0.0), 1.0);
        assert_eq!(sign(-0.0), -1.0);
        assert_eq!(sign(-3.5), -1.0);
        assert_eq!(sign(2.0), 1.0);
    }

    #[test]
    fn empty_input_flags_error() {
        let fit = rq0(0, 2, &[], &[], 0.5, 1e-4);
        assert_eq!(fit.ift, FLAG_EMPTY);
        assert_eq!(fit.coef, vec![0.0, 0.0]);
    }

    #[test]
    fn tau_outside_unit_interval_flags_error() {
        let fit = rq0(1, 1, &[1.0], &[1.0], 1.5, 1e-4);
        assert_eq!(fit.ift, FLAG_TAU);
    }

    #[test]
    fn median_of_three_values() {
        // Intercept-only LP at tau = 0.5: the coefficient is the sample median.
        let a = [1.0, 1.0, 1.0];
        let b = [1.0, 5.0, 2.0];
        let fit = rq0(3, 1, &a, &b, 0.5, 1e-4);
        assert_eq!(fit.ift, 0);
        assert!((fit.coef[0] - 2.0).abs() < 1e-12, "got {}", fit.coef[0]);
    }
}
