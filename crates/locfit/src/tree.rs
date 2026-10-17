//! Adaptive tree evaluation structure: locfit's default `ev = rbox()`
//! (type "tree", `ETREE`), ported from locfit 1.5-9.12:
//!
//! - `ev_atree.c` `atree_guessnv`, `atree_split`, `atree_grow`, `atree_start`
//!   and `atree_int` (the cell split rule, the recursive build and the
//!   descent that interpolates a point);
//! - `ev_main.c` `findpt` and `newsplit` (vertex lookup and midpoints);
//! - `ev_interp.c` `hermite2`, `linear_interp`, `exvval`, `exvvalpv` and
//!   `rectcell_interp` (vertex values and the cubic blending).
//!
//! The vertices are fitted by a caller-supplied local fit (`fitv`), so the
//! same tree serves the Gaussian (quasi) family and the density family.
//! A pseudo-vertex (locfit `pv`, a midpoint of a coarse cell) is not fitted:
//! its bandwidth is the mean of its two ends, and its coefficients stay zero,
//! as R's zero-filled work arrays do.

/// Maximum dimension (locfit `MXDIM`).
pub const MXDIM: usize = 15;

/// One vertex's local fit (locfit `procv`): coefficient, standard-error factor
/// and influence vectors (each `ncoef` long, value then first derivatives),
/// bandwidth, and the likelihood triple.
#[derive(Clone, Debug, Default)]
pub struct VFit {
    pub coef: Vec<f64>,
    pub nlx: Vec<f64>,
    pub t0: Vec<f64>,
    pub h: f64,
    pub lik: [f64; 3],
}

/// Which vertex quantity to interpolate (locfit `what`: PCOEF, PNLX, PT0).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum What {
    Coef,
    Nlx,
    T0,
}

#[derive(Clone, Debug)]
struct Vert {
    x: Vec<f64>,
    /// Edge endpoints for a midpoint vertex (locfit `lo`, `hi`), `lo <= hi`.
    lo: usize,
    hi: usize,
    pseudo: bool,
    fit: VFit,
}

/// The built adaptive tree.
#[derive(Clone, Debug)]
pub struct Tree {
    d: usize,
    vc: usize,
    /// Length of each vertex's coefficient vectors.
    ncoef: usize,
    /// locfit `hasd`: the vertex carries first derivatives.
    hasd: bool,
    /// Split threshold (locfit `cut`, floored at 0.01 by `atree_guessnv`).
    cut: f64,
    /// Scales per dimension (locfit `sca`).
    sca: Vec<f64>,
    /// Bounding box: lower corner then upper corner (locfit `fl`).
    fl: Vec<f64>,
    /// Vertex capacity (locfit `nvm`).
    nvm: usize,
    verts: Vec<Vert>,
}

/// locfit `atree_guessnv`: the vertex capacity, and the cut after the floor.
fn guess_nvm(d: usize, alp: f64, cut: f64) -> (f64, usize) {
    let vc = 1usize << d;
    let mut cut = cut;
    let mut nvm = 1usize << 30;
    if alp > 0.0 {
        if cut < 0.01 {
            cut = 0.01;
        }
        let a0 = if alp > 1.0 { 1.0 } else { 1.0 / alp };
        let mut cu = 1.0;
        for _ in 0..d {
            cu *= cut.min(1.0);
        }
        let nv = ((5.0 * a0 / cu + 1.0) * vc as f64) as usize;
        if nv < nvm {
            nvm = nv;
        }
    }
    if nvm == 1usize << 30 {
        nvm = 102 * vc;
    }
    // mk = 100 (locfit default), so the inflation factor is 1.
    (cut, nvm)
}

