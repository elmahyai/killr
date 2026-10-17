"""Cross product in n dimensions."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric, is_r_vector


def crossn(A):
    if not is_r_numeric(A):
        raise PracmaError("Argument 'A' must be numeric.")
    if is_r_vector(A) and np.asarray(A).size == 2:
        values = np.asarray(A, dtype=float).reshape(-1)
        return np.array([values[1], -values[0]])
    matrix = np.asarray(A, dtype=float)
    if matrix.ndim == 2 and matrix.shape[0] >= 2 and matrix.shape[1] == matrix.shape[0] + 1:
        width = matrix.shape[1]
        result = np.zeros(width)
        for index in range(width):
            minor = np.delete(matrix, index, axis=1)
            result[index] = ((-1.0) ** index) * float(np.linalg.det(minor))
        return result
    raise PracmaError("Matrix 'A' must be of size n x (n+1) with n >= 1.")
