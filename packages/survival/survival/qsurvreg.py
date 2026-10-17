"""Quantile function for survreg-supported distributions (survival::qsurvreg)."""

from __future__ import annotations

import numpy as np
from scipy.stats import norm, t as student_t

from survival.dsurvreg import _lookup_distribution, _recycle


def _quantile_extreme(p: np.ndarray, _parms) -> np.ndarray:
    p = np.asarray(p, dtype=float)
    return np.log(-np.log1p(-p))


def _quantile_logistic(p: np.ndarray, _parms) -> np.ndarray:
    p = np.asarray(p, dtype=float)
    return np.log(p / (1.0 - p))


def _quantile_gaussian(p: np.ndarray, _parms) -> np.ndarray:
    return np.asarray(norm.ppf(p), dtype=float)


def _t_quantile(p: np.ndarray, parms) -> np.ndarray:
    if parms is None:
        raise ValueError("missing value for 'parms'")
    df = float(np.asarray(parms, dtype=float).reshape(-1)[0])
    return np.asarray(student_t.ppf(p, df), dtype=float)


_QUANTILE = {
    "extreme": _quantile_extreme,
    "logistic": _quantile_logistic,
    "gaussian": _quantile_gaussian,
    "t": _t_quantile,
}


def qsurvreg(
    p,
    mean,
    scale=1,
    distribution="weibull",
    parms=None,
):
    """Quantile function for a survreg location-scale family at probability ``p``."""
    p_arr = np.asarray(p, dtype=float)
    orig_shape = p_arr.shape
    _, (p_vec, mean_vec, scale_vec) = _recycle(
        p_arr.reshape(-1),
        np.asarray(mean, dtype=float),
        np.asarray(scale, dtype=float),
    )
    key, alias = _lookup_distribution(distribution)

    if alias is not None:
        x_std = _QUANTILE[alias["dist"]](p_vec, parms)
        out = np.exp(x_std * scale_vec + mean_vec)
    else:
        x_std = _QUANTILE[key](p_vec, parms)
        out = x_std * scale_vec + mean_vec

    if orig_shape == ():
        return float(out[0])
    return out.reshape(orig_shape)
