"""Kronecker product, polynomials, and structured matrices."""

from __future__ import annotations

import warnings

import numpy as np

from pracma._util import PracmaError
from pracma.arrays import conv, rot90
from pracma.linalg_internal import (
    as_vector,
    is_complex,
    is_matrix,
    is_number,
    is_numeric,
    is_vector,
    length,
)


def _warn(message):
    warnings.warn(message, stacklevel=3)


def hankel(a, b=None):
    if not is_vector(a):
        raise PracmaError("Argument 'a' must be a numeric or complex vector.")
    left = as_vector(a, complex_ok=True)
    n = left.size
    if b is None:
        if n == 0:
            right = np.array([], dtype=left.dtype)
        else:
            right = np.concatenate([left[-1:], np.zeros(n - 1, dtype=left.dtype)])
    else:
        if not is_vector(b):
            raise PracmaError("Argument 'b' must be a numeric or complex vector.")
        right = as_vector(b, complex_ok=True)
    m = right.size
    if n and m and left[n - 1] != right[0]:
        _warn("a[n] not equal to b[1], b[1] set to a[n].")
        right = right.copy()
        right[0] = left[n - 1]
    result = np.zeros((n, m), dtype=complex if np.iscomplexobj(left) or np.iscomplexobj(right) else float)
    for i in range(2, n + m + 1):
        mask_row, mask_col = np.indices((n, m))
        mask = (mask_row + 1) + (mask_col + 1) == i
        result[mask] = left[i - 2] if i <= n + 1 else right[i - n - 1]
    if result.dtype != complex:
        return result
    if np.all(np.isreal(result)):
        return np.real(result)
    return result


def Toeplitz(a, b=None):
    if not is_vector(a) or (b is not None and not is_vector(b)):
        raise PracmaError("Arguments 'a' and 'b' must be vectors.")
    left = as_vector(a, complex_ok=True)
    right = left.copy() if b is None else as_vector(b, complex_ok=True)
    if left.size and right.size and left[0] != right[0]:
        _warn("First elements of vectors 'a', 'b' are not equal.")
    n = left.size
    m = right.size
    dtype = complex if np.iscomplexobj(left) or np.iscomplexobj(right) else float
    result = np.zeros((n, m), dtype=dtype)
    if m:
        result[0, :] = right
    if n:
        result[:, 0] = left
    # R's 2:n is c(2, 1) when n is 1, which indexes past the end.
    rows = list(range(2, n + 1)) if n >= 2 else ([2, 1] if n == 1 else [])
    for i in rows:
        if i - 1 >= n or i - 2 < 0:
            raise PracmaError("subscript out of bounds")
        result[i - 1, 1:m] = result[i - 2, 0 : m - 1]
    return np.real(result) if result.dtype == complex and np.all(np.isreal(result)) else result


def blkdiag(*dots):
    if not dots or not all(is_matrix(item) and is_numeric(item) for item in dots):
        raise PracmaError("All input arguments in '...' must be numeric matrices")
    matrices = [np.array(item, dtype=float, copy=False) for item in dots]
    if any(matrix.shape[0] == 0 or matrix.shape[1] == 0 for matrix in matrices):
        raise PracmaError("All input matrices '...' must be non-empty.")
    nrows = [matrix.shape[0] for matrix in matrices]
    ncols = [matrix.shape[1] for matrix in matrices]
    result = np.zeros((sum(nrows), sum(ncols)))
    row_at = 0
    col_at = 0
    for matrix, height, width in zip(matrices, nrows, ncols):
        result[row_at : row_at + height, col_at : col_at + width] = matrix
        row_at += height
        col_at += width
    return result


