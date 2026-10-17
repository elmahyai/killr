//! Barrodale-Roberts parametric process of R package quantreg 6.1, ported from
//! its Fortran `src/rqbr.f` (`rqbr`).
//!
//! R's `rq.fit.br` calls `rqbr` with `tau` outside `[0, 1]`. The routine then
//! sweeps the objective weight `t` from `1/(2m)` to `1 - 1/(2m)` and records one
//! basic solution per breakpoint. The output is the `sol` matrix (rows `tau`,
//! `Qbar`, `Obj.Fun`, then one row per coefficient) and the `dsol` matrix of
//! duals, one column per solution. `ranks` and `predict.rq.process` read these.
//!
//! Only the process path is ported: `ci = FALSE` and `tau` outside `[0, 1]`, so
//! `lci1 = lci2 = FALSE` and the confidence interval branches never run. The
//! Fortran's `e`, `h` and `s` output and the sign flips after the last solution
//! do not reach R's result, so they are not kept.
//!
//! Indices follow the Fortran (1-based). `Tableau` stores each matrix
//! column-major with the Fortran leading dimension, and every accessor takes
//! 1-based `(row, column)` pairs, so each loop reads like the Fortran. The
//! Fortran's `goto` labels become the states of `Stage`.

#![allow(clippy::too_many_arguments, clippy::needless_range_loop)]

#[cfg(feature = "python")]
mod python;

/// `ift` value when the solution may be nonunique (R warning code 1).
pub const FLAG_NONUNIQUE: i32 = 1;
/// `ift` value for a premature end, a conditioning problem in x (R warning code 2).
pub const FLAG_PREMATURE_END: i32 = 2;
/// `ift` value for an empty design or response (the Fortran's `ift = 6`).
pub const FLAG_EMPTY: i32 = 6;
/// `ift` value when the basis bookkeeping breaks (not an R code; the Rust port stops instead of writing outside the arrays).
pub const FLAG_BOOKKEEPING: i32 = 7;
/// `ift` value when more solutions appear than the `3m` columns the R call allocates.
pub const FLAG_TOO_MANY: i32 = 8;

