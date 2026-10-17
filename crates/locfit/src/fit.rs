//! Direct local regression for the Gaussian identity (quasi) family, ported
//! from locfit 1.5-9.12:
//!
//! - `startlf.c` / `compparcomp` (`pcomp.c`): the global parametric component
//!   fitted at the weighted mean `xbar`;
//! - `lf_nbhd.c` `nbhd` / `compbandwid`: nearest-neighbour bandwidth and
//!   kernel weights;
//! - `locfit.c` / `family.c` / `max_nr` (`m_max.c`): the Newton step for the
//!   Gaussian identity family, which is exact after one step, so the weighted
//!   least squares solution is computed directly;
//! - `procv.c` `procvraw` + `procv`, `lf_vari.c` `lf_vcov` / `comp_vari`, and
//!   `pcomp.c` `subparcomp` / `subparcomp2` for each vertex;
//! - `frend.c` `ressumm` for the `ev = "data"` evaluation (degrees of freedom,
//!   log-likelihood, residual variance).
//!
//! Evaluation structures: `Eval::Data` fits at each data point (locfit
//! `EDATA`), `Eval::Points` fits at given points (locfit `EPRES`), and
//! `Eval::Tree` the default kd-tree / vertex interpolation (`ETREE`, `tree.rs`).

use crate::eig::Jac;
use crate::kernel::{calcp, fitfun, w_fn, Kernel, Kt};
use crate::tree::{self, VFit, What};

/// Options that map onto locfit's `smpar` and `mi` settings.
#[derive(Clone, Debug)]
pub struct FitOpts {
    /// Smoothing parameter `alpha` (nearest-neighbour fraction).
    pub nn: f64,
    /// Fixed bandwidth floor `h` (locfit `fixh`).
    pub fixh: f64,
    /// Local polynomial degree (`deg0 == deg` is assumed).
    pub deg: usize,
    pub kern: Kernel,
    pub kt: Kt,
    /// Quasi-likelihood variance estimate (`family = "qgaussian"`).
    pub quasi: bool,
}

/// Evaluation structure.
#[derive(Clone, Copy, Debug)]
pub enum Eval<'a> {
    /// Fit at every data point (locfit `ev = "data"`).
    Data,
    /// Fit at the given points, row-major `m x d` (locfit `ev = "preset"`).
    Points(&'a [f64], usize),
    /// Adaptive tree with split threshold `cut` (locfit `ev = rbox()`, the
    /// default, `ETREE`): fit at the vertices and interpolate.
    Tree(f64),
}

/// Input data. `x` is row-major `n x d`.
#[derive(Clone, Copy, Debug)]
pub struct Input<'a> {
    pub x: &'a [f64],
    pub n: usize,
    pub d: usize,
    pub y: &'a [f64],
    pub weights: Option<&'a [f64]>,
    pub base: Option<&'a [f64]>,
    /// Scales per dimension; a value `<= 0` requests the sample standard deviation.
    pub scale: Option<&'a [f64]>,
    pub eval: Eval<'a>,
    /// New points, row-major `m x d`, at which `Tree` also interpolates the
    /// fitted value (locfit `preplot`, `where = "vect"`). Ignored otherwise.
    pub xnew: Option<&'a [f64]>,
}

