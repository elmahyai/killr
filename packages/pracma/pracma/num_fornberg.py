"""Fornberg finite-difference weights."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.arrays import zeros
from pracma.num_helpers import is_r_numeric


def fornberg(x, y, xs, k=1):
    if not is_r_numeric(x) or not is_r_numeric(y) or not is_r_numeric(xs):
        raise PracmaError("is.numeric(x) is not TRUE")
    abscissa = np.asarray(x, dtype=float).reshape(-1)
    ordinate = np.asarray(y, dtype=float).reshape(-1)
    targets = np.asarray(xs, dtype=float).reshape(-1)
    if np.any(np.isnan(ordinate)):
        keep = ~np.isnan(ordinate)
        abscissa = abscissa[keep]
        ordinate = ordinate[keep]
    n = abscissa.size
    order = int(k)
    if np.unique(abscissa).size != n:
        raise PracmaError("All elements in vector 'x' must be different.")
    if order >= n:
        raise PracmaError("Length of 'x' must be greater than k.")
    if order <= 0:
        raise PracmaError("Order 'k' must be between 1 and length of 'x'.")
    # 1-based tables, matching the R loops.
    nodes = np.concatenate([[0.0], abscissa])
    weights = np.full((targets.size, order + 1), np.nan)
    for ij, origin in enumerate(targets):
        c1 = 1.0
        c4 = nodes[1] - origin
        table = np.asarray(zeros(n, order + 1), dtype=float)
        padded = np.zeros((n + 1, order + 2))
        padded[1:n + 1, 1:order + 2] = table
        padded[1, 1] = 1.0
        for i in range(1, n):
            i1 = i + 1
            mn = min(i, order)
            c2 = 1.0
            c5 = c4
            c4 = nodes[i1] - origin
            for j in range(0, i):
                j1 = j + 1
                c3 = nodes[i1] - nodes[j1]
                c2 = c2 * c3
                if j == i - 1:
                    for s in range(mn, 0, -1):
                        s1 = s + 1
                        padded[i1, s1] = c1 * (s * padded[i1 - 1, s1 - 1] - c5 * padded[i1 - 1, s1]) / c2
                    padded[i1, 1] = -c1 * c5 * padded[i1 - 1, 1] / c2
                for s in range(mn, 0, -1):
                    s1 = s + 1
                    padded[j1, s1] = (c4 * padded[j1, s1] - s * padded[j1, s1 - 1]) / c3
                padded[j1, 1] = c4 * padded[j1, 1] / c3
            c1 = c2
        used = padded[1:n + 1, 1:order + 2]
        weights[ij, :] = ordinate @ used
    if order == 0:
        return weights[:, :1]
    return weights