/// locfit `hermite2`: Hermite basis on `[0, z]` at `x`.
fn hermite2(x: f64, z: f64) -> [f64; 4] {
    let mut phi = [0.0_f64; 4];
    if z == 0.0 {
        phi[0] = 1.0;
        return phi;
    }
    let h = x / z;
    if h < 0.0 {
        phi[0] = 1.0;
        phi[1] = 0.0;
        phi[2] = h;
        phi[3] = 0.0;
        return phi;
    }
    if h > 1.0 {
        phi[0] = 0.0;
        phi[1] = 1.0;
        phi[2] = 0.0;
        phi[3] = h - 1.0;
        return phi;
    }
    phi[1] = h * h * (3.0 - 2.0 * h);
    phi[0] = 1.0 - phi[1];
    phi[2] = h * (1.0 - h) * (1.0 - h);
    phi[3] = h * h * (h - 1.0);
    phi
}

/// locfit `linear_interp`.
fn linear_interp(h: f64, d: f64, f0: f64, f1: f64) -> f64 {
    if d == 0.0 {
        return f0;
    }
    ((d - h) * f0 + h * f1) / d
}

/// locfit `exvvalpv`: values and derivatives at the midpoint of an edge in
/// dimension `k`, of length `1 << d`, from the two end rows `vl` and `vr`.
fn exvvalpv(vl: &[f64], vr: &[f64], d: usize, k: usize, dl: f64, nc: usize) -> Vec<f64> {
    let vc = 1usize << d;
    let mut vv = vec![0.0; vc];
    if nc == 1 {
        vv[0] = (vl[0] + vr[0]) / 2.0;
        return vv;
    }
    let tk = 1usize << k;
    for i in 0..vc {
        if i & tk == 0 {
            let f0 = (vl[i] + vr[i]) / 2.0 + dl * (vl[i + tk] - vr[i + tk]) / 8.0;
            let f1 = 1.5 * (vr[i] - vl[i]) / dl - (vl[i + tk] + vr[i + tk]) / 4.0;
            vv[i] = f0;
            vv[i + tk] = f1;
        }
    }
    vv
}

/// locfit `rectcell_interp`: interpolate over a rectangular cell from the
/// corner rows `vv` (row `j` holds the value and derivatives at corner `j`).
/// `nc` is 1 (values only, multilinear), `d + 1` (cubic blend) or `1 << d`
/// (multicubic). `vv` is overwritten, as in locfit.
fn rectcell_interp(x: &[f64], vv: &mut [Vec<f64>], ll: &[f64], ur: &[f64], d: usize, nc: usize) -> f64 {
    if nc == 1 {
        for i in (0..d).rev() {
            let tk = 1usize << i;
            for j in 0..tk {
                vv[j][0] = linear_interp(x[i] - ll[i], ur[i] - ll[i], vv[j][0], vv[j + tk][0]);
            }
        }
        return vv[0][0];
    }
    if nc == d + 1 {
        for i in (0..d).rev() {
            let mut phi = hermite2(x[i] - ll[i], ur[i] - ll[i]);
            let tk = 1usize << i;
            phi[2] *= ur[i] - ll[i];
            phi[3] *= ur[i] - ll[i];
            for j in 0..tk {
                vv[j][0] = phi[0] * vv[j][0] + phi[1] * vv[j + tk][0]
                    + phi[2] * vv[j][i + 1] + phi[3] * vv[j + tk][i + 1];
                for k in 1..=i {
                    vv[j][k] = phi[0] * vv[j][k] + phi[1] * vv[j + tk][k];
                }
            }
        }
        return vv[0][0];
    }
    for i in (0..d).rev() {
        let mut phi = hermite2(x[i] - ll[i], ur[i] - ll[i]);
        let tk = 1usize << i;
        phi[2] *= ur[i] - ll[i];
        phi[3] *= ur[i] - ll[i];
        for j in 0..tk {
            for k in 0..tk {
                vv[j][k] = phi[0] * vv[j][k] + phi[1] * vv[j + tk][k]
                    + phi[2] * vv[j][k + tk] + phi[3] * vv[j + tk][k + tk];
            }
        }
    }
    vv[0][0]
}

