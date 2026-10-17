//! Random-effect kernels of ordinal 2026.7-26 (clmm), from `src/utilityFuns.c`.
//!
//! The C is vendored under `vendor/ordinal` with its GPL notice (LICENCE.note,
//! DESCRIPTION) and compiled by `build.rs` together with the R API shim in
//! `vendor/shim`. The Python binding passes the same arrays that R's `.C()`
//! call passes, in the same order, and returns the outputs.
//!
//! Bound here: `NRalgv3` (inner Newton-Raphson for the modes of u), `getNAGQ`
//! (adaptive Gauss-Hermite), `getNGHQ_C` (standard Gauss-Hermite) and `nll`.
//! `NRalg`, `hess`, `grad_C`, `gradC` and `grFacSum_C` are compiled too but
//! are only used by the general random-effects path (clmm with several terms
//! and clmm2), which is not ported.
//!
//! Link codes follow ordinal: 1 logit, 2 probit, 3 cloglog, 4 loglog, 5 cauchit.

use std::os::raw::{c_char, c_int};

// The BLAS and the long-double sum mirror what R does, so the objective's
// rounding matches R's: B %*% v goes through dgemv in the system BLAS that R
// uses here (OpenBLAS), and sum(log(x)) accumulates in long double.
#[link(name = "blas")]
unsafe extern "C" {
    fn dgemv_(
        trans: *const c_char,
        m: *const c_int,
        n: *const c_int,
        alpha: *const f64,
        a: *const f64,
        lda: *const c_int,
        x: *const f64,
        incx: *const c_int,
        beta: *const f64,
        y: *mut f64,
        incy: *const c_int,
        trans_len: usize,
    );
}

#[link(name = "lapack")]
unsafe extern "C" {
    fn dsyevr_(
        jobz: *const c_char,
        range: *const c_char,
        uplo: *const c_char,
        n: *const c_int,
        a: *mut f64,
        lda: *const c_int,
        vl: *const f64,
        vu: *const f64,
        il: *const c_int,
        iu: *const c_int,
        abstol: *const f64,
        m: *mut c_int,
        w: *mut f64,
        z: *mut f64,
        ldz: *const c_int,
        isuppz: *mut c_int,
        work: *mut f64,
        lwork: *const c_int,
        iwork: *mut c_int,
        liwork: *const c_int,
        info: *mut c_int,
        jobz_len: usize,
        range_len: usize,
        uplo_len: usize,
    );
}

unsafe extern "C" {
    fn ordinal_sum_log(x: *const f64, n: c_int) -> f64;
}

#[allow(non_snake_case, dead_code)]
unsafe extern "C" {
    fn NRalgv3(
        trace: *mut c_int,
        maxIter: *mut c_int,
        gradTol: *mut f64,
        maxLineIter: *mut c_int,
        grFac: *mut c_int,
        stDev: *mut f64,
        o1: *mut f64,
        o2: *mut f64,
        eta1Fix: *mut f64,
        eta2Fix: *mut f64,
        sigma: *mut f64,
        link: *mut c_int,
        weights: *mut f64,
        u: *mut f64,
        pr: *mut f64,
        funValue: *mut f64,
        gradValues: *mut f64,
        hessValues: *mut f64,
        nx: *mut c_int,
        nu: *mut c_int,
        maxGrad: *mut f64,
        conv: *mut c_int,
        lambda: *mut f64,
        Niter: *mut c_int,
    );

    fn getNAGQ(
        nll: *mut f64,
        grFac: *mut c_int,
        stDev: *mut f64,
        eta1Fix: *mut f64,
        eta2Fix: *mut f64,
        o1: *mut f64,
        o2: *mut f64,
        Sigma: *mut f64,
        weights: *mut f64,
        nx: *mut c_int,
        nu: *mut c_int,
        ghqns: *mut f64,
        lghqws: *mut f64,
        ghqns2: *mut f64,
        u: *mut f64,
        D: *mut f64,
        nAGQ: *mut c_int,
        link: *mut c_int,
        lambda: *mut f64,
    );

    fn getNGHQ_C(
        nll: *mut f64,
        grFac: *mut c_int,
        stDev: *mut f64,
        eta1Fix: *mut f64,
        eta2Fix: *mut f64,
        o1: *mut f64,
        o2: *mut f64,
        Sigma: *mut f64,
        weights: *mut f64,
        nx: *mut c_int,
        nu: *mut c_int,
        ghqns: *mut f64,
        lghqws: *mut f64,
        nGHQ: *mut c_int,
        link: *mut c_int,
        ns: *mut f64,
        lambda: *mut f64,
    );

    #[link_name = "nll"]
    fn ordinal_nll(
        u: *mut f64,
        nu: *mut c_int,
        grFac: *mut c_int,
        stDev: *mut f64,
        o1: *mut f64,
        o2: *mut f64,
        no: *mut c_int,
        eta1: *mut f64,
        eta2: *mut f64,
        eta1Fix: *mut f64,
        eta2Fix: *mut f64,
        sigma: *mut f64,
        pr: *mut f64,
        weights: *mut f64,
        lambda: *mut f64,
        link: *mut c_int,
        nll: *mut f64,
    );
}

