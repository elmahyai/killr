//! Density-family least-squares cross-validation (locfit `geth = 6`,
//! R's `lscv` default path), ported from locfit 1.5-9.12:
//!
//! - `dens_int.c` `dens_lscv` (the criterion and its degrees of freedom) and
//!   `dens_integrate` / `estdiv` (the integral of the fitted density squared);
//! - `density.c` `densinit` / `likeden` / `prodint` (the log-density local
//!   likelihood and its Newton system, one-dimensional, log link);
//! - `m_max.c` `max_nr` (the Newton iteration) and `procv.c` / `lf_vari.c`
//!   (the influence `t0` of each vertex, `A^{-1} e_0`).
//!
//! The fit is at the data (`ev = dat()`): every observation is a vertex, so
//! the interpolation the default `ev = rbox()` needs is not used here.
//!
//! The one-dimensional integrals `int W(|t|/h) t^j exp(P(t)) dt` come from
//! `odi.rs` (a port of `dens_odi.c` `onedint` / `recurint`, with the same
//! series truncations as R). The Gaussian kernel (locfit `gausint`) is not
//! ported.

use crate::eig::Jac;
use crate::fit::{compbandwid, vvari};
use crate::tree::{self, VFit, What};
use crate::kernel::{w_fn, Kernel};
use crate::odi::{estdiv_log, onedint};

/// Newton settings from locfit `locfit.raw`: `maxit = 20`, and the log-link
/// density tolerance `tol = 1e-6` (locfit `likeden`, `lfiter`).
const MAXIT: usize = 20;
const TOL: f64 = 1.0e-6;

/// Options that map onto `locfit.raw` for the density path.
#[derive(Clone, Copy, Debug)]
pub struct DensOpts {
    /// Nearest-neighbour fraction (`alpha[1]`).
    pub nn: f64,
    /// Fixed bandwidth floor (`alpha[2]`).
    pub fixh: f64,
    /// Local polynomial degree (`deg`).
    pub deg: usize,
    /// Compact kernel (locfit `ker`).
    pub kern: Kernel,
}

/// Basis `t^j / j!`, j = 0..=deg (locfit `fitfun` for d = 1).
fn basis(t: f64, deg: usize, out: &mut [f64]) {
    let mut v = 1.0;
    out[0] = 1.0;
    for j in 1..=deg {
        v *= t / j as f64;
        out[j] = v;
    }
}

/// Local log-density likelihood at one vertex (locfit `likeden`, log link).
struct Local<'a> {
    hs: f64,
    ker: Kernel,
    deg: usize,
    p: usize,
    ss: &'a [f64],
}

impl Local<'_> {
    /// Returns `(lk, score, A, reduce)`. `coef` is updated in place: the
    /// intercept is shifted by log(ss0 / A00), as locfit does for the log link.
    /// `reduce` is true when |coef[0]| > 700 (locfit `NR_REDUCE`).
    fn eval(&self, coef: &mut [f64]) -> Result<(f64, Vec<f64>, Vec<f64>, bool), String> {
        let p = self.p;
        let deg = self.deg;
        let hs = self.hs;
        let c: Vec<f64> = coef.to_vec();
        // In the scaled variable u = t / hs, P(u) = sum_i (c_i hs^i) u^i / i!,
        // which is the convention `onedint` takes (its quadratic term is c2 u^2/2).
        let mut cf = [0.0_f64; 3];
        for i in 0..p.min(3) {
            cf[i] = c[i] * hs.powi(i as i32);
        }
        // int W(|t|/hs) t^j/j! t^k/k! exp(P) dt over [-hs, hs] = hs^{j+k+1} / (j! k!) * resp[j+k].
        let resp = onedint(&cf, -1.0, 1.0, deg, self.ker)?;
        let mut a = vec![0.0; p * p];
        for j in 0..p {
            for k in j..p {
                let fj: f64 = (1..=j).map(|v| v as f64).product();
                let fk: f64 = (1..=k).map(|v| v as f64).product();
                let v = hs.powi((j + k + 1) as i32) / (fj * fk) * resp[j + k];
                a[j * p + k] = v;
                a[k * p + j] = v;
            }
        }
        let r = self.ss[0] / a[0];
        coef[0] += r.ln();
        for v in a.iter_mut() {
            *v *= r;
        }
        a[0] = self.ss[0];
        let mut lk = -a[0];
        let reduce = coef[0].abs() > 700.0;
        let mut f1 = vec![0.0; p];
        for i in 0..p {
            lk += coef[i] * self.ss[i];
            f1[i] = self.ss[i] - a[i];
        }
        Ok((lk, f1, a, reduce))
    }
}

