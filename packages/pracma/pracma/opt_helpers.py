"""Private numeric helpers for the pracma optimization ports."""

from __future__ import annotations

import math
import warnings

import numpy as np

from pracma._util import PracmaError, as_1d

_EPS = float(np.finfo(float).eps)
_XMAX = float(np.finfo(float).max)
_MISSING = object()


def _warn(message: str) -> None:
    warnings.warn(message, RuntimeWarning, stacklevel=3)


def _is_numeric(value) -> bool:
    if value is None or isinstance(value, (bool, np.bool_)):
        return False
    if isinstance(value, (int, float, np.integer, np.floating)):
        return True
    array = np.asarray(value)
    if array.dtype == object or array.dtype == bool:
        return False
    return np.issubdtype(array.dtype, np.number) and not np.issubdtype(
        array.dtype, np.complexfloating
    )


def _is_complex(value) -> bool:
    if isinstance(value, complex):
        return True
    if value is None or isinstance(value, (bool, np.bool_)):
        return False
    array = np.asarray(value)
    return array.dtype != object and np.issubdtype(array.dtype, np.complexfloating)


def _scalar(value) -> float:
    array = np.asarray(value, dtype=float).reshape(-1)
    if array.size != 1:
        raise PracmaError("function value must have length 1")
    return float(array[0])


def _vector_value(fun, x):
    return as_1d(fun(x))


def _identical(left, right) -> bool:
    a = np.asarray(left, dtype=float).reshape(-1)
    b = np.asarray(right, dtype=float).reshape(-1)
    if a.shape != b.shape:
        return False
    both_nan = np.isnan(a) & np.isnan(b)
    return bool(np.all(both_nan | (a == b)))


def _match_one(arg, choices):
    if arg is None:
        return choices[0]
    text = str(arg)
    hits = [choice for choice in choices if choice.startswith(text)]
    if len(hits) != 1:
        quoted = ", ".join("\u201c" + choice + "\u201d" for choice in choices)
        raise PracmaError(f"'{text}' should be one of {quoted}")
    return hits[0]


def _grad(f, x0, heps=_EPS ** (1.0 / 3.0)):
    if not _is_numeric(x0):
        raise PracmaError("Argument 'x0' must be a numeric value.")
    point = as_1d(x0)
    if _vector_value(f, point).size != 1:
        raise PracmaError("Function 'f' must be a univariate function of 2 variables.")
    step = np.zeros(point.size)
    gradient = np.zeros(point.size)
    for i in range(point.size):
        step[i] = heps
        gradient[i] = (_scalar(f(point + step)) - _scalar(f(point - step))) / (2.0 * heps)
        step[i] = 0.0
    return gradient


def _jacobian(f, x0, heps=_EPS ** (1.0 / 3.0)):
    point = as_1d(x0)
    if point.size == 0 or not _is_numeric(point):
        raise PracmaError("Argument 'x' must be a non-empty numeric vector.")
    base = _vector_value(f, point)
    jacob = np.zeros((base.size, point.size))
    step = np.zeros(point.size)
    for i in range(point.size):
        step[i] = heps
        jacob[:, i] = (_vector_value(f, point + step) - _vector_value(f, point - step)) / (2.0 * heps)
        step[i] = 0.0
    return jacob


def _fderiv(f, x, n=1, h=0.0):
    order = math.floor(float(n))
    if order < 0:
        raise PracmaError("The order of the derivative, 'n', can only be between 0 and 8.")
    if order > 8:
        _warn("Numerical derivatives of order 'n > 8' will be very inexact.")
    point = float(x)
    if order == 0:
        return _scalar(f(point))
    if h == 0:
        h = _EPS ** (1.0 / (order + 2))
    if order == 1:
        return (_scalar(f(point + h)) - _scalar(f(point - h))) / (2.0 * h)
    if order == 2:
        return (_scalar(f(point + h)) - 2.0 * _scalar(f(point)) + _scalar(f(point - h))) / h**2
    raise PracmaError("Unknown 'method'; use 'central', 'forward' or 'backward' instead.")


def _horner(p, x):
    coeff = as_1d(p)
    points = np.atleast_1d(np.asarray(x, dtype=float))
    if coeff.size == 0 or points.size == 0:
        return None
    if coeff.size == 1:
        return {"y": np.full(points.shape, coeff[0]), "dy": np.zeros(points.shape)}
    y = np.full(points.shape, coeff[0])
    dy = np.zeros(points.shape)
    for value in coeff[1:]:
        dy = dy * points + y
        y = y * points + value
    if points.shape == ():
        return {"y": float(y), "dy": float(dy)}
    return {"y": y, "dy": dy}


def _hornerdefl(p, x):
    coeff = as_1d(p)
    root = float(np.asarray(x, dtype=float).reshape(-1)[0])
    if coeff.size == 0:
        return None
    degree = coeff.size - 1
    quotient = np.zeros(degree + 1)
    quotient[0] = coeff[0]
    for j in range(1, degree + 1):
        quotient[j] = coeff[j] + quotient[j - 1] * root
    return {"y": float(quotient[degree]), "q": quotient[:degree].copy()}


