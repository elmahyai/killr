"""Binding of the quantreg kernels in crates/quantreg (quantreg_kernel).

The kernels are the Rust port of rqfnb, pfnb, pwxy and bootnp from quantreg 6.1.
Each wrapper takes the arguments that the R `.Fortran` or `.C` call takes, minus
the scratch arrays that the Rust side allocates itself. The wrappers take the
Fortran layouts: a design is n x p, one row per observation.

The kernels draw from R's Mersenne-Twister. boot.rng holds the same generator,
so each draw reads its state from boot.rng and writes the advanced state back.
The R stream therefore continues across calls, as it does in an R session.
"""

from __future__ import annotations

import numpy as np

import quantreg_kernel as _k

_BETA = 0.99995


def _rng_state():
    from boot import rng

    return list(rng._mt), int(rng._mti)


def _store_rng_state(mt, mti):
    from boot import rng

    rng._mt[:] = mt
    rng._mti = int(mti)


def _design(x):
    design = np.ascontiguousarray(np.asarray(x, dtype=float))
    if design.ndim == 1:
        design = design.reshape(-1, 1)
    return design


def fnb(x, y, tau, rhs=None, beta=_BETA, eps=1e-6):
    """rq.fit.fnb: the coefficient, the counters, and the info of the Frisch-Newton kernel."""
    design = _design(x)
    response = np.ascontiguousarray(np.asarray(y, dtype=float).reshape(-1))
    n, p = design.shape
    if response.shape[0] != n:
        raise ValueError("x and y don't match n")
    tau = float(tau)
    if tau < eps or tau > 1.0 - eps:
        raise ValueError("No parametric Frisch-Newton method.  Set tau in (0,1)")
    if rhs is None:
        rhs = (1.0 - tau) * design.sum(axis=0)
    rhs = np.ascontiguousarray(np.asarray(rhs, dtype=float).reshape(-1))
    ones = np.ones(n)
    start = np.full(n, 1.0 - tau)
    dual, nit, info = _k.rqfnb(design, -response, rhs, ones, start, float(beta), float(eps))
    return {"coefficients": -dual, "nit": nit, "info": int(info)}


def pfnb(x, y, tau, residuals, band, m0):
    """pfnb over every tau. Returns the duals (p x m), nit (5 x m), and the info flag."""
    design = _design(x)
    response = np.ascontiguousarray(np.asarray(y, dtype=float).reshape(-1))
    taus = np.ascontiguousarray(np.asarray(tau, dtype=float).reshape(-1))
    resid = np.ascontiguousarray(np.asarray(residuals, dtype=float).reshape(-1))
    scale = np.ascontiguousarray(np.asarray(band, dtype=float).reshape(-1))
    duals, nit, info = _k.pfnb(design, response, taus, resid, scale, int(m0))
    return duals, nit, int(info)


def pwxy(x, y, tau, residuals, m0, reps):
    """pwxy over reps replicates. x, y and residuals are already sorted by the scaled residual."""
    design = _design(x)
    response = np.ascontiguousarray(np.asarray(y, dtype=float).reshape(-1))
    resid = np.ascontiguousarray(np.asarray(residuals, dtype=float).reshape(-1))
    mt, mti = _rng_state()
    duals, nit, info, mt, mti = _k.pwxy(design, response, float(tau), resid, int(m0), int(reps), mt, mti)
    _store_rng_state(mt, mti)
    return duals, nit, np.asarray(info, dtype=int)


def bootnp(x, y, tau, theta_tilde, zstar, sumxij, sumabsxij, reps):
    """bootnp. zstar is ZTilda as an n x p array. Returns theta (p x (reps + 1))."""
    design = _design(x)
    response = np.ascontiguousarray(np.asarray(y, dtype=float).reshape(-1))
    z_flat = np.asfortranarray(np.asarray(zstar, dtype=float)).ravel(order="F")
    mt, mti = _rng_state()
    theta, mt, mti = _k.bootnp(
        design,
        response,
        float(tau),
        np.ascontiguousarray(np.asarray(theta_tilde, dtype=float).reshape(-1)),
        np.ascontiguousarray(z_flat),
        np.ascontiguousarray(np.asarray(sumxij, dtype=float).reshape(-1)),
        np.ascontiguousarray(np.asarray(sumabsxij, dtype=float).reshape(-1)),
        int(reps),
        mt,
        mti,
    )
    _store_rng_state(mt, mti)
    return theta
