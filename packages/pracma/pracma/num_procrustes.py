"""Orthogonal Procrustes and Kabsch alignment."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.arrays import eye, ones, zeros
from pracma.num_helpers import is_r_numeric, r_svd


def procrustes(A, B):
    if not is_r_numeric(A):
        raise PracmaError("is.numeric(A) is not TRUE")
    if not is_r_numeric(B):
        raise PracmaError("is.numeric(B) is not TRUE")
    left = np.asarray(A, dtype=float)
    right = np.asarray(B, dtype=float)
    if left.ndim != 2 or right.ndim != 2:
        raise PracmaError("Arguments 'A' and 'B' must be numeric matrices.")
    if left.shape != right.shape:
        raise PracmaError("Matrices 'A' and 'B' must be of the same size.")
    u, _, v = r_svd(right.T @ left)
    rotation = u @ v.T
    aligned = right @ rotation
    residual = left - aligned
    distance = math.sqrt(float(np.sum(residual * residual)))
    return {"P": aligned, "Q": rotation, "d": distance}


def kabsch(A, B, w=None):
    if not is_r_numeric(A):
        raise PracmaError("is.numeric(A) is not TRUE")
    if not is_r_numeric(B):
        raise PracmaError("is.numeric(B) is not TRUE")
    left = np.asarray(A, dtype=float)
    right = np.asarray(B, dtype=float)
    if left.ndim != 2 or right.ndim != 2:
        raise PracmaError("Arguments 'A' and 'B' must be numeric matrices.")
    if left.shape != right.shape:
        raise PracmaError("Matrices 'A' and 'B' must be of the same size.")
    dimension, count = left.shape
    if w is None:
        weights = np.full((count, 1), 1.0 / count)
    else:
        if not is_r_numeric(w) or np.asarray(w).size != count:
            raise PracmaError("Argument 'w' must be a (column) vector of length ncol(A).")
        weights = np.asarray(w, dtype=float).reshape(-1, 1)
    centroid_a = left @ weights
    centroid_b = right @ weights
    ones_row = ones(1, count)
    centered_a = left - centroid_a @ ones_row
    centered_b = right - centroid_b @ ones_row
    weighted = zeros(dimension, count)
    for index in range(count):
        weighted[:, index] = weights[index, 0] * centered_a[:, index]
    u, _, v = r_svd(weighted @ centered_b.T)
    reflection = eye(dimension)
    if np.linalg.det(u @ v.T) < 0:
        reflection[-1, -1] = -1.0
    rotation = v @ reflection @ u.T
    translation = centroid_b - rotation @ centroid_a
    difference = rotation @ centered_a - centered_b
    lrms = np.zeros((1, 1))
    for index in range(count):
        column = difference[:, index]
        lrms = lrms + weights[index, 0] * float(column @ column)
    return {
        "U": rotation,
        "R": np.asarray(translation, dtype=float).reshape(-1, 1),
        "d": np.sqrt(lrms),
    }
