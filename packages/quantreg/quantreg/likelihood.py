"""Gaussian likelihood of a fitted quantile regression, as logLik.rq defines it."""

from __future__ import annotations

import math

import numpy as np


def _length(value):
    array = np.asarray(value)
    if array.ndim == 0:
        return 1
    return int(array.shape[0])


def log_lik_rq(object, edf_thresh=None):
    """n * (log(tau * (1 - tau)) - 1 - log(rho / n)), with df = p."""
    residuals = np.asarray(object["residuals"], dtype=float)
    coefficients = np.asarray(object["coefficients"], dtype=float)
    n = residuals.shape[0]
    p = coefficients.shape[0] if coefficients.ndim == 1 else coefficients.shape[0]
    lam = object.get("lambda")
    penalized = lam is not None and _length(lam) > 0
    tau = float(np.asarray(object["tau"]).reshape(-1)[0])
    fidelity = float(np.asarray(object["rho"]).reshape(-1)[0])
    value = n * (math.log(tau * (1.0 - tau)) - 1.0 - math.log(fidelity / n))
    if penalized:
        if edf_thresh is None:
            edf_thresh = 0.0001
        df = int(np.sum(np.abs(coefficients) > edf_thresh))
    else:
        df = int(p)
    return {"value": value, "n": n, "df": df}


def aic_rq(object, k=2, edf_thresh=None):
    """AIC of logLik.rq. k <= 0 uses log(n)."""
    likelihood = log_lik_rq(object, edf_thresh=edf_thresh)
    penalty = float(k)
    if penalty <= 0:
        penalty = math.log(likelihood["n"])
    value = -2.0 * likelihood["value"] + penalty * likelihood["df"]
    return {"value": value, "edf": likelihood["df"]}


def extract_aic_rq(fit, scale=0, k=2):
    """c(edf, AIC) as extractAIC.rq returns it. scale is unused, matching R."""
    del scale
    scored = aic_rq(fit, k=k)
    return np.array([scored["edf"], scored["value"]], dtype=float)
