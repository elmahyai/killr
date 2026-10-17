"""Fit of a survreg model without penalized terms (survival::survreg.fit).

The Newton-Raphson loop and the derivatives run in the survreg6 crate, which
is the Csurvreg6 kernel. Only the built-in distributions are in scope: extreme
value, logistic, and Gaussian (dnum 1, 2, and 3). Distributions whose R name is
not one of those three use R's density callback (dnum 4), which the crate does
not include.

Arrays are column-major inside the kernel, the same as R's as.double(). The
return value is a dict with the R list field names. Named vectors are returned
as plain arrays; R's names are not carried.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
from survreg6 import survreg6

from survival.control import survreg_control
from survival.survreg_distributions import survreg_distributions
from survival.wtest import coxph_wtest

_BUILT_IN = {"Extreme value": 1, "Logistic": 2, "Gaussian": 3}


def _f64(values: Any) -> np.ndarray:
    return np.ascontiguousarray(values, dtype=np.float64)


def _i32(values: Any) -> np.ndarray:
    return np.ascontiguousarray(values, dtype=np.int32)


def _resolve_dist(dist: Any) -> tuple[dict[str, Any], int]:
    """Return the distribution list and its dnum, as survreg.fit does."""
    if isinstance(dist, str):
        sd = survreg_distributions.get(dist)
        if sd is None:
            raise ValueError("Unrecognized distribution")
    else:
        sd = dist
    if not callable(sd.get("density")):
        raise ValueError("Missing density function in the definition of the distribution")
    dnum = _BUILT_IN.get(sd.get("name"))
    if dnum is None:
        raise NotImplementedError(
            f"distribution {sd.get('name')!r} needs the R density callback (dnum 4), "
            "which the survreg6 crate does not include"
        )
    return sd, dnum


def _derfun(y: np.ndarray, eta: Any, sigma: Any, density: Any, parms: Any):
    """First and second derivatives at the starting values, for each censoring type."""
    ny = y.shape[1]
    status = y[:, ny - 1]
    z = (y[:, 0] - eta) / sigma
    dmat = np.asarray(density(z, parms), dtype=float)
    dtemp = dmat[:, 2] * dmat[:, 3]
    if np.any(status == 3):
        z2 = (y[:, 1] - eta) / sigma
        dmat2 = np.asarray(density(z2, parms), dtype=float)
    else:
        dmat2 = np.zeros((1, 5))

    s0 = (status == 0).astype(float)
    s1 = (status == 1).astype(float)
    s2 = (status == 2).astype(float)
    s3 = (status == 3).astype(float)

    tdenom = (
        s0 * dmat[:, 1]
        + s1 * 1.0
        + s2 * dmat[:, 0]
        + s3 * np.where(z > 0, dmat[:, 1] - dmat2[:, 1], dmat2[:, 0] - dmat[:, 0])
    )
    tdenom = 1.0 / (tdenom * sigma)
    dg = -tdenom * (
        s0 * (0.0 - dmat[:, 2])
        + s1 * dmat[:, 3]
        + s2 * dmat[:, 2]
        + s3 * (dmat2[:, 2] - dmat[:, 2])
    )
    ddg = (tdenom / sigma) * (
        s0 * (0.0 - dtemp)
        + s1 * dmat[:, 4]
        + s2 * dtemp
        + s3 * (dmat2[:, 2] * dmat2[:, 3] - dtemp)
    )
    return dg, ddg - dg * dg


def _kernel(maxiter, nvar, y, ny, x, wt, offset, beta, nstrat, strata, eps, tol, dnum):
    coef, iter_, var, loglik, flag, u = survreg6(
        int(maxiter),
        int(nvar),
        _f64(y.ravel(order="F")),
        int(ny),
        _f64(x.ravel(order="F")),
        _f64(wt),
        _f64(offset),
        _f64(beta),
        int(nstrat),
        _i32(strata),
        float(eps),
        float(tol),
        int(dnum),
    )
    return {
        "coef": np.asarray(coef, dtype=float),
        "iter": int(iter_),
        "var": np.asarray(var, dtype=float),
        "loglik": float(loglik),
        "flag": int(flag),
        "u": np.asarray(u, dtype=float),
    }


def survreg_fit(
    x,
    y,
    weights=None,
    offset=None,
    init=None,
    controlvals=None,
    dist="extreme",
    scale=0,
    nstrat=1,
    strata=None,
    parms=None,
    assign=None,
):
    """Fit a survreg model for the matrix ``x`` and response matrix ``y``.

    ``y`` has two columns (time, status) or three (time1, time2, status), as in
    ``Surv``. ``dist`` is a distribution name in ``survreg_distributions`` or a
    distribution dict. ``scale > 0`` fixes the scale, and ``nstrat`` gives the
    number of scales to estimate. ``controlvals`` comes from ``survreg_control``.
    """
    del assign  # R accepts it and never reads it.
    if controlvals is None:
        controlvals = survreg_control()
    iter_max = controlvals["iter.max"]
    eps = controlvals["rel.tolerance"]
    toler_chol = controlvals["toler.chol"]

    x = np.array(x, dtype=float, copy=True)
    if x.ndim != 2:
        raise ValueError("Invalid X matrix ")
    n, nvar = x.shape
    y = np.asarray(y, dtype=float)
    if y.ndim != 2:
        raise ValueError("y must be a matrix")
    ny = y.shape[1]
    if ny < 2:
        raise ValueError("y must have a time and a status column")

    if offset is None:
        offset = np.zeros(n)
    else:
        offset = np.asarray(offset, dtype=float)
    if weights is None:
        weights = np.ones(n)
    else:
        weights = np.asarray(weights, dtype=float)
        if np.any(weights <= 0):
            raise ValueError("Invalid weights, must be >0")

    if scale < 0:
        raise ValueError("Invalid scale")
    if scale > 0 and nstrat > 1:
        raise ValueError("Cannot have both a fixed scale and strata")
    if nstrat > 1 and (strata is None or np.size(strata) != n):
        raise ValueError("Invalid strata variable")
    if nstrat == 1:
        strata = np.ones(n, dtype=np.int32)
    else:
        strata = np.asarray(strata, dtype=np.int32)
    nstrat2 = 0 if scale > 0 else nstrat

    sd, dnum = _resolve_dist(dist)
    density = sd["density"]

    def derfun(eta, sigma):
        return _derfun(y, eta, sigma, density, parms)

    # Rescale the X matrix when the first column is an intercept and the
    # starting values are not given. Columns of 0 and 1 are left alone.
    rescaled = False
    center = stdev = None
    if init is None and np.all(x[:, 0] == 1) and nvar > 1:
        okay = np.array([np.all((x[:, j] == 0) | (x[:, j] == 1)) for j in range(nvar)])
        if not np.all(okay):
            rescaled = True
            center = np.where(okay, 0.0, x.mean(axis=0))
            stdev = np.where(okay, 1.0, np.std(x, axis=0, ddof=1))
            x = (x - center) / stdev

    nvar2 = nvar + nstrat2
    meanonly = nvar == 1 and bool(np.all(x == 1))
    fit0 = None
    yy = None
    if not meanonly:
        yy = np.where(y[:, ny - 1] != 3, y[:, 0], (y[:, 0] + y[:, 1]) / 2.0)
        coef = np.asarray(sd["init"](yy, weights, parms), dtype=float)
        if scale > 0:
            vars_ = np.log(scale)
        else:
            vars_ = np.log(4.0 * coef[1]) / 2.0
        coef = np.concatenate(([coef[0]], np.repeat(vars_, nstrat)))

        dg, ddg = derfun(yy, np.exp(vars_))
        wt = -1.0 * ddg * weights
        coef[0] = np.sum(weights * dg + wt * (yy - offset)) / np.sum(wt)

        fit0 = _kernel(
            20, 1, y, ny, np.ones((n, 1)), weights, offset, coef,
            nstrat2, strata, eps, toler_chol, dnum,
        )
        if (
            not np.all(np.isfinite(fit0["coef"]))
            or not np.isfinite(fit0["loglik"])
            or not np.all(np.isfinite(fit0["var"]))
        ):
            raise RuntimeError("initial iteration failed (use starting estimates?)")

    if init is not None:
        init = np.asarray(init, dtype=float)
        if init.size == nvar and nvar2 > nvar:
            if fit0 is None:
                raise RuntimeError("object 'fit0' not found")
            init = np.concatenate([init, fit0["coef"][1:]])
        if init.size != nvar2:
            raise ValueError("Wrong length for initial parameters")
        if scale > 0:
            init = np.concatenate([init, [np.log(scale)]])
    else:
        if meanonly:
            yy = np.where(y[:, ny - 1] != 3, y[:, 0], (y[:, 0] + y[:, 1]) / 2.0)
            coef = np.asarray(sd["init"](yy, weights, parms), dtype=float)
            if scale > 0:
                vars_ = np.repeat(np.log(scale), nstrat)
            else:
                vars_ = np.repeat(np.log(4.0 * coef[1]) / 2.0, nstrat)
        else:
            vars_ = fit0["coef"][1:]
        eta = yy - offset

        dg, ddg = derfun(yy, np.exp(vars_)[strata - 1])
        wt = -1.0 * ddg * weights
        var_mat = x.T @ (wt[:, None] * x)
        rhs = (wt * eta + weights * dg) @ x
        coef = coxph_wtest(var_mat, rhs, toler_chol=toler_chol)["solve"]
        init = np.concatenate([np.asarray(coef, dtype=float), vars_])

    fit = _kernel(
        iter_max, nvar, y, ny, x, weights, offset, init,
        nstrat2, strata, eps, toler_chol, dnum,
    )
    if iter_max > 1 and fit["flag"] > nvar2:
        warnings.warn("Ran out of iterations and did not converge")

    coef_fit = fit["coef"]
    if scale > 0:
        coef_fit = coef_fit[:nvar2]

    if meanonly:
        coef0 = coef_fit.copy()
        loglik = np.array([fit["loglik"], fit["loglik"]])
    else:
        coef0 = fit0["coef"].copy()
        loglik = np.array([fit0["loglik"], fit["loglik"]])

    var_new = fit["var"].reshape((nvar2, nvar2), order="F")
    coef_new = coef_fit.copy()
    if rescaled:
        vtemp = np.diag(np.concatenate([1.0 / stdev, np.ones(nvar2 - stdev.size)]))
        vtemp[0, 1:nvar] = -center[1:nvar] / stdev[1:nvar]
        coef_new = vtemp @ coef_new
        var_new = vtemp @ var_new @ vtemp.T

    linear_predictors = x @ coef_fit[:nvar] + offset

    return {
        "coefficients": coef_new,
        "icoef": coef0,
        "var": var_new,
        "loglik": loglik,
        "iter": fit["iter"],
        "linear.predictors": linear_predictors,
        "df": int(coef_fit.size),
        "score": fit["u"],
    }
