"""Intersection area of axis-aligned rectangles."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric, is_r_vector


def rectint(x, y):
    if not is_r_numeric(x):
        raise PracmaError("is.numeric(x) is not TRUE")
    if not is_r_numeric(y):
        raise PracmaError("is.numeric(y) is not TRUE")
    left = np.asarray(x, dtype=float)
    right = np.asarray(y, dtype=float)
    if is_r_vector(x) and left.size == 4 and is_r_vector(y) and right.size == 4:
        a = left.reshape(-1)
        b = right.reshape(-1)
        if np.any(np.array([a[2], a[3], b[2], b[3]]) < 0):
            raise PracmaError("All widths and heights must be greater than 0.")
        if a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0] or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1]:
            return 0.0
        if a[0] > b[0]:
            a, b = b, a
        z1 = b[0]
        z2 = max(a[1], b[1])
        z3 = min(a[0] + a[2], b[0] + b[2])
        z4 = min(a[1] + a[3], b[1] + b[3])
        return float((z3 - z1) * (z4 - z2))
    if left.ndim == 2 and left.shape[1] == 4 and right.ndim == 2 and right.shape[1] == 4:
        area = np.empty((left.shape[0], right.shape[0]))
        for i in range(left.shape[0]):
            for j in range(right.shape[0]):
                area[i, j] = rectint(left[i], right[j])
        return area
    raise PracmaError("All lengths and no. of matrix columns must be equal to 4.")