/// Fit output. Per-vertex arrays are row-major with `ncoef` columns.
#[derive(Clone, Debug, Default)]
pub struct FitOut {
    pub nv: usize,
    pub ncoef: usize,
    /// Local coefficients: value, then first derivatives.
    pub coef: Vec<f64>,
    /// `||l(x)||`: local standard error factor (locfit `nlx`).
    pub nlx: Vec<f64>,
    /// Influence factor (locfit `t0`).
    pub t0: Vec<f64>,
    /// Bandwidth at each vertex.
    pub h: Vec<f64>,
    /// Per-vertex `[likelihood, trace(M1^-1 M2), tr0 - tr2]`.
    pub lik: Vec<f64>,
    /// Fitted values at the data (locfit `sfitted`, `ev = "data"` only):
    /// base + local coefficient + parametric component, one per observation.
    pub fitted: Vec<f64>,
    /// Fitted values at `Input::xnew` (`Tree` only): interpolated coefficient
    /// plus the parametric component, one per new point.
    pub xnew_fitted: Vec<f64>,
    /// Global summaries (locfit `dp`): log-likelihood, `df0`, `df1`, `rv`, `rsc`.
    pub lk: f64,
    pub df0: f64,
    pub df1: f64,
    pub rv: f64,
    pub rsc: f64,
    /// Evaluation points, row-major `nv x d`: the data, the given points, or
    /// the tree vertices.
    pub xev: Vec<f64>,
    /// Standard-error factor at the data (locfit `dointpoint(PNLX)` with the
    /// parametric part; `Tree` and `Data`). The standard error is `sqrt(rv) * nlx_data`.
    pub nlx_data: Vec<f64>,
    /// Leave-one-out criterion sum (locfit `residuals(type = "d2", cv = TRUE)`
    /// summed, `Tree` only): `sum_i w_i (y_i - th_cv_i)^2`, where
    /// `th_cv_i = th_i - t0_i^2 * w_i * (y_i - th_i)` and `t0_i` is the
    /// interpolated influence factor at data point `i` (locfit `fitted.c`,
    /// `cv` branch).
    pub cv_sum: f64,
}

/// Parametric component: global polynomial fitted at `xbar`.
struct Pc {
    xbar: Vec<f64>,
    coef: Vec<f64>,
    jac: Jac,
}

fn dot(a: &[f64], b: &[f64]) -> f64 {
    a.iter().zip(b).map(|(x, y)| x * y).sum()
}

pub(crate) fn vvari(v: &[f64]) -> f64 {
    let n = v.len() as f64;
    let xb = v.iter().sum::<f64>() / n;
    v.iter().map(|x| (x - xb) * (x - xb)).sum::<f64>() / (n - 1.0)
}

fn matmul(a: &[f64], b: &[f64], p: usize) -> Vec<f64> {
    let mut c = vec![0.0; p * p];
    for i in 0..p {
        for k in 0..p {
            let aik = a[i * p + k];
            for j in 0..p {
                c[i * p + j] += aik * b[k * p + j];
            }
        }
    }
    c
}

/// Locfit `compbandwid`: `h` is the `nn`-th smallest distance, floored at `fixh`.
pub(crate) fn compbandwid(di: &[f64], nn: usize, n: usize, d: usize, fixh: f64) -> f64 {
    if nn == 0 {
        return fixh;
    }
    let nnh = if nn < n {
        let mut s = di.to_vec();
        s.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        s[nn - 1]
    } else {
        let mx = di.iter().cloned().fold(0.0_f64, f64::max);
        mx * ((nn as f64 / n as f64).ln() / d as f64).exp()
    };
    fixh.max(nnh)
}

/// Gaussian identity weighted least squares, as one Newton step of locfit's
/// `likereg` / `max_nr` from the `reginit` start. Returns `(theta, A, rank)`
/// with `A = sum K pw X X^T`.
fn wls(
    xm: &[f64],
    m: usize,
    p: usize,
    kw: &[f64],
    pw: &[f64],
    y: &[f64],
    base: &[f64],
) -> Result<(Vec<f64>, Vec<f64>, usize), String> {
    // Products are grouped as locfit's C does (reginit, likereg, addouter),
    // so that the roundoff matches R's and the Jacobi sweeps take the same path.
    let mut s0 = 0.0;
    let mut s1 = 0.0;
    let mut sb = 0.0;
    for k in 0..m {
        s0 += kw[k] * pw[k];
        s1 += kw[k] * (pw[k] * y[k]);
        sb += kw[k] * pw[k] * base[k];
    }
    if s0 == 0.0 {
        return Err("no points with non-zero weight".to_string());
    }
    let mut cf = vec![0.0; p];
    cf[0] = (s1 - sb) / s0;

    let mut a = vec![0.0; p * p];
    let mut g = vec![0.0; p];
    for k in 0..m {
        let row = &xm[k * p..(k + 1) * p];
        let th = base[k] + dot(row, &cf);
        let z = y[k] - th;
        let zdll = pw[k] * z;
        let ww = kw[k] * pw[k];
        for r in 0..p {
            g[r] += row[r] * kw[k] * zdll;
            for c in 0..p {
                a[r * p + c] += ww * row[r] * row[c];
            }
        }
    }
    let jac = Jac::new(&a, p);
    let mut delta = g;
    let rank = jac.solve(&mut delta);
    if rank == 0 {
        return Err("singular local design".to_string());
    }
    let theta: Vec<f64> = cf.iter().zip(&delta).map(|(c, d)| c + d).collect();
    Ok((theta, a, rank))
}