def _inv(a):
    matrix = np.asarray(a, dtype=float)
    if matrix.size == 0:
        return np.zeros((0, 0))
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise PracmaError("Matrix 'a' must be square.")
    try:
        return np.linalg.inv(matrix)
    except np.linalg.LinAlgError:
        _warn("Matrix appears to be singular.")
        return np.full(matrix.shape, np.inf)


def _pinv(a, tol=_EPS ** (2.0 / 3.0)):
    matrix = np.asarray(a, dtype=float)
    if matrix.ndim != 2:
        raise PracmaError("is.matrix(A) is not TRUE")
    u, singular, vh = np.linalg.svd(matrix, full_matrices=False)
    if singular.size == 0:
        return np.zeros((matrix.shape[1], matrix.shape[0]))
    keep = singular > max(tol * singular[0], 0.0)
    if np.all(keep):
        return vh.T * (1.0 / singular) @ u.T
    if np.any(keep):
        return vh.T[:, keep] * (1.0 / singular[keep]) @ u.T[keep, :]
    return np.zeros((matrix.shape[1], matrix.shape[0]))


def _nullspace(m):
    matrix = np.asarray(m, dtype=float)
    if matrix.ndim == 1:
        matrix = matrix.reshape(-1, 1)
    if matrix.ndim != 2:
        raise PracmaError("Argument 'M' must be a numeric matrix.")
    q_factor, r_factor = np.linalg.qr(matrix.T, mode="complete")
    diagonal = np.abs(np.diag(r_factor)) if r_factor.size else np.array([])
    if diagonal.size == 0 or diagonal[0] == 0:
        rank = 0
    else:
        rank = int(np.sum(diagonal > 1e-7 * diagonal[0]))
    if rank == matrix.shape[1]:
        return None
    basis = q_factor if rank == 0 else q_factor[:, rank:]
    if basis.size == 0:
        return None
    return basis


def _repmat(a, n, m=None):
    if m is None:
        m = n
    array = np.asarray(a, dtype=float)
    if array.size == 0:
        return np.array([])
    if array.ndim == 1:
        array = array.reshape(1, -1)
    rows = max(math.floor(float(n)), 0)
    cols = max(math.floor(float(m)), 0)
    if rows <= 0 or cols <= 0:
        return np.zeros((rows, cols))
    return np.tile(array, (rows, cols))


def _lstsq(a, b):
    matrix = np.asarray(a, dtype=float)
    rhs = np.asarray(b, dtype=float).reshape(-1)
    if matrix.ndim == 1:
        matrix = matrix.reshape(-1, 1)
    solution, *_ = np.linalg.lstsq(matrix, rhs, rcond=None)
    return solution


def _solve(a, b):
    matrix = np.asarray(a, dtype=float)
    rhs = np.asarray(b, dtype=float)
    if rhs.ndim == 2 and 1 in rhs.shape:
        rhs = rhs.reshape(-1)
    return np.linalg.solve(matrix, rhs)


def _spectral_norm(a):
    matrix = np.atleast_2d(np.asarray(a, dtype=float))
    singular = np.linalg.svd(matrix, compute_uv=False)
    return float(singular[0]) if singular.size else 0.0


def _frobenius(a):
    values = np.asarray(a, dtype=float).reshape(-1)
    return float(np.sqrt(np.sum(values * values)))


def _inf_norm(a):
    matrix = np.atleast_2d(np.asarray(a, dtype=float))
    if matrix.size == 0:
        return 0.0
    return float(np.max(np.sum(np.abs(matrix), axis=1)))


def _mdhess(h_matrix, gk):
    hessian = np.array(h_matrix, dtype=float, copy=True)
    gradient = np.asarray(gk, dtype=float).reshape(-1, 1)
    n = gradient.shape[0]
    lower = np.zeros((n, n))
    diagonal = np.zeros((n, n))
    h00 = hessian[0, 0] if hessian[0, 0] > 0 else 1.0
    for k in range(1, n):
        m = k - 1
        lower[m, m] = 1.0
        if hessian[m, m] <= 0:
            hessian[m, m] = h00
        for i in range(k, n):
            lower[i, m] = -hessian[i, m] / hessian[m, m]
            hessian[i, m] = 0.0
            for j in range(k, n):
                hessian[i, j] = hessian[i, j] + lower[i, m] * hessian[m, j]
        if hessian[k, k] > 0 and hessian[k, k] < h00:
            h00 = hessian[k, k]
    lower[n - 1, n - 1] = 1.0
    if hessian[n - 1, n - 1] <= 0:
        hessian[n - 1, n - 1] = h00
    for i in range(n):
        diagonal[i, i] = hessian[i, i]
    yk = -lower @ gradient
    direction = lower.T @ ((1.0 / np.diag(diagonal))[:, None] * yk)
    return direction.reshape(-1)
