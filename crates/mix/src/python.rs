//! pyo3 entry points. Each function takes the arguments of one `.Fortran` call of
//! mix 1.0-13, in the order of the Fortran signature. Integer and double arrays are
//! passed as NumPy arrays that the Python layer has copied into Fortran order, and the
//! Fortran writes into them in place. Scalars are passed by value and given to the
//! Fortran by reference.

use numpy::{PyReadwriteArrayDyn};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use crate::{
    bipf_, ctrsc_, estepm_, ipf_, istepm_, lobsm_, mkpsi_, mstepcm_, mstepm_, pstepcm_,
    pstepm_, rngs_, stvlm_, tobsm_,
};

/// Address of the first element of a Fortran-ordered NumPy array of integers.
fn ip(a: &mut PyReadwriteArrayDyn<'_, i32>) -> PyResult<*mut i32> {
    let mut v = a.as_array_mut();
    if !v.t().is_standard_layout() {
        return Err(PyValueError::new_err(
            "mix_kernel arrays must be Fortran-ordered and contiguous",
        ));
    }
    Ok(v.as_mut_ptr())
}

/// Address of the first element of a Fortran-ordered NumPy array of doubles.
fn fp(a: &mut PyReadwriteArrayDyn<'_, f64>) -> PyResult<*mut f64> {
    let mut v = a.as_array_mut();
    if !v.t().is_standard_layout() {
        return Err(PyValueError::new_err(
            "mix_kernel arrays must be Fortran-ordered and contiguous",
        ));
    }
    Ok(v.as_mut_ptr())
}

/// Sets the Park-Miller seed (`rngs`).
#[pyfunction]
#[pyo3(name = "rngs")]
fn rngs_py(mut seed: i32) {
    unsafe { rngs_(&mut seed) }
}

/// Packed storage index matrix (`mkpsi`). `psi` is (p+1) x (p+1).
#[pyfunction]
#[pyo3(name = "mkpsi")]
fn mkpsi_py(mut p: i32, mut psi: PyReadwriteArrayDyn<'_, i32>) -> PyResult<()> {
    let psi_p = ip(&mut psi)?;
    unsafe { mkpsi_(&mut p, psi_p) };
    Ok(())
}

/// Centers and scales the observed values of each column (`ctrsc`).
#[pyfunction]
#[pyo3(name = "ctrsc")]
fn ctrsc_py(
    mut x: PyReadwriteArrayDyn<'_, f64>,
    mut n: i32,
    mut p: i32,
    mut xbar: PyReadwriteArrayDyn<'_, f64>,
    mut sdv: PyReadwriteArrayDyn<'_, f64>,
    mut mvcode: f64,
) -> PyResult<()> {
    let x_p = fp(&mut x)?;
    let xbar_p = fp(&mut xbar)?;
    let sdv_p = fp(&mut sdv)?;
    unsafe { ctrsc_(x_p, &mut n, &mut p, xbar_p, sdv_p, &mut mvcode) };
    Ok(())
}

/// Tabulates the known part of the sufficient statistics (`tobsm`).
#[pyfunction]
#[pyo3(name = "tobsm")]
fn tobsm_py(
    mut q: i32,
    mut psi: PyReadwriteArrayDyn<'_, i32>,
    mut npsi: i32,
    mut t1: PyReadwriteArrayDyn<'_, f64>,
    mut ncells: i32,
    mut t2: PyReadwriteArrayDyn<'_, f64>,
    mut t3: PyReadwriteArrayDyn<'_, f64>,
    mut npattz: i32,
    mut rz: PyReadwriteArrayDyn<'_, i32>,
    mut mdpzgrp: PyReadwriteArrayDyn<'_, i32>,
    mut npattw: i32,
    mut p: i32,
    mut rw: PyReadwriteArrayDyn<'_, i32>,
    mut mdpwgrp: PyReadwriteArrayDyn<'_, i32>,
    mut ngrp: i32,
    mut mobs: PyReadwriteArrayDyn<'_, i32>,
    mut mobsst: PyReadwriteArrayDyn<'_, i32>,
    mut nmobs: PyReadwriteArrayDyn<'_, i32>,
    mut n: i32,
    mut z: PyReadwriteArrayDyn<'_, f64>,
    mut ocw: PyReadwriteArrayDyn<'_, i32>,
    mut ocz: PyReadwriteArrayDyn<'_, i32>,
) -> PyResult<()> {
    let psi_p = ip(&mut psi)?;
    let t1_p = fp(&mut t1)?;
    let t2_p = fp(&mut t2)?;
    let t3_p = fp(&mut t3)?;
    let rz_p = ip(&mut rz)?;
    let mdpzgrp_p = ip(&mut mdpzgrp)?;
    let rw_p = ip(&mut rw)?;
    let mdpwgrp_p = ip(&mut mdpwgrp)?;
    let mobs_p = ip(&mut mobs)?;
    let mobsst_p = ip(&mut mobsst)?;
    let nmobs_p = ip(&mut nmobs)?;
    let z_p = fp(&mut z)?;
    let ocw_p = ip(&mut ocw)?;
    let ocz_p = ip(&mut ocz)?;
    unsafe {
        tobsm_(
            &mut q, psi_p, &mut npsi, t1_p, &mut ncells, t2_p, t3_p, &mut npattz, rz_p,
            mdpzgrp_p, &mut npattw, &mut p, rw_p, mdpwgrp_p, &mut ngrp, mobs_p, mobsst_p,
            nmobs_p, &mut n, z_p, ocw_p, ocz_p,
        )
    };
    Ok(())
}

