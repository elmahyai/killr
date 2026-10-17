//! R nlme `mixed_*` kernels from `src/nlmefit.c` for `lme`.
//!
//! The C is vendored unchanged from nlme 3.1-171 in `c/`, with the LINPACK
//! routines R uses (`dqrdc2`, `dqrsl`, `dtrsl`, `dpofa`) in `fortran/`. The
//! BLAS calls go to the system `libblas.so.3` that R links. The R API is a
//! stand-in (`c/include`, `c/nlme_mixedem_entry.c`). Each function takes the
//! arguments of the matching R `.C()` call, in the same order, and returns
//! the arrays that call would return.

use std::os::raw::{c_char, c_int};

const MSG_LEN: usize = 512;

unsafe extern "C" {
    fn nlme_mixed_em(
        zxy: *mut f64,
        pdims: *mut c_int,
        dm_half: *mut f64,
        n_iter: *mut c_int,
        pd_class: *mut c_int,
        rml: *mut c_int,
        log_lik: *mut f64,
        ra: *mut f64,
        lrss: *mut f64,
        sigma: *mut f64,
        msg: *mut c_char,
        msglen: usize,
    ) -> c_int;

    fn nlme_mixed_loglik(
        zxy: *mut f64,
        pdims: *mut c_int,
        pars: *mut f64,
        settings: *mut c_int,
        log_lik: *mut f64,
        lrss: *mut f64,
        sigma: *mut f64,
        msg: *mut c_char,
        msglen: usize,
    ) -> c_int;

    fn nlme_mixed_estimate(
        zxy: *mut f64,
        pdims: *mut c_int,
        dm_half: *mut f64,
        rml: *mut c_int,
        log_lik: *mut f64,
        dc: *mut f64,
        invert: *mut c_int,
        sigma: *mut f64,
        msg: *mut c_char,
        msglen: usize,
    ) -> c_int;

    fn nlme_mixed_decomp(zxy: *mut f64, pdims: *mut c_int, msg: *mut c_char, msglen: usize) -> c_int;

    fn nlme_pdsymm_start(block: *mut f64, q: c_int, params: *mut f64, msg: *mut c_char, msglen: usize) -> c_int;
}

/// Error from the kernel or from the input shapes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct KernelError(pub String);

/// The result of `mixed_EM`: the updated `DmHalf` factor (in place), the
/// log-likelihood, the `Ra` array, and `lRSS`.
#[derive(Debug, Clone, PartialEq)]
pub struct EmResult {
    pub log_lik: f64,
    pub ra: Vec<f64>,
    pub lrss: f64,
}

fn bad(msg: &str) -> KernelError {
    KernelError(msg.to_string())
}

/// Checks `pdims` as R's `unlist(dims)` lays it out: `N`, `ZXrows`, `ZXcols`,
/// `Q`, `Srows`, then the `Q + 2` vectors `q`, `ngrp`, `DmOff`, `ncol`,
/// `nrot`, then the offset vectors `ZXoff`, `ZXlen`, `SToff`, `DecOff`,
/// `DecLen`, each of length `sum(ngrp)`. Returns `Q`.
fn check_pdims(zxy: &[f64], pdims: &[i32]) -> Result<usize, KernelError> {
    if pdims.len() < 5 {
        return Err(bad("pdims must hold N, ZXrows, ZXcols, Q and Srows"));
    }
    let q = pdims[3];
    if q < 0 {
        return Err(bad("Q must not be negative"));
    }
    let q = q as usize;
    let qp2 = q + 2;
    let header = 5 + 5 * qp2;
    if pdims.len() < header {
        return Err(bad("pdims is shorter than the level vectors"));
    }
    let total: usize = pdims[5 + qp2..5 + 2 * qp2].iter().map(|&g| g.max(0) as usize).sum();
    if pdims.len() < header + 5 * total {
        return Err(bad("pdims is shorter than the offset vectors"));
    }
    let zx_rows = pdims[1].max(0) as usize;
    let zx_cols = pdims[2].max(0) as usize;
    if zxy.len() < zx_rows * zx_cols {
        return Err(bad("ZXy is shorter than ZXrows * ZXcols"));
    }
    Ok(q)
}