/// Newton iteration (locfit `max_nr`). `coef` is updated in place. Returns
/// the matrix `A` of the last likelihood evaluation, which locfit leaves in
/// the design's `xtwx` and uses for the influence `t0`.
fn max_nr(local: &Local, coef: &mut [f64]) -> Result<Vec<f64>, String> {
    let p = local.p;
    let (mut f, mut f1, mut a, _) = local.eval(coef)?;
    for _ in 0..MAXIT {
        let old_coef = coef.to_vec();
        let old_f = f;
        let jac = Jac::new(&a, p);
        let mut solved = f1.clone();
        let rank = jac.solve(&mut solved);
        let mut delta = solved.clone();
        if rank == 0 {
            delta[0] = -f / solved[0];
        }
        let nc: f64 = old_coef.iter().map(|v| v * v).sum();
        let nd: f64 = delta.iter().map(|v| v * v).sum();
        let cut = (nc / nd).sqrt().min(1.0) * 0.0001;
        let mut lambda = 1.0;
        let mut reduce;
        loop {
            for j in 0..p {
                coef[j] = old_coef[j] + lambda * delta[j];
            }
            let (fnew, f1new, anew, red) = local.eval(coef)?;
            f = fnew;
            f1 = f1new;
            a = anew;
            reduce = red;
            lambda = if reduce { lambda / 2.0 } else { lambda / 10.0 };
            if !(lambda > cut && f <= old_f - 1.0e-3) {
                break;
            }
        }
        if f < old_f - 1.0e-3 {
            return Err("max_nr reduction problem".to_string());
        }
        if reduce {
            return Ok(a);
        }
        if (f - old_f).abs() < TOL {
            return Ok(a);
        }
    }
    Err("max_nr not converged".to_string())
}

/// Integral of exp(c0 + c1 t + c2 t^2) over [0, len] (locfit `recurint`,
/// with the rectangle weight, as `estdiv` calls it).
/// Integral of the fitted density squared over the vertices (locfit
/// `dens_integrate` with z = 2 and the log link). `xs` must be sorted
/// ascending. `deriv` holds the derivative at each vertex when the degree is
/// positive; for degree 0 locfit uses the slope of each interval instead.
fn dens_integrate_sq(xs: &[f64], fit: &[f64], deriv: Option<&[f64]>) -> Result<f64, String> {
    let nv = xs.len();
    let slope = |i: usize| (fit[i + 1] - fit[i]) / (xs[i + 1] - xs[i]);
    // Values and derivatives for the log link: both doubled (z = 2).
    let fz = |i: usize| 2.0 * fit[i];
    let dz = |i: usize| match deriv {
        Some(d) => 2.0 * d[i],
        None => 2.0 * slope(i.min(nv - 2)),
    };
    // Left tail, from the first vertex (locfit writes exp(f1) / d1).
    let mut sum = fz(0).exp() / dz(0);
    // Right tail, as locfit writes it (exp(f0) / d0 with the last vertex).
    sum += fz(nv - 1).exp() / dz(nv - 1);
    for i in 1..nv {
        let (d0, d1) = match deriv {
            Some(_) => (dz(i - 1), dz(i)),
            None => {
                let s = 2.0 * slope(i - 1);
                (s, s)
            }
        };
        sum += estdiv_log(xs[i - 1], xs[i], fz(i - 1), fz(i), d0, d1)?;
    }
    Ok(sum)
}

/// Local density fit at each data point (the vertices of `ev = dat()`).
/// `value` is the log density (after locfit's `log(n)` normalisation),
/// `deriv` its first derivative, and `infl` the influence `A^{-1}_00`, capped
/// at 1, that locfit stores as `t0^2`.
pub struct DensVertices {
    pub value: Vec<f64>,
    pub deriv: Vec<f64>,
    pub infl: Vec<f64>,
}