/// Starting values, sigma = identity and mu = 0 (`stvlm`).
#[pyfunction]
#[pyo3(name = "stvlm")]
fn stvlm_py(
    mut q: i32,
    mut psi: PyReadwriteArrayDyn<'_, i32>,
    mut npsi: i32,
    mut t1: PyReadwriteArrayDyn<'_, f64>,
    mut ncells: i32,
    mut t2: PyReadwriteArrayDyn<'_, f64>,
) -> PyResult<()> {
    let psi_p = ip(&mut psi)?;
    let t1_p = fp(&mut t1)?;
    let t2_p = fp(&mut t2)?;
    unsafe { stvlm_(&mut q, psi_p, &mut npsi, t1_p, &mut ncells, t2_p) };
    Ok(())
}

/// E-step of EM and ECM (`estepm`).
#[pyfunction]
#[pyo3(name = "estepm")]
fn estepm_py(
    mut q: i32,
    mut psi: PyReadwriteArrayDyn<'_, i32>,
    mut npsi: i32,
    mut ncells: i32,
    mut sigma: PyReadwriteArrayDyn<'_, f64>,
    mut mu: PyReadwriteArrayDyn<'_, f64>,
    mut pii: PyReadwriteArrayDyn<'_, f64>,
    mut kn1: PyReadwriteArrayDyn<'_, f64>,
    mut kn2: PyReadwriteArrayDyn<'_, f64>,
    mut kn3: PyReadwriteArrayDyn<'_, f64>,
    mut t1: PyReadwriteArrayDyn<'_, f64>,
    mut t2: PyReadwriteArrayDyn<'_, f64>,
    mut t3: PyReadwriteArrayDyn<'_, f64>,
    mut npattz: i32,
    mut rz: PyReadwriteArrayDyn<'_, i32>,
    mut mcz: PyReadwriteArrayDyn<'_, i32>,
    mut ocz: PyReadwriteArrayDyn<'_, i32>,
    mut mdpzgrp: PyReadwriteArrayDyn<'_, i32>,
    mut npattw: i32,
    mut p: i32,
    mut rw: PyReadwriteArrayDyn<'_, i32>,
    mut mcw: PyReadwriteArrayDyn<'_, i32>,
    mut mdpwgrp: PyReadwriteArrayDyn<'_, i32>,
    mut ngrp: i32,
    mut mobs: PyReadwriteArrayDyn<'_, i32>,
    mut mobsst: PyReadwriteArrayDyn<'_, i32>,
    mut nmobs: PyReadwriteArrayDyn<'_, i32>,
    mut n: i32,
    mut z: PyReadwriteArrayDyn<'_, f64>,
    mut d: PyReadwriteArrayDyn<'_, i32>,
    mut jmp: PyReadwriteArrayDyn<'_, i32>,
    mut c: PyReadwriteArrayDyn<'_, i32>,
    mut theta: PyReadwriteArrayDyn<'_, f64>,
) -> PyResult<()> {
    let psi_p = ip(&mut psi)?;
    let sigma_p = fp(&mut sigma)?;
    let mu_p = fp(&mut mu)?;
    let pii_p = fp(&mut pii)?;
    let kn1_p = fp(&mut kn1)?;
    let kn2_p = fp(&mut kn2)?;
    let kn3_p = fp(&mut kn3)?;
    let t1_p = fp(&mut t1)?;
    let t2_p = fp(&mut t2)?;
    let t3_p = fp(&mut t3)?;
    let rz_p = ip(&mut rz)?;
    let mcz_p = ip(&mut mcz)?;
    let ocz_p = ip(&mut ocz)?;
    let mdpzgrp_p = ip(&mut mdpzgrp)?;
    let rw_p = ip(&mut rw)?;
    let mcw_p = ip(&mut mcw)?;
    let mdpwgrp_p = ip(&mut mdpwgrp)?;
    let mobs_p = ip(&mut mobs)?;
    let mobsst_p = ip(&mut mobsst)?;
    let nmobs_p = ip(&mut nmobs)?;
    let z_p = fp(&mut z)?;
    let d_p = ip(&mut d)?;
    let jmp_p = ip(&mut jmp)?;
    let c_p = ip(&mut c)?;
    let theta_p = fp(&mut theta)?;
    unsafe {
        estepm_(
            &mut q, psi_p, &mut npsi, &mut ncells, sigma_p, mu_p, pii_p, kn1_p, kn2_p, kn3_p,
            t1_p, t2_p, t3_p, &mut npattz, rz_p, mcz_p, ocz_p, mdpzgrp_p, &mut npattw,
            &mut p, rw_p, mcw_p, mdpwgrp_p, &mut ngrp, mobs_p, mobsst_p, nmobs_p, &mut n,
            z_p, d_p, jmp_p, c_p, theta_p,
        )
    };
    Ok(())
}

