"""Translation of permute's shuffleFree (R/shuffle-utils.R).

``shuffleFree(x, size)`` draws ``size`` values without replacement. A scalar
``x`` draws from ``1..x`` through R's ``sample.int``; a vector draws the
elements of ``x``. Results are R's values (1-based for a scalar ``x``).
"""

from __future__ import annotations

import numpy as np

from ._rng import sample_int


def shuffleFree(x, size=None):
    if np.size(x) > 1:
        a = np.asarray(x)
        size = len(a) if size is None else size
        p = np.asarray(sample_int(len(a), size, replace=False), dtype=int)
        return a[p - 1]
    n = np.ravel(np.asarray(x))[0]  # kept as a number: sample.int uses it as a double
    size = n if size is None else size
    return np.asarray(sample_int(n, size, replace=False), dtype=int)