/// Per-vertex fit output before the global summaries.
struct Vertex {
    coef: Vec<f64>,
    nlx: Vec<f64>,
    t0: Vec<f64>,
    h: f64,
    lik: [f64; 3],
}

struct Ctx<'a> {
    x: &'a [f64],
    n: usize,
    d: usize,
    y: &'a [f64],
    pw: &'a [f64],
    base: &'a [f64],
    sca: &'a [f64],
    opts: &'a FitOpts,
    p: usize,
    ncoef: usize,
    pc: &'a Pc,
}

/// Local fit at one vertex `xv` (locfit `procvraw` + `procv`).
fn vertex(c: &Ctx, xv: &[f64]) -> Result<Vertex, String> {
    let (n, d, p) = (c.n, c.d, c.p);
    let o = c.opts;

    // Distances in scaled units (locfit `rho`).
    let mut di = vec![0.0; n];
    for i in 0..n {
        if o.kt == Kt::Prod {
            let mut mx = 0.0_f64;
            for j in 0..d {
                mx = mx.max(((c.x[i * d + j] - xv[j]) / c.sca[j]).abs());
            }
            di[i] = mx;
        } else {
            if d == 1 {
                // locfit `rho`: one dimension is fabs(x / sc), not sqrt(x^2).
                di[i] = ((c.x[i] - xv[0]) / c.sca[0]).abs();
            } else {
                let mut s = 0.0;
                for j in 0..d {
                    let r = (c.x[i * d + j] - xv[j]) / c.sca[j];
                    s += r * r;
                }
                di[i] = s.sqrt();
            }
        }
    }

    // Bandwidth and neighbourhood (locfit `nbhd`).
    let nn = (n as f64 * o.nn + 1e-12) as usize;
    let h = if o.kern == Kernel::Parm {
        0.0
    } else {
        compbandwid(&di, nn, n, d, o.fixh)
    };
    let mut idx = Vec::new();
    let mut kw = Vec::new();
    for i in 0..n {
        let w = if o.kern == Kernel::Parm {
            1.0
        } else {
            match o.kt {
                Kt::Sph => {
                    if h == 0.0 {
                        if di[i] == 0.0 {
                            1.0
                        } else {
                            0.0
                        }
                    } else {
                        w_fn(di[i] / h, o.kern)
                    }
                }
                Kt::Prod => {
                    let mut w = 1.0;
                    for j in 0..d {
                        let u = c.x[i * d + j] - xv[j];
                        w *= w_fn(u.abs() / (h * c.sca[j]), o.kern);
                        if w == 0.0 {
                            break;
                        }
                    }
                    w
                }
            }
        };
        if w > 0.0 {
            idx.push(i);
            kw.push(w);
        }
    }
    let m = idx.len();

    // Local design, weights and responses.
    let mut xm = vec![0.0; m * p];
    for (k, &i) in idx.iter().enumerate() {
        fitfun(
            &c.x[i * d..(i + 1) * d],
            Some(xv),
            d,
            o.kt,
            o.deg,
            &[],
            &mut xm[k * p..(k + 1) * p],
        );
    }
    let pw_m: Vec<f64> = idx.iter().map(|&i| c.pw[i]).collect();
    let y_m: Vec<f64> = idx.iter().map(|&i| c.y[i]).collect();
    let base_m: Vec<f64> = idx.iter().map(|&i| c.base[i]).collect();

    let (theta, a, _rank) = wls(&xm, m, p, &kw, &pw_m, &y_m, &base_m)?;
    let jac = Jac::new(&a, p);

    // Log-likelihood at the local fit (locfit `likereg`, `lk`).
    let mut llk = 0.0;
    for k in 0..m {
        let th = base_m[k] + dot(&xm[k * p..(k + 1) * p], &theta);
        let z = y_m[k] - th;
        llk += kw[k] * (-pw_m[k] * z * z / 2.0);
    }

    // Covariance pieces (locfit `vmat`, `lf_vcov`, `comp_vari`).
    let mut m2 = vec![0.0; p * p];
    let mut tr0 = 0.0;
    for k in 0..m {
        let ww = kw[k] * kw[k] * pw_m[k];
        tr0 += kw[k];
        let row = &xm[k * p..(k + 1) * p];
        for r in 0..p {
            for s in 0..p {
                m2[r * p + s] += ww * row[r] * row[s];
            }
        }
    }
    let inv = jac.inverse();
    let t_mat = matmul(&m2, &inv, p);
    let cov = matmul(&inv, &t_mat, p);
    let tr2: f64 = (0..p).map(|i| t_mat[i * p + i]).sum();

    // Influence column A^{-1} e_0 (locfit `comp_vari`, t0).
    let mut t0v: Vec<f64> = (0..c.ncoef).map(|i| inv[i * p]).collect();
    // Variance of the coefficients (locfit `procv`, `vari`).
    let mut vari: Vec<f64> = (0..c.ncoef).map(|i| cov[i]).collect();
    let mut coef: Vec<f64> = (0..c.ncoef).map(|i| theta[i]).collect();

    vari[0] = vari[0].sqrt();
    if vari[0] > 0.0 {
        for i in 1..c.ncoef {
            vari[i] /= vari[0];
        }
    }
    t0v[0] = t0v[0].sqrt();
    if t0v[0] > 0.0 {
        for i in 1..c.ncoef {
            t0v[i] /= t0v[0];
        }
    }

    // Parametric component correction (locfit `subparcomp`, `subparcomp2`).
    let pc = c.pc;
    let f0 = {
        let mut f = vec![0.0; p];
        fitfun(xv, Some(&pc.xbar), d, o.kt, o.deg, &[], &mut f);
        f
    };
    coef[0] -= dot(&pc.coef, &f0);
    if c.ncoef > 1 {
        for i in 0..d {
            let mut f = vec![0.0; p];
            fitfun(xv, Some(&pc.xbar), d, o.kt, o.deg, &[i], &mut f);
            coef[i + 1] -= dot(&pc.coef, &f);
        }
    }
    let g = {
        let mut g = f0.clone();
        pc.jac.solve(&mut g);
        g
    };
    let t = dot(&f0, &g).sqrt();
    vari[0] -= t;
    t0v[0] -= t;
    if t != 0.0 && c.ncoef > 1 {
        for i in 0..d {
            let mut f = vec![0.0; p];
            fitfun(xv, Some(&pc.xbar), d, o.kt, o.deg, &[i], &mut f);
            let t1 = dot(&f, &g) / t;
            vari[i + 1] -= t1;
            t0v[i + 1] -= t1;
        }
    }

    Ok(Vertex {
        coef,
        nlx: vari,
        t0: t0v,
        h,
        lik: [llk, tr2, tr0 - tr2],
    })
}