impl Tree {
    /// Number of vertices (locfit `fp.nv`).
    pub fn nv(&self) -> usize {
        self.verts.len()
    }

    /// Coefficient vector length per vertex.
    pub fn ncoef(&self) -> usize {
        self.ncoef
    }

    /// Vertex coordinates, row-major `nv x d`.
    pub fn xev(&self) -> Vec<f64> {
        self.verts.iter().flat_map(|v| v.x.iter().copied()).collect()
    }

    /// Whether vertex `v` is a pseudo-vertex (locfit `s[v] == 1`).
    pub fn is_pseudo(&self, v: usize) -> bool {
        self.verts[v].pseudo
    }

    /// The fit stored at vertex `v`.
    pub fn vfit(&self, v: usize) -> &VFit {
        &self.verts[v].fit
    }

    /// Vertex coefficient `k` of quantity `what` at vertex `v`.
    pub fn value(&self, v: usize, what: What, k: usize) -> f64 {
        let f = &self.verts[v].fit;
        match what {
            What::Coef => f.coef[k],
            What::Nlx => f.nlx[k],
            What::T0 => f.t0[k],
        }
    }

    /// locfit `exvval` with `z = 1`: fill the corner row `vv` for vertex `v`
    /// (value at `vv[0]`, derivative in dimension `i` at `vv[1 << i]`), and
    /// return how many entries are meaningful (`1 << d` with derivatives, else 1).
    fn exvval(&self, v: usize, what: What, vv: &mut [f64]) -> usize {
        let vc = self.vc;
        for item in vv.iter_mut().take(vc).skip(1) {
            *item = 0.0;
        }
        vv[0] = self.value(v, what, 0);
        if !self.hasd {
            return 1;
        }
        for i in 0..self.d {
            vv[1 << i] = self.value(v, what, i + 1);
        }
        vc
    }

    /// locfit `findpt`: the midpoint vertex of edge `(i0, i1)`, searched above `max(i0, i1)`.
    fn findpt(&self, i0: usize, i1: usize) -> Option<usize> {
        let (i0, i1) = if i0 > i1 { (i1, i0) } else { (i0, i1) };
        (i1 + 1..self.verts.len()).find(|&i| self.verts[i].lo == i0 && self.verts[i].hi == i1)
    }

    /// locfit `atree_split`: the split dimension of a cell with corners `ce`
    /// and box `ll`..`ur`, or `None` when the cell is terminal. `le` receives
    /// the cell widths over the scales.
    fn split(&self, ce: &[usize], ll: &[f64], ur: &[f64], le: &mut [f64]) -> Option<usize> {
        let d = self.d;
        let vc = self.vc;
        let mut hmin = 0.0_f64;
        for &c in ce.iter().take(vc) {
            let h = self.verts[c].fit.h;
            if h > 0.0 && (hmin == 0.0 || h < hmin) {
                hmin = h;
            }
        }
        let mut is = 0usize;
        let mut score = [0.0_f64; MXDIM];
        for i in 0..d {
            le[i] = (ur[i] - ll[i]) / self.sca[i];
            score[i] = if hmin == 0.0 {
                2.0 * (ur[i] - ll[i]) / (self.fl[i + d] - self.fl[i])
            } else {
                le[i] / hmin
            };
            if score[i] > score[is] {
                is = i;
            }
        }
        if self.cut < score[is] {
            Some(is)
        } else {
            None
        }
    }
}

/// Builder state: the tree under construction and the vertex fit.
struct Builder<'a> {
    t: Tree,
    fitv: &'a dyn Fn(&[f64]) -> Result<VFit, String>,
}

