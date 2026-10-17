"""Polygon area, center, length, and segment crossings."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.interp_support import is_number_or_complex, is_numeric_value, is_r_matrix, repmat, stopifnot, which_arr


def polyarea(x, y):
    if (x is None or np.asarray(x).size == 0) and (y is None or np.asarray(y).size == 0):
        return np.array([0.0])
    if not is_number_or_complex(x) or not is_number_or_complex(y):
        raise PracmaError("Arguments 'x' and 'y' must be real or complex.")
    left = np.asarray(x, dtype=float)
    right = np.asarray(y, dtype=float)
    if left.ndim <= 1:
        left = left.reshape(-1, 1)
    if right.ndim <= 1:
        right = right.reshape(-1, 1)
    if left.shape != right.shape:
        raise PracmaError("Matrices 'x' and 'y' must be of same size.")
    rows, cols = left.shape
    areas = np.zeros(cols)
    for i in range(cols):
        xi = left[:, i]
        yi = right[:, i]
        forward = np.sum(xi[:-1] * yi[1:]) + xi[-1] * yi[0]
        backward = np.sum(xi[1:] * yi[:-1]) + xi[0] * yi[-1]
        areas[i] = 0.5 * (forward - backward)
    return areas


def poly_center(x, y):
    stopifnot(is_numeric_value(x), "is.numeric(x)")
    stopifnot(is_numeric_value(y), "is.numeric(y)")
    horizontal = np.asarray(x, dtype=float).reshape(-1)
    vertical = np.asarray(y, dtype=float).reshape(-1)
    if vertical.size != horizontal.size or horizontal.size <= 2:
        raise PracmaError("Arguments 'x' and 'y' must be of the same length >= 3.")
    area = float(np.asarray(polyarea(horizontal, vertical)).reshape(-1)[0])
    if area == 0:
        return np.array([np.nan, np.nan])
    x1 = horizontal[:-1]
    x2 = horizontal[1:]
    y1 = vertical[:-1]
    y2 = vertical[1:]
    xy = x1 * y2 - x2 * y1
    return (1 / area / 6) * np.array([np.sum((x1 + x2) * xy), np.sum((y1 + y2) * xy)])


def poly_length(x, y):
    stopifnot(is_numeric_value(x), "is.numeric(x)")
    stopifnot(is_numeric_value(y), "is.numeric(y)")
    points = np.column_stack([np.asarray(x, dtype=float).reshape(-1), np.asarray(y, dtype=float).reshape(-1)])
    steps = np.diff(points, axis=0)
    return np.array([np.sum(np.sqrt(np.sum(steps**2, axis=1)))])


def _dd(x, y):
    x1 = x[:, :-1]
    x2 = x[:, 1:]
    if x1.ndim == 1:
        raise PracmaError("Arguments 'n' and 'm' must be single integers.")
    column = np.asarray(y, dtype=float).reshape(-1, 1)
    y1 = repmat(column, 1, x1.shape[1])
    return (x1 - y1) * (x2 - y1)


def poly_crossings(L1, L2):
    stopifnot(is_numeric_value(L1), "is.numeric(L1)")
    stopifnot(is_numeric_value(L2), "is.numeric(L2)")
    if not is_r_matrix(L1) or not is_r_matrix(L2) or np.asarray(L1).shape[0] != 2 or np.asarray(L2).shape[0] != 2:
        raise PracmaError("Arguments 'L1', 'L2' must be matrices with 2 rows.")
    first = np.asarray(L1, dtype=float)
    second = np.asarray(L2, dtype=float)
    x1 = first[0, :]
    x2 = second[0, :]
    y1 = first[1, :]
    y2 = second[1, :]
    dx1 = np.diff(x1)
    dy1 = np.diff(y1)
    dx2 = np.diff(x2)
    dy2 = np.diff(y2)
    n1 = x1.size
    n2 = x2.size
    s1 = dx1 * y1[:-1] - dy1 * x1[:-1]
    s2 = dx2 * y2[:-1] - dy2 * x2[:-1]
    x_outer = np.multiply.outer(dx1, y2) - np.multiply.outer(dy1, x2)
    y_outer = np.multiply.outer(y1, dx2) - np.multiply.outer(x1, dy2)
    c1 = _dd(x_outer, s1)
    c2 = _dd(y_outer.T, s2).T
    rows, cols = which_arr((c1 <= 0) & (c2 <= 0))
    if rows.size == 0:
        return None
    i = rows - 1
    j = cols - 1
    denom = dy2[j] * dx1[i] - dy1[i] * dx2[j]
    keep = denom != 0
    i = i[keep]
    j = j[keep]
    denom = denom[keep]
    points = np.column_stack(
        [
            (dx2[j] * s1[i] - dx1[i] * s2[j]) / denom,
            (dy2[j] * s1[i] - dy1[i] * s2[j]) / denom,
        ]
    )
    return points
