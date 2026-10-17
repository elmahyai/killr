"""Polynomial and rational fitting, Padé, Savitzky-Golay, and Taylor."""

from __future__ import annotations

import math
import warnings

import numpy as np

from pracma._util import PracmaError
from pracma.arrays import finds, ones
from pracma.interp_basis import chebCoeff, chebPoly
from pracma.interp_poly import Poly, polyadd, polyder, polypow, polytrans, polyval
from pracma.interp_roots import roots
from pracma.interp_support import (
    convolve_open,
    fact,
    fderiv,
    fnorm,
    is_numeric_value,
    is_r_vector,
    match_arg,
    nullspace,
    pinv,
    qr_solve,
    stopifnot,
    toeplitz,
    zapsmall,
)
from pracma.interp_sort import is_sorted


def polyfit(x, y, n=1):
    if not is_numeric_value(x) or not is_numeric_value(y):
        raise PracmaError("Arguments x and y must be numeric.")
    if np.asarray(x).size != np.asarray(y).size:
        raise PracmaError("Vectors/matrices x and y must be of same length.")
    if n is None or float(n) < 0 or math.ceil(float(n)) != math.floor(float(n)):
        raise PracmaError("Degree n must be a non-negative integer.")
    degree = int(math.floor(float(n)))
    abscissa = np.asarray(x, dtype=float).reshape(-1)
    ordinate = np.asarray(y, dtype=float).reshape(-1)
    design = abscissa.reshape(-1, 1) ** np.arange(degree, -1, -1)
    return qr_solve(design, ordinate)


def polyfix(x, y, n, xfix, yfix):
    stopifnot(is_numeric_value(x), "is.numeric(x)")
    stopifnot(is_numeric_value(y), "is.numeric(y)")
    stopifnot(is_numeric_value(xfix), "is.numeric(xfix)")
    stopifnot(is_numeric_value(yfix), "is.numeric(yfix)")
    abscissa = np.asarray(x, dtype=float).reshape(-1)
    ordinate = np.asarray(y, dtype=float).reshape(-1)
    fixed_x = np.asarray(xfix, dtype=float).reshape(-1)
    fixed_y = np.asarray(yfix, dtype=float).reshape(-1)
    if ordinate.size != abscissa.size:
        raise PracmaError("Arguments 'x' and 'y' must have the same length.")
    if fixed_y.size != fixed_x.size:
        raise PracmaError("Arguments 'xfix' and 'yfix' must have the same length.")
    if not is_numeric_value(n) or float(n) < 0 or math.floor(float(n)) != math.ceil(float(n)):
        raise PracmaError("Argument 'n' must be an integer.")
    degree = int(n)
    nfix = fixed_x.size
    if degree < nfix - 1:
        raise PracmaError("Argument 'n' shall be greater or equal to 'nfix-1'.")
    if degree == nfix - 1:
        warnings.warn("Data points can not be taken into account.", stacklevel=2)
        return polyfit(fixed_x, fixed_y, degree)
    design = ones(nfix, degree + 1)
    for i in range(degree + 1):
        design[:, i] = fixed_x ** (degree - i)
    low = qr_solve(design[:, degree + 1 - nfix :], fixed_y)
    full = np.zeros((degree + 1, 1))
    full[degree + 1 - nfix :, 0] = low
    fitted = ordinate - polyval(low, abscissa)
    basis = nullspace(design)
    vandermonde = np.zeros((abscissa.size, degree + 1))
    for i in range(degree + 1):
        vandermonde[:, i] = abscissa ** (degree - i)
    correction = qr_solve(vandermonde @ basis, fitted)
    particular = basis @ correction.reshape(-1, 1)
    return (particular + full).reshape(-1)