/// M-step of EM (`mstepm`).
#[pyfunction]
#[pyo3(name = "mstepm")]
fn mstepm_py(
    mut q: i32,
    mut psi: PyReadwriteArrayDyn<'_, i32>,
    mut npsi: i32,
    mut ncells: i32,
    mut t1: PyReadwriteArrayDyn<'_, f64>,
    mut t2: PyReadwriteArrayDyn<'_, f64>,
    mut t3: PyReadwriteArrayDyn<'_, f64>,
    mut n: i32,
    mut prior: PyReadwriteArrayDyn<'_, f64>,
) -> PyResult<()> {
    let psi_p = ip(&mut psi)?;
    let t1_p = fp(&mut t1)?;
    let t2_p = fp(&mut t2)?;
    let t3_p = fp(&mut t3)?;
    let prior_p = fp(&mut prior)?;
    unsafe {
        mstepm_(
            &mut q, psi_p, &mut npsi, &mut ncells, t1_p, t2_p, t3_p, &mut n, prior_p,
        )
    };
    Ok(())
}

/// One data-augmentation step, the I-step (`istepm`).
#[pyfunction]
#[pyo3(name = "istepm")]
fn istepm_py(
    mut q: i32,
    mut psi: PyReadwriteArrayDyn<'_, i32>,
    mut npsi: i32,
    mut ncells: i32,
    mut sigma: PyReadwriteArrayDyn<'_, f64>,
    mut mu: PyReadwriteArrayDyn<'_, f64>,
    mut pii: PyReadwriteArrayDyn<'_, f64>,
    mut kn1: PyReadwriteArrayDyn<'_, f64>,
    mut kn2: PyReadwriteArrayDyn<'_, f64>,
    mut kn3: PyReadwriteArrayDyn<'_, f64>,
    mut t1: PyReadwriteArrayDyn<'_, f64>,
    mut t2: PyReadwriteArrayDyn<'_, f64>,
    mut t3: PyReadwriteArrayDyn<'_, f64>,
    mut npattz: i32,
    mut rz: PyReadwriteArrayDyn<'_, i32>,
    mut mcz: PyReadwriteArrayDyn<'_, i32>,
    mut ocz: PyReadwriteArrayDyn<'_, i32>,
    mut mdpzgrp: PyReadwriteArrayDyn<'_, i32>,
    mut npattw: i32,
    mut p: i32,
    mut rw: PyReadwriteArrayDyn<'_, i32>,
    mut mcw: PyReadwriteArrayDyn<'_, i32>,
    mut mdpwgrp: PyReadwriteArrayDyn<'_, i32>,
    mut ngrp: i32,
    mut mobs: PyReadwriteArrayDyn<'_, i32>,
    mut mobsst: PyReadwriteArrayDyn<'_, i32>,
    mut nmobs: PyReadwriteArrayDyn<'_, i32>,
    mut n: i32,
    mut z: PyReadwriteArrayDyn<'_, f64>,
    mut d: PyReadwriteArrayDyn<'_, i32>,
    mut jmp: PyReadwriteArrayDyn<'_, i32>,
    mut c: PyReadwriteArrayDyn<'_, i32>,
    mut theta: PyReadwriteArrayDyn<'_, f64>,
    mut chf: PyReadwriteArrayDyn<'_, f64>,
    mut w: PyReadwriteArrayDyn<'_, i32>,
    mut zz: PyReadwriteArrayDyn<'_, f64>,
) -> PyResult<()> {
    let psi_p = ip(&mut psi)?;
    let sigma_p = fp(&mut sigma)?;
    let mu_p = fp(&mut mu)?;
    let pii_p = fp(&mut pii)?;
    let kn1_p = fp(&mut kn1)?;
    let kn2_p = fp(&mut kn2)?;
    let kn3_p = fp(&mut kn3)?;
    let t1_p = fp(&mut t1)?;
    let t2_p = fp(&mut t2)?;
    let t3_p = fp(&mut t3)?;
    let rz_p = ip(&mut rz)?;
    let mcz_p = ip(&mut mcz)?;
    let ocz_p = ip(&mut ocz)?;
    let mdpzgrp_p = ip(&mut mdpzgrp)?;
    let rw_p = ip(&mut rw)?;
    let mcw_p = ip(&mut mcw)?;
    let mdpwgrp_p = ip(&mut mdpwgrp)?;
    let mobs_p = ip(&mut mobs)?;
    let mobsst_p = ip(&mut mobsst)?;
    let nmobs_p = ip(&mut nmobs)?;
    let z_p = fp(&mut z)?;
    let d_p = ip(&mut d)?;
    let jmp_p = ip(&mut jmp)?;
    let c_p = ip(&mut c)?;
    let theta_p = fp(&mut theta)?;
    let chf_p = fp(&mut chf)?;
    let w_p = ip(&mut w)?;
    let zz_p = fp(&mut zz)?;
    unsafe {
        istepm_(
            &mut q, psi_p, &mut npsi, &mut ncells, sigma_p, mu_p, pii_p, kn1_p, kn2_p, kn3_p,
            t1_p, t2_p, t3_p, &mut npattz, rz_p, mcz_p, ocz_p, mdpzgrp_p, &mut npattw,
            &mut p, rw_p, mcw_p, mdpwgrp_p, &mut ngrp, mobs_p, mobsst_p, nmobs_p, &mut n,
            z_p, d_p, jmp_p, c_p, theta_p, chf_p, w_p, zz_p,
        )
    };
    Ok(())
}

