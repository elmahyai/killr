"""chull: the convex hull vertices in the order R's ``chull()`` returns them.

R's ``grDevices::chull`` is two steps. A C routine (``C_chull``, Eddy's 1977
algorithm, ACM 523) returns the hull vertex set. Then R code (shown by
``print(grDevices::chull)``) orders that set by angle about its own centroid:

    res <- .Call(C_chull, x)
    xx <- sweep(x[res, ], 2L, colMeans(x[res, ]))
    angs <- atan2(xx[, 2L], -xx[, 1L])
    res[order(angs)]

The order therefore depends on the set only. The port reproduces the second
step exactly. The first step is a monotone-chain hull on the exact coordinates:
collinear points on an edge are not vertices, and exact duplicates collapse to
one copy (the first index).

The C source of ``C_chull`` is not on this machine, so the first step is not a
port of Eddy's code; it is checked against R's output. Known deviations, from
``proof/chull-r.R`` and ``proof/chull-py.py`` (4000 random tie-heavy point sets):
R sometimes keeps more than one copy of a duplicated vertex, and sometimes keeps
a collinear point on an edge. Those cases are about 0.7 per cent of the battery.
On the mclust ellipse inputs, ELLIPSE2 and ELLIPSE3 match exactly and ELLIPSE1
keeps two copies of one vertex in R but not here.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

__all__ = ["chull"]


def _cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _hull_points(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Strict hull vertices of distinct points, from the lowest-x point, counter-clockwise."""
    lower: list[tuple[float, float]] = []
    for p in points:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list[tuple[float, float]] = []
    for p in reversed(points):
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def chull(xy: Any) -> np.ndarray:
    """0-based indices of the hull vertices of an n by 2 matrix, in R's ``chull`` order.

    Duplicate points are returned once, at their first index. A point on an
    edge between two vertices is not returned.
    """
    pts = np.asarray(xy, dtype=float)
    if pts.ndim != 2 or pts.shape[1] != 2:
        raise ValueError("chull needs an n by 2 matrix")
    if not np.all(np.isfinite(pts)):
        raise ValueError("finite coordinates are needed")
    n = pts.shape[0]
    if n == 0:
        return np.zeros(0, dtype=int)
    if n == 1:
        return np.zeros(1, dtype=int)

    first: dict[tuple[float, float], int] = {}
    for i, (px, py) in enumerate(pts.tolist()):
        first.setdefault((px, py), i)
    distinct = sorted(first)
    if len(distinct) < 3:
        hull = distinct
    else:
        hull = _hull_points(distinct)
    res = [first[p] for p in hull]
    if len(res) < 2:
        return np.asarray(res, dtype=int)

    sel = pts[res]
    centre = [math.fsum(sel[:, j]) / len(res) for j in range(2)]
    xx = sel - np.asarray(centre)
    angs = np.arctan2(xx[:, 1], -xx[:, 0])
    order = np.argsort(angs, kind="stable")
    return np.asarray(res, dtype=int)[order]