/// Outputs of `NRalgv3`, in the order the Python binding returns them.
#[derive(Debug, Clone)]
pub struct NrOut {
    pub u: Vec<f64>,
    pub fitted: Vec<f64>,
    pub fun_value: f64,
    pub grad: Vec<f64>,
    pub hess: Vec<f64>,
    pub max_grad: f64,
    pub conv: i32,
    pub niter: i32,
}

/// `B %*% v` for a column-major `nrow` x `ncol` matrix, as R computes it (dgemv).
pub fn matvec(b_colmajor: &[f64], nrow: usize, ncol: usize, v: &[f64]) -> Result<Vec<f64>, String> {
    check_len("matrix", b_colmajor.len(), nrow * ncol)?;
    check_len("vector", v.len(), ncol)?;
    let mut y = vec![0.0f64; nrow];
    let mut a = b_colmajor.to_vec();
    let mut x = v.to_vec();
    let trans = b"N";
    let (m, n, lda, one_i) = (nrow as c_int, ncol as c_int, nrow.max(1) as c_int, 1 as c_int);
    let (alpha, beta) = (1.0f64, 0.0f64);
    if nrow == 0 || ncol == 0 {
        return Ok(y);
    }
    // SAFETY: a has nrow*ncol elements, x has ncol, y has nrow; dgemv reads
    // within those bounds with unit increments.
    unsafe {
        dgemv_(
            trans.as_ptr() as *const c_char,
            &m,
            &n,
            &alpha,
            a.as_mut_ptr(),
            &lda,
            x.as_mut_ptr(),
            &one_i,
            &beta,
            y.as_mut_ptr(),
            &one_i,
            1,
        );
    }
    Ok(y)
}

/// `eigen(A, symmetric = TRUE)` as R's La_rs computes it: dsyevr with jobz V, range A,
/// uplo L. Returns the eigenvalues in ascending order and the eigenvectors column-major.
pub fn eigen_sym(a_colmajor: &[f64], n: usize) -> Result<(Vec<f64>, Vec<f64>), String> {
    check_len("A", a_colmajor.len(), n * n)?;
    if n == 0 {
        return Ok((Vec::new(), Vec::new()));
    }
    let jobz = b"V";
    let range = b"A";
    let uplo = b"L";
    let nn = n as c_int;
    let mut a = a_colmajor.to_vec();
    let (vl, vu, il, iu, abstol) = (0.0f64, 0.0f64, 0 as c_int, 0 as c_int, 0.0f64);
    let mut m: c_int = 0;
    let mut w = vec![0.0f64; n];
    let mut z = vec![0.0f64; n * n];
    let mut isuppz = vec![0 as c_int; 2 * n];
    let mut info: c_int = 0;
    let mut tmp = [0.0f64; 1];
    let mut itmp = [0 as c_int; 1];
    let query: c_int = -1;
    // SAFETY: buffers are sized per the LAPACK dsyevr contract (workspace query first).
    unsafe {
        dsyevr_(
            jobz.as_ptr() as *const c_char,
            range.as_ptr() as *const c_char,
            uplo.as_ptr() as *const c_char,
            &nn,
            a.as_mut_ptr(),
            &nn,
            &vl,
            &vu,
            &il,
            &iu,
            &abstol,
            &mut m,
            w.as_mut_ptr(),
            z.as_mut_ptr(),
            &nn,
            isuppz.as_mut_ptr(),
            tmp.as_mut_ptr(),
            &query,
            itmp.as_mut_ptr(),
            &query,
            &mut info,
            1,
            1,
            1,
        );
    }
    let lwork = tmp[0] as c_int;
    let liwork = itmp[0];
    let mut work = vec![0.0f64; lwork.max(1) as usize];
    let mut iwork = vec![0 as c_int; liwork.max(1) as usize];
    // SAFETY: work and iwork have the sizes the query returned.
    unsafe {
        dsyevr_(
            jobz.as_ptr() as *const c_char,
            range.as_ptr() as *const c_char,
            uplo.as_ptr() as *const c_char,
            &nn,
            a.as_mut_ptr(),
            &nn,
            &vl,
            &vu,
            &il,
            &iu,
            &abstol,
            &mut m,
            w.as_mut_ptr(),
            z.as_mut_ptr(),
            &nn,
            isuppz.as_mut_ptr(),
            work.as_mut_ptr(),
            &lwork,
            iwork.as_mut_ptr(),
            &liwork,
            &mut info,
            1,
            1,
            1,
        );
    }
    if info != 0 {
        return Err(format!("dsyevr failed with info {info}"));
    }
    Ok((w, z))
}