/// Draws the complete-data posterior (`pstepm`). `err` is a one-element array and is
/// set to 1 when a non-structural cell is empty.
#[pyfunction]
#[pyo3(name = "pstepm")]
fn pstepm_py(
    mut q: i32,
    mut psi: PyReadwriteArrayDyn<'_, i32>,
    mut npsi: i32,
    mut ncells: i32,
    mut t1: PyReadwriteArrayDyn<'_, f64>,
    mut t2: PyReadwriteArrayDyn<'_, f64>,
    mut t3: PyReadwriteArrayDyn<'_, f64>,
    mut n: i32,
    mut p: i32,
    mut prior: PyReadwriteArrayDyn<'_, f64>,
    mut chf: PyReadwriteArrayDyn<'_, f64>,
    mut mx: PyReadwriteArrayDyn<'_, f64>,
    mut zz: PyReadwriteArrayDyn<'_, f64>,
    mut mcz: PyReadwriteArrayDyn<'_, i32>,
    mut err: PyReadwriteArrayDyn<'_, f64>,
) -> PyResult<()> {
    let psi_p = ip(&mut psi)?;
    let t1_p = fp(&mut t1)?;
    let t2_p = fp(&mut t2)?;
    let t3_p = fp(&mut t3)?;
    let prior_p = fp(&mut prior)?;
    let chf_p = fp(&mut chf)?;
    let mx_p = fp(&mut mx)?;
    let zz_p = fp(&mut zz)?;
    let mcz_p = ip(&mut mcz)?;
    let err_p = fp(&mut err)?;
    unsafe {
        pstepm_(
            &mut q, psi_p, &mut npsi, &mut ncells, t1_p, t2_p, t3_p, &mut n, &mut p,
            prior_p, chf_p, mx_p, zz_p, mcz_p, err_p,
        )
    };
    Ok(())
}

