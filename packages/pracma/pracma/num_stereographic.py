"""Stereographic projection and its inverse."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.arrays import zeros
from pracma.num_helpers import column_matrix, is_r_numeric, repmat


def stereographic(p):
    if not is_r_numeric(p):
        raise PracmaError("is.numeric(p) is not TRUE")
    points = column_matrix(p)
    rows, cols = points.shape
    scale = 2.0 / (1.0 + points[rows - 1, :])
    tiled = repmat(scale, rows, 1)
    pole = np.asarray(zeros(rows, 1), dtype=float)
    pole[rows - 1, 0] = -1.0
    shift = repmat(pole, 1, cols)
    return tiled * points + (1.0 - tiled) * shift


def stereographic_inv(q):
    if not is_r_numeric(q):
        raise PracmaError("is.numeric(q) is not TRUE")
    points = column_matrix(q)
    rows, cols = points.shape
    pole = np.asarray(zeros(rows, 1), dtype=float)
    pole[rows - 1, 0] = -1.0
    shift = repmat(pole, 1, cols)
    height = points[:rows - 1, :] ** 2
    scale = 4.0 / (4.0 + np.sum(height, axis=0))
    tiled = repmat(scale, rows, 1)
    return tiled * points + (1.0 - tiled) * shift[:rows, :cols]