/// R's `sum(log(x))`: log in double, sum in long double.
pub fn sum_log(x: &[f64]) -> f64 {
    // SAFETY: x is a valid slice of length x.len().
    unsafe { ordinal_sum_log(x.as_ptr(), x.len() as c_int) }
}

fn check_len(name: &str, got: usize, want: usize) -> Result<(), String> {
    if got != want {
        Err(format!("{name} has length {got}, expected {want}"))
    } else {
        Ok(())
    }
}

fn check_link(link: i32) -> Result<(), String> {
    if (1..=5).contains(&link) {
        Ok(())
    } else {
        Err(format!("link code {link} is not one of 1..5 (logit, probit, cloglog, loglog, cauchit)"))
    }
}

fn check_groups(gr_fac: &[i32], nu: usize) -> Result<(), String> {
    for &g in gr_fac {
        if g < 1 || g as usize > nu {
            return Err(format!("grouping code {g} outside 1..{nu}"));
        }
    }
    Ok(())
}

/// Inner Newton-Raphson for the random-effect modes (`NRalgv3`).
#[allow(clippy::too_many_arguments)]
pub fn nr_inner(
    trace: i32,
    max_iter: i32,
    grad_tol: f64,
    max_line_iter: i32,
    gr_fac: &[i32],
    st_dev: f64,
    o1: &[f64],
    o2: &[f64],
    eta1_fix: &[f64],
    eta2_fix: &[f64],
    sigma: &[f64],
    link: i32,
    weights: &[f64],
    u0: &[f64],
    lambda: f64,
    niter: i32,
) -> Result<NrOut, String> {
    let nx = gr_fac.len();
    let nu = u0.len();
    for (name, v) in [("o1", o1), ("o2", o2), ("eta1Fix", eta1_fix), ("eta2Fix", eta2_fix), ("sigma", sigma), ("weights", weights)] {
        check_len(name, v.len(), nx)?;
    }
    check_link(link)?;
    check_groups(gr_fac, nu)?;

    let mut trace = trace;
    let mut max_iter = max_iter;
    let mut grad_tol = grad_tol;
    let mut max_line_iter = max_line_iter;
    let mut gr_fac: Vec<c_int> = gr_fac.to_vec();
    let mut st_dev = st_dev;
    let mut o1 = o1.to_vec();
    let mut o2 = o2.to_vec();
    let mut eta1_fix = eta1_fix.to_vec();
    let mut eta2_fix = eta2_fix.to_vec();
    let mut sigma = sigma.to_vec();
    let mut link = link;
    let mut weights = weights.to_vec();
    let mut u = u0.to_vec();
    let mut pr = vec![0.0f64; nx];
    let mut fun_value = 0.0f64;
    let mut grad = vec![0.0f64; nu];
    let mut hess = vec![1.0f64; nu];
    let mut nx_c = nx as c_int;
    let mut nu_c = nu as c_int;
    let mut max_grad = 0.0f64;
    let mut conv: c_int = 0;
    let mut lambda = lambda;
    let mut niter = niter;

    // SAFETY: every pointer refers to a live buffer of the length R's .C()
    // call would pass (nx for per-observation arrays, nu for random effects).
    unsafe {
        NRalgv3(
            &mut trace,
            &mut max_iter,
            &mut grad_tol,
            &mut max_line_iter,
            gr_fac.as_mut_ptr(),
            &mut st_dev,
            o1.as_mut_ptr(),
            o2.as_mut_ptr(),
            eta1_fix.as_mut_ptr(),
            eta2_fix.as_mut_ptr(),
            sigma.as_mut_ptr(),
            &mut link,
            weights.as_mut_ptr(),
            u.as_mut_ptr(),
            pr.as_mut_ptr(),
            &mut fun_value,
            grad.as_mut_ptr(),
            hess.as_mut_ptr(),
            &mut nx_c,
            &mut nu_c,
            &mut max_grad,
            &mut conv,
            &mut lambda,
            &mut niter,
        );
    }
    Ok(NrOut {
        u,
        fitted: pr,
        fun_value,
        grad,
        hess,
        max_grad,
        conv,
        niter,
    })
}