/// Log-likelihood of the observed data at a parameter value (`lobsm`). Returns `ll`.
#[pyfunction]
#[pyo3(name = "lobsm")]
fn lobsm_py(
    mut q: i32,
    mut psi: PyReadwriteArrayDyn<'_, i32>,
    mut npsi: i32,
    mut ncells: i32,
    mut sigma: PyReadwriteArrayDyn<'_, f64>,
    mut mu: PyReadwriteArrayDyn<'_, f64>,
    mut pii: PyReadwriteArrayDyn<'_, f64>,
    mut npattz: i32,
    mut rz: PyReadwriteArrayDyn<'_, i32>,
    mut mcz: PyReadwriteArrayDyn<'_, i32>,
    mut ocz: PyReadwriteArrayDyn<'_, i32>,
    mut mdpzgrp: PyReadwriteArrayDyn<'_, i32>,
    mut npattw: i32,
    mut p: i32,
    mut rw: PyReadwriteArrayDyn<'_, i32>,
    mut mcw: PyReadwriteArrayDyn<'_, i32>,
    mut mdpwgrp: PyReadwriteArrayDyn<'_, i32>,
    mut ngrp: i32,
    mut mobs: PyReadwriteArrayDyn<'_, i32>,
    mut mobsst: PyReadwriteArrayDyn<'_, i32>,
    mut nmobs: PyReadwriteArrayDyn<'_, i32>,
    mut n: i32,
    mut z: PyReadwriteArrayDyn<'_, f64>,
    mut d: PyReadwriteArrayDyn<'_, i32>,
    mut jmp: PyReadwriteArrayDyn<'_, i32>,
    mut c: PyReadwriteArrayDyn<'_, i32>,
) -> PyResult<f64> {
    let psi_p = ip(&mut psi)?;
    let sigma_p = fp(&mut sigma)?;
    let mu_p = fp(&mut mu)?;
    let pii_p = fp(&mut pii)?;
    let rz_p = ip(&mut rz)?;
    let mcz_p = ip(&mut mcz)?;
    let ocz_p = ip(&mut ocz)?;
    let mdpzgrp_p = ip(&mut mdpzgrp)?;
    let rw_p = ip(&mut rw)?;
    let mcw_p = ip(&mut mcw)?;
    let mdpwgrp_p = ip(&mut mdpwgrp)?;
    let mobs_p = ip(&mut mobs)?;
    let mobsst_p = ip(&mut mobsst)?;
    let nmobs_p = ip(&mut nmobs)?;
    let z_p = fp(&mut z)?;
    let d_p = ip(&mut d)?;
    let jmp_p = ip(&mut jmp)?;
    let c_p = ip(&mut c)?;
    let mut ll = 0.0_f64;
    unsafe {
        lobsm_(
            &mut q, psi_p, &mut npsi, &mut ncells, sigma_p, mu_p, pii_p, &mut npattz, rz_p,
            mcz_p, ocz_p, mdpzgrp_p, &mut npattw, &mut p, rw_p, mcw_p, mdpwgrp_p, &mut ngrp,
            mobs_p, mobsst_p, nmobs_p, &mut n, z_p, d_p, jmp_p, c_p, &mut ll,
        )
    };
    Ok(ll)
}

