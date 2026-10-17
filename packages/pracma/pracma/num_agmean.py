"""Arithmetic-geometric mean."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import r_length

_EPS = float(np.finfo(float).eps)


def _as_values(value):
    array = np.asarray(value)
    if np.iscomplexobj(array):
        return np.array(array, dtype=complex).reshape(-1)
    return np.array(array, dtype=float).reshape(-1)


def agmean(a, b):
    left = _as_values(a)
    right = _as_values(b)
    real_left = not np.iscomplexobj(left)
    real_right = not np.iscomplexobj(right)
    if (real_left and np.any(left < 0)) or (real_right and np.any(right < 0)):
        left = left.astype(complex)
        right = right.astype(complex)
    if left.size == 1:
        left = np.repeat(left, right.size)
    elif right.size == 1:
        right = np.repeat(right, left.size)
    elif left.size != right.size:
        raise PracmaError("Arguments must have the same length or one has length 1.")
    niter = 0
    while np.any(np.abs(left - right) >= _EPS):
        niter += 1
        a1 = (left + right) / 2
        b1 = np.sqrt(left * right)
        if np.max(np.abs(left - a1)) < _EPS and np.max(np.abs(right - b1)) < _EPS:
            break
        left = a1
        right = b1
    return {"agm": (left + right) / 2, "niter": int(niter), "prec": float(np.max(np.abs(right - left)))}
