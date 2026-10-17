"""``qclass``: quantile classification of a one-dimensional sample (mclust 6.1.3, R/mbahc.R).

Used in place of hierarchical clustering when the data is one-dimensional.
It is an internal helper of mclust; it is not an exported function.
"""

from __future__ import annotations

from typing import Any

import numpy as np

__all__ = ["qclass"]


def qclass(x: Any, k: int) -> np.ndarray:
    """Return class labels 1..k for the values of ``x`` by quantile breaks."""
    x = np.asarray(x, dtype=float).ravel()
    k = int(k)
    eps = float(np.std(x, ddof=1)) * np.sqrt(np.finfo(float).eps)
    q = np.array([np.nan])
    n = k
    # R: while (length(q) < k + 1) take more quantile breaks
    while q.size < k + 1:
        n += 1
        q = np.unique(np.quantile(x, np.linspace(0.0, 1.0, n)))
    if q.size > k + 1:
        dq = np.diff(q)
        nr = q.size - k - 1
        drop = np.argsort(dq, kind="stable")[:nr]
        q = np.delete(q, drop)
    q[0] = x.min() - eps
    q[-1] = x.max() + eps
    cl = np.zeros(x.size)
    for i in range(1, k + 1):
        # R's q[i] and q[i + 1] are q[i - 1] and q[i] here.
        cl[(x >= q[i - 1]) & (x < q[i])] = i
    return cl