/// Least-squares fit of the regression of the cell means on the design, and the
/// ECM M-step (`mstepcm`). Sets `sigma` and `mu`.
#[pyfunction]
#[pyo3(name = "mstepcm")]
fn mstepcm_py(
    mut q: i32,
    mut psi: PyReadwriteArrayDyn<'_, i32>,
    mut npsi: i32,
    mut ncells: i32,
    mut t1: PyReadwriteArrayDyn<'_, f64>,
    mut t2: PyReadwriteArrayDyn<'_, f64>,
    mut t3: PyReadwriteArrayDyn<'_, f64>,
    mut sigma: PyReadwriteArrayDyn<'_, f64>,
    mut mu: PyReadwriteArrayDyn<'_, f64>,
    mut n: i32,
    mut r: i32,
    mut design: PyReadwriteArrayDyn<'_, f64>,
    mut wk: PyReadwriteArrayDyn<'_, f64>,
    mut mcr: PyReadwriteArrayDyn<'_, i32>,
    mut psir: PyReadwriteArrayDyn<'_, i32>,
    mut npsir: i32,
    mut wkr: PyReadwriteArrayDyn<'_, f64>,
    mut wkd: PyReadwriteArrayDyn<'_, f64>,
    mut beta: PyReadwriteArrayDyn<'_, f64>,
) -> PyResult<()> {
    let psi_p = ip(&mut psi)?;
    let t1_p = fp(&mut t1)?;
    let t2_p = fp(&mut t2)?;
    let t3_p = fp(&mut t3)?;
    let sigma_p = fp(&mut sigma)?;
    let mu_p = fp(&mut mu)?;
    let design_p = fp(&mut design)?;
    let wk_p = fp(&mut wk)?;
    let mcr_p = ip(&mut mcr)?;
    let psir_p = ip(&mut psir)?;
    let wkr_p = fp(&mut wkr)?;
    let wkd_p = fp(&mut wkd)?;
    let beta_p = fp(&mut beta)?;
    unsafe {
        mstepcm_(
            &mut q, psi_p, &mut npsi, &mut ncells, t1_p, t2_p, t3_p, sigma_p, mu_p, &mut n,
            &mut r, design_p, wk_p, mcr_p, psir_p, &mut npsir, wkr_p, wkd_p, beta_p,
        )
    };
    Ok(())
}

/// One Iterative Proportional Fitting cycle over the margins (`ipf`). Sets `fit`.
#[pyfunction]
#[pyo3(name = "ipf")]
fn ipf_py(
    mut ncells: i32,
    mut table: PyReadwriteArrayDyn<'_, f64>,
    mut fit: PyReadwriteArrayDyn<'_, f64>,
    mut ncon: i32,
    mut con: PyReadwriteArrayDyn<'_, i32>,
    mut p: i32,
    mut d: PyReadwriteArrayDyn<'_, i32>,
    mut jmp: PyReadwriteArrayDyn<'_, i32>,
    mut c: PyReadwriteArrayDyn<'_, i32>,
    mut marg: PyReadwriteArrayDyn<'_, i32>,
    mut rest: PyReadwriteArrayDyn<'_, i32>,
    mut eps: f64,
) -> PyResult<()> {
    let table_p = fp(&mut table)?;
    let fit_p = fp(&mut fit)?;
    let con_p = ip(&mut con)?;
    let d_p = ip(&mut d)?;
    let jmp_p = ip(&mut jmp)?;
    let c_p = ip(&mut c)?;
    let marg_p = ip(&mut marg)?;
    let rest_p = ip(&mut rest)?;
    unsafe {
        ipf_(
            &mut ncells, table_p, fit_p, &mut ncon, con_p, &mut p, d_p, jmp_p, c_p, marg_p,
            rest_p, &mut eps,
        )
    };
    Ok(())
}

