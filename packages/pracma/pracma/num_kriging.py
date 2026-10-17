"""Ordinary and simple kriging."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import distmat, is_r_numeric, is_r_vector, match_arg, r_inv


def kriging(u, v, u0, type=("ordinary", "simple")):
    if not is_r_numeric(u):
        raise PracmaError("is.numeric(u) is not TRUE")
    if not is_r_numeric(v):
        raise PracmaError("is.numeric(v) is not TRUE")
    if not is_r_numeric(u0):
        raise PracmaError("is.numeric(u0) is not TRUE")
    sites = np.asarray(u, dtype=float)
    if sites.ndim != 2:
        raise PracmaError("Argument 'u' must be a numeric matrix.")
    rows, cols = sites.shape
    values = np.asarray(v, dtype=float)
    if is_r_vector(v):
        values = values.reshape(-1)
        if values.size != rows:
            raise PracmaError("Length of vector 'v' must be equal to ncol(u).")
    elif values.ndim == 2:
        if values.shape[1] == 1 or values.shape[0] == rows:
            values = values.reshape(-1, order="F")
        else:
            raise PracmaError("As matrix 'v' must be a column vector (with ncol(u) elements).")
    else:
        raise PracmaError("Argument 'v' must be a vector or matrix (with ncol(u) elements).")
    target = np.asarray(u0, dtype=float)
    if is_r_vector(u0):
        target = target.reshape(-1)
        if target.size == cols:
            target = target.reshape(1, -1)
        else:
            raise PracmaError("Length of vector 'u0' must be equal to ncol(u).")
    elif target.ndim == 2:
        if target.shape[1] != cols:
            raise PracmaError("Matrix 'u0' must have the same number of colums as 'u'.")
    else:
        raise PracmaError("Argument 'u0' must be a vector or matrix (with ncol(u) elements).")
    kind = match_arg(type, ("ordinary", "simple"))
    variogram = distmat(sites, sites)
    distances = distmat(sites, target)
    if kind == "simple":
        weights = values.reshape(1, -1) @ r_inv(variogram) @ distances
    elif kind == "ordinary":
        k = target.shape[0]
        system = np.ones((rows + 1, rows + 1))
        system[:rows, :rows] = variogram
        system[rows, rows] = 0.0
        rhs = np.ones((rows + 1, k))
        rhs[:rows, :] = distances
        extended = np.concatenate([values, [0.0]])
        weights = extended.reshape(1, -1) @ r_inv(system) @ rhs
    else:
        raise PracmaError("Argument 'type' can only be 'simple' or 'ordinary'.")
    return np.asarray(weights, dtype=float).reshape(-1)
