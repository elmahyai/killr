//! Direct local regression kernel for R package locfit 1.5-9.12.
//!
//! Ported from the compiled C kernel in `src/` of the CRAN tarball:
//! `locfit.c`, `startlf.c`, `lf_fitfun.c`, `lf_nbhd.c`, `weight.c`,
//! `procv.c`, `lf_vari.c`, `frend.c`, `pcomp.c`, `family.c`, `m_eigen.c`,
//! `m_jacob.c`, and `m_max.c`; plus the fitted values of `fitted.c` /
//! `S_enter.c` (`sfitted`), the exact least-squares criterion of `band.c`
//! (`kdecri`) and `smisc.c` (`slscv`).
//!
//! Covered: the Gaussian identity (quasi) family with `ev = "data"` or fits at
//! given points, spherical and product kernels, degree 0 to 2 (3 for the
//! spherical kernel), and the nearest-neighbour or fixed bandwidth. Also the
//! default kd-tree vertex interpolation (`ev = rbox()`, `tree.rs`) with the
//! leave-one-out criterion (`cv_sum`, the `lcv` default). Not yet ported: the
//! adaptive degree and criterion, the robust, density, binomial and other
//! families, and the density-based `lscv` selector (`dens_lscv`, geth = 6).

pub mod critval;
pub mod density;
pub mod density_lf;
pub mod eig;
pub mod kdeb;
pub mod fit;
pub mod kappa0;
pub mod kdecri;
pub mod kernel;
mod odi;
pub mod tree;

pub use fit::{fit, Eval, FitOpts, FitOut, Input};
pub use kernel::{kernel_from_str, kt_from_str, Kernel, Kt};

#[cfg(feature = "python")]
mod py {
    use numpy::ndarray::Array2;
    use numpy::{IntoPyArray, PyArray1, PyReadonlyArray1, PyReadonlyArray2};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;
    use pyo3::types::PyDict;

    use crate::density::{
        dens_lscv as dens_lscv_rs, dens_lscv_tree as dens_lscv_tree_rs,
        dens_vertices as dens_vertices_rs, DensOpts,
    };
    use crate::fit::{fit, Eval, FitOpts, FitOut, Input};
    use crate::kdeb::{kdeb as kdeb_rs, kern_from_r, meth_from_str};
    use crate::critval::scritval as scritval_rs;
    use crate::kdecri::{kdecri as kdecri_rs, slscv as slscv_rs};
    use crate::kernel::{kernel_from_str, kt_from_str};
    use crate::density_lf::density_grid as density_grid_rs;
    use crate::kappa0::{kappa0_const as kappa0_const_rs, Geth2Opts};

    fn err<E: ToString>(e: E) -> PyErr {
        PyValueError::new_err(e.to_string())
    }

    /// Shared argument handling for the fit entry points.
    #[allow(clippy::too_many_arguments)]
    fn run_fit(
        x: &PyReadonlyArray2<'_, f64>,
        y: &PyReadonlyArray1<'_, f64>,
        weights: Option<&PyReadonlyArray1<'_, f64>>,
        base: Option<&PyReadonlyArray1<'_, f64>>,
        xev: Option<&PyReadonlyArray2<'_, f64>>,
        nn: f64,
        fixh: f64,
        deg: usize,
        kern: &str,
        kt: &str,
        scale: Option<Vec<f64>>,
        quasi: bool,
        tree: bool,
        cut: f64,
    ) -> PyResult<FitOut> {
        let xa = x.as_array();
        let (n, d) = xa.dim();
        let xv: Vec<f64> = xa.iter().copied().collect();
        let yv: Vec<f64> = y.as_array().iter().copied().collect();
        let wv: Option<Vec<f64>> = weights.map(|w| w.as_array().iter().copied().collect());
        let bv: Option<Vec<f64>> = base.map(|b| b.as_array().iter().copied().collect());
        let ev_pts: Option<(Vec<f64>, usize)> = xev.map(|e| {
            let ea = e.as_array();
            let (m, _) = ea.dim();
            (ea.iter().copied().collect(), m)
        });

        let kernel = kernel_from_str(kern).map_err(err)?;
        let ktype = kt_from_str(kt).map_err(err)?;
        let opts = FitOpts {
            nn,
            fixh,
            deg,
            kern: kernel,
            kt: ktype,
            quasi,
        };
        let eval = match &ev_pts {
            _ if tree => Eval::Tree(cut),
            None => Eval::Data,
            Some((e, m)) => Eval::Points(e, *m),
        };
        let inp = Input {
            x: &xv,
            n,
            d,
            y: &yv,
            weights: wv.as_deref(),
            base: bv.as_deref(),
            scale: scale.as_deref(),
            eval,
            xnew: if tree {
                ev_pts.as_ref().map(|(e, _)| e.as_slice())
            } else {
                None
            },
        };
        fit(&inp, &opts).map_err(err)
    }