/// `DmOff[Q]`: the length of the `DmHalf` factor for `pdims`.
fn dm_half_len(pdims: &[i32], q: usize) -> usize {
    let qp2 = q + 2;
    pdims[5 + 2 * qp2 + q].max(0) as usize
}

/// Number of free parameters for `pdClass` (R's `count_DmHalf_pars`).
fn count_pars(pdims: &[i32], pd_class: &[i32], q: usize) -> usize {
    let qp2 = q + 2;
    let qs = &pdims[5..5 + qp2];
    (0..q)
        .map(|i| {
            let s = qs[i].max(0) as usize;
            match pd_class[i] {
                0 | 4 => s * (s + 1) / 2,
                1 => s,
                2 => 1,
                3 => 2,
                _ => 0,
            }
        })
        .sum()
}

fn settings_for(settings: &[i32], q: usize) -> Result<(), KernelError> {
    if settings.len() < 3 + q {
        return Err(bad("settings must hold RML, asDelta, gradHess and pdClass"));
    }
    Ok(())
}

/// Runs `mixed_EM` on copies of the inputs. `dm_half` is updated in place,
/// as the `DmHalf` argument is in R's `.C` call.
pub fn mixed_em(
    zxy: &[f64],
    pdims: &[i32],
    dm_half: &mut [f64],
    n_iter: i32,
    pd_class: &[i32],
    rml: i32,
    sigma: f64,
) -> Result<EmResult, KernelError> {
    let q = check_pdims(zxy, pdims)?;
    if pd_class.len() < q {
        return Err(bad("pdClass must have one entry per level"));
    }
    if dm_half.len() < dm_half_len(pdims, q) {
        return Err(bad("DmHalf is shorter than DmOff[Q]"));
    }
    let mut zxy = zxy.to_vec();
    let mut pdims = pdims.to_vec();
    let mut pd_class = pd_class.to_vec();
    let mut n_iter = n_iter as c_int;
    let mut rml = rml as c_int;
    let mut sigma = sigma;
    let mut log_lik = 0.0f64;
    let mut lrss = 0.0f64;
    // R passes Ra as double(length(precvec)), zero-filled.
    let mut ra = vec![0.0f64; dm_half.len()];
    let mut msg = vec![0 as c_char; MSG_LEN];
    let status = unsafe {
        nlme_mixed_em(
            zxy.as_mut_ptr(),
            pdims.as_mut_ptr(),
            dm_half.as_mut_ptr(),
            &mut n_iter,
            pd_class.as_mut_ptr(),
            &mut rml,
            &mut log_lik,
            ra.as_mut_ptr(),
            &mut lrss,
            &mut sigma,
            msg.as_mut_ptr(),
            msg.len(),
        )
    };
    check_status(status, &msg)?;
    Ok(EmResult { log_lik, ra, lrss })
}

fn check_status(status: c_int, msg: &[c_char]) -> Result<(), KernelError> {
    if status == 0 {
        return Ok(());
    }
    let text = unsafe { std::ffi::CStr::from_ptr(msg.as_ptr()) }
        .to_string_lossy()
        .into_owned();
    Err(KernelError(text))
}

