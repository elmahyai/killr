"""Algebraic circle fit."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric, is_r_vector, qr_solve


def circlefit(xp, yp):
    if not (is_r_vector(xp) and is_r_numeric(xp)) or not (is_r_vector(yp) and is_r_numeric(yp)):
        raise PracmaError("Arguments 'xp' and 'yp' must be numeric vectors.")
    x = np.asarray(xp, dtype=float).reshape(-1)
    y = np.asarray(yp, dtype=float).reshape(-1)
    if x.size != y.size:
        raise PracmaError("Vectors 'xp' and 'yp' must be of the same length.")
    design = np.column_stack([x, y, np.ones(x.size)])
    coeff = qr_solve(design, x ** 2 + y ** 2)
    center_x = coeff[0] / 2.0
    center_y = coeff[1] / 2.0
    radius = np.sqrt((coeff[0] ** 2 + coeff[1] ** 2) / 4.0 + coeff[2])
    fitted = np.array([center_x, center_y, radius], dtype=float)
    rms = float(np.sqrt(np.sum((np.sqrt((x - fitted[0]) ** 2 + (y - fitted[1]) ** 2) - fitted[2]) ** 2) / x.size))
    print(f"RMS error: {rms}")
    return fitted
