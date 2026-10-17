"""Formula interface for linear quantile regression."""

from __future__ import annotations

import numpy as np

from quantreg.fit import rq_fit, rq_wfit


def _as_column(value):
    array = np.asarray(value, dtype=float).reshape(-1)
    return array


def parse_formula(formula):
    """A small piece of R's formula: response ~ terms, optional trailing - 1."""
    text = str(formula).replace(" ", "")
    if "~" not in text:
        raise ValueError("formula has no ~")
    response, right = text.split("~", 1)
    intercept = True
    if right.endswith("-1"):
        intercept = False
        right = right[: -2]
    if right.endswith("+0"):
        intercept = False
        right = right[: -2]
    terms = [part for part in right.split("+") if part and part not in {"1", "0"}]
    if response == "" or any(not term for term in terms):
        raise ValueError(f"cannot parse formula {formula}")
    return {"response": response, "terms": terms, "intercept": intercept}


def model_matrix(spec, data, subset=None):
    """Columns in R model.matrix order for a parsed formula."""
    response = _as_column(data[spec["response"]])
    columns = [_as_column(data[name]) for name in spec["terms"]]
    n = response.shape[0]
    for column in columns:
        if column.shape[0] != n:
            raise ValueError("variables in the formula have different lengths")
    keep = np.ones(n, dtype=bool)
    if subset is not None:
        chosen = np.asarray(subset)
        if chosen.dtype == bool:
            keep = chosen
        else:
            # R subset indexes are 1-based.
            keep = np.zeros(n, dtype=bool)
            keep[chosen.astype(int) - 1] = True
    used = np.column_stack([response, *columns]) if columns else response.reshape(-1, 1)
    keep &= np.all(np.isfinite(used), axis=1)
    response = response[keep]
    built = []
    names = []
    if spec["intercept"]:
        built.append(np.ones(response.shape[0]))
        names.append("(Intercept)")
    for name, column in zip(spec["terms"], columns):
        built.append(column[keep])
        names.append(name)
    design = np.column_stack(built) if built else np.zeros((response.shape[0], 0))
    return design, response, names


def _rho(residuals, tau):
    residuals = np.asarray(residuals, dtype=float)
    return float(np.sum(residuals * (tau - (residuals < 0))))


def rq(formula, tau=0.5, data=None, subset=None, weights=None, method="br", model=True):
    """Linear quantile regression from a formula and a column dictionary.

    method \"sfn\" needs MatrixModels, which is not in the registry. The
    checked path is method \"br\".
    """
    if data is None:
        raise ValueError("data is required")
    if method == "sfn":
        raise NotImplementedError("method sfn needs MatrixModels, which is not in the registry")
    if method == "conquer":
        raise RuntimeError("method conquer requires package conquer")
    spec = parse_formula(formula)
    design, response, names = model_matrix(spec, data, subset=subset)
    taus = np.atleast_1d(np.asarray(tau, dtype=float))
    eps = np.finfo(float).eps ** (2.0 / 3.0)
    taus = np.array(sorted(set(taus.tolist())), dtype=float)
    taus = np.where(taus == 0, eps, taus)
    taus = np.where(taus == 1, 1 - eps, taus)
    weight = None if weights is None else np.asarray(weights, dtype=float).reshape(-1)
    if weight is not None and subset is not None:
        chosen = np.asarray(subset)
        if chosen.dtype != bool:
            mask = np.zeros(weight.shape[0], dtype=bool)
            mask[chosen.astype(int) - 1] = True
            weight = weight[mask]
    fits = []
    for value in taus:
        if weight is None:
            fits.append(rq_fit(design, response, tau=float(value), method=method))
        else:
            fits.append(rq_wfit(design, response, tau=float(value), weights=weight, method=method))
    if taus.size == 1:
        fit = fits[0]
        fit["coefficients"] = np.asarray(fit["coefficients"], dtype=float)
        fit["rho"] = _rho(fit["residuals"], float(taus[0]))
        fit["class"] = "rq"
    else:
        fit = dict(fits[-1])
        fit["coefficients"] = np.column_stack([item["coefficients"] for item in fits])
        fit["residuals"] = np.column_stack([item["residuals"] for item in fits])
        fit["fitted.values"] = response.reshape(-1, 1) - fit["residuals"]
        fit["rho"] = np.array([_rho(item["residuals"], float(value)) for item, value in zip(fits, taus)])
        fit["class"] = "rqs"
    fit["names"] = names
    fit["tau"] = taus if taus.size > 1 else float(taus[0])
    fit["formula"] = str(formula)
    fit["terms"] = spec
    fit["method"] = method
    fit["weights"] = weight
    fit["call"] = f"rq(formula = {formula}, tau = {tau}, data = data)"
    fit["x"] = design
    fit["y"] = response
    if model:
        fit["model"] = data
    return fit


def formula_rq(x):
    """The formula stored on an rq fit."""
    form = x.get("formula")
    if form is None:
        raise ValueError("this fit has no formula")
    return form
