"""Shepard plot data for non-metric MDS (MASS ``Shepard``)."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from mass.errors import MassError
from mass.iso_mds import _mds_fn, _ws


def _distance_vector(d: Any) -> np.ndarray:
    if hasattr(d, "_mass_dist_size"):
        return np.asarray(getattr(d, "data", d), dtype=float).reshape(-1)
    arr = np.asarray(d, dtype=float)
    if arr.ndim == 2 and arr.shape[0] == arr.shape[1]:
        n = arr.shape[0]
        return arr[np.triu(np.ones((n, n), dtype=bool), k=1)]
    return arr.reshape(-1)


def _minkowski_dist_condensed(x: np.ndarray, p: float) -> np.ndarray:
    n = x.shape[0]
    euclid = p == 2.0
    out: list[float] = []
    for r1 in range(n):
        for r2 in range(r1 + 1, n):
            if euclid:
                tmp = 0.0
                for c in range(x.shape[1]):
                    diff = x[r1, c] - x[r2, c]
                    tmp += diff * diff
                out.append(math.sqrt(tmp))
            else:
                tmp = 0.0
                for c in range(x.shape[1]):
                    tmp += abs(x[r1, c] - x[r2, c]) ** p
                out.append(tmp ** (1.0 / p))
    return np.asarray(out, dtype=float)


def shepard(d: Any, x: Any, p: float = 2) -> dict[str, np.ndarray]:
    """Ordered dissimilarities, configuration distances, and isotonic fit."""
    x = np.asarray(x, dtype=float)
    if x.ndim != 2:
        raise MassError("invalid row(x)")
    n = int(x.shape[0])
    if math.isnan(float(n)):
        raise MassError("invalid row(x)")
    k = int(x.shape[1])

    d_vec = _distance_vector(d)
    ord_idx = np.argsort(d_vec, kind="mergesort")
    y = _minkowski_dist_condensed(x, float(p))
    y = y[ord_idx]
    nd = int(ord_idx.size)
    if math.isnan(float(nd)):
        raise MassError("invalid length(d)")

    ord2 = np.argsort(ord_idx)
    y_list = y.astype(float).tolist()
    yf_list = list(y_list)
    x_colmajor = x.reshape(-1, order="F").tolist()
    der = [0.0] * (n * k)

    _ws.n = nd
    _ws.nr = n
    _ws.nc = k
    _ws.x = x_colmajor
    _ws.ord2 = ord2.astype(int)
    _ws.mink_pow = 2.0
    _mds_fn(y_list, yf_list, True, der)

    return {
        "x": d_vec[ord_idx],
        "y": y,
        "yf": np.asarray(yf_list, dtype=float),
    }
