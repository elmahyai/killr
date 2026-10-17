"""Matrix exponential, logarithm, and p-th roots."""

from __future__ import annotations

import math

import numpy as np

_np = np

from pracma._util import PracmaError
from pracma.arrays import eye, zeros
from pracma.linalg_eig import eig
from pracma.linalg_internal import frobenius, is_matrix, is_numeric, zapsmall
from pracma.linalg_solve import inv


def expm(A, np=128):
    if not is_numeric(A) or not is_matrix(A) or _np.array(A).shape[0] != _np.array(A).shape[1]:
        raise PracmaError("Argument 'A' must be a square numeric matrix.")
    count = np
    if (
        not is_numeric(count)
        or _np.asarray(count).size != 1
        or math.floor(float(count)) != math.ceil(float(count))
        or float(count) < 2
    ):
        raise PracmaError("Argument 'np' must be an integer greater or equal to 2.")
    count = int(float(count))
    matrix = _np.array(A, dtype=float, copy=False)
    n = matrix.shape[0]
    circle = _np.exp(2j * math.pi * _np.arange(1, count + 1) / count)
    values = eig(matrix)
    real = _np.real(values)
    center = math.ceil(float(_np.mean([_np.min(real), _np.max(real)])) + 0.1)
    radius = math.ceil(float(_np.max(_np.abs(values - center))) + 0.1)
    z = center + radius * circle
    identity = eye(n)
    total = zeros(n).astype(complex)
    for point in z:
        resolvent = inv(point * identity - matrix)
        total = total + resolvent * (point - center) * _np.exp(point)
    total = _np.real(total) / count
    return zapsmall(total)


def logm(A):
    if not is_numeric(A) or not is_matrix(A) or np.array(A).shape[0] != np.array(A).shape[1]:
        raise PracmaError("Argument 'A' must be a square numeric matrix.")
    matrix = np.array(A, dtype=float, copy=False)
    values, vectors = np.linalg.eig(matrix)
    if np.any((np.imag(values) == 0) & (np.real(values) <= 0)):
        raise PracmaError("A must not have any nonpositive real eigenvalues.")
    logged = vectors @ np.diag(np.log(values.astype(complex))) @ np.linalg.inv(vectors)
    return np.real(logged)


def sqrtm(A, kmax=20, tol=float(np.finfo(float).eps) ** 0.5):
    if not is_numeric(A):
        raise PracmaError("is.numeric(A) is not TRUE")
    if not is_matrix(A):
        raise PracmaError("is.matrix(A) is not TRUE")
    matrix = np.array(A, dtype=float, copy=False)
    if matrix.shape[0] != matrix.shape[1]:
        raise PracmaError("Matrix 'A' must be square.")
    current = matrix.copy()
    inverse = np.eye(matrix.shape[0])
    k = 0
    while frobenius(matrix - current @ current) > tol and k < kmax:
        nxt = 0.5 * (current + np.linalg.inv(inverse))
        inv_next = 0.5 * (inverse + np.linalg.inv(current))
        current = nxt
        inverse = inv_next
        k += 1
    if k >= kmax:
        k = -1
    return {"B": current, "Binv": inverse, "k": np.array([float(k)]), "acc": np.array([frobenius(matrix - current @ current)])}


def signm(A, kmax=20, tol=float(np.finfo(float).eps) ** 0.5):
    matrix = np.array(A, dtype=float, copy=False)
    root = sqrtm(matrix @ matrix, kmax=kmax, tol=tol)
    return matrix @ root["Binv"]


def rootm(A, p, kmax=20, tol=float(np.finfo(float).eps) ** 0.5):
    if not is_numeric(A):
        raise PracmaError("is.numeric(A) is not TRUE")
    if not is_matrix(A):
        raise PracmaError("is.matrix(A) is not TRUE")
    original = np.array(A, dtype=float, copy=True)
    if original.shape[0] != original.shape[1]:
        raise PracmaError("Matrix 'A' must be square.")
    n = original.shape[0]
    matrix = original.copy()
    power = p
    if power % 2 == 1:
        matrix = matrix @ matrix
        power = 2 * power
    else:
        while power % 4 == 0:
            matrix = sqrtm(matrix)["B"]
            power = power / 2
    count = 1
    acc = math.inf
    k = 0
    total = None
    while acc > tol and k < kmax:
        count = 2 * count
        root = math.cos(2 * math.pi / count) + 1j * math.sin(2 * math.pi / count)
        total = np.linalg.inv(matrix) / 4
        for j in range(1, count):
            weight = ((1 - root**j) / (1 + root**j)) ** power
            solved = np.linalg.inv(matrix - weight * np.eye(n))
            total = total + solved * root**j / (1 + root**j) ** 2
        total = 2 * power * math.sin(math.pi / power) / count * matrix @ total
        total = np.real(total)
        product = total.copy()
        for _ in range(int(p) - 1):
            product = product @ total
        acc = frobenius(original - product)
        k += 1
    if k >= kmax:
        k = -1
    return {"B": total, "k": np.array([float(k)]), "acc": np.array([acc])}
