"""Hommel (1988) multiple testing accept/reject decisions.

Translated from statmod 1.5.2 ``hommel.test`` in ``R/hommel.R``.
"""

from __future__ import annotations

import numpy as np


def hommel_test(p, alpha=0.05):
    """Return whether each hypothesis is accepted at level ``alpha``."""
    p_arr = np.asarray(p, dtype=float)
    flat = p_arr.reshape(-1)
    n = flat.size
    if n == 0:
        return np.array([], dtype=bool).reshape(p_arr.shape)

    po = np.sort(flat)
    j = n
    while True:
        if j == 0:
            break
        # k runs 1..j in R; po[n - j + k] is po[n-j : n] (j largest sorted p-values)
        thresholds = (np.arange(1, j + 1, dtype=float) * alpha) / j
        segment = po[n - j : n]
        if np.all(segment > thresholds):
            break
        j -= 1

    if j == 0:
        cutoff = np.inf
    else:
        cutoff = alpha / j
    out = flat >= cutoff
    return out.reshape(p_arr.shape)