/// Default evaluation structure (locfit `ev = rbox()`, `ETREE`): fit at the
/// adaptive-tree vertices, then interpolate the coefficient, the influence and
/// the standard-error factor at each data point (locfit `dointpoint`, then the
/// parametric component, as `ressumm` does).
#[allow(clippy::too_many_arguments)]
fn fit_tree(
    inp: &Input,
    o: &FitOpts,
    ctx: &Ctx,
    pc: &Pc,
    base: &[f64],
    pw: &[f64],
    sca: &[f64],
    ncoef: usize,
    p: usize,
    cut: f64,
) -> Result<FitOut, String> {
    let (n, d) = (inp.n, inp.d);
    // locfit `set_flim`: the bounding box of the data.
    let mut lo = vec![f64::INFINITY; d];
    let mut hi = vec![f64::NEG_INFINITY; d];
    for i in 0..n {
        for j in 0..d {
            let v = inp.x[i * d + j];
            lo[j] = lo[j].min(v);
            hi[j] = hi[j].max(v);
        }
    }
    let fitv = |xv: &[f64]| -> Result<VFit, String> {
        let v = vertex(ctx, xv)?;
        Ok(VFit {
            coef: v.coef,
            nlx: v.nlx,
            t0: v.t0,
            h: v.h,
            lik: v.lik,
        })
    };
    let tree = tree::build(&lo, &hi, sca, cut, o.nn, ncoef, &fitv)?;

    let nv = tree.nv();
    let mut out = FitOut {
        nv,
        ncoef,
        coef: Vec::with_capacity(nv * ncoef),
        nlx: Vec::with_capacity(nv * ncoef),
        t0: Vec::with_capacity(nv * ncoef),
        h: Vec::with_capacity(nv),
        lik: Vec::with_capacity(nv * 3),
        fitted: Vec::with_capacity(n),
        lk: 0.0,
        df0: 0.0,
        df1: 0.0,
        rv: 1.0,
        rsc: 1.0,
        xev: tree.xev(),
        nlx_data: Vec::with_capacity(n),
        cv_sum: 0.0,
        xnew_fitted: Vec::new(),
    };
    for v in 0..nv {
        let f = tree.vfit(v);
        out.coef.extend_from_slice(&f.coef);
        out.nlx.extend_from_slice(&f.nlx);
        out.t0.extend_from_slice(&f.t0);
        out.h.push(f.h);
        out.lik.extend_from_slice(&f.lik);
    }

    // locfit `ressumm` for the tree: interpolated values at the data.
    let mut llk = 0.0;
    let mut df0 = 0.0;
    let mut df1 = 0.0;
    let mut r1 = 0.0;
    let mut r2 = 0.0;
    for i in 0..n {
        let u = &inp.x[i * d..(i + 1) * d];
        let mut fu = vec![0.0; p];
        fitfun(u, Some(&pc.xbar), d, o.kt, o.deg, &[], &mut fu);
        let add_coef = dot(&pc.coef, &fu);
        let th = base[i] + (tree.interp(u, What::Coef) + add_coef);
        out.fitted.push(th);

        // locfit dointpoint: clamp at zero, then add the parametric part.
        let mut t0 = tree.interp(u, What::T0);
        if t0 < 0.0 {
            t0 = 0.0;
        }
        t0 += pc.jac.qf(&fu).sqrt();

        let mut t1 = tree.interp(u, What::Nlx);
        if t1 < 0.0 {
            t1 = 0.0;
        }
        t1 += pc.jac.qf(&fu).sqrt();
        out.nlx_data.push(t1);

        let z = inp.y[i] - th;
        let zlik = -pw[i] * z * z / 2.0;
        let zdll = pw[i] * z;
        let zddll = pw[i];

        // locfit fitted.c `cv` branch: inl = t0^2 (the dointpoint PT0 value,
        // parametric part included), th_cv = th - inl * ZDLL, and the residual
        // is -2 * ZLIK at th_cv, i.e. w * (y - th_cv)^2.
        let inl = t0 * t0;
        let th_cv = th - inl * zdll;
        let zcv = inp.y[i] - th_cv;
        out.cv_sum += pw[i] * zcv * zcv;

        let mut t1s = t1 * t1 * zddll;
        if t1s > 1.0 {
            t1s = 1.0;
        }
        let mut t0s = t0 * t0 * zddll;
        if t0s > 1.0 {
            t0s = 1.0;
        }
        llk += zlik;
        df0 += t0s;
        df1 += t1s;
        if pw[i] > 0.0 {
            r1 += zdll * zdll / pw[i];
            r2 += zddll / pw[i];
        }
    }
    let mut rv = 1.0;
    if o.quasi {
        let rdf = n as f64 - 2.0 * df0 + df1;
        if rdf >= 1.0 {
            rv = r1 / r2 * n as f64 / rdf;
        }
    }
    // locfit `preplot` with `where = "vect"`: the vertex interpolation at the
    // new points, plus the parametric component (`addparcomp`).
    if let Some(xn) = inp.xnew {
        if xn.len() % d != 0 {
            return Err("xnew must be m x d".to_string());
        }
        for u in xn.chunks(d) {
            let mut fu = vec![0.0; p];
            fitfun(u, Some(&pc.xbar), d, o.kt, o.deg, &[], &mut fu);
            out.xnew_fitted
                .push(tree.interp(u, What::Coef) + dot(&pc.coef, &fu));
        }
    }
    out.lk = llk;
    out.df0 = df0;
    out.df1 = df1;
    out.rv = rv;
    Ok(out)
}