/// Adaptive Gauss-Hermite negative log-likelihood (`getNAGQ`).
#[allow(clippy::too_many_arguments)]
pub fn nagq(
    gr_fac: &[i32],
    st_dev: f64,
    eta1_fix: &[f64],
    eta2_fix: &[f64],
    o1: &[f64],
    o2: &[f64],
    sigma: &[f64],
    weights: &[f64],
    ghqns: &[f64],
    lghqws: &[f64],
    ghqns2: &[f64],
    u: &[f64],
    d: &[f64],
    n_agq: i32,
    link: i32,
    lambda: f64,
) -> Result<f64, String> {
    let nx = gr_fac.len();
    let nu = u.len();
    for (name, v) in [("o1", o1), ("o2", o2), ("eta1Fix", eta1_fix), ("eta2Fix", eta2_fix), ("sigma", sigma), ("weights", weights)] {
        check_len(name, v.len(), nx)?;
    }
    check_len("D", d.len(), nu)?;
    check_len("ghqns", ghqns.len(), n_agq.unsigned_abs() as usize)?;
    check_len("lghqws", lghqws.len(), ghqns.len())?;
    check_len("ghqns2", ghqns2.len(), ghqns.len())?;
    check_link(link)?;
    check_groups(gr_fac, nu)?;

    let mut out = 0.0f64;
    let mut gr_fac: Vec<c_int> = gr_fac.to_vec();
    let mut st_dev = st_dev;
    let mut eta1_fix = eta1_fix.to_vec();
    let mut eta2_fix = eta2_fix.to_vec();
    let mut o1 = o1.to_vec();
    let mut o2 = o2.to_vec();
    let mut sigma = sigma.to_vec();
    let mut weights = weights.to_vec();
    let mut nx_c = nx as c_int;
    let mut nu_c = nu as c_int;
    let mut ghqns = ghqns.to_vec();
    let mut lghqws = lghqws.to_vec();
    let mut ghqns2 = ghqns2.to_vec();
    let mut u = u.to_vec();
    let mut d = d.to_vec();
    let mut n_agq = n_agq.abs();
    let mut link = link;
    let mut lambda = lambda;
    // SAFETY: buffers are sized as getNAGQ expects (see its comment in utilityFuns.c).
    unsafe {
        getNAGQ(
            &mut out,
            gr_fac.as_mut_ptr(),
            &mut st_dev,
            eta1_fix.as_mut_ptr(),
            eta2_fix.as_mut_ptr(),
            o1.as_mut_ptr(),
            o2.as_mut_ptr(),
            sigma.as_mut_ptr(),
            weights.as_mut_ptr(),
            &mut nx_c,
            &mut nu_c,
            ghqns.as_mut_ptr(),
            lghqws.as_mut_ptr(),
            ghqns2.as_mut_ptr(),
            u.as_mut_ptr(),
            d.as_mut_ptr(),
            &mut n_agq,
            &mut link,
            &mut lambda,
        );
    }
    Ok(out)
}

