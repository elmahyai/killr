"""Triangular parts and distance-matrix reshaping."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.linalg_internal import is_complex, is_matrix, is_number, is_vector, stopifnot


def tril(M, k=0):
    array = np.array(M, dtype=complex if is_complex(M) else float, copy=True)
    if array.ndim != 2:
        raise PracmaError("argument is not a matrix")
    rows, cols = np.indices(array.shape)
    # R col(M) >= row(M) + k + 1, with 1-based indices.
    array[(cols + 1) >= (rows + 1) + k + 1] = 0
    if not np.iscomplexobj(M):
        array = np.real(array)
    return array


def triu(M, k=0):
    array = np.array(M, dtype=complex if is_complex(M) else float, copy=True)
    if array.ndim != 2:
        raise PracmaError("argument is not a matrix")
    rows, cols = np.indices(array.shape)
    array[(cols + 1) <= (rows + 1) + k - 1] = 0
    if not np.iscomplexobj(M):
        array = np.real(array)
    return array


def _strict_lower_indices(k):
    inds = []
    for i in range(1, k):
        start = 1 + i + (i - 1) * k
        stop = i * k
        inds.extend(range(start, stop + 1))
    return np.array(inds, dtype=int)


def squareform(x):
    stopifnot([("is.numeric(x) || is.complex(x)", is_number(x))])
    if is_vector(x):
        values = np.array(x, dtype=complex if is_complex(x) else float).reshape(-1)
        n = values.size
        m = math.floor(math.sqrt(2 * n))
        if m * (m + 1) != 2 * n:
            raise PracmaError("Argument 'x' does not correspond to a distance matrix.")
        k = m + 1
        inds = _strict_lower_indices(k)
        y = np.zeros(k * k, dtype=values.dtype)
        y[inds - 1] = values
        matrix = y.reshape((k, k), order="F")
        matrix = matrix + matrix.T
        return np.real(matrix) if not np.iscomplexobj(values) else matrix
    if is_matrix(x):
        matrix = np.array(x, dtype=complex if is_complex(x) else float, copy=False)
        m, n = matrix.shape
        if m != n:
            raise PracmaError("Argument 'x' must be a vector or a square matrix.")
        diagonal = np.diag(matrix)
        if np.any(diagonal != 0):
            raise PracmaError("Argument 'x' can only have 0s on the diagonal.")
        if n == 1:
            return None
        inds = _strict_lower_indices(n)
        flat = np.ravel(matrix, order="F")
        return flat[inds - 1]
    raise PracmaError("Argument 'x' must be a numeric or complex vector or matrix.")
