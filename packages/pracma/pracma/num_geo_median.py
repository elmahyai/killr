"""Geometric median by Weiszfeld's iteration."""

from __future__ import annotations

import warnings

import numpy as np

from pracma._util import PracmaError
from pracma.arrays import Norm
from pracma.num_helpers import is_r_numeric, r_median


def geo_median(P, tol=1e-07, maxiter=200):
    if not is_r_numeric(P):
        raise PracmaError("is.numeric(P) is not TRUE")
    points = np.asarray(P, dtype=float)
    if points.ndim != 2:
        raise PracmaError("Argument 'P' must be a matrix (of points in R^n).")
    rows, cols = points.shape
    if cols == 1:
        center = r_median(points)
        return {
            "p": center,
            "d": float(np.sum(np.abs(points - center))),
            "reltol": 0.0,
            "niter": 0,
        }
    current = np.mean(points, axis=0)
    updated = current + 1.0
    iteration = 1
    while np.max(np.abs(current - updated)) > tol and iteration < maxiter:
        iteration += 1
        current = updated
        weighted = np.zeros(cols)
        scale = 0.0
        for row in points:
            distance = Norm(row - current)
            weighted = weighted + row / distance
            scale = scale + 1.0 / distance
        updated = weighted / scale
    if iteration >= maxiter:
        warnings.warn("Maximum number of iterations reached; may not converge.", stacklevel=2)
    distance = 0.0
    for row in points:
        distance += Norm(row - updated)
    return {
        "p": updated,
        "d": float(distance),
        "reltol": float(np.max(np.abs(current - updated))),
        "niter": int(iteration),
    }
