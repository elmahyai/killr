"""LU factorization without and with partial pivoting."""

from __future__ import annotations

import warnings

import numpy as np

from pracma._util import PracmaError
from pracma.arrays import eye, zeros
from pracma.linalg_internal import is_matrix, is_numeric, match_arg
from pracma.linalg_tri import tril, triu


def _square(A, message):
    if not is_numeric(A):
        raise PracmaError("is.numeric(A) is not TRUE")
    if not is_matrix(A):
        raise PracmaError("is.matrix(A) is not TRUE")
    matrix = np.array(A, dtype=float, copy=True)
    n, m = matrix.shape
    if n != m or n <= 1:
        raise PracmaError(message)
    return matrix


def lu(A, scheme="kji"):
    matrix = _square(A, "Argument 'A' must be a square, positive definite matrix.")
    n = matrix.shape[0]
    scheme = match_arg(scheme, ["kji", "jki", "ijk"])
    if scheme == "kji":
        for k in range(n - 1):
            if matrix[k, k] == 0:
                raise PracmaError("All diagonal elements of matrix 'A' must be non-zero.")
            for i in range(k + 1, n):
                matrix[i, k] = matrix[i, k] / matrix[k, k]
                matrix[i, k + 1 :] = matrix[i, k + 1 :] - matrix[i, k] * matrix[k, k + 1 :]
    elif scheme == "jki":
        if matrix[0, 0] == 0:
            raise PracmaError("All diagonal elements of matrix 'A' must be non-zero.")
        matrix[1:, 0] = matrix[1:, 0] / matrix[0, 0]
        for j in range(1, n):
            if matrix[j, j] == 0:
                raise PracmaError("All diagonal elements of matrix 'A' must be non-zero.")
            for k in range(j):
                matrix[k + 1 :, j] = matrix[k + 1 :, j] - matrix[k + 1 :, k] * matrix[k, j]
            if j < n - 1:
                matrix[j + 1 :, j] = matrix[j + 1 :, j] / matrix[j, j]
    else:
        for i in range(1, n):
            for j in range(1, i + 1):
                if matrix[j, j] == 0:
                    raise PracmaError("All diagonal elements of matrix 'A' must be non-zero.")
                matrix[i, j - 1] = matrix[i, j - 1] / matrix[j - 1, j - 1]
                k = np.arange(j)
                matrix[i, j] = matrix[i, j] - float(np.dot(matrix[i, k], matrix[k, j]))
            if i < n - 1:
                k = np.arange(i)
                for j in range(i + 1, n):
                    matrix[i, j] = matrix[i, j] - float(np.dot(matrix[i, k], matrix[k, j]))
    lower = eye(n) + tril(matrix, -1)
    upper = triu(matrix)
    return {"L": lower, "U": upper}


def lu_crout(A):
    matrix = _square(A, "Argument 'A' must be a square, positive definite matrix.")
    n = matrix.shape[0]
    lower = np.zeros((n, n))
    upper = np.zeros((n, n))
    for i in range(n):
        lower[i, 0] = matrix[i, 0]
        upper[i, i] = 1
    for j in range(1, n):
        upper[0, j] = matrix[0, j] / lower[0, 0]
    for i in range(1, n):
        for j in range(1, i + 1):
            lower[i, j] = matrix[i, j] - np.sum(lower[i, :j] * upper[:j, j])
        if i < n - 1:
            for j in range(i + 1, n):
                lower_dot = np.sum(lower[i, :i] * upper[:i, j])
                upper[i, j] = (matrix[i, j] - lower_dot) / lower[i, i]
    return {"L": lower, "U": upper}


def lufact(A):
    if not is_numeric(A):
        raise PracmaError("is.numeric(A) is not TRUE")
    if not is_matrix(A):
        raise PracmaError("is.matrix(A) is not TRUE")
    matrix = np.array(A, dtype=float, copy=True)
    m, n = matrix.shape
    if m != n or m == 1:
        raise PracmaError("Matrix 'A' must be a square matrix with 2 rows at least.")
    det = 1.0
    rows = np.arange(n)
    for p in range(n - 1):
        prow = int(np.argmax(np.abs(matrix[p:, p]))) + p
        if p < prow:
            rows[p], rows[prow] = rows[prow], rows[p]
            det = -det
        det = det * matrix[rows[p], p]
        if det == 0:
            warnings.warn("Matrix 'A' is singular, no results computed.", stacklevel=2)
            return {"LU": matrix, "perm": (rows + 1).astype(float), "det": np.nan, "x": None}
        for k in range(p + 1, n):
            factor = matrix[rows[k], p] / matrix[rows[p], p]
            matrix[rows[k], p] = factor
            matrix[rows[k], p + 1 :] = matrix[rows[k], p + 1 :] - factor * matrix[rows[p], p + 1 :]
    det = det * matrix[rows[n - 1], n - 1]
    return {"LU": matrix, "perm": (rows + 1).astype(float), "det": float(det)}


def lusys(A, b):
    if not is_numeric(A):
        raise PracmaError("is.numeric(A) is not TRUE")
    if not is_matrix(A):
        raise PracmaError("is.matrix(A) is not TRUE")
    if not is_numeric(b):
        raise PracmaError("is.numeric(b) is not TRUE")
    matrix = np.array(A, dtype=float, copy=True)
    rhs = np.array(b, dtype=float, copy=True).reshape(-1, order="F")
    m, n = matrix.shape
    if m != n or m == 1:
        raise PracmaError("Matrix 'A' must be a square matrix with 2 rows at least.")
    x = zeros(n, 1)
    y = zeros(n, 1)
    order = np.arange(n)
    for p in range(n - 1):
        q = int(np.argmax(np.abs(matrix[p:, p]))) + p
        matrix[[p, q], :] = matrix[[q, p], :]
        order[p], order[q] = order[q], order[p]
        if matrix[p, p] == 0:
            raise PracmaError("Matrix 'A' singular: no unique solution.")
        for k in range(p + 1, n):
            factor = matrix[k, p] / matrix[p, p]
            matrix[k, p] = factor
            matrix[k, p + 1 :] = matrix[k, p + 1 :] - factor * matrix[p, p + 1 :]
    y[0, 0] = rhs[order[0]]
    for k in range(1, n):
        y[k, 0] = rhs[order[k]] - float(np.dot(matrix[k, :k], y[:k, 0]))
    x[n - 1, 0] = y[n - 1, 0] / matrix[n - 1, n - 1]
    for k in range(n - 2, -1, -1):
        x[k, 0] = (y[k, 0] - float(np.dot(matrix[k, k + 1 :], x[k + 1 :, 0]))) / matrix[k, k]
    return x
