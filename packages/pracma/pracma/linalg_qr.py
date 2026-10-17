"""Gram-Schmidt, Householder, and Givens QR factorizations."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.arrays import Norm, eye
from pracma.linalg_internal import is_matrix, is_numeric
from pracma.linalg_struct import blkdiag
from pracma.linalg_tri import triu


def gramSchmidt(A, tol=float(np.finfo(float).eps) ** 0.5):
    if not is_numeric(A):
        raise PracmaError("is.numeric(A) is not TRUE")
    if not is_matrix(A):
        raise PracmaError("is.matrix(A) is not TRUE")
    matrix = np.array(A, dtype=float, copy=False)
    m, n = matrix.shape
    if m < n:
        raise PracmaError("No. of rows of 'A' must be greater or equal no. of colums.")
    q = np.zeros((m, n))
    r = np.zeros((n, n))
    for k in range(n):
        q[:, k] = matrix[:, k]
        if k > 0:
            for i in range(k):
                r[i, k] = float(np.dot(q[:, i], q[:, k]))
                q[:, k] = q[:, k] - r[i, k] * q[:, i]
        r[k, k] = Norm(q[:, k])
        if abs(r[k, k]) <= tol:
            raise PracmaError("Matrix 'A' does not have full rank.")
        q[:, k] = q[:, k] / r[k, k]
    return {"Q": q, "R": r}


def _givens_pair(xk, xl):
    if xl != 0:
        radius = Norm(np.array([xk, xl]))
        rotation = np.array([[xk, xl], [-xl, xk]], dtype=float) / radius
        transformed = np.array([[radius], [0.0]])
    else:
        rotation = eye(2)
        transformed = np.array([[xk], [0.0]])
    return rotation, transformed


def givens(A):
    if not is_numeric(A):
        raise PracmaError("is.numeric(A) is not TRUE")
    if not is_matrix(A):
        raise PracmaError("is.matrix(A) is not TRUE")
    matrix = np.array(A, dtype=float, copy=True)
    n, m = matrix.shape
    if n != m:
        raise PracmaError("Matrix 'A' must be a square matrix.")
    q = eye(n)
    for k in range(n - 1):
        below = np.abs(matrix[k + 1 :, k])
        pivot = int(np.argmax(below)) + k + 1
        if matrix[k, k] == 0 and matrix[pivot, k] == 0:
            raise PracmaError("Matrix 'A' does not have full rank.")
        rows = [index + k + 1 for index, value in enumerate(matrix[k + 1 :, k]) if value != 0]
        ordered = []
        for row in [pivot, *rows]:
            # R drops absolute row 1. The subcolumn starts at row k+2, so this is idle.
            if row != 0 and row not in ordered:
                ordered.append(row)
        for h in ordered:
            rotation, transformed = _givens_pair(matrix[k, k], matrix[h, k])
            q[[k, h], :] = rotation @ q[[k, h], :]
            matrix[k, k] = transformed[0, 0]
            matrix[h, k] = 0
            if k + 1 < m:
                matrix[[k, h], k + 1 :] = rotation @ matrix[[k, h], k + 1 :]
    return {"Q": q.T, "R": triu(matrix)}


def householder(A):
    matrix = np.array(A, dtype=float, copy=True)
    if matrix.ndim != 2:
        raise PracmaError("argument is not a matrix")
    m, n = matrix.shape
    q = eye(m)
    for k in range(min(m - 1, n)):
        column = matrix[k:, k : k + 1]
        sign = 1.0 if column[0, 0] >= 0 else -1.0
        length = m - k
        vk = column + sign * Norm(column) * np.concatenate([np.ones((1, 1)), np.zeros((length - 1, 1))])
        vk2 = float(np.asarray(vk.T @ vk).reshape(-1)[0])
        reflector = eye(length) - (2.0 / vk2) * (vk @ vk.T)
        if k == 0:
            qk = reflector
        else:
            qk = blkdiag(eye(k), reflector)
        matrix = qk @ matrix
        q = q @ qk
    return {"Q": q, "R": matrix}


def qrSolve(A, b):
    if not is_numeric(A):
        raise PracmaError("is.numeric(A) is not TRUE")
    if not is_matrix(A):
        raise PracmaError("is.matrix(A) is not TRUE")
    if not is_numeric(b):
        raise PracmaError("is.numeric(b) is not TRUE")
    matrix = np.array(A, dtype=float, copy=False)
    m, n = matrix.shape
    rhs = np.array(b, dtype=float).reshape(-1)
    if m < n or rhs.size != m:
        raise PracmaError("Matrix 'A' and vektor 'b' have non-fitting dimensions.")
    factors = householder(matrix)
    q = factors["Q"]
    r = factors["R"]
    projected = q[:, :n].T @ rhs
    x = np.zeros(n)
    x[n - 1] = projected[n - 1] / r[n - 1, n - 1]
    for k in range(n - 2, -1, -1):
        x[k] = (projected[k] - float(np.dot(r[k, k + 1 : n], x[k + 1 : n]))) / r[k, k]
    return x