impl Builder<'_> {
    /// locfit `des->vfun` at vertex `v`: fit and store the local quantities.
    fn vfit(&mut self, v: usize) -> Result<(), String> {
        let f = (self.fitv)(&self.t.verts[v].x)?;
        if f.coef.len() != self.t.ncoef || f.nlx.len() != self.t.ncoef || f.t0.len() != self.t.ncoef {
            return Err("tree: vertex fit has the wrong coefficient count".to_string());
        }
        self.t.verts[v].fit = f;
        Ok(())
    }

    /// locfit `newsplit`: the midpoint of edge `(i0, i1)`, created if new.
    fn newsplit(&mut self, i0: usize, i1: usize, pv: bool) -> Result<usize, String> {
        if let Some(i) = self.t.findpt(i0, i1) {
            return Ok(i);
        }
        let (i0, i1) = if i0 > i1 { (i1, i0) } else { (i0, i1) };
        let nv = self.t.verts.len();
        if nv == self.t.nvm {
            return Err("newsplit: out of vertex space".to_string());
        }
        let x: Vec<f64> = (0..self.t.d)
            .map(|k| (self.t.verts[i0].x[k] + self.t.verts[i1].x[k]) / 2.0)
            .collect();
        let zero = VFit {
            coef: vec![0.0; self.t.ncoef],
            nlx: vec![0.0; self.t.ncoef],
            t0: vec![0.0; self.t.ncoef],
            h: 0.0,
            lik: [0.0; 3],
        };
        self.t.verts.push(Vert { x, lo: i0, hi: i1, pseudo: pv, fit: zero });
        if pv {
            let h = (self.t.verts[i0].fit.h + self.t.verts[i1].fit.h) / 2.0;
            self.t.verts[nv].fit.h = h;
        } else {
            self.vfit(nv)?;
        }
        Ok(nv)
    }

    /// locfit `atree_grow`: split the cell with corners `ce` and box `ll`..`ur`
    /// recursively, lower half first.
    fn grow(&mut self, ce: &[usize], ll: &mut [f64], ur: &mut [f64]) -> Result<(), String> {
        let d = self.t.d;
        let vc = self.t.vc;
        let mut le = vec![0.0_f64; d];
        let ns = match self.t.split(ce, ll, ur, &mut le) {
            None => return Ok(()),
            Some(ns) => ns,
        };
        let tk = 1usize << ns;
        let mut nce = vec![0usize; vc];
        for i in 0..vc {
            if i & tk == 0 {
                nce[i] = ce[i];
            } else {
                let i0 = ce[i];
                let i1 = ce[i - tk];
                let pv = le[ns] < self.t.cut * self.t.verts[i0].fit.h.min(self.t.verts[i1].fit.h);
                nce[i] = self.newsplit(i0, i1, pv)?;
            }
        }
        let z = ur[ns];
        ur[ns] = (z + ll[ns]) / 2.0;
        self.grow(&nce, ll, ur)?;
        ur[ns] = z;
        let old = nce.clone();
        for i in 0..vc {
            nce[i] = if i & tk == 0 { old[i + tk] } else { ce[i] };
        }
        let z = ll[ns];
        ll[ns] = (z + ur[ns]) / 2.0;
        self.grow(&nce, ll, ur)?;
        ll[ns] = z;
        Ok(())
    }
}