/// `mixed_loglik(ZXy, pdims, pars, settings, logLik, lRSS, sigma)`.
///
/// `settings` is `RML, asDelta, gradHess, pdClass...`. With `asDelta = 1`,
/// `pars` is the `DmHalf` factor. With `asDelta = 0` it is the parameter
/// vector. With `gradHess = 1` (R's `lme` objective), the first value is the
/// Koshal intercept, followed by the gradient and Hessian. Returns the values
/// (room for `1 + q * (q + 1)`, as R allocates) and `lRSS`.
pub fn mixed_loglik(
    zxy: &[f64],
    pdims: &[i32],
    pars: &[f64],
    settings: &[i32],
    sigma: f64,
) -> Result<(Vec<f64>, f64), KernelError> {
    let q = check_pdims(zxy, pdims)?;
    settings_for(settings, q)?;
    let pd_class = &settings[3..3 + q];
    if settings[1] != 0 {
        if pars.len() < dm_half_len(pdims, q) {
            return Err(bad("pars is shorter than DmOff[Q]"));
        }
    } else if pars.len() < count_pars(pdims, pd_class, q) {
        return Err(bad("pars is shorter than the parameter count of pdClass"));
    }
    let mut zxy = zxy.to_vec();
    let mut pdims = pdims.to_vec();
    let mut pars = pars.to_vec();
    let mut settings = settings.to_vec();
    let mut sigma = sigma;
    let n_out = (1 + pars.len() * (pars.len() + 1)).max(1);
    let mut log_lik = vec![0.0f64; n_out];
    let mut lrss = 0.0f64;
    let mut msg = vec![0 as c_char; MSG_LEN];
    let status = unsafe {
        nlme_mixed_loglik(
            zxy.as_mut_ptr(),
            pdims.as_mut_ptr(),
            pars.as_mut_ptr(),
            settings.as_mut_ptr(),
            log_lik.as_mut_ptr(),
            &mut lrss,
            &mut sigma,
            msg.as_mut_ptr(),
            msg.len(),
        )
    };
    check_status(status, &msg)?;
    Ok((log_lik, lrss))
}

/// `mixed_estimate(ZXy, pdims, DmHalf, RML, logLik, estimates, invert, sigma)`.
/// Returns `(logLik, estimates)`, where `estimates` holds `Srows * ZXcols`
/// values (column-major), as R's `estimates = double(StrRows * ZXcols)`.
pub fn mixed_estimate(
    zxy: &[f64],
    pdims: &[i32],
    dm_half: &[f64],
    rml: i32,
    invert: i32,
    sigma: f64,
) -> Result<(f64, Vec<f64>), KernelError> {
    let q = check_pdims(zxy, pdims)?;
    if dm_half.len() < dm_half_len(pdims, q) {
        return Err(bad("DmHalf is shorter than DmOff[Q]"));
    }
    let srows = pdims[4].max(0) as usize;
    let zx_cols = pdims[2].max(0) as usize;
    let mut zxy = zxy.to_vec();
    let mut pdims = pdims.to_vec();
    let mut dm_half = dm_half.to_vec();
    let mut rml = rml as c_int;
    let mut invert = invert as c_int;
    let mut sigma = sigma;
    let mut log_lik = 0.0f64;
    let mut dc = vec![0.0f64; srows * zx_cols];
    let mut msg = vec![0 as c_char; MSG_LEN];
    let status = unsafe {
        nlme_mixed_estimate(
            zxy.as_mut_ptr(),
            pdims.as_mut_ptr(),
            dm_half.as_mut_ptr(),
            &mut rml,
            &mut log_lik,
            dc.as_mut_ptr(),
            &mut invert,
            &mut sigma,
            msg.as_mut_ptr(),
            msg.len(),
        )
    };
    check_status(status, &msg)?;
    Ok((log_lik, dc))
}

/// `mixed_decomp(ZXy, pdims)`: returns `ZXy` with its leading
/// `Srows * ZXcols` entries replaced by the decomposition, as R's `.C` does.
pub fn mixed_decomp(zxy: &[f64], pdims: &[i32]) -> Result<Vec<f64>, KernelError> {
    check_pdims(zxy, pdims)?;
    let mut zxy = zxy.to_vec();
    let mut pdims = pdims.to_vec();
    let mut msg = vec![0 as c_char; MSG_LEN];
    let status = unsafe {
        nlme_mixed_decomp(zxy.as_mut_ptr(), pdims.as_mut_ptr(), msg.as_mut_ptr(), msg.len())
    };
    check_status(status, &msg)?;
    Ok(zxy)
}

/// `matrix(object[[i]]) <- crossprod(matrix(zz[block], ncol = q))` on a
/// pdSymm, read back as its parameters (R's `matrix<-.pdMat` with `chol`,
/// then `pdConstruct.pdSymm`'s `svd`). `block` is the q x q EM factor block
/// (column-major). Returns the `q (q + 1) / 2` parameters, bit-exact with R.
pub fn pdsymm_from_block(block: &[f64], q: usize) -> Result<Vec<f64>, KernelError> {
    if q == 0 || block.len() < q * q {
        return Err(bad("block must hold a q x q matrix"));
    }
    let mut block = block[..q * q].to_vec();
    let mut params = vec![0.0f64; q * (q + 1) / 2];
    let mut msg = vec![0 as c_char; MSG_LEN];
    let status = unsafe {
        nlme_pdsymm_start(
            block.as_mut_ptr(),
            q as c_int,
            params.as_mut_ptr(),
            msg.as_mut_ptr(),
            msg.len(),
        )
    };
    check_status(status, &msg)?;
    Ok(params)
}

