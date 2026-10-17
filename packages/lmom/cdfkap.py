"""Kappa CDF, a port of lmom 3.3 R/lmom.r cdfkap.

para = (xi, alpha, k, h). The transform is applied twice: y = -log(F) style
generalized-extreme-value step with shape k, then with shape h.
"""
from __future__ import annotations

import numpy as np

from ._cdf_common import scalarize


def cdfkap(x, para=(0.0, 1.0, 0.0, 0.0)):
    p = np.asarray(para, dtype=float).ravel()
    if p.size != 4:
        raise ValueError("parameter vector has wrong length")
    if np.any(np.isnan(p)):
        raise ValueError("missing values in parameter vector")
    xi, alpha, k, h = p
    if alpha <= 0:
        raise ValueError("distribution parameters invalid")

    xs = np.asarray(x, dtype=float)
    with np.errstate(all="ignore"):
        y = (xs - xi) / alpha
        if k != 0:
            y = -1.0 / k * np.log(np.maximum(0.0, 1.0 - k * y))
        y = np.exp(-y)
        if h != 0:
            y = -1.0 / h * np.log(np.maximum(0.0, 1.0 - h * y))
        y = np.exp(-y)
    return scalarize(x, y)
