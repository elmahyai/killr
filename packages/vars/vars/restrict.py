"""Coefficient restrictions by t-statistic or by a supplied pattern."""

import numpy as np
from scipy.linalg import qr

from .estimate import VARResult, _lstsq


def restrict(x, method="ser", thresh=2, resmat=None):
    method = method if method in ("ser", "manual") else _one(method, ("ser", "manual"))
    thresh = abs(float(thresh))
    k = x.K
    design = x.datamat[:, k:]
    names = list(x.rhs_names)
    response = x.datamat[:, :k]
    pattern = np.zeros((k, design.shape[1]))
    equations = dict(x.varresult)
    if method == "ser":
        for i, name in enumerate(x.names):
            keep = list(range(design.shape[1]))
            current = design
            coef = equations[name]["coefficients"]
            resid = equations[name]["residuals"]
            while True:
                tvals = np.abs(_t_values(current, response[:, i], coef if current is design else None, resid if current is design else None))
                if tvals.size == 0 or np.min(tvals) >= thresh:
                    break
                if len(keep) <= 1:
                    raise ValueError(f"no significant regressors remaining in equation for {name}")
                drop = int(np.argmin(tvals))
                keep.pop(drop)
                current = design[:, keep]
                coef, resid, fitted = _lstsq(current, response[:, i])
            if not keep:
                raise ValueError(f"no significant regressors remaining in equation for {name}")
            coef, resid, fitted = _lstsq(current, response[:, i])
            equations[name] = {
                "coefficients": coef,
                "residuals": resid,
                "fitted": fitted,
                "df_residual": current.shape[0] - current.shape[1],
                "names": [names[j] for j in keep],
            }
            pattern[i, keep] = 1
    else:
        pattern = np.array(resmat, dtype=float)
        if pattern.shape != (k, design.shape[1]):
            raise ValueError(f"resmat must be {k} by {design.shape[1]}")
        for i, name in enumerate(x.names):
            keep = np.flatnonzero(pattern[i] == 1)
            current = design[:, keep]
            coef, resid, fitted = _lstsq(current, response[:, i])
            equations[name] = {
                "coefficients": coef,
                "residuals": resid,
                "fitted": fitted,
                "df_residual": current.shape[0] - current.shape[1],
                "names": [names[j] for j in keep],
            }
    updated = VARResult(**x.__dict__)
    updated.varresult = equations
    updated.restrictions = pattern
    updated.coefficients = None
    return updated


def _one(value, choices):
    hits = [item for item in choices if item.startswith(str(value))]
    if len(hits) != 1:
        raise ValueError(f"{value!r} does not match one of {choices}")
    return hits[0]


def _t_values(design, response, coef=None, resid=None):
    if coef is None or resid is None:
        coef, resid, _fitted = _lstsq(design, response)
    df = design.shape[0] - design.shape[1]
    sigma2 = float(np.sum(resid ** 2) / df)
    _q, rr, piv = qr(design, mode="economic", pivoting=True)
    diag = np.abs(np.diag(rr))
    tol = diag[0] * np.sqrt(np.finfo(float).eps)
    rank = int(np.sum(diag > tol))
    inv = np.linalg.inv(rr[:rank, :rank])
    unscaled = np.zeros((design.shape[1], design.shape[1]))
    unscaled[np.ix_(piv[:rank], piv[:rank])] = inv @ inv.T
    se = np.sqrt(sigma2 * np.diag(unscaled))
    return coef / se
