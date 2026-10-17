"""Point-in-polygon test."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric


def inpolygon(x, y, xp, yp, boundary=False):
    if not is_r_numeric(x):
        raise PracmaError("is.numeric(x) is not TRUE")
    if not is_r_numeric(y):
        raise PracmaError("is.numeric(y) is not TRUE")
    x_array = np.asarray(x, dtype=float)
    y_array = np.asarray(y, dtype=float)
    if x_array.size != y_array.size:
        raise PracmaError("length(x) == length(y) is not TRUE")
    if not is_r_numeric(xp):
        raise PracmaError("is.numeric(xp) is not TRUE")
    if not is_r_numeric(yp):
        raise PracmaError("is.numeric(yp) is not TRUE")
    poly_x = np.asarray(xp, dtype=float).reshape(-1)
    poly_y = np.asarray(yp, dtype=float).reshape(-1)
    if poly_x.size != poly_y.size:
        raise PracmaError("length(xp) == length(yp) is not TRUE")
    if poly_x.size == 0 or poly_x[0] != poly_x[-1] or poly_y[0] != poly_y[-1]:
        poly_x = np.concatenate([poly_x, poly_x[:1]])
        poly_y = np.concatenate([poly_y, poly_y[:1]])
    flat_x = x_array.reshape(-1, order="F")
    flat_y = y_array.reshape(-1, order="F")
    inside = np.zeros(flat_x.size, dtype=bool)
    on_edge = np.zeros(flat_x.size, dtype=bool)
    previous = poly_x.size - 1
    for index in range(poly_x.size):
        dxp = poly_x[previous] - poly_x[index]
        dyp = poly_y[previous] - poly_y[index]
        dist = dxp * (flat_y - poly_y[index]) - (flat_x - poly_x[index]) * dyp
        crossing = (
            ((poly_y[index] <= flat_y) & (flat_y < poly_y[previous]))
            | ((poly_y[previous] <= flat_y) & (flat_y < poly_y[index]))
        ) & (0 < dist * dyp)
        inside[crossing] = ~inside[crossing]
        touching = (
            ((poly_y[index] <= flat_y) & (flat_y <= poly_y[previous]))
            | ((poly_y[previous] <= flat_y) & (flat_y <= poly_y[index]))
        ) & (
            ((poly_x[index] <= flat_x) & (flat_x <= poly_x[previous]))
            | ((poly_x[previous] <= flat_x) & (flat_x <= poly_x[index]))
        ) & ((dist == 0) | (dxp == 0))
        on_edge[touching] = True
        previous = index
    if boundary:
        inside[on_edge] = True
    else:
        inside[on_edge] = False
    result = inside.astype(float).reshape(x_array.shape, order="F")
    return result
