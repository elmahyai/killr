"""Small matrix and vector helpers."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError, as_1d


def _shape(n, m):
    rows = math.floor(float(np.asarray(n).reshape(-1)[0]))
    cols = rows if m is None else math.floor(float(np.asarray(m).reshape(-1)[0]))
    return rows, cols


def eye(n, m=None):
    rows, cols = _shape(n, m)
    if rows <= 0 or cols <= 0:
        return np.full((0, 0), np.nan)
    return np.eye(rows, cols)


def ones(n, m=None):
    rows, cols = _shape(n, m)
    if rows <= 0 or cols <= 0:
        return np.ones((0, 0))
    return np.ones((rows, cols))


def zeros(n, m=None):
    rows, cols = _shape(n, m)
    if rows <= 0 or cols <= 0:
        return np.zeros((0, 0))
    return np.zeros((rows, cols))


def finds(v):
    values = np.asarray(v)
    if values.dtype == bool:
        mask = values.reshape(-1)
    else:
        mask = as_1d(v) != 0
    return (np.flatnonzero(mask) + 1).astype(float)


def _drop(array):
    if array.ndim == 2 and 1 in array.shape:
        return array.reshape(-1)
    return array


def dot(x, y):
    if (x is None or np.asarray(x).size == 0) and (y is None or np.asarray(y).size == 0):
        return np.array([0.0])
    left = _drop(np.asarray(x, dtype=complex))
    right = _drop(np.asarray(y, dtype=complex))
    if left.ndim <= 1 and right.ndim <= 1:
        left = np.reshape(left, (-1, 1))
        right = np.reshape(right, (-1, 1))
    elif left.ndim == 1:
        left = left.reshape(-1, 1)
    elif right.ndim == 1:
        right = right.reshape(-1, 1)
    if left.shape != right.shape:
        raise PracmaError("Matrices 'x' and 'y' must be of same size")
    columns = np.sum(np.conj(left) * right, axis=0)
    return np.real(columns) if np.all(np.isreal(columns)) else columns


def Diag(x, k=0):
    if float(k) != round(float(k)):
        raise PracmaError("Argument 'k' must be an integer.")
    offset = int(k)
    array = np.asarray(x, dtype=float)
    if array.ndim == 2:
        rows, cols = array.shape
        if offset >= cols or -offset >= rows:
            return np.zeros((0, 0))
        return np.diag(array, offset)
    values = as_1d(x)
    side = values.size + abs(offset)
    out = np.zeros((side, side))
    row = np.arange(values.size) + max(-offset, 0)
    col = np.arange(values.size) + max(offset, 0)
    out[row, col] = values
    return out


def Trace(a):
    array = np.asarray(a, dtype=float)
    if array.size <= 1:
        return array.reshape(-1)
    if array.ndim != 2:
        raise PracmaError("Argument 'a' must be a real or complex matrix.")
    if array.shape[0] != array.shape[1]:
        raise PracmaError("Matrix 'a' must be square.")
    return np.array([float(np.trace(array))])


def Norm(x, p=2):
    values = np.abs(as_1d(x))
    power = float(p)
    if math.isinf(power) and power > 0:
        return float(np.max(values)) if values.size else float("nan")
    if math.isinf(power) and power < 0:
        return float(np.min(values)) if values.size else float("nan")
    if values.size == 0:
        return 0.0
    return float(np.sum(values**power) ** (1.0 / power))


def conv(x, y):
    left = as_1d(x)
    right = as_1d(y)
    width = left.size + right.size - 1
    if width <= 0:
        return np.array([])
    product = np.fft.fft(left, width) * np.fft.fft(right, width)
    result = np.fft.ifft(product)
    return np.real(result)


def circshift(a, sz):
    if a is None:
        return None
    shift = np.asarray(sz, dtype=int).reshape(-1)
    array = np.asarray(a, dtype=float)
    if array.ndim == 1 and shift.size == 1:
        return np.roll(array, int(shift[0]))
    if array.ndim == 2 and shift.size == 2:
        return np.roll(array, (int(shift[0]), int(shift[1])), axis=(0, 1))
    raise PracmaError("Length of 'sz' must be equal to the no. of dimensions of 'a'.")


def flipdim(a, dim=1):
    array = np.asarray(a, dtype=float)
    if array.ndim != 2:
        raise PracmaError("Argument 'a' must ba a matrix.")
    if dim not in (1, 2):
        raise PracmaError("Argument 'dim' must be 1 or 2 (for rows or columns).")
    axis = 0 if dim == 1 else 1
    return np.flip(array, axis=axis)


def flipud(a):
    return flipdim(a, 1)


def fliplr(a):
    return flipdim(a, 2)


def rot90(a, k=1):
    array = np.asarray(a, dtype=float)
    if array.ndim != 2:
        raise PracmaError("Argument 'a' must ba a matrix.")
    turns = int(math.floor(float(k)))
    if float(k) != math.ceil(float(k)):
        turns = 0
    # R rot90(k=1) is the transpose of the column-reversed matrix, which is
    # NumPy rot90 counterclockwise. R's switch uses k %% 4.
    return np.rot90(array, k=turns % 4)


def Real(z):
    return np.real(np.asarray(z, dtype=complex)).reshape(-1).astype(float)


def Imag(z):
    return np.imag(np.asarray(z, dtype=complex)).reshape(-1).astype(float)


def angle(z):
    values = np.asarray(z, dtype=complex).reshape(-1)
    return np.arctan2(np.imag(values), np.real(values))


def std(x, flag=0):
    if x is not None and np.asarray(x).size == 0:
        return np.array([])
    values = as_1d(x)
    if values.size == 0:
        return np.array([])
    divisor = values.size - 1 if flag == 0 else values.size
    if divisor == 0:
        return np.array([np.nan])
    centered = values - np.mean(values)
    return np.array([math.sqrt(float(np.sum(centered * centered) / divisor))])


def std_err(x):
    if x is not None and np.asarray(x).size == 0:
        return np.array([])
    array = np.asarray(x, dtype=float)
    if array.ndim <= 1:
        values = array.reshape(-1)
        sample = std(values, 0)[0]
        return np.array([sample / math.sqrt(values.size)])
    covariance = np.cov(array, rowvar=False, ddof=1)
    return np.sqrt(covariance / array.size)


def Mode(x):
    values = np.asarray(x, dtype=float).reshape(-1)
    if values.size == 0 or np.all(np.isnan(values)):
        return np.nan
    finite = values[~np.isnan(values)]
    ordered = np.sort(finite)
    unique, counts = np.unique(ordered, return_counts=True)
    return float(unique[int(np.argmax(counts))])
