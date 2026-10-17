"""Point estimates for linear quantile regression."""

from __future__ import annotations

import warnings

import numpy as np
from scipy.optimize import linprog


def _as_matrix(x):
    array = np.asarray(x, dtype=float)
    if array.ndim == 1:
        array = array.reshape(-1, 1)
    return array


def _rank(x):
    """R qr(x)$rank with the default tolerance 1e-7."""
    if x.shape[0] == 0 or x.shape[1] == 0:
        return 0
    _q, r = np.linalg.qr(x, mode="reduced")
    diagonal = np.abs(np.diag(r))
    if diagonal.size == 0 or diagonal[0] == 0:
        return 0
    return int(np.sum(diagonal > 1e-7 * diagonal[0]))


def rq_fit_br(x, y, tau=0.5, alpha=0.1, ci=False, iid=True, interp=True, tcrit=True):
    """Regression quantile by the linear program that rq.fit.br solves.

    tau outside [0, 1] is the whole quantile process, and ci=True is the
    simplex confidence interval. Both stay in the Fortran path and are not
    returned by this solver.
    """
    del alpha, iid, interp, tcrit
    design = _as_matrix(x)
    response = np.asarray(y, dtype=float).reshape(-1)
    n, p = design.shape
    if response.shape[0] != n:
        raise ValueError("x and y don't match n")
    if _rank(design) < p:
        raise ValueError("Singular design matrix")
    tau = float(tau)
    if tau < 0 or tau > 1 or ci:
        raise NotImplementedError(
            "The tau process and the simplex confidence interval are still the Fortran path"
        )
    objective = np.concatenate([np.zeros(p), np.full(n, tau), np.full(n, 1.0 - tau)])
    equalities = np.hstack([design, np.eye(n), -np.eye(n)])
    bounds = [(None, None)] * p + [(0.0, None)] * (2 * n)
    solved = linprog(objective, A_eq=equalities, b_eq=response, bounds=bounds, method="highs")
    if not solved.success:
        raise RuntimeError(solved.message)
    coefficients = solved.x[:p]
    names = getattr(x, "columns", None)
    residuals = response - design @ coefficients
    dual = np.asarray(solved.eqlin.marginals, dtype=float) + tau
    return {
        "coefficients": coefficients,
        "x": design,
        "y": response,
        "residuals": residuals,
        "dual": dual,
        "names": list(names) if names is not None else None,
    }


def rq_fit(x, y, tau=0.5, method="br", **kwargs):
    """Dispatch one tau. br is the linear program. fn, fnb, lasso, scad, pfn, and ppro are Frisch-Newton."""
    from quantreg.interior import rq_fit_fnb, rq_fit_lasso, rq_fit_pfn, rq_fit_ppro, rq_fit_scad

    tau_array = np.atleast_1d(np.asarray(tau, dtype=float))
    if tau_array.size > 1 and method != "ppro":
        warnings.warn(
            "Multiple taus not allowed in rq.fit: solution restricted to first element",
            stacklevel=2,
        )
        tau_array = tau_array[:1]
    tau_value = float(tau_array[0])
    if method == "br":
        fit = rq_fit_br(x, y, tau=tau_value, **kwargs)
    elif method in ("fn", "fnb"):
        fit = rq_fit_fnb(x, y, tau=tau_value, **kwargs)
    elif method == "lasso":
        fit = rq_fit_lasso(x, y, tau=tau_value, **kwargs)
    elif method == "scad":
        fit = rq_fit_scad(x, y, tau=tau_value, **kwargs)
    elif method == "pfn":
        fit = rq_fit_pfn(x, y, tau=tau_value, **kwargs)
    elif method == "ppro":
        fit = rq_fit_ppro(x, y, tau=tau_array, **kwargs)
    elif method == "conquer":
        raise RuntimeError("method conquer requires package conquer")
    else:
        raise NotImplementedError(f"unimplemented method: {method}")
    response = np.asarray(y, dtype=float).reshape(-1)
    if "residuals" not in fit:
        coefficient = np.asarray(fit["coefficients"], dtype=float)
        design = np.asarray(x, dtype=float)
        if design.ndim == 1:
            design = design.reshape(-1, 1)
        fit["residuals"] = response.reshape(-1, 1) - design @ coefficient if coefficient.ndim == 2 else response - design @ coefficient
    fit["fitted.values"] = response.reshape(-1, 1) - np.asarray(fit["residuals"], dtype=float) if np.asarray(fit["residuals"]).ndim == 2 else response - np.asarray(fit["residuals"], dtype=float)
    return fit


def rq_wfit(x, y, tau=0.5, weights=None, method="br", **kwargs):
    """Weighted fit. Rows are scaled, then residuals are put back on the original scale."""
    if weights is None:
        raise TypeError("weights is required")
    weights = np.asarray(weights, dtype=float).reshape(-1)
    if np.any(weights < 0):
        raise ValueError("negative weights not allowed")
    tau = np.atleast_1d(np.asarray(tau, dtype=float))
    if tau.size > 1:
        warnings.warn(
            "Multiple taus not allowed in rq.wfit: solution restricted to first element",
            stacklevel=2,
        )
        tau = tau[:1]
    design = _as_matrix(x)
    response = np.asarray(y, dtype=float).reshape(-1)
    weighted_x = design * weights[:, None]
    weighted_y = response * weights
    if method == "br":
        fit = rq_fit_br(weighted_x, weighted_y, tau=float(tau[0]), **kwargs)
    elif method in ("fn", "fnb"):
        from quantreg.interior import rq_fit_fnb

        fit = rq_fit_fnb(weighted_x, weighted_y, tau=float(tau[0]), **kwargs)
    else:
        raise NotImplementedError(f"unimplemented method: {method}")
    coefficients = fit["coefficients"]
    fitted = design @ coefficients
    fit["fitted.values"] = fitted
    fit["residuals"] = response - fitted
    fit["weights"] = weights
    fit["x"] = design
    fit["y"] = response
    return fit