/// The per-vertex density fits (locfit `procv` for the density family).
pub fn dens_vertices(x: &[f64], o: &DensOpts) -> Result<DensVertices, String> {
    let n = x.len();
    if n < 3 {
        return Err("lscv needs at least three observations".to_string());
    }
    if o.kern == Kernel::Gaus {
        return Err("Gaussian kernel density LSCV (gausint) is not ported".to_string());
    }
    if o.deg > 2 {
        return Err("density LSCV is ported for degree 0 to 2".to_string());
    }
    let nf = n as f64;
    let p = o.deg + 1;
    let sca = vvari(x).sqrt();
    let nnc = (nf * o.nn + 1e-12) as usize;
    let rnz = if o.deg <= 1 { 1 } else { 2 };

    let mut coef0 = vec![0.0; n];
    let mut coef1 = vec![0.0; n];
    let mut infl = vec![0.0; n];
    for v in 0..n {
        let xv = x[v];
        let di: Vec<f64> = x.iter().map(|xi| (xi - xv).abs() / sca).collect();
        let h = compbandwid(&di, nnc, n, 1, o.fixh);
        let hs = h * sca;
        // Kernel weights and the local right-hand side ss = sum w_i ff(x_i - x_v).
        let mut ss = vec![0.0; p];
        let mut nnz = 0usize;
        let mut ff = [0.0_f64; 8];
        for i in 0..n {
            let w = if h == 0.0 {
                if di[i] == 0.0 { 1.0 } else { 0.0 }
            } else {
                w_fn(di[i] / h, o.kern)
            };
            if w > 1.0e-5 {
                nnz += 1;
            }
            if w > 0.0 {
                basis(x[i] - xv, o.deg, &mut ff);
                for j in 0..p {
                    ss[j] += ff[j] * w;
                }
            }
        }
        if nnz < rnz {
            return Err("density estimation -- insufficient points in smoothing window".to_string());
        }
        let mut coef = vec![0.0; p];
        let local = Local {
            hs,
            ker: o.kern,
            deg: o.deg,
            p,
            ss: &ss,
        };
        let a_last = max_nr(&local, &mut coef)?;
        // procv: locfit divides by the sample size (smwt = n) for the log link.
        coef[0] -= nf.ln();
        // Influence: t0 = A^{-1} e_0, squared (infl = t0 * t0), capped at 1.
        let jac = Jac::new(&a_last, p);
        let mut e0 = vec![0.0; p];
        e0[0] = 1.0;
        jac.solve(&mut e0);
        infl[v] = e0[0].min(1.0);
        coef0[v] = coef[0];
        coef1[v] = if p > 1 { coef[1] } else { 0.0 };
    }
    Ok(DensVertices {
        value: coef0,
        deriv: coef1,
        infl,
    })
}

/// Density-family LSCV criterion and degrees of freedom (locfit `dens_lscv`
/// with `ev = dat()`). Returns `[criterion, df]`, the two values of R's
/// `lscv()`.
pub fn dens_lscv(x: &[f64], o: &DensOpts) -> Result<[f64; 2], String> {
    let n = x.len();
    let nf = n as f64;
    let vert = dens_vertices(x, o)?;
    let (coef0, coef1, infl) = (&vert.value, &vert.deriv, &vert.infl);

    // dens_integrate needs the vertices in increasing order.
    let mut ord: Vec<usize> = (0..n).collect();
    ord.sort_by(|&a, &b| x[a].partial_cmp(&x[b]).unwrap_or(std::cmp::Ordering::Equal));
    let xs: Vec<f64> = ord.iter().map(|&i| x[i]).collect();
    let fs: Vec<f64> = ord.iter().map(|&i| coef0[i]).collect();
    let ds: Vec<f64> = ord.iter().map(|&i| coef1[i]).collect();
    let deriv = if o.deg > 0 { Some(ds.as_slice()) } else { None };
    let z0 = dens_integrate_sq(&xs, &fs, deriv)?;

    // dens_lscv: the leave-one-out density at each data point.
    let mut z1 = 0.0;
    let mut df = 0.0;
    for v in 0..n {
        let fh = coef0[v].exp();
        let inf = infl[v];
        z1 += fh * (1.0 - inf) * nf / (nf - 1.0);
        df += inf;
    }
    Ok([z0 - 2.0 * z1 / nf, df])
}