/// The parametric process: `sol` is `(n + 3) x lsol`, `dsol` is `m x lsol`, both column-major.
#[derive(Clone, Debug)]
pub struct Process {
    pub sol: Vec<f64>,
    pub dsol: Vec<f64>,
    /// Number of rows of `sol`, the Fortran's `p + 3`.
    pub sol_rows: usize,
    /// Number of rows of `dsol`, the observations `m`.
    pub dsol_rows: usize,
    pub lsol: usize,
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

/// The control-flow labels of `rqbr`, one per Fortran `goto` target.
#[derive(Clone, Copy, Debug, PartialEq)]
enum Stage {
    /// Label 23045: reduced costs at the current `t`, then the stage choice.
    Start,
    /// Label 30: entering column for the feasibility stage.
    StageEnter,
    /// Label 23055: entering column for the optimality stage.
    OptEnter,
    /// Label 23072: collect the ratio-test candidates.
    Candidates,
    /// Label 23079: pick the smallest ratio, flip or pivot.
    Ratio,
    /// Label 10: pivot on `(out, enter)`.
    Pivot,
    /// Label 20: the feasibility stage's end test.
    AfterPivot,
    /// Label 23081: swap the entering column into position `kr`.
    StageSwap,
    /// Label 23054 and 80: read the solution at the current breakpoint.
    Extract,
    /// Label 40: the last solution, `t = t1`.
    Final,
    /// Label 23047: no ratio candidate, the premature end.
    Failure,
    /// Label 23018: copy the last dual column and return.
    Done,
}

/// The parametric process of `rqbr` for `tau` outside `[0, 1]`.
///
/// `a` is the `m x n` design, row-major (`a[(i - 1) * n + (j - 1)]` is `a(i, j)`).
/// `b` is the response of length `m`, and `tol` is R's `.Machine$double.eps^(2/3)`.
/// The Fortran sweeps `t` over `[1/(2m), 1 - 1/(2m)]`, as `rq.fit.br` calls it.
pub fn rqbr_process(m: usize, n: usize, a: &[f64], b: &[f64], tol: f64) -> Process {
    let empty = |ift: i32| Process { sol: Vec::new(), dsol: Vec::new(), sol_rows: n + 3, dsol_rows: m, lsol: 0, ift };
    if m == 0 || n == 0 {
        return empty(FLAG_EMPTY);
    }
    debug_assert_eq!(a.len(), m * n);
    debug_assert_eq!(b.len(), m);

    let big = f64::MAX;
    let half = 0.5;
    let one = 1.0;
    let two = 2.0;
    let mf = m as f64;

    // Row bounds of the tableau: m1..m5 are the Fortran's m+1..m+5, and n1..n4 the columns.
    let (m1, m2, m3, m4, m5) = (m + 1, m + 2, m + 3, m + 4, m + 5);
    let (n1, n2, n3, n4) = (n + 1, n + 2, n + 3, n + 4);

    let mut wa = Mat::new(m5, n4);
    let mut wb = vec![0.0f64; m + 2];
    let mut s = vec![0usize; m + 2];

    // The sweep range: t0 = 1/(2m), t1 = 1 - t0. `rq.fit.br` passes tau outside [0, 1], so t starts at t0.
    let t0 = one / (two * mf);
    let t1 = one - t0;
    let mut t = t0;
    let mut iend = false;

    let mut ift: i32 = 0;
    let mut x = vec![0.0f64; n + 1];
    let mut dif = 0.0f64;
    // The Fortran leaves smax unset before the first record. It is overwritten
    // at label 40 whenever lsol > 2, so it starts at zero here.
    let mut smax = 0.0f64;

    // Solution storage, with the 3m columns R's .Fortran call allocates.
    let max_sol = 3 * m + 4;
    let mut sol = Mat::new(n + 3, max_sol);
    let mut dsol = Mat::new(m, max_sol);
    let mut lsol: usize = 1;

    // Label 23016: the tableau rows. Columns 1..n are the design, n1 the
    // right-hand side, n2 the response, n3 zero (no idxcf), n4 the row id.
    for i in 1..=m {
        for j in 1..=n {
            wa.set(i, j, a[(i - 1) * n + (j - 1)]);
        }
        wa.set(i, n4, (n + i) as f64);
        wa.set(i, n2, b[i - 1]);
        wa.set(i, n3, 0.0);
        let rhs = wa.at(i, n2) - wa.at(i, n3);
        wa.set(i, n1, rhs);
        if wa.at(i, n1) < 0.0 {
            for j in 1..=n4 {
                wa.set(i, j, -wa.at(i, j));
            }
        }
    }

    // Label 23035: column ids, and the slopes m2 (constant) and m3 (in t) of the reduced costs.
    for j in 1..=n {
        wa.set(m4, j, j as f64);
        wa.set(m2, j, 0.0);
        wa.set(m3, j, 0.0);
        for i in 1..=m {
            let aux = sign(wa.at(m4, j)) * wa.at(i, j);
            let v2 = wa.at(m2, j) + aux * (one - sign(wa.at(i, n4)));
            wa.set(m2, j, v2);
            let v3 = wa.at(m3, j) + aux * sign(wa.at(i, n4));
            wa.set(m3, j, v3);
        }
        let v3 = two * wa.at(m3, j);
        wa.set(m3, j, v3);
    }

    // Column means of the design, kept in row m5 for Qbar.
    for k in 1..=n {
        wa.set(m5, k, 0.0);
        for i in 1..=m {
            let v = wa.at(m5, k) + a[(i - 1) * n + (k - 1)];
            wa.set(m5, k, v);
        }
        let v = wa.at(m5, k) / mf;
        wa.set(m5, k, v);
    }

    let mut init = false;
    let mut stage_feas = false; // the Fortran's `stage`
    let mut kr: usize = 1;
    let mut kl: usize = 1;
    let mut kount: usize = 0;
    let mut enter: usize = 1;
    let mut out: usize = 1;
    let mut j_ratio: usize = 1;
    let mut k: usize = 0;
    let mut test = false;
    let mut pivot = 0.0f64;

    let mut state = Stage::Start;
    loop {
        match state {
            Stage::Start => {
                // Label 23045: reduced costs at t.
                for j in 1..=n {
                    let v = wa.at(m2, j) + wa.at(m3, j) * t;
                    wa.set(m1, j, v);
                }
                if !init {
                    stage_feas = true;
                    kr = 1;
                    kl = 1;
                    state = Stage::StageEnter;
                } else {
                    stage_feas = false;
                    state = Stage::OptEnter;
                }
            }
            Stage::StageEnter => {
                // Label 30: the largest |reduced cost| among structural columns.
                let mut max = -1.0f64;
                for j in kr..=n {
                    if wa.at(m4, j).abs() <= n as f64 {
                        let d = wa.at(m1, j).abs();
                        if d > max {
                            max = d;
                            enter = j;
                        }
                    }
                }
                if wa.at(m1, enter) < 0.0 {
                    for i in 1..=m4 {
                        let v = -wa.at(i, enter);
                        wa.set(i, enter, v);
                    }
                }
                state = Stage::Candidates;
            }
            Stage::OptEnter => {
                // Label 23055: the most negative reduced cost, with the Fortran's folding of d in (-2, 0).
                let mut max = -big;
                for j in kr..=n {
                    let mut d = wa.at(m1, j);
                    if d < 0.0 {
                        if d > -two {
                            continue;
                        }
                        d = -d - two;
                    }
                    if d > max {
                        max = d;
                        enter = j;
                    }
                }
                if max <= tol {
                    state = Stage::Extract;
                } else {
                    if wa.at(m1, enter) <= 0.0 {
                        for i in 1..=m4 {
                            let v = -wa.at(i, enter);
                            wa.set(i, enter, v);
                        }
                        let v1 = wa.at(m1, enter) - two;
                        wa.set(m1, enter, v1);
                        let v2 = wa.at(m2, enter) - two;
                        wa.set(m2, enter, v2);
                    }
                    state = Stage::Candidates;
                }
            }
            Stage::Candidates => {
                // Label 23072: rows with a positive entry in the entering column.
                k = 0;
                for i in kl..=m {
                    let d = wa.at(i, enter);
                    if d > tol {
                        k += 1;
                        wb[k] = wa.at(i, n1) / d;
                        s[k] = i;
                        test = true;
                    }
                }
                state = Stage::Ratio;
            }
            Stage::Ratio => {
                // Label 23079: the smallest ratio, and the bound flip or pivot it leads to.
                if k == 0 {
                    test = false;
                } else {
                    let mut min = big;
                    for i in 1..=k {
                        if wb[i] < min {
                            j_ratio = i;
                            min = wb[i];
                            out = s[i];
                        }
                    }
                    wb[j_ratio] = wb[k];
                    s[j_ratio] = s[k];
                    k -= 1;
                }
                if !test && stage_feas {
                    state = Stage::StageSwap;
                } else if !test {
                    state = Stage::Failure;
                } else {
                    pivot = wa.at(out, enter);
                    if wa.at(m1, enter) - pivot - pivot <= tol {
                        state = Stage::Pivot;
                    } else {
                        for j in kr..=n3 {
                            let d = wa.at(out, j);
                            let v1 = wa.at(m1, j) - d - d;
                            wa.set(m1, j, v1);
                            let v2 = wa.at(m2, j) - d - d;
                            wa.set(m2, j, v2);
                            wa.set(out, j, -d);
                        }
                        let v = -wa.at(out, n4);
                        wa.set(out, n4, v);
                        state = Stage::Ratio;
                    }
                }
            }
            Stage::Pivot => {
                // Label 10: the pivot on (out, enter).
                for j in kr..=n3 {
                    if j != enter {
                        let v = wa.at(out, j) / pivot;
                        wa.set(out, j, v);
                    }
                }
                for i in 1..=m3 {
                    if i != out {
                        let d = wa.at(i, enter);
                        for j in kr..=n3 {
                            if j != enter {
                                let v = wa.at(i, j) - d * wa.at(out, j);
                                wa.set(i, j, v);
                            }
                        }
                    }
                }
                for i in 1..=m3 {
                    if i != out {
                        let v = -wa.at(i, enter) / pivot;
                        wa.set(i, enter, v);
                    }
                }
                wa.set(out, enter, one / pivot);
                let d = wa.at(out, n4);
                let v = wa.at(m4, enter);
                wa.set(out, n4, v);
                wa.set(m4, enter, d);
                kount += 1;
                if !stage_feas {
                    state = Stage::OptEnter;
                } else {
                    kl += 1;
                    for j in kr..=n4 {
                        let d = wa.at(out, j);
                        let v = wa.at(kount, j);
                        wa.set(out, j, v);
                        wa.set(kount, j, d);
                    }
                    state = Stage::AfterPivot;
                }
            }
            Stage::AfterPivot => {
                // Label 20: the feasibility stage ends when kount + kr = n + 1.
                if kount + kr == n1 {
                    stage_feas = false;
                    state = Stage::OptEnter;
                } else {
                    state = Stage::StageEnter;
                }
            }
            Stage::StageSwap => {
                // Label 23081: the entering column moves to position kr.
                for i in 1..=m4 {
                    let d = wa.at(i, kr);
                    let v = wa.at(i, enter);
                    wa.set(i, kr, v);
                    wa.set(i, enter, d);
                }
                kr += 1;
                state = Stage::AfterPivot;
            }
            Stage::Failure => {
                ift = FLAG_PREMATURE_END;
                state = Stage::Done;
            }
            Stage::Extract => {
                // Label 23054 and 80: the basis at this breakpoint.
                if kr == 1 {
                    for j in 1..=n {
                        let d = wa.at(m1, j).abs();
                        if d <= tol || two - d <= tol {
                            ift = FLAG_NONUNIQUE;
                            break;
                        }
                    }
                }
                let mut sum = 0.0f64;
                for i in 1..kl {
                    let kk = wa.at(i, n4).abs() as usize;
                    if kk < 1 || kk > n {
                        return empty(FLAG_BOOKKEEPING);
                    }
                    x[kk] = wa.at(i, n1) * sign(wa.at(i, n4));
                }
                for i in 1..=n {
                    let kd = wa.at(m4, i).abs() as usize;
                    if kd <= n || kd > n + m {
                        return empty(FLAG_BOOKKEEPING);
                    }
                    let kd = kd - n;
                    let mut dv = one + wa.at(m1, i) / two;
                    if wa.at(m4, i) < 0.0 {
                        dv = one - dv;
                    }
                    dsol.set(kd, lsol, dv);
                    sum += x[i] * wa.at(m5, i);
                    sol.set(i + 3, lsol, x[i]);
                }
                for i in kl..=m {
                    let kd = wa.at(i, n4).abs() as usize;
                    if kd <= n || kd > n + m {
                        return empty(FLAG_BOOKKEEPING);
                    }
                    let kd = kd - n;
                    if wa.at(i, n4) < 0.0 {
                        dsol.set(kd, lsol, 0.0);
                    }
                    if wa.at(i, n4) > 0.0 {
                        dsol.set(kd, lsol, 1.0);
                    }
                }
                sol.set(1, lsol, smax);
                sol.set(2, lsol, sum);
                let mut obj = 0.0f64;
                for j in kl..=m {
                    let d = wa.at(j, n1) * sign(wa.at(j, n4));
                    obj += d * (smax + half * (sign(d) - one));
                }
                sol.set(3, lsol, obj);
                if lsol + 1 > max_sol {
                    return empty(FLAG_TOO_MANY);
                }
                for i in 1..=m {
                    let v = dsol.at(i, lsol);
                    dsol.set(i, lsol + 1, v);
                }
                if iend {
                    state = Stage::Final;
                } else {
                    init = true;
                    lsol += 1;
                    if lsol + 1 > max_sol {
                        return empty(FLAG_TOO_MANY);
                    }
                    for j in 1..=n {
                        x[j] = 0.0;
                    }
                    smax = two;
                    for j in 1..=n {
                        let mut b1 = wa.at(m3, j);
                        let a1 = (-two - wa.at(m2, j)) / b1;
                        b1 = -wa.at(m2, j) / b1;
                        if a1 >= t && a1 < smax {
                            smax = a1;
                            dif = (b1 - a1) / two;
                        }
                        if b1 > t && b1 < smax {
                            smax = b1;
                            dif = (b1 - a1) / two;
                        }
                    }
                    let tnt = smax + tol * (one + dif.abs());
                    if tnt >= t1 + tol {
                        iend = true;
                    }
                    t = tnt;
                    if iend {
                        t = t1;
                    }
                    state = Stage::Start;
                }
            }
            Stage::Final => {
                // Label 40: the boundary solutions at tau = 0 and tau = 1.
                if lsol > 2 {
                    sol.set(1, 1, 0.0);
                    sol.set(3, 1, 0.0);
                    sol.set(1, lsol, one);
                    sol.set(3, lsol, 0.0);
                    for i in 1..=m {
                        dsol.set(i, 1, one);
                        dsol.set(i, lsol, 0.0);
                        dsol.set(i, lsol + 1, 0.0);
                    }
                }
                state = Stage::Done;
            }
            Stage::Done => {
                // Label 23018: the last dual column is the one copied to lsol.
                for i in 1..=m {
                    let v = dsol.at(i, lsol + 1);
                    dsol.set(i, lsol, v);
                }
                break;
            }
        }
    }

    let mut sol_out = Vec::with_capacity((n + 3) * lsol);
    for col in 1..=lsol {
        for row in 1..=n + 3 {
            sol_out.push(sol.at(row, col));
        }
    }
    let mut dsol_out = Vec::with_capacity(m * lsol);
    for col in 1..=lsol {
        for row in 1..=m {
            dsol_out.push(dsol.at(row, col));
        }
    }
    Process { sol: sol_out, dsol: dsol_out, sol_rows: n + 3, dsol_rows: m, lsol, ift }
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
        let out = rqbr_process(0, 2, &[], &[], 1e-10);
        assert_eq!(out.ift, FLAG_EMPTY);
        assert_eq!(out.lsol, 0);
    }
}
