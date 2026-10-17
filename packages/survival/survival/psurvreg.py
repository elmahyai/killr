"""CDF for survreg-supported distributions (survival::psurvreg)."""

from __future__ import annotations

import numpy as np
from scipy.stats import t as student_t

from survival.dsurvreg import _DENSITY, _lookup_distribution, _recycle


def _t_cdf(q: np.ndarray, parms) -> np.ndarray:
    if parms is None:
        raise ValueError("missing value for 'parms'")
    df = float(np.asarray(parms, dtype=float).reshape(-1)[0])
    return np.asarray(student_t.cdf(q, df), dtype=float)


def psurvreg(
    q,
    mean,
    scale=1,
    distribution="weibull",
    parms=None,
):
    """Distribution function for a survreg location-scale family at ``q``."""
    q_arr = np.asarray(q, dtype=float)
    orig_shape = q_arr.shape
    _, (q_vec, mean_vec, scale_vec) = _recycle(
        q_arr.reshape(-1),
        np.asarray(mean, dtype=float),
        np.asarray(scale, dtype=float),
    )
    key, alias = _lookup_distribution(distribution)

    if alias is not None:
        q_work = alias["trans"](q_vec)
        q_work = (q_work - mean_vec) / scale_vec
        key = alias["dist"]
    else:
        q_work = (q_vec - mean_vec) / scale_vec

    if key == "t":
        out = _t_cdf(q_work, parms)
    else:
        out = _DENSITY[key](q_work, parms)[:, 0]

    if orig_shape == ():
        return float(out[0])
    return out.reshape(orig_shape)