/// Standard Gauss-Hermite negative log-likelihood (`getNGHQ_C`).
/// `lghqws` holds `log(w) + x^2/2`, as R's getNGHQ.ssr passes it.
#[allow(clippy::too_many_arguments)]
pub fn ghq(
    gr_fac: &[i32],
    st_dev: f64,
    eta1_fix: &[f64],
    eta2_fix: &[f64],
    o1: &[f64],
    o2: &[f64],
    sigma: &[f64],
    weights: &[f64],
    nu: usize,
    ghqns: &[f64],
    lghqws: &[f64],
    n_ghq: i32,
    link: i32,
    ns: &[f64],
    lambda: f64,
) -> Result<f64, String> {
    let nx = gr_fac.len();
    for (name, v) in [("o1", o1), ("o2", o2), ("eta1Fix", eta1_fix), ("eta2Fix", eta2_fix), ("sigma", sigma), ("weights", weights)] {
        check_len(name, v.len(), nx)?;
    }
    let nq = n_ghq.unsigned_abs() as usize;
    check_len("ghqns", ghqns.len(), nq)?;
    check_len("lghqws", lghqws.len(), nq)?;
    check_len("ns", ns.len(), nq)?;
    check_link(link)?;
    check_groups(gr_fac, nu)?;

    let mut out = 0.0f64;
    let mut gr_fac: Vec<c_int> = gr_fac.to_vec();
    let mut st_dev = st_dev;
    let mut eta1_fix = eta1_fix.to_vec();
    let mut eta2_fix = eta2_fix.to_vec();
    let mut o1 = o1.to_vec();
    let mut o2 = o2.to_vec();
    let mut sigma = sigma.to_vec();
    let mut weights = weights.to_vec();
    let mut nx_c = nx as c_int;
    let mut nu_c = nu as c_int;
    let mut ghqns = ghqns.to_vec();
    let mut lghqws = lghqws.to_vec();
    let mut n_ghq = n_ghq.abs();
    let mut link = link;
    let mut ns = ns.to_vec();
    let mut lambda = lambda;
    // SAFETY: buffers are sized as getNGHQ_C expects.
    unsafe {
        getNGHQ_C(
            &mut out,
            gr_fac.as_mut_ptr(),
            &mut st_dev,
            eta1_fix.as_mut_ptr(),
            eta2_fix.as_mut_ptr(),
            o1.as_mut_ptr(),
            o2.as_mut_ptr(),
            sigma.as_mut_ptr(),
            weights.as_mut_ptr(),
            &mut nx_c,
            &mut nu_c,
            ghqns.as_mut_ptr(),
            lghqws.as_mut_ptr(),
            &mut n_ghq,
            &mut link,
            ns.as_mut_ptr(),
            &mut lambda,
        );
    }
    Ok(out)
}

/// Joint negative log-likelihood at given random effects (`nll`).
#[allow(clippy::too_many_arguments)]
pub fn nll_value(
    u: &[f64],
    gr_fac: &[i32],
    st_dev: f64,
    o1: &[f64],
    o2: &[f64],
    eta1_fix: &[f64],
    eta2_fix: &[f64],
    sigma: &[f64],
    weights: &[f64],
    link: i32,
    lambda: f64,
) -> Result<f64, String> {
    let nx = gr_fac.len();
    for (name, v) in [("o1", o1), ("o2", o2), ("eta1Fix", eta1_fix), ("eta2Fix", eta2_fix), ("sigma", sigma), ("weights", weights)] {
        check_len(name, v.len(), nx)?;
    }
    check_link(link)?;
    check_groups(gr_fac, u.len())?;
    let mut u = u.to_vec();
    let mut nu_c = u.len() as c_int;
    let mut gr_fac: Vec<c_int> = gr_fac.to_vec();
    let mut st_dev = st_dev;
    let mut o1 = o1.to_vec();
    let mut o2 = o2.to_vec();
    let mut no = nx as c_int;
    let mut eta1 = vec![0.0f64; nx];
    let mut eta2 = vec![0.0f64; nx];
    let mut eta1_fix = eta1_fix.to_vec();
    let mut eta2_fix = eta2_fix.to_vec();
    let mut sigma = sigma.to_vec();
    let mut pr = vec![0.0f64; nx];
    let mut weights = weights.to_vec();
    let mut lambda = lambda;
    let mut link = link;
    let mut out = 0.0f64;
    // SAFETY: all per-observation buffers have length nx; u has length nu.
    unsafe {
        ordinal_nll(
            u.as_mut_ptr(),
            &mut nu_c,
            gr_fac.as_mut_ptr(),
            &mut st_dev,
            o1.as_mut_ptr(),
            o2.as_mut_ptr(),
            &mut no,
            eta1.as_mut_ptr(),
            eta2.as_mut_ptr(),
            eta1_fix.as_mut_ptr(),
            eta2_fix.as_mut_ptr(),
            sigma.as_mut_ptr(),
            pr.as_mut_ptr(),
            weights.as_mut_ptr(),
            &mut lambda,
            &mut link,
            &mut out,
        );
    }
    Ok(out)
}