def ratinterp(x, y, xs=None):
    if not (is_r_vector(x) and is_numeric_value(x) and is_r_vector(y) and is_numeric_value(y)):
        raise PracmaError("Arguments 'x' and 'y' must be numeric vectors.")
    nodes = np.asarray(x, dtype=float).reshape(-1)
    values = np.asarray(y, dtype=float).reshape(-1)
    if values.size != nodes.size:
        raise PracmaError("Arguments 'x' and 'y' must be vectors of the same length.")
    if nodes.size <= 2:
        raise PracmaError("Arguments 'x', 'y' must have at least a length >= 3.")
    if not bool(is_sorted(nodes)[0] == 1):
        raise PracmaError("Argument 'x' must be a sorted vector")
    if xs is None:
        xs = nodes
    points = np.asarray(xs, dtype=float).reshape(-1)
    result = np.zeros(points.size)
    m = nodes.size
    for h, point in enumerate(points):
        on_node = False
        for i in range(m):
            if point - nodes[i] == 0:
                result[h] = values[i]
                on_node = True
        if on_node:
            continue
        table = np.zeros((m, m))
        table[:, 0] = values
        for i in range(m - 1):
            difference = table[i + 1, 0] - table[i, 0]
            ratio = (point - nodes[i]) / (point - nodes[i + 1])
            denom = ratio * (1 - difference / table[i + 1, 0]) - 1
            table[i, 1] = table[i + 1, 0] + difference / denom
        for j in range(2, m):
            for i in range(m - j):
                difference = table[i + 1, j - 1] - table[i, j - 1]
                ratio = (point - nodes[i]) / (point - nodes[i + j])
                if difference == 0:
                    table[i, j] = table[i + 1, j - 1]
                else:
                    previous = table[i + 1, j - 1] - table[i + 1, j - 2]
                    denom = ratio * (previous - difference) - previous
                    table[i, j] = table[i + 1, j - 1] + difference * previous / denom
        result[h] = table[0, m - 1]
    return result


def pade(p1, p2=None, d1=5, d2=5):
    if p2 is None:
        p2 = np.array([1.0])
    stopifnot(is_numeric_value(p1), "is.numeric(p1)")
    stopifnot(is_numeric_value(p2), "is.numeric(p2)")
    stopifnot(is_numeric_value(d1) and np.asarray(d1).size == 1, "is.numeric(d1)")
    degree1 = float(np.asarray(d1).reshape(-1)[0])
    degree2 = float(np.asarray(d2).reshape(-1)[0])
    stopifnot(math.floor(degree1) == math.ceil(degree1) and degree1 >= 0, "floor(d1) == ceiling(d1)")
    stopifnot(is_numeric_value(d2) and np.asarray(d2).size == 1, "is.numeric(d2)")
    stopifnot(math.floor(degree2) == math.ceil(degree2) and degree2 >= 0, "floor(d2) == ceiling(d2)")
    degree1 = int(degree1)
    degree2 = int(degree2)
    num = np.asarray(p1, dtype=float).reshape(-1)
    den = np.asarray(p2, dtype=float).reshape(-1)
    if degree1 == 0 and degree2 == 0:
        return {"r1": np.array([num[-1]]), "r2": np.array([den[-1]])}
    width = degree1 + degree2 + 3
    pad = np.zeros(width)
    den = np.concatenate([pad, den])[::-1][:width]
    num = np.concatenate([pad, num])[::-1][:width]
    span = degree1 + degree2
    left = toeplitz(den[:span])
    left[np.triu_indices(span, 1)] = 0
    right = toeplitz(num[:span])
    right[np.triu_indices(span, 1)] = 0
    columns = []
    if degree1 > 0:
        columns.append(left[:, :degree1])
    if degree2 > 0:
        columns.append(-right[:, :degree2])
    design = np.column_stack(columns) if columns else np.zeros((span, 0))
    target = den[0] * num[1 : span + 1] - num[0] * den[1 : span + 1]
    if design.size == 0:
        solved = np.array([])
    else:
        u, singular, vt = np.linalg.svd(design, full_matrices=True)
        rank = int(np.sum(singular > max(design.shape) * np.max(singular) * np.finfo(float).eps)) if singular.size else 0
        if rank == 0:
            inverse = np.zeros((design.shape[0], design.shape[0]))
        else:
            inverse = vt[:rank].T @ np.diag(1.0 / singular[:rank]) @ u[:, :rank].T
        solved = zapsmall(inverse @ target)
    numerator = np.concatenate([np.array([num[0]]), solved[:degree1]])[::-1]
    denominator = np.concatenate([np.array([den[0]]), solved[degree1:]])[::-1]
    scale = float(np.max(np.abs(denominator)))
    if scale == 0:
        scale = 1.0
    return {"r1": numerator / scale, "r2": denominator / scale}


