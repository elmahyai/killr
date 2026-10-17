"""Eigenvalues, Hessenberg form, Arnoldi, and the characteristic polynomial."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.arrays import Norm, eye, zeros
from pracma.linalg_internal import array_ind, is_complex, is_matrix, is_numeric, length, which_max


def eig(a):
    if length(a) == 0:
        return np.zeros((0, 0))
    if length(a) == 1:
        return np.array(a, dtype=complex if is_complex(a) else float, copy=True)
    if (not is_numeric(a) and not is_complex(a)) or not is_matrix(a):
        raise PracmaError("Argument 'a' must be a numeric or complex matrix.")
    matrix = np.array(a, dtype=complex if is_complex(a) else float, copy=False)
    if matrix.shape[0] != matrix.shape[1]:
        raise PracmaError("Matrix 'a' must be square matrix.")
    values = np.linalg.eigvals(matrix)
    symmetric = matrix.shape[0] == matrix.shape[1] and np.allclose(matrix, matrix.T.conj())
    if symmetric and not np.iscomplexobj(matrix):
        order = np.argsort(-np.real(values), kind="mergesort")
        values = np.real(values[order])
    else:
        order = np.argsort(-np.abs(values), kind="mergesort")
        values = values[order]
    if np.all(np.isreal(values)):
        return np.real(values)
    return values


def eigjacobi(A, tol=float(np.finfo(float).eps) ** (2.0 / 3.0)):
    if not is_numeric(A):
        raise PracmaError("is.numeric(A) is not TRUE")
    matrix = np.array(A, dtype=float, copy=True)
    if matrix.ndim != 2:
        raise PracmaError("Matrix 'A' must be a square and real symmetric matrix.")
    n = matrix.shape[0]
    if matrix.shape[1] != n or not np.all(matrix.T == matrix):
        raise PracmaError("Matrix 'A' must be a square and real symmetric matrix.")
    diagonal = matrix.copy()
    vectors = eye(n)
    while True:
        off = diagonal - np.diag(np.diag(diagonal))
        index = which_max(np.abs(off))
        p, q = array_ind(index, diagonal.shape)
        p -= 1
        q -= 1
        gap = diagonal[q, q] - diagonal[p, p]
        t = diagonal[p, q] / gap if gap != 0 else np.inf
        d = 1.0 / math.sqrt(t * t + 1.0)
        s = d * t
        rotation = np.array([[d, s], [-s, d]])
        # R stores matrix(c(d, -s, s, d), 2, 2), column-major:
        # d  s
        # -s d
        diagonal[[p, q], :] = rotation.T @ diagonal[[p, q], :]
        diagonal[:, [p, q]] = diagonal[:, [p, q]] @ rotation
        vectors[:, [p, q]] = vectors[:, [p, q]] @ rotation
        off = diagonal - np.diag(np.diag(diagonal))
        index = which_max(np.abs(off))
        p, q = array_ind(index, diagonal.shape)
        p -= 1
        q -= 1
        scale = math.sqrt(np.sum(np.diag(diagonal) ** 2) / n)
        if abs(diagonal[p, q]) < tol * scale:
            break
    return {"V": vectors, "D": np.diag(diagonal)}


def hessenberg(A):
    if not is_numeric(A):
        raise PracmaError("is.numeric(A) is not TRUE")
    if not is_matrix(A):
        raise PracmaError("is.matrix(A) is not TRUE")
    matrix = np.array(A, dtype=float, copy=True)
    m, n = matrix.shape
    if m != n:
        raise PracmaError("Input 'A' must be a square matrix.")
    if n <= 2:
        return {"H": matrix, "P": eye(n)}
    h = matrix.copy()
    reflectors = []
    for k in range(n - 2):
        v = h[k + 1 :, k].copy()
        sgn = float(np.sign(v[0]))
        if sgn == 0:
            sgn = 1.0
        v[0] = v[0] + sgn * Norm(v)
        if Norm(v) != 0:
            v = v / Norm(v)
        block = h[k + 1 :, k:]
        h[k + 1 :, k:] = block - 2 * np.outer(v, v @ block)
        right = h[:, k + 1 :]
        h[:, k + 1 :] = right - 2 * np.outer(right @ v, v)
        reflectors.append(v)
    q = eye(n)
    for j in range(n - 3, -1, -1):
        v = reflectors[j]
        block = q[j + 1 :, :]
        q[j + 1 :, :] = block - 2 * np.outer(v, v @ block)
    return {"H": h, "P": q}


def arnoldi(A, q, m=None):
    if not is_numeric(A):
        raise PracmaError("is.numeric(A) is not TRUE")
    if not is_numeric(q):
        raise PracmaError("is.numeric(q) is not TRUE")
    # The source tests nrow(A) != nrow(A), which never fires.
    if not is_matrix(A):
        raise PracmaError("Argument 'A' must be a square matrix")
    matrix = np.array(A, dtype=float, copy=False)
    n = matrix.shape[0]
    start = np.array(q, dtype=float).reshape(-1, 1)
    if start.size != n:
        raise PracmaError("Argument 'q' must be a vector of length 'nrow(A)'.")
    if m is None:
        m = n
    m = int(m)
    start = start / Norm(start)
    basis = zeros(n, m)
    basis[:, 0] = start[:, 0]
    # zeros(min(m+1, m), n) is m by n.
    hess = zeros(min(m + 1, m), n)
    for k in range(m):
        z = matrix @ basis[:, k : k + 1]
        for i in range(k + 1):
            hess[i, k] = float(np.asarray(basis[:, i].reshape(-1) @ z.reshape(-1)).reshape(-1)[0])
            z = z - hess[i, k] * basis[:, i : i + 1]
        if k < n - 1:
            hess[k + 1, k] = Norm(z)
            if hess[k + 1, k] == 0:
                return {"Q": basis, "H": hess}
            if k + 1 < m:
                basis[:, k + 1] = (z / hess[k + 1, k])[:, 0]
    return {"Q": basis, "H": hess}


def charpoly(a, info=False):
    if not is_numeric(a):
        raise PracmaError("is.numeric(a) is not TRUE")
    if not is_matrix(a):
        raise PracmaError("is.matrix(a) is not TRUE")
    matrix = np.array(a, dtype=float, copy=False)
    n, m = matrix.shape
    if n != m or n < 2:
        raise PracmaError("Argument 'a' must be a square matrix.")
    if n > 100:
        print("The algorithm will be *very* slow for n > 100.", flush=True)
    coef = np.ones(n + 1)
    current = matrix.copy()
    previous = None
    for k in range(2, n + 1):
        coef[k - 1] = -np.sum(np.diag(current)) / (k - 1)
        if k == n:
            previous = current.copy()
        current = matrix @ (current + coef[k - 1] * np.eye(n))
    coef[n] = -np.sum(np.diag(current)) / n
    if info:
        adet = ((-1) ** n) * coef[n]
        if adet != 0:
            ainv = -1 * (previous + coef[n - 1] * np.eye(n)) / coef[n]
        else:
            ainv = np.nan
        error = previous @ matrix + coef[n - 1] * matrix - adet * np.eye(n)
        error = float(np.max(np.abs(error)))
        print(f"Error term: {_cat_number(error)} ", flush=True)
        return {"cp": coef, "det": np.array([adet]), "inv": ainv}
    return coef


def _cat_number(value):
    if math.isfinite(value) and float(value) == math.trunc(value) and abs(value) < 1e16:
        return str(int(value))
    return format(float(value), ".7g")
