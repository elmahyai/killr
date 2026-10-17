"""Ridge regression linear models (MASS ``lm.ridge``)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from mass.addterm import _model_matrix
from mass.errors import MassError
from mass.lm_gls import _expand_dot_formula


@dataclass
class Ridgelm:
    """Ridge fit (class ``ridgelm``)."""

    coef: np.ndarray
    scales: np.ndarray
    Inter: bool
    lambda_: np.ndarray
    ym: float
    xm: np.ndarray
    GCV: np.ndarray
    kHKB: float
    kLW: float
    formula: str
    data: dict[str, Any]


def lm_ridge(
    formula: str,
    data: dict[str, Any] | None = None,
    *,
    lambda_: float | np.ndarray | list[float] = 0,
    **kwargs: Any,
) -> Ridgelm:
    """Fit a linear model by ridge regression."""
    if kwargs:
        raise MassError(f"unused arguments: {', '.join(sorted(kwargs))}")
    if data is None:
        raise MassError("'data' must be supplied")
    formula = _expand_dot_formula(formula, data)
    x, y, names, _labels = _model_matrix(data, formula)
    n, p_full = x.shape
    y = np.asarray(y, dtype=float).reshape(-1)
    inter = "(Intercept)" in names
    if inter:
        xm = np.mean(x[:, 1:], axis=0)
        ym = float(np.mean(y))
        p = p_full - 1
        x = x[:, 1:] - xm
        y = y - ym
    else:
        ym = float("nan")
        xm = np.array([], dtype=float)
        p = p_full
    xscale = np.sqrt(np.mean(x**2, axis=0))
    x = x / xscale
    u, d, vt = np.linalg.svd(x, full_matrices=False)
    v = vt.T
    rhs = u.T @ y
    lscoef = v @ (rhs / d)
    lsfit = x @ lscoef
    resid = y - lsfit
    inter_int = int(inter)
    s2 = float(np.sum(resid**2) / (n - p - inter_int))
    hkb = (p - 2) * s2 / float(np.sum(lscoef**2))
    l_w = (p - 2) * s2 * n / float(np.sum(lsfit**2))
    lam = np.atleast_1d(np.asarray(lambda_, dtype=float)).reshape(-1)
    k = lam.shape[0]
    dx = d.shape[0]
    div = (d**2)[:, None] + lam[None, :]
    a = (d * rhs)[:, None] / div
    coef = v @ a
    if k == 1 and coef.shape[1] == 1:
        coef_out = coef[:, 0]
    else:
        coef_out = coef
    fitted = x @ coef
    rss = np.sum((y[:, None] - fitted) ** 2, axis=0)
    gcv = rss / (n - np.sum((d**2)[:, None] / div, axis=0)) ** 2
    return Ridgelm(
        coef=coef_out,
        scales=xscale,
        Inter=inter,
        lambda_=lam,
        ym=ym,
        xm=xm,
        GCV=gcv,
        kHKB=hkb,
        kLW=l_w,
        formula=formula,
        data=data,
    )


def coef_ridgelm(object: Ridgelm) -> np.ndarray:
    """Return coefficients on the original scale (``coef.ridgelm``)."""
    raw = np.asarray(object.coef, dtype=float)
    if raw.ndim == 1:
        scaled = raw / object.scales
        if object.Inter:
            inter = object.ym - float(scaled @ object.xm)
            return np.concatenate([[inter], scaled])
        return scaled
    scaled = (raw / object.scales[:, None]).T
    if object.Inter:
        inter = object.ym - scaled @ object.xm
        return np.column_stack([inter, scaled])
    return scaled