def compan(p):
    if length(p) == 0:
        return None
    if not is_vector(p) or not is_number(p):
        raise PracmaError("Argument p must be a vector of real or complex numbers.")
    coef = as_vector(p, complex_ok=True)
    while coef.size >= 2 and coef[0] == 0:
        coef = coef[1:]
    n = coef.size
    if n <= 1:
        return None
    if n == 2:
        return np.array([-coef[1] / coef[0]])
    result = np.zeros((n - 1, n - 1), dtype=complex if np.iscomplexobj(coef) else float)
    for i in range(1, n - 1):
        result[i, i - 1] = 1
    result[0, :] = -coef[1:] / coef[0]
    if result.dtype == complex and np.all(np.isreal(result)):
        return np.real(result)
    return result


def kron(a, b):
    if length(a) == 0 or length(b) == 0:
        return None
    if not is_number(a) or not is_number(b):
        raise PracmaError("Arguments 'a' and 'b' must be real/complex vectors/matrices.")
    left = np.asarray(a)
    right = np.asarray(b)
    dtype = complex if np.iscomplexobj(left) or np.iscomplexobj(right) else float
    product = np.kron(np.array(left, dtype=dtype), np.array(right, dtype=dtype))
    if product.dtype == complex and np.all(np.isreal(product)):
        product = np.real(product)
    return product


def deconv(b, a):
    if length(b) == 0:
        return {"q": np.array([0.0]), "r": None}
    if not is_number(b) or not is_number(a):
        raise PracmaError("Arguments 'b' and 'a' must be numeric or complex.")
    dividend = as_vector(b, complex_ok=True)
    divisor = as_vector(a, complex_ok=True)
    if divisor.size == 0 or divisor[0] == 0:
        raise PracmaError("First element of argument 'a' must be nonzero.")
    nb = dividend.size
    na = divisor.size
    if nb < na:
        return {"q": np.array([0.0]), "r": dividend}
    quotient = []
    while nb >= na:
        scale = dividend[0] / divisor[0]
        tail = np.concatenate([np.array([scale], dtype=dividend.dtype), np.zeros(nb - na, dtype=dividend.dtype)])
        dividend = dividend - conv(divisor, tail)
        quotient.append(scale)
        dividend = dividend[1:nb]
        nb -= 1
    q = np.array(quotient, dtype=complex if np.iscomplexobj(dividend) else float)
    if q.dtype == complex and np.all(np.isreal(q)):
        q = np.real(q)
    if isinstance(dividend, np.ndarray) and dividend.dtype == complex and np.all(np.isreal(dividend)):
        dividend = np.real(dividend)
    return {"q": q, "r": dividend}


def pascal(n, k=0):
    from pracma.linalg_internal import stopifnot

    stopifnot(
        [
            ("is.numeric(n)", is_numeric(n) and not is_matrix(n)),
            ("length(n) == 1", length(n) == 1),
            ("is.numeric(k)", is_numeric(k) and not is_matrix(k)),
            ("length(k) == 1", length(k) == 1),
        ]
    )
    kind = float(np.asarray(k).reshape(-1)[0])
    if kind not in (0.0, 1.0, 2.0):
        raise PracmaError("Argument 'k' must be 0, 1 or 2.")
    size = float(np.asarray(n).reshape(-1)[0])
    if math_floor(size) != math_ceil(size):
        size = math_floor(size)
    size = int(size)
    if size <= 0:
        return None
    if size == 1:
        return np.array([1.0])
    triangle = np.zeros((size, size))
    triangle[0, :] = 1
    for i in range(1, size):
        triangle[i, :] = np.cumsum(triangle[i - 1, :])
    if kind == 0:
        return triangle
    signed = np.zeros((size, size))
    for j in range(1, size + 1):
        block = triangle[:j, j - 1 :: -1]
        signed[j - 1, :j] = np.diag(block) * ((-1.0) ** np.arange(j))
    if kind == 2:
        signed = rot90(signed, -1)
        if size % 2 == 0:
            signed = -signed
    return signed


def math_floor(value):
    return float(np.floor(value))


def math_ceil(value):
    return float(np.ceil(value))
