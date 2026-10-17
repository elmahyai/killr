"""Inverses, condition, and the Matlab division operators."""

from __future__ import annotations

import warnings

import numpy as np

from pracma._util import PracmaError
from pracma.elementary import eps
from pracma.linalg_internal import (
    column_vector,
    is_complex,
    is_matrix,
    is_number,
    is_numeric,
    is_vector,
    length,
    svd_full,
)


def inv(a):
    if length(a) == 0:
        return np.zeros((0, 0))
    if (not is_numeric(a) and not is_complex(a)) or not is_matrix(a):
        raise PracmaError("Argument 'a' must be a numeric or complex matrix.")
    matrix = np.array(a, dtype=complex if is_complex(a) else float, copy=True)
    if matrix.shape[0] != matrix.shape[1]:
        raise PracmaError("Matrix 'a' must be square.")
    try:
        solved = np.linalg.inv(matrix)
    except np.linalg.LinAlgError:
        warnings.warn("Matrix appears to be singular.", stacklevel=2)
        solved = np.full(matrix.shape, np.inf)
    if solved.dtype == complex and np.all(np.isreal(solved)):
        return np.real(solved)
    return solved


def pinv(A, tol=float(np.finfo(float).eps) ** (2.0 / 3.0)):
    if not is_number(A):
        raise PracmaError("is.numeric(A) || is.complex(A) is not TRUE")
    if not is_matrix(A):
        raise PracmaError("is.matrix(A) is not TRUE")
    matrix = np.array(A, dtype=complex if is_complex(A) else float, copy=False)
    u, singular, v = svd_full(matrix)
    if is_complex(A):
        u = np.conj(u)
    # Economy factors: R svd defaults to min(n, p) vectors.
    rank_cap = singular.size
    u = u[:, :rank_cap]
    v = v[:, :rank_cap]
    if singular.size == 0:
        keep = np.array([], dtype=bool)
    else:
        keep = singular > max(tol * singular[0], 0)
    if keep.size and np.all(keep):
        inverse = v @ ((1.0 / singular).reshape(-1, 1) * u.T)
    elif keep.size and np.any(keep):
        inverse = v[:, keep] @ ((1.0 / singular[keep]).reshape(-1, 1) * u[:, keep].T)
    else:
        inverse = np.zeros((matrix.shape[1], matrix.shape[0]), dtype=matrix.dtype)
    if inverse.dtype == complex and np.all(np.isreal(inverse)):
        return np.real(inverse)
    return inverse


def _prepare_divide(A, B):
    if not is_number(A) or not is_number(B):
        raise PracmaError("is.numeric(A) || is.complex(A) is not TRUE")
    return A, B


def mldivide(A, B, pinv=True):
    _prepare_divide(A, B)
    left = column_vector(A) if is_vector(A) else np.array(A, dtype=complex if is_complex(A) else float, copy=True)
    right = column_vector(B) if is_vector(B) else np.array(B, dtype=complex if is_complex(B) else float, copy=True)
    if left.shape[0] != right.shape[0]:
        raise PracmaError("Matrices 'A' and 'B' must have the same number of rows.")
    if pinv:
        # R uses t(A), not the conjugate transpose. The parameter shadows the function.
        gram = left.T @ left
        result = globals()["pinv"](gram) @ left.T @ right
    else:
        result = np.linalg.lstsq(left, right, rcond=None)[0]
        if result.ndim == 1:
            result = result.reshape(-1, 1)
    if result.dtype == complex and np.all(np.isreal(result)):
        return np.real(result)
    return result


def mrdivide(A, B, pinv=True):
    _prepare_divide(A, B)
    if is_vector(A):
        left = np.array(A, dtype=complex if is_complex(A) else float).reshape(1, -1)
    else:
        left = np.array(A, dtype=complex if is_complex(A) else float, copy=True)
    if is_vector(B):
        right = np.array(B, dtype=complex if is_complex(B) else float).reshape(1, -1)
    else:
        right = np.array(B, dtype=complex if is_complex(B) else float, copy=True)
    if left.shape[1] != right.shape[1]:
        raise PracmaError("Matrices 'A' and 'B' must have the same number of columns.")
    solved = mldivide(right.T, left.T, pinv=pinv)
    result = solved.T
    if result.dtype == complex and np.all(np.isreal(result)):
        return np.real(result)
    return result


def cond(M, p=2):
    if length(M) == 0:
        return np.array([0.0])
    if not is_numeric(M):
        raise PracmaError("Argument 'M' must be a numeric matrix.")
    matrix = column_vector(M) if is_vector(M) else np.array(M, dtype=float, copy=True)
    if matrix.shape[0] != matrix.shape[1] and p != 2:
        raise PracmaError("Matrix 'M' must be square if p = 2.")
    if p == 2:
        _, singular, _ = svd_full(matrix)
        if singular.size == 0 or np.any(singular == 0):
            return np.array([np.inf])
        return np.array([float(np.max(singular) / np.min(singular))])
    raise PracmaError("At the moment, p-norms other than p = 2 are not implemented.")


def rref(A):
    if not is_numeric(A):
        raise PracmaError("is.numeric(A) is not TRUE")
    if not is_matrix(A):
        raise PracmaError("Input parameter 'A' must be a matrix.")
    matrix = np.array(A, dtype=float, copy=True)
    nr, nc = matrix.shape
    tol = float(eps()) * max(nr, nc) * (float(np.max(np.abs(matrix))) if matrix.size else 0.0)
    row = 0
    for col in range(nc):
        if row >= nr:
            break
        pivot = row + int(np.argmax(np.abs(matrix[row:, col])))
        magnitude = abs(matrix[pivot, col])
        if magnitude <= tol:
            matrix[row:, col] = 0
        else:
            if pivot != row:
                matrix[[pivot, row], col:] = matrix[[row, pivot], col:]
            matrix[row, col:] = matrix[row, col:] / matrix[row, col]
            others = [index for index in range(nr) if index != row]
            if others:
                coeffs = matrix[others, col : col + 1]
                matrix[others, col:] = matrix[others, col:] - coeffs @ matrix[row : row + 1, col:]
            if row == nr - 1:
                break
            row += 1
    matrix[np.abs(matrix) < tol] = 0
    return matrix
