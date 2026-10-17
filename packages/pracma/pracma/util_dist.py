"""Distance matrices from distmat.R."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.util_support import is_numeric, require


def _rows(value):
    array = np.asarray(value, dtype=float)
    if array.ndim <= 1:
        array = array.reshape(1, -1)
    return array


def distmat(X, Y):
    if not is_numeric(X) or not is_numeric(Y):
        raise PracmaError("X and Y must be numeric vectors or matrices.")
    left = _rows(X)
    right = _rows(Y)
    if left.shape[1] != right.shape[1]:
        raise PracmaError("X and Y must have the same number of columns.")
    product = left @ right.T
    left_norm = np.sum(left * left, axis=1)
    right_norm = np.sum(right * right, axis=1)
    xx = np.repeat(left_norm.reshape(-1, 1), right.shape[0], axis=1)
    yy = np.repeat(right_norm.reshape(1, -1), left.shape[0], axis=0)
    return np.sqrt(np.maximum(xx + yy - 2.0 * product, 0.0))


def pdist(X):
    return distmat(X, X)


def pdist2(X, Y):
    return distmat(X, Y)


def hausdorff_dist(P, Q):
    require(is_numeric(P), "is.numeric(P) is not TRUE")
    require(is_numeric(Q), "is.numeric(Q) is not TRUE")
    left = np.asarray(P, dtype=float)
    right = np.asarray(Q, dtype=float)
    if left.ndim <= 1:
        left = left.reshape(-1, 1)
    if right.ndim <= 1:
        right = right.reshape(-1, 1)
    if left.shape[1] != right.shape[1]:
        raise PracmaError("'P' and 'Q' must have the same number of columns.")
    distances = distmat(left, right)
    forward = np.max(np.min(distances, axis=1))
    backward = np.max(np.min(distances, axis=0))
    return float(max(forward, backward))
