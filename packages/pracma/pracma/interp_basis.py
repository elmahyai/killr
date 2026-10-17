"""Neville, Newton, Lagrange, barycentric, Chebyshev, and Bernstein."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.interp_poly import polyval
from pracma.interp_support import is_numeric_value, r_matrix, stopifnot
from pracma.numbers import nchoosek


def _pair(x, y):
    stopifnot(is_numeric_value(x), "is.numeric(x)")
    stopifnot(is_numeric_value(y), "is.numeric(y)")
    nodes = np.asarray(x, dtype=float).reshape(-1)
    values = np.asarray(y, dtype=float).reshape(-1)
    if nodes.size != values.size:
        raise PracmaError("Vectors 'x' and 'y' must be of the same length.")
    return nodes, values


def neville(x, y, xs):
    nodes, values = _pair(x, y)
    if not is_numeric_value(xs):
        raise PracmaError("Argument 'xs' must be empty or a numeric vector.")
    point = float(np.asarray(xs, dtype=float).reshape(-1)[0]) if np.asarray(xs).size else np.nan
    n = nodes.size
    column = values.copy()
    for k in range(1, n):
        column[: n - k] = (
            (point - nodes[k:n]) * column[: n - k] + (nodes[: n - k] - point) * column[1 : n - k + 1]
        ) / (nodes[: n - k] - nodes[k:n])
    return np.array([column[0]])


def newtonInterp(x, y, xs=None):
    nodes, values = _pair(x, y)
    if xs is None:
        xs = np.array([])
    if np.asarray(xs).size != 0 and not is_numeric_value(xs):
        raise PracmaError("Argument 'xs' must be empty or a numeric vector.")
    points = np.asarray(xs, dtype=float).reshape(-1)
    n = nodes.size
    divided = values.copy()
    for k in range(1, n):
        divided[k:n] = (divided[k:n] - divided[k - 1]) / (nodes[k:n] - nodes[k - 1])
    if points.size == 0:
        return divided
    estimate = np.full(points.shape, divided[n - 1])
    for k in range(1, n):
        estimate = divided[n - k - 1] + (points - nodes[n - k - 1]) * estimate
    return estimate


def lagrangeInterp(x, y, xs):
    nodes, values = _pair(x, y)
    if not is_numeric_value(xs):
        raise PracmaError("Argument 'xs' must be empty or a numeric vector.")
    points = np.asarray(xs, dtype=float).reshape(-1)
    n = nodes.size
    table = np.zeros((n, n))
    table[:, 0] = values
    for i in range(1, n):
        table[i:n, i] = (table[i:n, i - 1] - table[i - 1, i - 1]) / (nodes[i:n] - nodes[i - 1])
    estimate = table[n - 1, n - 1] * (points - nodes[n - 2]) + table[n - 2, n - 2]
    for i in range(2, n):
        estimate = estimate * (points - nodes[n - i - 1]) + table[n - i - 1, n - i - 1]
    return estimate


def barylag(xi, yi, x):
    if not (is_r_vector_numeric(xi) and is_r_vector_numeric(yi)):
        raise PracmaError("is.vector(xi, mode = \"numeric\") is not TRUE")
    if not is_numeric_value(x):
        raise PracmaError("Argument 'x' must be a numeric vector or matrix.")
    nodes = np.asarray(xi, dtype=float).reshape(-1)
    values = np.asarray(yi, dtype=float).reshape(-1)
    points = np.asarray(x, dtype=float)
    shape = points.shape if points.ndim == 2 else None
    flat = points.reshape(-1)
    n = nodes.size
    if values.size != n:
        raise PracmaError("Node vectors xi an yi must be of same length.")
    if np.min(flat) < np.min(nodes) or np.max(flat) > np.max(nodes):
        raise PracmaError("Some interpolation points outside the nodes.")
    grid = np.repeat(nodes.reshape(n, 1), n, axis=1)
    weights = 1.0 / np.prod(grid - grid.T + np.eye(n), axis=1)
    distance = flat.reshape(-1, 1) - nodes.reshape(1, -1)
    hit = np.argwhere(distance == 0)
    distance = distance.astype(float)
    distance[distance == 0] = np.nan
    weights_at = weights.reshape(1, -1) / distance
    estimated = (weights_at @ values) / np.sum(weights_at, axis=1)
    for row, col in hit:
        estimated[row] = values[col]
    if shape is not None:
        return estimated.reshape(shape)
    return estimated


def is_r_vector_numeric(value) -> bool:
    if not is_numeric_value(value):
        return False
    array = np.asarray(value)
    return array.ndim <= 1


def barylag2d(F, xn, yn, xf, yf):
    values = np.asarray(F, dtype=float)
    rows, cols = values.shape
    x_nodes = np.asarray(xn, dtype=float).reshape(-1)
    y_nodes = np.asarray(yn, dtype=float).reshape(-1)
    x_points = np.asarray(xf, dtype=float).reshape(-1)
    y_points = np.asarray(yf, dtype=float).reshape(-1)
    row_count = x_points.size
    col_count = y_points.size
    x_grid = np.kron(x_nodes.reshape(rows, 1), np.ones((1, rows)))
    y_grid = np.kron(y_nodes.reshape(cols, 1), np.ones((1, cols)))
    wx = np.kron((1.0 / np.prod(x_grid - x_grid.T + np.eye(rows), axis=1)).reshape(1, -1), np.ones((row_count, 1)))
    wy = np.kron((1.0 / np.prod(y_grid - y_grid.T + np.eye(cols), axis=1)).reshape(1, -1), np.ones((col_count, 1)))
    xdist = np.kron(x_points.reshape(row_count, 1), np.ones((1, rows))) - np.kron(
        x_nodes.reshape(1, rows), np.ones((row_count, 1))
    )
    ydist = np.kron(y_points.reshape(col_count, 1), np.ones((1, cols))) - np.kron(
        y_nodes.reshape(1, cols), np.ones((col_count, 1))
    )
    eps = np.finfo(float).eps
    xdist[xdist == 0] = eps
    ydist[ydist == 0] = eps
    hx = wx / xdist
    hy = wy / ydist
    row_sum = np.sum(hx, axis=1).reshape(row_count, 1)
    col_sum = np.sum(hy, axis=1).reshape(1, col_count)
    numerator = hx @ values @ hy.T
    denominator = np.kron(row_sum, np.ones((1, col_count))) * np.kron(col_sum, np.ones((row_count, 1)))
    return numerator / denominator


def chebPoly(n, x=None):
    stopifnot(is_numeric_value(n) and np.asarray(n).size == 1, "is.numeric(n)")
    degree = float(np.asarray(n).reshape(-1)[0])
    stopifnot(math.floor(degree) == math.ceil(degree) and degree >= 0, "floor(n) == ceiling(n)")
    degree = int(degree)
    width = max(2, degree + 1)
    table = np.zeros((width, width))
    table[0, 0] = 1
    table[1, 1] = 1
    if degree >= 2:
        for i in range(2, width):
            shifted = np.concatenate([np.array([0.0]), table[i - 1, : width - 1]])
            table[i, :] = 2 * shifted - table[i - 2, :]
    table = table[:, ::-1]
    if x is None:
        return table
    if not is_numeric_value(x):
        raise PracmaError("Argument 'x' must be a numeric vector.")
    return polyval(table[degree, :], x)


def chebCoeff(fun, a, b, n):
    count = int(n) + 1
    c1 = 0.5 * (float(b) - float(a))
    c2 = 0.5 * (float(b) + float(a))
    k = np.arange(count, dtype=float)
    angles = np.cos(np.pi * (k + 0.5) / count)
    samples = np.asarray(fun(c1 * angles + c2), dtype=float).reshape(-1)
    scale = 2.0 / count
    nodes = (k + 0.5).reshape(count, 1)
    transform = np.cos(np.pi / count * (nodes @ k.reshape(1, -1)))
    coeffs = scale * (samples.reshape(1, -1) @ transform)
    tiny = 2 * np.finfo(float).eps
    coeffs = np.where(np.abs(coeffs) < tiny, 0.0, coeffs)
    return coeffs.reshape(-1)


def chebApprox(x, fun, a, b, n):
    basis = chebPoly(n)
    coeffs = chebCoeff(fun, a, b, n)
    polynomial = coeffs @ basis
    mapped = (2 * np.asarray(x, dtype=float) - (float(b) + float(a))) / (float(b) - float(a))
    return polyval(polynomial, mapped) - coeffs[0] / 2


def _in_unit(x) -> None:
    points = np.asarray(x, dtype=float).reshape(-1)
    if points.size > 1:
        raise PracmaError("'length = 2' in coercion to 'logical(1)'" if points.size == 2 else f"'length = {points.size}' in coercion to 'logical(1)'")
    if points.size == 1 and (points[0] < -1.0 or points[0] > 1.0):
        raise PracmaError("Elements of argument 'x' must all lie in [0, 1].")


def bernstein(f, n, x):
    stopifnot(callable(f), "is.function(f)")
    stopifnot(is_numeric_value(n), "is.numeric(n)")
    stopifnot(is_numeric_value(x), "is.numeric(x)")
    degree = float(np.asarray(n).reshape(-1)[0])
    if math.floor(degree) != math.ceil(degree) or degree < 0:
        raise PracmaError("Argument 'n' must be a nonnegative integer.")
    _in_unit(x)
    degree = int(degree)
    points = np.asarray(x, dtype=float).reshape(-1)
    if points.size == 1:
        point = float(points[0])
        stage = np.array([float(np.asarray(f(k / degree)).reshape(-1)[0]) for k in range(degree + 1)])
        for j in range(1, degree + 1):
            previous = stage
            width = degree - j + 1
            stage = stage.copy()
            stage[:width] = previous[:width] * (1 - point) + previous[1 : width + 1] * point
        return np.array([stage[0]])
    total = 0.0
    for k in range(degree + 1):
        total = total + nchoosek(degree, k) * points**k * (1 - points) ** (degree - k) * float(f(k / degree))
    return total


def bernsteinb(k, n, x):
    stopifnot(is_numeric_value(k), "is.numeric(k)")
    stopifnot(is_numeric_value(n), "is.numeric(n)")
    stopifnot(is_numeric_value(x), "is.numeric(x)")
    degree = float(np.asarray(n).reshape(-1)[0])
    index = float(np.asarray(k).reshape(-1)[0])
    if math.floor(degree) != math.ceil(degree) or degree < 0:
        raise PracmaError("Argument 'n' must be a nonnegative integer.")
    if math.floor(index) != math.ceil(index) or index < 0 or index > degree:
        raise PracmaError("Argument 'k' must be an integer between 0 and 'n'.")
    _in_unit(x)
    points = np.asarray(x, dtype=float).reshape(-1)
    return nchoosek(int(degree), int(index)) * points**int(index) * (1 - points) ** int(degree - index)