/// Run the local fit at each vertex and the summary statistics.
pub fn fit(inp: &Input, o: &FitOpts) -> Result<FitOut, String> {
    let (n, d) = (inp.n, inp.d);
    if n == 0 || d == 0 {
        return Err("empty data".to_string());
    }
    if inp.x.len() != n * d || inp.y.len() != n {
        return Err("x must be n x d and y must have length n".to_string());
    }
    if o.kt == Kt::Sph && o.deg > 3 {
        return Err("spherical kernel supports degree <= 3".to_string());
    }
    if o.deg > 7 {
        return Err("degree above 7 is not supported".to_string());
    }

    let pw: Vec<f64> = match inp.weights {
        Some(w) => w.to_vec(),
        None => vec![1.0; n],
    };
    let base: Vec<f64> = match inp.base {
        Some(b) => b.to_vec(),
        None => vec![0.0; n],
    };
    let mut sca: Vec<f64> = match inp.scale {
        Some(s) => s.to_vec(),
        None => vec![1.0; d],
    };
    for j in 0..d {
        if sca[j] <= 0.0 {
            let col: Vec<f64> = (0..n).map(|i| inp.x[i * d + j]).collect();
            sca[j] = vvari(&col).sqrt();
        }
    }

    let p = calcp(o.kt, d, o.deg);
    let ncoef = if o.deg == 0 { 1 } else { d + 1 };

    // Parametric component (locfit `compparcomp`): global unweighted-kernel fit.
    let sw: f64 = pw.iter().sum();
    let mut xbar = vec![0.0; d];
    for i in 0..n {
        for j in 0..d {
            xbar[j] += inp.x[i * d + j] * pw[i];
        }
    }
    for j in 0..d {
        xbar[j] /= sw;
    }
    let mut xg = vec![0.0; n * p];
    for i in 0..n {
        fitfun(
            &inp.x[i * d..(i + 1) * d],
            Some(&xbar),
            d,
            o.kt,
            o.deg,
            &[],
            &mut xg[i * p..(i + 1) * p],
        );
    }
    let kw_g = vec![1.0; n];
    let (theta_g, a_g, _) = wls(&xg, n, p, &kw_g, &pw, inp.y, &base)?;
    let pc = Pc {
        xbar,
        coef: theta_g,
        jac: Jac::new(&a_g, p),
    };

    let ctx = Ctx {
        x: inp.x,
        n,
        d,
        y: inp.y,
        pw: &pw,
        base: &base,
        sca: &sca,
        opts: o,
        p,
        ncoef,
        pc: &pc,
    };

    if let Eval::Tree(cut) = inp.eval {
        return fit_tree(inp, o, &ctx, &pc, &base, &pw, &sca, ncoef, p, cut);
    }

    let nv = match inp.eval {
        Eval::Data => n,
        Eval::Points(xe, m) => {
            if xe.len() != m * d {
                return Err("xev must be m x d".to_string());
            }
            m
        }
        Eval::Tree(_) => unreachable!("the tree is handled above"),
    };

    let mut out = FitOut {
        nv,
        ncoef,
        coef: Vec::with_capacity(nv * ncoef),
        nlx: Vec::with_capacity(nv * ncoef),
        t0: Vec::with_capacity(nv * ncoef),
        h: Vec::with_capacity(nv),
        lik: Vec::with_capacity(nv * 3),
        fitted: Vec::new(),
        lk: 0.0,
        df0: 0.0,
        df1: 0.0,
        rv: 1.0,
        rsc: 1.0,
        xev: match inp.eval {
            Eval::Points(xe, _) => xe.to_vec(),
            _ => inp.x.to_vec(),
        },
        nlx_data: Vec::new(),
        cv_sum: 0.0,
        xnew_fitted: Vec::new(),
    };

    for v in 0..nv {
        let xv: &[f64] = match inp.eval {
            Eval::Data => &inp.x[v * d..(v + 1) * d],
            Eval::Points(xe, _) => &xe[v * d..(v + 1) * d],
            Eval::Tree(_) => unreachable!("the tree is handled above"),
        };
        let vf = vertex(&ctx, xv)?;
        out.coef.extend_from_slice(&vf.coef);
        out.nlx.extend_from_slice(&vf.nlx);
        out.t0.extend_from_slice(&vf.t0);
        out.h.push(vf.h);
        out.lik.extend_from_slice(&vf.lik);
    }

    if let Eval::Data = inp.eval {
        // locfit `ressumm` for the data evaluation structure.
        let mut llk = 0.0;
        let mut df0 = 0.0;
        let mut df1 = 0.0;
        let mut r1 = 0.0;
        let mut r2 = 0.0;
        for i in 0..n {
            let u = &inp.x[i * d..(i + 1) * d];
            let mut fu = vec![0.0; p];
            fitfun(u, Some(&pc.xbar), d, o.kt, o.deg, &[], &mut fu);
            let add_coef = dot(&pc.coef, &fu);
            let th = base[i] + (out.coef[i * ncoef] + add_coef);
            out.fitted.push(th);

            let mut t0 = out.t0[i * ncoef];
            if t0 < 0.0 {
                t0 = 0.0;
            }
            t0 += pc.jac.qf(&fu).sqrt();

            let mut t1 = out.nlx[i * ncoef];
            if t1 < 0.0 {
                t1 = 0.0;
            }
            t1 += pc.jac.qf(&fu).sqrt();
            out.nlx_data.push(t1);

            let z = inp.y[i] - th;
            let zlik = -pw[i] * z * z / 2.0;
            let zdll = pw[i] * z;
            let zddll = pw[i];

            let mut t1s = t1 * t1 * zddll;
            if t1s > 1.0 {
                t1s = 1.0;
            }
            let mut t0s = t0 * t0 * zddll;
            if t0s > 1.0 {
                t0s = 1.0;
            }
            llk += zlik;
            df0 += t0s;
            df1 += t1s;
            if pw[i] > 0.0 {
                r1 += zdll * zdll / pw[i];
                r2 += zddll / pw[i];
            }
        }
        let mut rv = 1.0;
        if o.quasi {
            let rdf = n as f64 - 2.0 * df0 + df1;
            if rdf >= 1.0 {
                rv = r1 / r2 * n as f64 / rdf;
            }
        }
        out.lk = llk;
        out.df0 = df0;
        out.df1 = df1;
        out.rv = rv;
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn local_quadratic_reproduces_quadratic() {
        // A local quadratic fit reproduces a quadratic exactly, so the
        // parametric and local parts must recover the curve at each point.
        let n = 25;
        let x: Vec<f64> = (0..n).map(|i| i as f64 / (n as f64 - 1.0)).collect();
        let y: Vec<f64> = x.iter().map(|t| 1.0 + 2.0 * t - 3.0 * t * t).collect();
        let inp = Input {
            x: &x,
            n,
            d: 1,
            y: &y,
            weights: None,
            base: None,
            scale: None,
            eval: Eval::Data,
            xnew: None,
        };
        let o = FitOpts {
            nn: 0.5,
            fixh: 0.0,
            deg: 2,
            kern: Kernel::Tcub,
            kt: Kt::Sph,
            quasi: true,
        };
        let r = fit(&inp, &o).expect("fit");
        // The stored coefficients are the local fit minus the global
        // parametric component. For an exact quadratic that difference is 0.
        let worst = (0..n)
            .flat_map(|i| (0..r.ncoef).map(move |k| (i, k)))
            .map(|(i, k)| r.coef[i * r.ncoef + k].abs())
            .fold(0.0_f64, f64::max);
        eprintln!("max |stored coef| = {worst:e}");
        // locfit stops its Jacobi sweeps at a relative 3e-8 off-diagonal, so
        // the exact-quadratic residual is near 1e-7 at the boundary windows.
        assert!(worst < 1e-6, "worst {worst}");
    }
}