def rationalfit(x, y, d1=5, d2=5):
    stopifnot(is_numeric_value(x), "is.numeric(x)")
    stopifnot(is_numeric_value(y), "is.numeric(y)")
    abscissa = np.asarray(x, dtype=float).reshape(-1)
    ordinate = np.asarray(y, dtype=float).reshape(-1)
    if abscissa.size <= 2:
        raise PracmaError("Length of arguments 'x' and 'y' must be greater than 2.")
    if ordinate.size != abscissa.size:
        raise PracmaError("Arguments 'x' ans 'y' must be of the same length.")
    if not bool(is_sorted(abscissa)[0] == 1):
        raise PracmaError("Argument 'x' must be a sorted vector")
    degree1 = int(d1)
    degree2 = int(d2)
    poles = []
    bad = finds(~np.isfinite(ordinate))
    while bad.size:
        index = int(bad[0]) - 1
        ordinate = ordinate * (abscissa - abscissa[index])
        ordinate = np.delete(ordinate, index)
        poles.append(abscissa[index])
        abscissa = np.delete(abscissa, index)
        if degree2 > 0:
            degree2 -= 1
        bad = finds(~np.isfinite(ordinate))
    numerator = abscissa.reshape(-1, 1) ** np.arange(degree1, -1, -1)
    denominator = ordinate.reshape(-1, 1) * (abscissa.reshape(-1, 1) ** np.arange(degree2, -1, -1))
    design = np.column_stack([numerator, -denominator])
    _u, _s, vt = np.linalg.svd(design, full_matrices=True)
    coeff = vt[-1, :]
    num = coeff[: degree1 + 1]
    den = coeff[degree1 + 1 :]
    scale = den[0] if den.size and den[0] != 0 else 1.0
    num = num / scale
    den = den / scale
    found = np.asarray(roots(den)).reshape(-1)
    recovered = Poly(np.concatenate([np.asarray(poles, dtype=float), found]))
    if np.all(np.imag(np.asarray(recovered, dtype=complex)) < np.finfo(float).eps):
        recovered = np.real(np.asarray(recovered, dtype=complex))
    largest = float(np.max(np.abs(recovered)))
    if largest == 0:
        largest = 1.0
    return {"p1": np.asarray(num, dtype=float) / largest, "p2": np.asarray(recovered, dtype=float) / largest}


def savgol(T, fl, forder=4, dorder=0):
    stopifnot(is_numeric_value(T), "is.numeric(T)")
    stopifnot(is_numeric_value(fl), "is.numeric(fl)")
    window = float(np.asarray(fl).reshape(-1)[0])
    if window <= 1 or window % 2 == 0:
        raise PracmaError("Argument 'fl' must be an odd integer greater than 1.")
    half = (window - 1) / 2
    design = np.arange(-half, half + 1).reshape(-1, 1) ** np.arange(0, int(forder) + 1)
    inverse = pinv(design)
    row = inverse[int(dorder), :]
    # convolve(T, rev(row), conj = TRUE) is the ordinary convolution with row.
    smoothed = np.convolve(np.asarray(T, dtype=float).reshape(-1), row, mode="full")
    start = int(half)
    smoothed = smoothed[start : smoothed.size - start]
    return ((-1) ** int(dorder)) * smoothed


def taylor(f, x0, n=4):
    if not is_numeric_value(x0):
        raise PracmaError("Argument 'x0' must be a numeric value or vector.")
    if not is_numeric_value(n) or np.asarray(n).size != 1 or math.floor(float(n)) != math.ceil(float(n)):
        raise PracmaError("Order 'n' must be an scalar integer between 1 and 8.")
    order = int(n)
    if order > 8:
        warnings.warn("Order 'n' is too high; should not be greater than 'n=8'.", stacklevel=2)
    elif order <= 0:
        order = 4
        warnings.warn("Order 'n' is too low; will be reset to the default 'n=4'.", stacklevel=2)
    origin = np.asarray(x0, dtype=float).reshape(-1)

    def call(at):
        return np.asarray(f(at), dtype=float).reshape(-1)

    series = call(origin)
    for i in range(1, order + 1):
        term = fderiv(call, origin, i) / np.asarray(fact(i)).reshape(-1) * polypow(np.array([1.0, -float(origin[0])]), i)
        series = polyadd(series, term)
    return series


def polyApprox(f, a, b, n):
    if (
        not is_numeric_value(a)
        or not is_numeric_value(b)
        or not is_numeric_value(n)
        or np.asarray(a).size != 1
        or np.asarray(b).size != 1
        or np.asarray(n).size != 1
        or float(a) >= float(b)
        or float(n) <= 0
    ):
        raise PracmaError("One of arguments 'a', 'b', or 'n' incorrectly chosen.")

    def mapped(x):
        return np.asarray(f(x), dtype=float).reshape(-1)

    basis = chebPoly(n)
    coeffs = chebCoeff(mapped, a, b, n)
    chebyshev = coeffs @ basis
    constant = coeffs[0]
    change = np.array([2.0, -(float(b) + float(a))]) / (float(b) - float(a))
    polynomial = polyadd(polytrans(chebyshev, change), np.array([-constant / 2]))

    def evaluate(x):
        return polyval(polynomial, x)

    precision = fnorm(mapped, evaluate, a, b, p=np.inf)
    return {"p": polynomial, "f": evaluate, "cheb.coeff": chebyshev, "estim.prec": np.array([precision])}