#[cfg(feature = "python")]
mod python {
    use super::{eigen_sym, ghq, matvec, nagq, nll_value, nr_inner, sum_log};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    fn to_py(err: String) -> PyErr {
        PyValueError::new_err(err)
    }

    /// nr_inner(trace, max_iter, grad_tol, max_line_iter, gr_fac, st_dev, o1, o2,
    ///          eta1_fix, eta2_fix, sigma, link, weights, u, lambda, niter)
    /// -> (u, fitted, fun_value, grad, hess, max_grad, conv, niter)
    #[pyfunction]
    #[pyo3(name = "nr_inner", signature = (trace, max_iter, grad_tol, max_line_iter, gr_fac, st_dev, o1, o2, eta1_fix, eta2_fix, sigma, link, weights, u, lambda_, niter))]
    #[allow(clippy::too_many_arguments)]
    fn nr_inner_py(
        trace: i32,
        max_iter: i32,
        grad_tol: f64,
        max_line_iter: i32,
        gr_fac: Vec<i32>,
        st_dev: f64,
        o1: Vec<f64>,
        o2: Vec<f64>,
        eta1_fix: Vec<f64>,
        eta2_fix: Vec<f64>,
        sigma: Vec<f64>,
        link: i32,
        weights: Vec<f64>,
        u: Vec<f64>,
        lambda_: f64,
        niter: i32,
    ) -> PyResult<(Vec<f64>, Vec<f64>, f64, Vec<f64>, Vec<f64>, f64, i32, i32)> {
        let out = nr_inner(
            trace, max_iter, grad_tol, max_line_iter, &gr_fac, st_dev, &o1, &o2, &eta1_fix,
            &eta2_fix, &sigma, link, &weights, &u, lambda_, niter,
        )
        .map_err(to_py)?;
        Ok((out.u, out.fitted, out.fun_value, out.grad, out.hess, out.max_grad, out.conv, out.niter))
    }

    /// nagq(gr_fac, st_dev, eta1_fix, eta2_fix, o1, o2, sigma, weights, ghqns, lghqws,
    ///      ghqns2, u, d, n_agq, link, lambda_) -> nll
    #[pyfunction]
    #[pyo3(name = "nagq", signature = (gr_fac, st_dev, eta1_fix, eta2_fix, o1, o2, sigma, weights, ghqns, lghqws, ghqns2, u, d, n_agq, link, lambda_))]
    #[allow(clippy::too_many_arguments)]
    fn nagq_py(
        gr_fac: Vec<i32>,
        st_dev: f64,
        eta1_fix: Vec<f64>,
        eta2_fix: Vec<f64>,
        o1: Vec<f64>,
        o2: Vec<f64>,
        sigma: Vec<f64>,
        weights: Vec<f64>,
        ghqns: Vec<f64>,
        lghqws: Vec<f64>,
        ghqns2: Vec<f64>,
        u: Vec<f64>,
        d: Vec<f64>,
        n_agq: i32,
        link: i32,
        lambda_: f64,
    ) -> PyResult<f64> {
        nagq(
            &gr_fac, st_dev, &eta1_fix, &eta2_fix, &o1, &o2, &sigma, &weights, &ghqns, &lghqws,
            &ghqns2, &u, &d, n_agq, link, lambda_,
        )
        .map_err(to_py)
    }

