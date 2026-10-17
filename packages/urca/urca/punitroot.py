"""MacKinnon unit-root cumulative probabilities (``punitroot``)."""

from __future__ import annotations

import math

import numpy as np

from urca.mackinnon_core import urcval_p

_TREND = ("c", "nc", "ct", "ctt")
_STAT = ("t", "n")


def punitroot(q, n=math.inf, trend="c", statistic="t", na_rm=False):
    """Return cumulative probabilities for MacKinnon unit-root test statistics."""
    trend = _match(trend, _TREND)
    statistic = _match(statistic, _STAT)
    n_sample = 0 if n == math.inf else int(n)
    values = np.asarray(q, dtype=float)
    flat = values.ravel()
    if np.any(np.isnan(flat)):
        if not na_rm:
            raise ValueError("NAs are not allowed when na.rm=FALSE")
        flat = flat[~np.isnan(flat)]
    itt = 1 if statistic == "t" else 2
    itv = {"nc": 1, "c": 2, "ct": 3, "ctt": 4}[trend]
    out = np.array([urcval_p(float(x), n_sample, itt, itv) for x in flat], dtype=float)
    return out.reshape(values.shape) if values.shape else out


def _match(value, choices: tuple[str, ...]) -> str:
    if isinstance(value, (list, tuple, np.ndarray)):
        value = value[0]
    text = str(value)
    if text not in choices:
        raise ValueError(f"'{text}' should be one of {', '.join(choices)}")
    return text