/// Build the adaptive tree over the box `lo`..`hi` (locfit `atree_start`).
///
/// `alp` is the nearest-neighbour fraction (locfit `nn`), `cut` the split
/// threshold (`rbox()` default 0.8), `ncoef` the vertex coefficient count, and
/// `fitv` the local fit at a vertex.
pub fn build(
    lo: &[f64],
    hi: &[f64],
    sca: &[f64],
    cut: f64,
    alp: f64,
    ncoef: usize,
    fitv: &dyn Fn(&[f64]) -> Result<VFit, String>,
) -> Result<Tree, String> {
    let d = lo.len();
    if d == 0 || d > MXDIM || hi.len() != d || sca.len() != d {
        return Err("tree: bad dimensions".to_string());
    }
    let vc = 1usize << d;
    let (cut, nvm) = guess_nvm(d, alp, cut);
    let mut fl = lo.to_vec();
    fl.extend_from_slice(hi);
    let t = Tree {
        d,
        vc,
        ncoef,
        hasd: ncoef == d + 1,
        cut,
        sca: sca.to_vec(),
        fl,
        nvm,
        verts: Vec::new(),
    };
    let mut b = Builder { t, fitv };
    let mut ll = lo.to_vec();
    let mut ur = hi.to_vec();
    // The initial cell: vertex i has coordinate ur[k] where bit k of i is set.
    for i in 0..vc {
        let x: Vec<f64> = (0..d).map(|k| if (i >> k) & 1 == 1 { ur[k] } else { ll[k] }).collect();
        let zero = VFit {
            coef: vec![0.0; ncoef],
            nlx: vec![0.0; ncoef],
            t0: vec![0.0; ncoef],
            h: 0.0,
            lik: [0.0; 3],
        };
        b.t.verts.push(Vert { x, lo: 0, hi: 0, pseudo: false, fit: zero });
        b.vfit(i)?;
    }
    let ce: Vec<usize> = (0..vc).collect();
    b.grow(&ce, &mut ll, &mut ur)?;
    Ok(b.t)
}

impl Tree {
    /// locfit `atree_int`: interpolate `what` at point `x`.
    pub fn interp(&self, x: &[f64], what: What) -> f64 {
        let d = self.d;
        let vc = self.vc;
        let mut vv = vec![vec![0.0_f64; vc]; vc];
        let mut ce: Vec<usize> = (0..vc).collect();
        let mut nc = 0usize;
        for i in 0..vc {
            nc = self.exvval(i, what, &mut vv[i]);
        }
        loop {
            let ll: Vec<f64> = self.verts[ce[0]].x.clone();
            let ur: Vec<f64> = self.verts[ce[vc - 1]].x.clone();
            let mut le = vec![0.0_f64; d];
            let ns = match self.split(&ce, &ll, &ur, &mut le) {
                None => break,
                Some(ns) => ns,
            };
            let tk = 1usize << ns;
            let h = ur[ns] - ll[ns];
            let lo_side = (2.0 * (x[ns] - ll[ns])) < h;
            for i in 0..vc {
                if i & tk != 0 {
                    continue;
                }
                let nv = match self.findpt(ce[i], ce[i + tk]) {
                    Some(v) => v,
                    None => return f64::NAN,
                };
                if lo_side {
                    ce[i + tk] = nv;
                    if self.verts[nv].pseudo {
                        vv[i + tk] = exvvalpv(&vv[i], &vv[i + tk], d, ns, h, nc);
                    } else {
                        self.exvval(nv, what, &mut vv[i + tk]);
                    }
                } else {
                    ce[i] = nv;
                    if self.verts[nv].pseudo {
                        vv[i] = exvvalpv(&vv[i], &vv[i + tk], d, ns, h, nc);
                    } else {
                        self.exvval(nv, what, &mut vv[i]);
                    }
                }
            }
        }
        let ll: Vec<f64> = self.verts[ce[0]].x.clone();
        let ur: Vec<f64> = self.verts[ce[vc - 1]].x.clone();
        rectcell_interp(x, &mut vv, &ll, &ur, d, nc)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A linear-in-x fit with a constant derivative is reproduced exactly by
    /// the cubic blend, so the interpolant equals the vertex function.
    #[test]
    fn linear_fit_is_reproduced() {
        let fitv = |xv: &[f64]| -> Result<VFit, String> {
            Ok(VFit {
                coef: vec![2.0 + 3.0 * xv[0], 3.0],
                nlx: vec![1.0, 0.0],
                t0: vec![1.0, 0.0],
                h: 0.3,
                lik: [0.0; 3],
            })
        };
        let t = build(&[0.0], &[1.0], &[1.0], 0.8, 0.7, 2, &fitv).expect("build");
        for k in 0..=20 {
            let x = k as f64 / 20.0;
            let f = t.interp(&[x], What::Coef);
            assert!((f - (2.0 + 3.0 * x)).abs() < 1e-12, "x={x} f={f}");
        }
    }
}