/// Draws the complete-data posterior (`pstepcm`). Sets `sigma` and `mu`. The t1 array
/// is overwritten in the Fortran, so the caller passes a copy.
#[pyfunction]
#[pyo3(name = "pstepcm")]
fn pstepcm_py(
    mut q: i32,
    mut psi: PyReadwriteArrayDyn<'_, i32>,
    mut npsi: i32,
    mut ncells: i32,
    mut t1: PyReadwriteArrayDyn<'_, f64>,
    mut t2: PyReadwriteArrayDyn<'_, f64>,
    mut t3: PyReadwriteArrayDyn<'_, f64>,
    mut sigma: PyReadwriteArrayDyn<'_, f64>,
    mut mu: PyReadwriteArrayDyn<'_, f64>,
    mut n: i32,
    mut r: i32,
    mut design: PyReadwriteArrayDyn<'_, f64>,
    mut wk: PyReadwriteArrayDyn<'_, f64>,
    mut mcr: PyReadwriteArrayDyn<'_, i32>,
    mut psir: PyReadwriteArrayDyn<'_, i32>,
    mut npsir: i32,
    mut wkr: PyReadwriteArrayDyn<'_, f64>,
    mut wkd: PyReadwriteArrayDyn<'_, f64>,
    mut mcz: PyReadwriteArrayDyn<'_, i32>,
    mut chf: PyReadwriteArrayDyn<'_, f64>,
    mut beta: PyReadwriteArrayDyn<'_, f64>,
    mut mx: PyReadwriteArrayDyn<'_, f64>,
) -> PyResult<()> {
    let psi_p = ip(&mut psi)?;
    let t1_p = fp(&mut t1)?;
    let t2_p = fp(&mut t2)?;
    let t3_p = fp(&mut t3)?;
    let sigma_p = fp(&mut sigma)?;
    let mu_p = fp(&mut mu)?;
    let design_p = fp(&mut design)?;
    let wk_p = fp(&mut wk)?;
    let mcr_p = ip(&mut mcr)?;
    let psir_p = ip(&mut psir)?;
    let wkr_p = fp(&mut wkr)?;
    let wkd_p = fp(&mut wkd)?;
    let mcz_p = ip(&mut mcz)?;
    let chf_p = fp(&mut chf)?;
    let beta_p = fp(&mut beta)?;
    let mx_p = fp(&mut mx)?;
    unsafe {
        pstepcm_(
            &mut q, psi_p, &mut npsi, &mut ncells, t1_p, t2_p, t3_p, sigma_p, mu_p, &mut n,
            &mut r, design_p, wk_p, mcr_p, psir_p, &mut npsir, wkr_p, wkd_p, mcz_p, chf_p,
            beta_p, mx_p,
        )
    };
    Ok(())
}

/// One cycle of Bayesian IPF (`bipf`). Sets `theta` and returns the error flag.
#[pyfunction]
#[pyo3(name = "bipf")]
fn bipf_py(
    mut ncells: i32,
    mut table: PyReadwriteArrayDyn<'_, f64>,
    mut theta: PyReadwriteArrayDyn<'_, f64>,
    mut prior: PyReadwriteArrayDyn<'_, f64>,
    mut ncon: i32,
    mut con: PyReadwriteArrayDyn<'_, i32>,
    mut p: i32,
    mut d: PyReadwriteArrayDyn<'_, i32>,
    mut jmp: PyReadwriteArrayDyn<'_, i32>,
    mut c: PyReadwriteArrayDyn<'_, i32>,
    mut marg: PyReadwriteArrayDyn<'_, i32>,
    mut rest: PyReadwriteArrayDyn<'_, i32>,
    mut err: PyReadwriteArrayDyn<'_, i32>,
) -> PyResult<()> {
    let table_p = fp(&mut table)?;
    let theta_p = fp(&mut theta)?;
    let prior_p = fp(&mut prior)?;
    let con_p = ip(&mut con)?;
    let d_p = ip(&mut d)?;
    let jmp_p = ip(&mut jmp)?;
    let c_p = ip(&mut c)?;
    let marg_p = ip(&mut marg)?;
    let rest_p = ip(&mut rest)?;
    let err_p = ip(&mut err)?;
    unsafe {
        bipf_(
            &mut ncells, table_p, theta_p, prior_p, &mut ncon, con_p, &mut p, d_p, jmp_p,
            c_p, marg_p, rest_p, err_p,
        )
    };
    Ok(())
}

#[pymodule]
#[pyo3(name = "mix_kernel")]
fn mix_kernel_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(rngs_py, m)?)?;
    m.add_function(wrap_pyfunction!(mkpsi_py, m)?)?;
    m.add_function(wrap_pyfunction!(ctrsc_py, m)?)?;
    m.add_function(wrap_pyfunction!(tobsm_py, m)?)?;
    m.add_function(wrap_pyfunction!(stvlm_py, m)?)?;
    m.add_function(wrap_pyfunction!(estepm_py, m)?)?;
    m.add_function(wrap_pyfunction!(mstepm_py, m)?)?;
    m.add_function(wrap_pyfunction!(istepm_py, m)?)?;
    m.add_function(wrap_pyfunction!(pstepm_py, m)?)?;
    m.add_function(wrap_pyfunction!(lobsm_py, m)?)?;
    m.add_function(wrap_pyfunction!(mstepcm_py, m)?)?;
    m.add_function(wrap_pyfunction!(ipf_py, m)?)?;
    m.add_function(wrap_pyfunction!(pstepcm_py, m)?)?;
    m.add_function(wrap_pyfunction!(bipf_py, m)?)?;
    Ok(())
}
