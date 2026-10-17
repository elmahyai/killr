"""meshgrid, peaks, repmat, Reshape, and sortrows."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.elementary import linspace
from pracma.util_support import is_numeric, is_numeric_or_complex, require, whole_number


def meshgrid(x, y=None):
    if not is_numeric(x) or (y is not None and not is_numeric(y)):
        raise PracmaError("Arguments 'x' and 'y' must be numeric vectors.")
    if y is None:
        y = x
    x_values = np.asarray(x, dtype=float).reshape(-1)
    y_values = np.asarray(y, dtype=float).reshape(-1)
    xx, yy = np.meshgrid(x_values, y_values)
    return {"X": xx, "Y": yy}


def peaks(v=49, w=None):
    require(is_numeric(v), "is.numeric(v) is not TRUE")
    if w is None:
        values = np.asarray(v, dtype=float).reshape(-1)
        if values.size == 1 and values[0] >= 1:
            grid = meshgrid(linspace(-3, 3, math.floor(float(values[0]))))
            x = grid["X"]
            y = grid["Y"]
        else:
            grid = meshgrid(values, values)
            x = grid["X"]
            y = grid["Y"]
    else:
        require(is_numeric(w), "is.numeric(w) is not TRUE")
        x = np.asarray(v, dtype=float)
        y = np.asarray(w, dtype=float)
    z = (
        3 * (1 - x) ** 2 * np.exp(-(x**2) - (y + 1) ** 2)
        - 10 * (x / 5 - x**3 - y**5) * np.exp(-x**2 - y**2)
        - 1 / 3 * np.exp(-((x + 1) ** 2) - y**2)
    )
    return {"X": x, "Y": y, "Z": z}


def repmat(a, n, m=None):
    if a is None or np.asarray(a).size == 0:
        return None
    if not is_numeric_or_complex(a):
        raise PracmaError("Argument 'a' must be a numeric or complex.")
    if m is None:
        m = n
    if not is_numeric(n) or not is_numeric(m) or np.asarray(n).size != 1 or np.asarray(m).size != 1:
        raise PracmaError("Arguments 'n' and 'm' must be single integers.")
    rows = max(math.floor(float(np.asarray(n).reshape(-1)[0])), 0)
    cols = max(math.floor(float(np.asarray(m).reshape(-1)[0])), 0)
    block = np.asarray(a)
    if block.ndim <= 1:
        block = block.reshape(1, -1)
    if rows <= 0 or cols <= 0:
        return np.zeros((rows, cols), dtype=block.dtype)
    return np.kron(np.ones((rows, cols), dtype=float), block)


def Reshape(a, n, m=None):
    flat = np.asarray(a).reshape(-1, order="F")
    rows = int(n)
    cols = flat.size // rows if m is None else int(m)
    if flat.size != rows * cols:
        raise PracmaError("Matrix 'a' does not have n*m elements")
    return flat.reshape((rows, cols), order="F")


def sortrows(A, k=1):
    require(is_numeric(A), "is.numeric(A) is not TRUE")
    require(is_numeric(k), "is.numeric(k) is not TRUE")
    array = np.asarray(A, dtype=float)
    if array.ndim != 2:
        raise PracmaError("Argument 'A' must be a numeric matrix.")
    if np.asarray(k).size != 1 or not whole_number(k):
        raise PracmaError("Argument 'k' must be a single integer number.")
    column = int(k)
    if column < 1 or column > array.shape[1]:
        raise PracmaError("Argument 'k' must satisfy 1 <= k <= ncol(A).")
    order = np.argsort(array[:, column - 1], kind="mergesort")
    return array[order, :]
