"""Separate polynomial fits for the coordinates of a curve."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric, lsqlin, polyval


def curvefit(u, x, y, n, U=None, V=None):
    if not is_r_numeric(u) or not is_r_numeric(x) or not is_r_numeric(y):
        raise PracmaError("is.numeric(u) is not TRUE")
    abscissa = np.asarray(u, dtype=float).reshape(-1)
    east = np.asarray(x, dtype=float).reshape(-1)
    north = np.asarray(y, dtype=float).reshape(-1)
    if east.size != abscissa.size or north.size != abscissa.size:
        raise PracmaError("Vectors 'x' and 'y' must have the same length as 't'.")
    if not is_r_numeric(n) or np.asarray(n).size != 1 or float(n) != math.floor(float(n)) or float(n) < 1:
        raise PracmaError("Argument 'n' must be an integer greater or equal 1.")
    degree = int(n)
    powers = np.arange(degree, -1, -1)
    design = abscissa[:, None] ** powers[None, :]
    if U is None or V is None:
        px = lsqlin(design, east)
        py = lsqlin(design, north)
    else:
        knots = np.asarray(U, dtype=float).reshape(-1)
        values = np.asarray(V, dtype=float)
        constraint = knots[:, None] ** powers[None, :]
        px = lsqlin(design, east, constraint, values[:, 0])
        py = lsqlin(design, north, constraint, values[:, 1])
    return {
        "xp": polyval(np.asarray(px).reshape(-1), abscissa),
        "yp": polyval(np.asarray(py).reshape(-1), abscissa),
        "px": np.asarray(px, dtype=float).reshape(-1, 1),
        "py": np.asarray(py, dtype=float).reshape(-1, 1),
    }