#[cfg(feature = "python")]
mod python {
    use super::{
        mixed_decomp as decomp_kernel, mixed_em as em_kernel, mixed_estimate as estimate_kernel,
        mixed_loglik as loglik_kernel, pdsymm_from_block as pdsymm_kernel,
    };
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    fn value_error(err: super::KernelError) -> PyErr {
        PyValueError::new_err(err.0)
    }

    /// `mixed_em(ZXy, pdims, DmHalf, nIter, pdClass, RML, sigma)`.
    ///
    /// Returns `(DmHalf, logLik, Ra, lRSS)`, the same outputs as R's
    /// `.C("mixed_EM")` call. Vectors are column-major, as in R.
    #[pyfunction]
    #[pyo3(name = "mixed_em")]
    fn mixed_em_py(
        zxy: Vec<f64>,
        pdims: Vec<i32>,
        mut dm_half: Vec<f64>,
        n_iter: i32,
        pd_class: Vec<i32>,
        rml: i32,
        sigma: f64,
    ) -> PyResult<(Vec<f64>, f64, Vec<f64>, f64)> {
        let out = em_kernel(&zxy, &pdims, &mut dm_half, n_iter, &pd_class, rml, sigma).map_err(value_error)?;
        Ok((dm_half, out.log_lik, out.ra, out.lrss))
    }

    /// `mixed_loglik(ZXy, pdims, pars, settings, sigma)`; returns `(val, lRSS)`.
    #[pyfunction]
    #[pyo3(name = "mixed_loglik")]
    fn mixed_loglik_py(
        zxy: Vec<f64>,
        pdims: Vec<i32>,
        pars: Vec<f64>,
        settings: Vec<i32>,
        sigma: f64,
    ) -> PyResult<(Vec<f64>, f64)> {
        loglik_kernel(&zxy, &pdims, &pars, &settings, sigma).map_err(value_error)
    }

    /// `mixed_estimate(ZXy, pdims, DmHalf, RML, invert, sigma)`; returns `(logLik, estimates)`.
    #[pyfunction]
    #[pyo3(name = "mixed_estimate")]
    fn mixed_estimate_py(
        zxy: Vec<f64>,
        pdims: Vec<i32>,
        dm_half: Vec<f64>,
        rml: i32,
        invert: i32,
        sigma: f64,
    ) -> PyResult<(f64, Vec<f64>)> {
        estimate_kernel(&zxy, &pdims, &dm_half, rml, invert, sigma).map_err(value_error)
    }

    /// `mixed_decomp(ZXy, pdims)`; returns the rewritten `ZXy`.
    #[pyfunction]
    #[pyo3(name = "mixed_decomp")]
    fn mixed_decomp_py(zxy: Vec<f64>, pdims: Vec<i32>) -> PyResult<Vec<f64>> {
        decomp_kernel(&zxy, &pdims).map_err(value_error)
    }

    /// `pdsymm_from_block(block, q)`: the pdSymm parameters of `crossprod(block)`.
    #[pyfunction]
    #[pyo3(name = "pdsymm_from_block")]
    fn pdsymm_from_block_py(block: Vec<f64>, q: usize) -> PyResult<Vec<f64>> {
        pdsymm_kernel(&block, q).map_err(value_error)
    }

    #[pymodule]
    fn nlme_mixedem(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(pdsymm_from_block_py, m)?)?;
        m.add_function(wrap_pyfunction!(mixed_em_py, m)?)?;
        m.add_function(wrap_pyfunction!(mixed_loglik_py, m)?)?;
        m.add_function(wrap_pyfunction!(mixed_estimate_py, m)?)?;
        m.add_function(wrap_pyfunction!(mixed_decomp_py, m)?)?;
        Ok(())
    }
}