    /// ghq(gr_fac, st_dev, eta1_fix, eta2_fix, o1, o2, sigma, weights, nu, ghqns, lghqws,
    ///     n_ghq, link, ns, lambda_) -> nll
    #[pyfunction]
    #[pyo3(name = "ghq", signature = (gr_fac, st_dev, eta1_fix, eta2_fix, o1, o2, sigma, weights, nu, ghqns, lghqws, n_ghq, link, ns, lambda_))]
    #[allow(clippy::too_many_arguments)]
    fn ghq_py(
        gr_fac: Vec<i32>,
        st_dev: f64,
        eta1_fix: Vec<f64>,
        eta2_fix: Vec<f64>,
        o1: Vec<f64>,
        o2: Vec<f64>,
        sigma: Vec<f64>,
        weights: Vec<f64>,
        nu: usize,
        ghqns: Vec<f64>,
        lghqws: Vec<f64>,
        n_ghq: i32,
        link: i32,
        ns: Vec<f64>,
        lambda_: f64,
    ) -> PyResult<f64> {
        ghq(
            &gr_fac, st_dev, &eta1_fix, &eta2_fix, &o1, &o2, &sigma, &weights, nu, &ghqns,
            &lghqws, n_ghq, link, &ns, lambda_,
        )
        .map_err(to_py)
    }

    /// nll(u, gr_fac, st_dev, o1, o2, eta1_fix, eta2_fix, sigma, weights, link, lambda_) -> nll
    #[pyfunction]
    #[pyo3(name = "nll", signature = (u, gr_fac, st_dev, o1, o2, eta1_fix, eta2_fix, sigma, weights, link, lambda_))]
    #[allow(clippy::too_many_arguments)]
    fn nll_py(
        u: Vec<f64>,
        gr_fac: Vec<i32>,
        st_dev: f64,
        o1: Vec<f64>,
        o2: Vec<f64>,
        eta1_fix: Vec<f64>,
        eta2_fix: Vec<f64>,
        sigma: Vec<f64>,
        weights: Vec<f64>,
        link: i32,
        lambda_: f64,
    ) -> PyResult<f64> {
        nll_value(&u, &gr_fac, st_dev, &o1, &o2, &eta1_fix, &eta2_fix, &sigma, &weights, link, lambda_)
            .map_err(to_py)
    }

    /// matvec(b_colmajor, nrow, ncol, v) -> B %*% v (dgemv, as R computes it)
    #[pyfunction]
    #[pyo3(name = "matvec", signature = (b_colmajor, nrow, ncol, v))]
    fn matvec_py(b_colmajor: Vec<f64>, nrow: usize, ncol: usize, v: Vec<f64>) -> PyResult<Vec<f64>> {
        matvec(&b_colmajor, nrow, ncol, &v).map_err(to_py)
    }

    /// eigen_sym(a_colmajor, n) -> (values ascending, vectors column-major), as R's eigen()
    #[pyfunction]
    #[pyo3(name = "eigen_sym", signature = (a_colmajor, n))]
    fn eigen_sym_py(a_colmajor: Vec<f64>, n: usize) -> PyResult<(Vec<f64>, Vec<f64>)> {
        eigen_sym(&a_colmajor, n).map_err(to_py)
    }

    /// sum_log(x) -> sum(log(x)) with R's long-double accumulation
    #[pyfunction]
    #[pyo3(name = "sum_log", signature = (x))]
    fn sum_log_py(x: Vec<f64>) -> f64 {
        sum_log(&x)
    }

    #[pymodule]
    #[pyo3(name = "ordinal_clmm")]
    fn ordinal_clmm_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(matvec_py, m)?)?;
        m.add_function(wrap_pyfunction!(eigen_sym_py, m)?)?;
        m.add_function(wrap_pyfunction!(sum_log_py, m)?)?;
        m.add_function(wrap_pyfunction!(nr_inner_py, m)?)?;
        m.add_function(wrap_pyfunction!(nagq_py, m)?)?;
        m.add_function(wrap_pyfunction!(ghq_py, m)?)?;
        m.add_function(wrap_pyfunction!(nll_py, m)?)?;
        Ok(())
    }
}