/// Density fit at one tree vertex `xv` (locfit `procv` for the density family
/// with the log link, no parametric component). Returns the log density and
/// its derivative (after locfit's `log(n)` shift), the influence `t0`
/// (`sqrt(A^{-1}_00)` then the derivative ratio, as `procv` stores it), and the
/// bandwidth. `sca` is the scale of the distances (locfit `sca`, 1 by default).
pub fn dens_point(x: &[f64], xv: f64, o: &DensOpts, sca: f64) -> Result<VFit, String> {
    let n = x.len();
    if n < 3 {
        return Err("lscv needs at least three observations".to_string());
    }
    if o.kern == Kernel::Gaus {
        return Err("Gaussian kernel density LSCV (gausint) is not ported".to_string());
    }
    if o.deg > 2 {
        return Err("density LSCV is ported for degree 0 to 2".to_string());
    }
    let nf = n as f64;
    let p = o.deg + 1;
    let nnc = (nf * o.nn + 1e-12) as usize;
    let rnz = if o.deg <= 1 { 1 } else { 2 };

    let di: Vec<f64> = x.iter().map(|xi| (xi - xv).abs() / sca).collect();
    let h = compbandwid(&di, nnc, n, 1, o.fixh);
    let hs = h * sca;
    let mut ss = vec![0.0; p];
    let mut nnz = 0usize;
    let mut ff = [0.0_f64; 8];
    for i in 0..n {
        let w = if h == 0.0 {
            if di[i] == 0.0 { 1.0 } else { 0.0 }
        } else {
            w_fn(di[i] / h, o.kern)
        };
        if w > 1.0e-5 {
            nnz += 1;
        }
        if w > 0.0 {
            basis(x[i] - xv, o.deg, &mut ff);
            for j in 0..p {
                ss[j] += ff[j] * w;
            }
        }
    }
    if nnz < rnz {
        return Err("density estimation -- insufficient points in smoothing window".to_string());
    }
    let mut coef = vec![0.0; p];
    let local = Local {
        hs,
        ker: o.kern,
        deg: o.deg,
        p,
        ss: &ss,
    };
    let a_last = max_nr(&local, &mut coef)?;
    coef[0] -= nf.ln();

    let jac = Jac::new(&a_last, p);
    let mut f1 = vec![0.0; p];
    f1[0] = 1.0;
    jac.solve(&mut f1);
    let ncoef = if p > 1 { 2 } else { 1 };
    let mut t0 = vec![0.0; ncoef];
    t0[0] = f1[0].sqrt();
    for i in 1..ncoef {
        t0[i] = if t0[0] > 0.0 { f1[i] / t0[0] } else { f1[i] };
    }
    Ok(VFit {
        coef: coef[..ncoef].to_vec(),
        nlx: vec![0.0; ncoef],
        t0,
        h,
        lik: [0.0; 3],
    })
}

/// Density-family LSCV on the adaptive tree: locfit's `lscv` default
/// (`geth = 6` with `ev = rbox()`, the `ETREE` structure). The vertices are
/// fitted with `dens_point`, the tree is interpolated at the data, and the
/// criterion uses locfit's `dens_integrate` (z = 2) and `dens_lscv`. Returns
/// `[criterion, degrees of freedom]`.
pub fn dens_lscv_tree(x: &[f64], o: &DensOpts, cut: f64) -> Result<[f64; 2], String> {
    let n = x.len();
    let nf = n as f64;
    let ncoef = if o.deg > 0 { 2 } else { 1 };
    let lo = [x.iter().cloned().fold(f64::INFINITY, f64::min)];
    let hi = [x.iter().cloned().fold(f64::NEG_INFINITY, f64::max)];
    let fitv = |xv: &[f64]| dens_point(x, xv[0], o, 1.0);
    let t = tree::build(&lo, &hi, &[1.0], cut, o.nn, ncoef, &fitv)?;

    // dens_integrate(z = 2): every vertex, pseudo-vertices included (their
    // coefficients are zero, as in R). Zero if there are more vertices than data.
    let nv = t.nv();
    let z0 = if n < nv {
        0.0
    } else {
        let xv = t.xev();
        let mut ord: Vec<usize> = (0..nv).collect();
        ord.sort_by(|&a, &b| xv[a].partial_cmp(&xv[b]).unwrap_or(std::cmp::Ordering::Equal));
        let xs: Vec<f64> = ord.iter().map(|&i| xv[i]).collect();
        let fs: Vec<f64> = ord.iter().map(|&i| t.value(i, What::Coef, 0)).collect();
        let ds: Vec<f64> = if o.deg > 0 {
            ord.iter().map(|&i| t.value(i, What::Coef, 1)).collect()
        } else {
            Vec::new()
        };
        let deriv = if o.deg > 0 { Some(ds.as_slice()) } else { None };
        dens_integrate_sq(&xs, &fs, deriv)?
    };

    // dens_lscv: leave-one-out density at each data point, from the tree.
    let mut z1 = 0.0;
    let mut df = 0.0;
    for i in 0..n {
        let u = [x[i]];
        let fh = t.interp(&u, What::Coef).exp();
        let mut infl = t.interp(&u, What::T0);
        if infl < 0.0 {
            infl = 0.0;
        }
        infl *= infl;
        if infl > 1.0 {
            infl = 1.0;
        }
        z1 += fh * (1.0 - infl) * nf / (nf - 1.0);
        df += infl;
    }
    Ok([z0 - 2.0 * z1 / nf, df])
}
