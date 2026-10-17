"""Isobands of a grid, as R's ``isobands()`` in isoband 0.3.0.

A band holds the values from ``levels_low`` up to, but not including, ``levels_high``.
If a low value is above its high value, the two are swapped. Each band gives a dict
with ``x``, ``y``, and ``id`` arrays. Cells that touch a non-finite value are skipped.
"""

from __future__ import annotations

import numpy as np
from isoband_kernel import isobands_kernel


def _recycle(values: np.ndarray, n: int) -> np.ndarray:
    if values.size == n:
        return values
    return np.full(n, values[0], dtype=np.float64)


def isobands(x, y, z, levels_low, levels_high) -> list[dict[str, np.ndarray]]:
    x_arr = np.asarray(x, dtype=np.float64).reshape(-1)
    y_arr = np.asarray(y, dtype=np.float64).reshape(-1)
    z_arr = np.asarray(z, dtype=np.float64)
    if z_arr.ndim != 2:
        raise ValueError("z must be a matrix with one row per y and one column per x")
    nrow, ncol = z_arr.shape

    low = np.asarray(levels_low, dtype=np.float64).reshape(-1)
    high = np.asarray(levels_high, dtype=np.float64).reshape(-1)
    nlow, nhigh = low.size, high.size
    nmax = max(nlow, nhigh)
    if (nlow != nmax and nlow != 1) or (nhigh != nmax and nhigh != 1):
        raise ValueError("Vectors specifying isoband levels must be of equal length or of length 1")
    if nmax == 0:
        low_arr = np.zeros(0, dtype=np.float64)
        high_arr = np.zeros(0, dtype=np.float64)
    else:
        low_arr = _recycle(low, nmax).copy()
        high_arr = _recycle(high, nmax).copy()
        # swap high and low levels when they are given in the wrong order
        swap = high_arr < low_arr
        if swap.any():
            tmp = high_arr[swap].copy()
            high_arr[swap] = low_arr[swap]
            low_arr[swap] = tmp

    z_flat = np.ravel(z_arr, order="F")
    out = isobands_kernel(x_arr, y_arr, z_flat, nrow, ncol, low_arr, high_arr)
    return [{"x": xs, "y": ys, "id": ids} for xs, ys, ids in out]