    fn to_2d<'py>(
        py: Python<'py>,
        data: Vec<f64>,
        rows: usize,
        cols: usize,
    ) -> PyResult<Bound<'py, numpy::PyArray2<f64>>> {
        Ok(Array2::from_shape_vec((rows, cols), data)
            .map_err(err)?
            .into_pyarray(py))
    }

    /// Local regression fit (locfit `slocfit` with `ev = "data"` or
    /// `ev = "preset"`), Gaussian identity quasi family.
    ///
    /// Returns a dict with `coef`, `nlx`, `t0` (each `nv x ncoef`), `h`
    /// (`nv`), `lik` (`nv x 3`), `fitted` (`n`, data fits only), and the
    /// summaries `lk`, `df0`, `df1`, `rv`, `rsc`. `df0` and `df1` are locfit's
    /// `dp` entries `df1` and `df2`.
    #[pyfunction]
    #[pyo3(signature = (x, y, weights=None, base=None, xev=None, nn=0.7, fixh=0.0,
                        deg=2, kern="tricube", kt="spherical", scale=None, quasi=true,
                        tree=false, cut=0.8))]
    #[allow(clippy::too_many_arguments)]
    fn locfit_fit<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        y: PyReadonlyArray1<'py, f64>,
        weights: Option<PyReadonlyArray1<'py, f64>>,
        base: Option<PyReadonlyArray1<'py, f64>>,
        xev: Option<PyReadonlyArray2<'py, f64>>,
        nn: f64,
        fixh: f64,
        deg: usize,
        kern: &str,
        kt: &str,
        scale: Option<Vec<f64>>,
        quasi: bool,
        tree: bool,
        cut: f64,
    ) -> PyResult<Bound<'py, PyDict>> {
        let out = run_fit(
            &x,
            &y,
            weights.as_ref(),
            base.as_ref(),
            xev.as_ref(),
            nn,
            fixh,
            deg,
            kern,
            kt,
            scale,
            quasi,
            tree,
            cut,
        )?;
        let nv = out.nv;
        let nc = out.ncoef;
        let dict = PyDict::new(py);
        dict.set_item("coef", to_2d(py, out.coef, nv, nc)?)?;
        dict.set_item("nlx", to_2d(py, out.nlx, nv, nc)?)?;
        dict.set_item("t0", to_2d(py, out.t0, nv, nc)?)?;
        dict.set_item("h", out.h.into_pyarray(py))?;
        dict.set_item("lik", to_2d(py, out.lik, nv, 3)?)?;
        dict.set_item("fitted", out.fitted.into_pyarray(py))?;
        dict.set_item("lk", out.lk)?;
        dict.set_item("df0", out.df0)?;
        dict.set_item("df1", out.df1)?;
        dict.set_item("rv", out.rv)?;
        dict.set_item("rsc", out.rsc)?;
        let nd = if nv == 0 { 0 } else { out.xev.len() / nv };
        dict.set_item("xev", to_2d(py, out.xev, nv, nd)?)?;
        dict.set_item("nlx_data", out.nlx_data.into_pyarray(py))?;
        dict.set_item("cv_sum", out.cv_sum)?;
        dict.set_item("xnew_fitted", out.xnew_fitted.into_pyarray(py))?;
        Ok(dict)
    }

    /// Density LSCV on the adaptive tree (locfit `lscv` default, `ev = rbox()`):
    /// returns `[criterion, degrees of freedom]`.
    #[pyfunction]
    #[pyo3(signature = (x, nn=0.7, fixh=0.0, deg=2, kern="tricube", cut=0.8))]
    fn lscv_tree<'py>(
        py: Python<'py>,
        x: PyReadonlyArray1<'py, f64>,
        nn: f64,
        fixh: f64,
        deg: usize,
        kern: &str,
        cut: f64,
    ) -> PyResult<Bound<'py, PyArray1<f64>>> {
        let xv: Vec<f64> = x.as_array().iter().copied().collect();
        let kernel = kernel_from_str(kern).map_err(err)?;
        let opts = DensOpts {
            nn,
            fixh,
            deg,
            kern: kernel,
        };
        let r = dens_lscv_tree_rs(&xv, &opts, cut).map_err(err)?;
        Ok(r.to_vec().into_pyarray(py))
    }

    /// Fitted values at the data (locfit `sfitted`, R's `fitted.locfit` with
    /// `what = "coef"` and `type = "fit"`), for the fit at the data
    /// (`ev = "data"`). Each value is `base + coef + parametric component`.
    #[pyfunction]
    #[pyo3(signature = (x, y, weights=None, base=None, nn=0.7, fixh=0.0,
                        deg=2, kern="tricube", kt="spherical", scale=None, quasi=true))]
    #[allow(clippy::too_many_arguments)]
    fn sfitted<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        y: PyReadonlyArray1<'py, f64>,
        weights: Option<PyReadonlyArray1<'py, f64>>,
        base: Option<PyReadonlyArray1<'py, f64>>,
        nn: f64,
        fixh: f64,
        deg: usize,
        kern: &str,
        kt: &str,
        scale: Option<Vec<f64>>,
        quasi: bool,
    ) -> PyResult<Bound<'py, PyArray1<f64>>> {
        let out = run_fit(
            &x,
            &y,
            weights.as_ref(),
            base.as_ref(),
            None,
            nn,
            fixh,
            deg,
            kern,
            kt,
            scale,
            quasi,
            false,
            0.8,
        )?;
        Ok(out.fitted.into_pyarray(py))
    }

    /// Exact least-squares cross-validation criterion for a Gaussian kernel
    /// density estimate (locfit `slscv`, R's `lscv.exact`). Returns
    /// `[criterion, degrees of freedom]`.
    #[pyfunction]
    fn slscv<'py>(
        py: Python<'py>,
        x: PyReadonlyArray1<'py, f64>,
        h: f64,
    ) -> PyResult<Bound<'py, PyArray1<f64>>> {
        let xv: Vec<f64> = x.as_array().iter().copied().collect();
        let r = slscv_rs(&xv, h).map_err(err)?;
        Ok(r.to_vec().into_pyarray(py))
    }

    /// Bandwidth criterion value and its derivative (locfit `kdecri`).
    /// `k` is 1 AIC, 2 OCV, 3 LSCV, 4 BCV, 5 SJPI, 6 gas-k-k. Returns the
    /// four-element `res` vector.
    #[pyfunction]
    #[pyo3(signature = (x, h, k, c=0.0, kern="gaussian"))]
    fn kdecri<'py>(
        py: Python<'py>,
        x: PyReadonlyArray1<'py, f64>,
        h: f64,
        k: usize,
        c: f64,
        kern: &str,
    ) -> PyResult<Bound<'py, PyArray1<f64>>> {
        let xv: Vec<f64> = x.as_array().iter().copied().collect();
        let ker = kernel_from_str(kern).map_err(err)?;
        let r = kdecri_rs(&xv, h, c, k, ker).map_err(err)?;
        Ok(r.to_vec().into_pyarray(py))
    }

    /// Density-family least-squares cross-validation, locfit `dens_lscv`
    /// (R's `lscv` default path, `geth = 6`) at the data (`ev = dat()`).
    /// Returns `[criterion, degrees of freedom]`, R's two values of `lscv()`.
    #[pyfunction]
    #[pyo3(signature = (x, nn=0.7, fixh=0.0, deg=2, kern="tricube"))]
    fn dens_lscv<'py>(
        py: Python<'py>,
        x: PyReadonlyArray1<'py, f64>,
        nn: f64,
        fixh: f64,
        deg: usize,
        kern: &str,
    ) -> PyResult<Bound<'py, PyArray1<f64>>> {
        let xv: Vec<f64> = x.as_array().iter().copied().collect();
        let kernel = kernel_from_str(kern).map_err(err)?;
        let opts = DensOpts {
            nn,
            fixh,
            deg,
            kern: kernel,
        };
        let r = dens_lscv_rs(&xv, &opts).map_err(err)?;
        Ok(r.to_vec().into_pyarray(py))
    }

    /// Per-observation density fits (locfit `procv`, density family, log link
    /// at `ev = dat()`): returns `(value, deriv, infl)` as three arrays.
    #[pyfunction]
    #[pyo3(signature = (x, nn=0.7, fixh=0.0, deg=2, kern="tricube"))]
    fn dens_vertices<'py>(
        py: Python<'py>,
        x: PyReadonlyArray1<'py, f64>,
        nn: f64,
        fixh: f64,
        deg: usize,
        kern: &str,
    ) -> PyResult<(
        Bound<'py, PyArray1<f64>>,
        Bound<'py, PyArray1<f64>>,
        Bound<'py, PyArray1<f64>>,
    )> {
        let xv: Vec<f64> = x.as_array().iter().copied().collect();
        let kernel = kernel_from_str(kern).map_err(err)?;
        let opts = DensOpts {
            nn,
            fixh,
            deg,
            kern: kernel,
        };
        let v = dens_vertices_rs(&xv, &opts).map_err(err)?;
        Ok((
            v.value.into_pyarray(py),
            v.deriv.into_pyarray(py),
            v.infl.into_pyarray(py),
        ))
    }

    /// Kernel density bandwidths (locfit `kdeselect`, R's `kdeb`). `h0` and
    /// `h1` are already multiplied by `gf`. `meth` holds R's method names
    /// (AIC, LCV, LSCV, BCV, SJPI, GKK) and `kern` R's kernel name. Returns
    /// one bandwidth per method, in the order given.
    #[pyfunction]
    #[pyo3(signature = (x, h0, h1, meth, kern="gauss"))]
    fn kdeb_bandwidth<'py>(
        py: Python<'py>,
        x: PyReadonlyArray1<'py, f64>,
        h0: f64,
        h1: f64,
        meth: Vec<String>,
        kern: &str,
    ) -> PyResult<Bound<'py, PyArray1<f64>>> {
        let xv: Vec<f64> = x.as_array().iter().copied().collect();
        let codes = meth
            .iter()
            .map(|m| meth_from_str(m))
            .collect::<Result<Vec<usize>, String>>()
            .map_err(err)?;
        let ker = kern_from_r(kern).map_err(err)?;
        let r = kdeb_rs(&xv, h0, h1, &codes, ker).map_err(err)?;
        Ok(r.into_pyarray(py))
    }

    /// Critical value for a Gaussian process with two-sided tails and rdf = 0,
    /// locfit `scritval`. `k0` is the constant vector of `crit()`, `d` the
    /// dimension, `cov` the coverage. Returns `c` with tail probability 1 - cov.
    #[pyfunction]
    #[pyo3(signature = (k0, d, cov))]
    fn scritval(k0: Vec<f64>, d: usize, cov: f64) -> PyResult<f64> {
        scritval_rs(&k0, d, cov).map_err(err)
    }

    /// density.lf values on a grid (locfit density family, one dimension,
    /// degree 0, link ident, no user limits). `h` is the bandwidth and `kern`
    /// the kernel name. Returns one density value per grid point.
    #[pyfunction]
    #[pyo3(signature = (x, grid, h, kern="gauss"))]
    fn density_lf_grid<'py>(
        py: Python<'py>,
        x: PyReadonlyArray1<'py, f64>,
        grid: PyReadonlyArray1<'py, f64>,
        h: f64,
        kern: &str,
    ) -> PyResult<Bound<'py, PyArray1<f64>>> {
        let xv: Vec<f64> = x.as_array().iter().copied().collect();
        let gv: Vec<f64> = grid.as_array().iter().copied().collect();
        let ker = kernel_from_str(kern).map_err(err)?;
        let r = density_grid_rs(&xv, &gv, h, ker).map_err(err)?;
        Ok(r.into_pyarray(py))
    }

    /// Tube constants of `kappa0` (locfit `geth = 2`, `dc = TRUE`) on the grid
    /// `lfgrid(mg)` over the data box. Returns `const` (`d + 1` values) for
    /// `crit()`. Ported for `d = 1` and `d = 2`, tricube kernel, spherical
    /// kernel type, degree 2.
    #[pyfunction]
    #[pyo3(signature = (x, nn=0.7, fixh=0.0, deg=2, kern="tricube", kt="sph", mg=20))]
    fn kappa0_const<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        nn: f64,
        fixh: f64,
        deg: usize,
        kern: &str,
        kt: &str,
        mg: usize,
    ) -> PyResult<Bound<'py, PyArray1<f64>>> {
        let xa = x.as_array();
        let (n, d) = xa.dim();
        let xv: Vec<f64> = xa.iter().copied().collect();
        let o = Geth2Opts {
            nn,
            fixh,
            deg,
            kern: kernel_from_str(kern).map_err(err)?,
            kt: kt_from_str(kt).map_err(err)?,
            mg,
        };
        let k = kappa0_const_rs(&xv, n, d, &o).map_err(err)?;
        Ok(k.into_pyarray(py))
    }

    #[pymodule]
    fn locfit(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(kappa0_const, m)?)?;
        m.add_function(wrap_pyfunction!(density_lf_grid, m)?)?;
        m.add_function(wrap_pyfunction!(scritval, m)?)?;
        m.add_function(wrap_pyfunction!(dens_vertices, m)?)?;
        m.add_function(wrap_pyfunction!(dens_lscv, m)?)?;
        m.add_function(wrap_pyfunction!(locfit_fit, m)?)?;
        m.add_function(wrap_pyfunction!(lscv_tree, m)?)?;
        m.add_function(wrap_pyfunction!(sfitted, m)?)?;
        m.add_function(wrap_pyfunction!(slscv, m)?)?;
        m.add_function(wrap_pyfunction!(kdecri, m)?)?;
        m.add_function(wrap_pyfunction!(kdeb_bandwidth, m)?)?;
        Ok(())
    }
}
