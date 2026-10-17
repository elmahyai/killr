"""Three-dimensional cross product."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric, is_r_vector


def cross(x, y):
    if not is_r_numeric(x) or not is_r_numeric(y):
        raise PracmaError("Arguments 'x' and 'y' must be numeric vectors or matrices.")
    left = np.asarray(x, dtype=float)
    right = np.asarray(y, dtype=float)
    if is_r_vector(x) and is_r_vector(y):
        left = left.reshape(-1)
        right = right.reshape(-1)
        if left.size == right.size == 3:
            return np.array([
                left[1] * right[2] - left[2] * right[1],
                left[2] * right[0] - left[0] * right[2],
                left[0] * right[1] - left[1] * right[0],
            ])
        raise PracmaError("Vectors 'x' and 'y' must be both of length 3.")
    if left.ndim == 2 and right.ndim == 2:
        if left.shape != right.shape:
            raise PracmaError("Matrices 'x' and 'y' must be of same size.")
        if left.shape[1] == 3:
            return np.column_stack([
                left[:, 1] * right[:, 2] - left[:, 2] * right[:, 1],
                left[:, 2] * right[:, 0] - left[:, 0] * right[:, 2],
                left[:, 0] * right[:, 1] - left[:, 1] * right[:, 0],
            ])
        if left.shape[0] == 3:
            return np.vstack([
                left[1, :] * right[2, :] - left[2, :] * right[1, :],
                left[2, :] * right[0, :] - left[0, :] * right[2, :],
                left[0, :] * right[1, :] - left[1, :] * right[0, :],
            ])
        raise PracmaError("'x', 'y' must have one dimension of length 3.")
    raise PracmaError("Arguments 'x', 'y' must be vectors/matrices of same size.")
