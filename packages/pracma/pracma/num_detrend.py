"""Remove a constant or piecewise linear trend."""

from __future__ import annotations

import warnings

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import column_matrix, pmatch, qr_solve, r_length


def detrend(x, tt="linear", bp=None):
    array = np.asarray(x)
    if not (np.iscomplexobj(array) or np.issubdtype(array.dtype, np.number)) or array.dtype == bool:
        raise PracmaError("'x' must be a numeric or complex vector or matrix.")
    trend = pmatch(tt, ("constant", "linear"))
    if array.ndim <= 1:
        values = column_matrix(np.real(array) if not np.iscomplexobj(array) else array)
    else:
        values = np.array(array, dtype=complex if np.iscomplexobj(array) else float, copy=True)
    rows = values.shape[0]
    if bp is not None and r_length(bp) > 0 and not np.all(np.isin(np.asarray(bp), np.arange(1, rows + 1))):
        raise PracmaError("Breakpoints 'bp' must elements of 1:length(x).")
    if trend == 1:
        if bp is not None:
            warnings.warn("Breakpoints not used for 'constant' trend type.", stacklevel=2)
        means = np.mean(values, axis=0)
        return values - means.reshape(1, -1)
    if trend == 2:
        breaks = np.asarray([] if bp is None else bp, dtype=float).reshape(-1)
        knots = np.unique(np.concatenate([[0.0], breaks, [rows - 1]]))
        knots.sort()
        pieces = knots.size - 1
        design = np.zeros((rows, pieces + 1), dtype=float)
        design[:, -1] = 1.0
        for index in range(pieces):
            start = int(knots[index])
            length = rows - start
            design[start:start + length, index] = np.arange(1, length + 1) / length
        fitted = design @ qr_solve(design, values)
        if fitted.ndim == 1:
            fitted = fitted.reshape(-1, 1)
        return values - fitted
    raise PracmaError("Trend type 'tt' must be 'constant' or 'linear'.")
