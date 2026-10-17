"""Discrete gradient of a vector or a matrix."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric, is_r_vector, r_length


def _axis(h, count, name, noun):
    values = np.asarray(h, dtype=float).reshape(-1)
    if values.size == 1:
        step = float(values[0])
        return np.linspace(step, count * step, count)
    if values.size == count:
        return values
    raise PracmaError(f"Length of '{name}' must be 1 or equal to {noun} of 'F'.")


def gradient(F, h1=1, h2=1):
    if r_length(F) == 0:
        return None
    if not is_r_numeric(F):
        raise PracmaError("Argument 'F' must be a numeric vector or matrix.")
    if r_length(h1) == 0 or r_length(h2) == 0 or (
        r_length(h1) == 1 and float(np.asarray(h1).reshape(-1)[0]) == 0
    ) or (r_length(h2) == 1 and float(np.asarray(h2).reshape(-1)[0]) == 0):
        raise PracmaError("Arguments 'h1', 'h2' must be non-empty and non-zero.")
    if np.any(np.diff(np.asarray(h1, dtype=float).reshape(-1)) == 0) or np.any(
        np.diff(np.asarray(h2, dtype=float).reshape(-1)) == 0
    ):
        raise PracmaError("Arguments 'h1' and 'h2' must be strictly increasing.")
    if is_r_vector(F):
        values = np.asarray(F, dtype=float).reshape(-1)
        count = values.size
        if count == 1:
            return np.array([0.0])
        abscissa = _axis(h1, count, "h1", "length")
        slope = np.zeros(count)
        slope[0] = (values[1] - values[0]) / (abscissa[1] - abscissa[0])
        slope[-1] = (values[-1] - values[-2]) / (abscissa[-1] - abscissa[-2])
        if count > 2:
            slope[1:-1] = (values[2:] - values[:-2]) / (abscissa[2:] - abscissa[:-2])
        return slope
    array = np.asarray(F, dtype=float)
    if array.ndim != 2:
        raise PracmaError("Argument 'F' cannot be a higher-dimensional array.")
    rows, cols = array.shape
    abscissa = _axis(h1, cols, "h1", "ncol")
    ordinate = _axis(h2, rows, "h2", "nrow")
    gx = np.zeros_like(array)
    gy = np.zeros_like(array)
    gx[:, 0] = (array[:, 1] - array[:, 0]) / (abscissa[1] - abscissa[0])
    gx[:, -1] = (array[:, -1] - array[:, -2]) / (abscissa[-1] - abscissa[-2])
    if cols > 2:
        gx[:, 1:-1] = (array[:, 2:] - array[:, :-2]) / (abscissa[2:] - abscissa[:-2])
    gy[0, :] = (array[1, :] - array[0, :]) / (ordinate[1] - ordinate[0])
    gy[-1, :] = (array[-1, :] - array[-2, :]) / (ordinate[-1] - ordinate[-2])
    if rows > 2:
        gy[1:-1, :] = (array[2:, :] - array[:-2, :]) / (ordinate[2:] - ordinate[:-2])
    return {"X": gx, "Y": gy}
