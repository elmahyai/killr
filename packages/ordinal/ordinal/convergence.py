"""Assess convergence of cumulative link models (ordinal convergence.clm)."""

from __future__ import annotations

import math
import warnings
from typing import Any

import numpy as np

from ordinal._clm_nll import clm_grad, clm_grad_direct, clm_nll
from ordinal.slice import _coef, _get_clm_rho


class ConvergenceClm:
    def __init__(
        self,
        info: dict[str, Any],
        coefficients: np.ndarray,
        coef_names: list[str],
        original_fit: Any,
        eigen_values: np.ndarray | None = None,
    ):
        self.info = info
        self.coefficients = coefficients
        self._coef_names = coef_names
        self.original_fit = original_fit
        self.eigen_values = eigen_values

    def coef(self):
        return self.coefficients


def cor_dec(error):
    error = np.asarray(error, dtype=float)
    xx = -np.log10(np.abs(error))
    lead = np.floor(xx)
    res = np.where(xx < lead - math.log10(0.5), lead - 1.0, lead)
    res = np.where(np.abs(error) >= 0.05, 0.0, res)
    return np.asarray(np.round(res), dtype=int)


def signif_digits(value, error):
    value = np.asarray(value, dtype=float)
    res = cor_dec(error) + np.ceil(np.log10(np.abs(value)))
    res = np.where(res < 0, 0, res)
    return np.asarray(np.round(res), dtype=int)


def _format_pval(x, digits=2, eps=1e-10):
    if not math.isfinite(x) or x < 0:
        return str(x)
    if x < eps:
        exp = int(math.floor(math.log10(eps)))
        return f"<1e{exp}"
    formatted = format(float(x), f".{digits}e")
    if "<" in formatted:
        return formatted
    return formatted


def _info_subset(object) -> dict[str, Any]:
    if hasattr(object, "info") and isinstance(object.info, dict):
        src = object.info
    else:
        src = {}
    keys = ("nobs", "logLik", "niter", "max.grad", "cond.H")
    out = {k: src.get(k, np.nan) for k in keys}
    if out["nobs"] is np.nan and hasattr(object, "nobs"):
        out["nobs"] = object.nobs
    if out["logLik"] is np.nan and hasattr(object, "logLik"):
        out["logLik"] = object.logLik
    return out


def convergence(object, tol=None, **kwargs):
    from ordinal._clm_rho import ClmLike

    if isinstance(object, ClmLike) or (
        hasattr(object, "Hessian") and hasattr(object, "logLik") and hasattr(object, "coef")
    ):
        return convergence_clm(object, tol=tol, **kwargs)
    raise TypeError(f"no convergence method for object of type {type(object).__name__}")


def convergence_clm(object, digits=None, tol=None, **_kwargs):
    del digits
    if tol is None:
        tol = math.sqrt(float(np.finfo(float).eps))
    info = _info_subset(object)
    coefs, names = _coef(object, na_rm=True)
    g = np.asarray(object.gradient, dtype=float).reshape(-1)
    if g.size != coefs.size:
        g = clm_grad_direct(_get_clm_rho(object), coefs.copy())
    h = np.asarray(object.Hessian, dtype=float)
    tab = np.full((coefs.size, 6), np.nan, dtype=float)
    tab[:, 0] = coefs
    tab[:, 2] = g
    res = ConvergenceClm(info=info, coefficients=tab, coef_names=names, original_fit=object)
    if not np.all(np.isfinite(h)):
        warnings.warn(
            "non-finite values in Hessian: illegitimate model fit",
            RuntimeWarning,
            stacklevel=2,
        )
        return res
    e_val = np.linalg.eigvalsh(h)[::-1]
    res.eigen_values = e_val
    try:
        ch = np.linalg.cholesky(h)
    except np.linalg.LinAlgError:
        return res
    if np.any(np.abs(e_val) <= tol):
        return res
    step = np.linalg.solve(ch.T, np.linalg.solve(ch, g))
    if np.max(np.abs(step)) > 1e-2:
        warnings.warn(
            "convergence assessment may be unreliable due to large numerical error",
            RuntimeWarning,
            stacklevel=2,
        )
    env = _get_clm_rho(object)
    trial = coefs - step
    clm_nll(env, trial)
    new_loglik = -clm_nll(env, trial)
    new_grad = clm_grad(env)
    new_max_grad = float(np.max(np.abs(new_grad)))
    if new_max_grad > float(np.max(np.abs(g))) and float(np.max(np.abs(step))) > tol:
        warnings.warn(
            "Convergence assessment may be unreliable: please assess the likelihood with slice()",
            RuntimeWarning,
            stacklevel=2,
        )
    loglik_err = float(object.logLik) - new_loglik
    err = _format_pval(loglik_err, digits=2, eps=1e-10)
    if "<" not in err:
        err = f"{float(err):.2e}"
    res.info = dict(info)
    res.info["logLik.Error"] = err
    cov = np.linalg.inv(h)
    se = np.sqrt(np.diag(cov))
    tab[:, 1] = se
    tab[:, 3] = step
    tab[:, 4] = cor_dec(step)
    tab[:, 5] = signif_digits(coefs, step)
    res.coefficients = tab
    return res


def convergence_values(result: ConvergenceClm) -> np.ndarray:
    """Flatten coefficient table and eigenvalues for checks."""
    parts = [np.ravel(result.coefficients, order="F")]
    if result.eigen_values is not None:
        parts.append(np.asarray(result.eigen_values, dtype=float))
    return np.concatenate(parts)
