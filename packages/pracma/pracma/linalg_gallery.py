"""Gallery matrices and the random orthogonal matrix."""

from __future__ import annotations

import math
import warnings

import numpy as np

from pracma._util import PracmaError
from pracma.arrays import Diag
from pracma.linalg_internal import is_complex, is_matrix, is_number, is_numeric, length, match_arg, stopifnot
from pracma.linalg_struct import Toeplitz, hankel, kron


def _warn(message):
    warnings.warn(message, stacklevel=3)


def hilb(n):
    if not is_numeric(n):
        raise PracmaError("Input argument 'n' must be a numeric scalar.")
    values = np.asarray(n, dtype=float).reshape(-1)
    if values.size != 1:
        raise PracmaError("the condition has length > 1")
    size = float(values[0])
    if size < 0:
        return np.full((0, 0), np.nan)
    if math.ceil(size) != math.floor(size):
        size = math.floor(size)
        _warn("Size 'n' should be a single integer number.")
    size = int(size)
    if size == 0:
        return np.zeros((0, 0))
    index = np.arange(1, size + 1, dtype=float)
    return 1.0 / (index.reshape(-1, 1) + index.reshape(1, -1) - 1.0)


def moler(n):
    values = np.asarray(n, dtype=float).reshape(-1) if is_numeric(n) else None
    if values is None or values.size != 1 or float(values[0]) != round(float(values[0])):
        raise PracmaError("Argument 'n' must be an integer.")
    size = int(values[0])
    if size <= 0:
        return None
    result = np.zeros((size, size))
    for i in range(size):
        result[i, : i + 1] = np.arange(1, i + 2) - 2
    result = result + result.T
    np.fill_diagonal(result, np.arange(1, size + 1, dtype=float))
    return result


def rosser():
    return np.array(
        [
            [611, 196, -192, 407, -8, -52, -49, 29],
            [196, 899, 113, -192, -71, -43, -8, -44],
            [-192, 113, 899, 196, 61, 49, 8, 52],
            [407, -192, 196, 611, 8, 44, 59, -23],
            [-8, -71, 61, 8, 411, -599, 208, 208],
            [-52, -43, 49, 44, -599, 411, 208, 208],
            [-49, -8, 8, 59, 208, 208, 99, -911],
            [29, -44, 52, -23, 208, 208, -911, 99],
        ],
        dtype=float,
    )


def vander(x):
    if length(x) == 0:
        return np.zeros((0, 0))
    if (not is_number(x)) or is_matrix(x):
        raise PracmaError("Argument 'x' must be a numeric or complex  vector.")
    values = np.array(x, dtype=complex if is_complex(x) else float).reshape(-1)
    n = values.size
    powers = np.arange(n - 1, -1, -1, dtype=float)
    result = values.reshape(-1, 1) ** powers.reshape(1, -1)
    if result.dtype == complex and np.all(np.isreal(result)):
        return np.real(result)
    return result


def wilkinson(n):
    values = np.asarray(n, dtype=float).reshape(-1) if is_numeric(n) else None
    if values is None or values.size != 1 or float(values[0]) != round(float(values[0])):
        raise PracmaError("Argument 'n' must be an integer.")
    size = int(values[0])
    if size <= 0:
        return None
    half = (size - 1) / 2.0
    diagonal = np.abs(np.arange(-half, half + 0.5))
    ones = np.ones(size - 1)
    return Diag(diagonal) + Diag(ones, 1) + Diag(ones, -1)


def _magic_indices(n):
    rows = np.arange(1, n + 1, dtype=float).reshape(-1, 1)
    cols = np.arange(1, n + 1, dtype=float).reshape(1, -1)
    return np.broadcast_to(rows, (n, n)).copy(), np.broadcast_to(cols, (n, n)).copy()


def magic(n):
    if not is_numeric(n):
        raise PracmaError("Argument 'n' must be numeric.")
    if length(n) != 1:
        raise PracmaError("Argument 'n' must be of length 1.")
    size = int(math.floor(float(np.asarray(n).reshape(-1)[0])))

    def odd_order(order):
        eye_i, eye_j = _magic_indices(order)
        first = (eye_i + eye_j - (order + 3) / 2) % order
        second = (eye_i + 2 * eye_j - 2) % order
        return order * first + second + 1

    def doubly_even(order):
        eye_i, eye_j = _magic_indices(order)
        mask = np.trunc((eye_i % 4) / 2) == np.trunc((eye_j % 4) / 2)
        numbers = np.arange(1, order * order + 1, dtype=float).reshape((order, order), order="F").T
        numbers[mask] = order * order + 1 - numbers[mask]
        return numbers

    def singly_even(order):
        half = order // 2
        block = magic(half)
        top = np.concatenate([block, block + 2 * half**2], axis=1)
        bottom = np.concatenate([block + 3 * half**2, block + half**2], axis=1)
        square = np.concatenate([top, bottom], axis=0)
        if order != 2:
            k = (order - 2) / 4
            k_int = int(k)
            columns = list(range(1, k_int + 1))
            if (order - k + 2) <= order:
                start = int(order - k + 2)
                step = -1 if start > order else 1
                columns.extend(list(range(start, order + step, step)))
            rows_top = np.arange(1, half + 1)
            rows_down = np.concatenate([rows_top, rows_top + half])
            rows_up = np.concatenate([rows_top + half, rows_top])
            col_index = np.array(columns, dtype=int) - 1
            square[np.ix_(rows_down - 1, col_index)] = square[np.ix_(rows_up - 1, col_index)]
            i = k_int + 1
            pair = np.array([i, i + half]) - 1
            swapped = np.array([i + half, i]) - 1
            cols = np.array([1, i]) - 1
            square[np.ix_(pair, cols)] = square[np.ix_(swapped, cols)]
        return square

    if size <= 0:
        result = np.zeros((0, 0))
    elif size == 1:
        result = np.array([[1.0]])
    elif size % 2 == 1:
        result = odd_order(size)
    elif size % 4 == 0:
        result = doubly_even(size)
    else:
        result = singly_even(size)
    if size == 2:
        _warn("There is no magic square of order 2.")
    return result


def hadamard(n):
    if (
        not is_numeric(n)
        or length(n) != 1
        or math.floor(float(np.asarray(n))) != math.ceil(float(np.asarray(n)))
        or float(np.asarray(n)) <= 1
    ):
        raise PracmaError("Argument 'n' must be a positiv integer.")
    order = float(np.asarray(n).reshape(-1)[0])
    logs = np.log2(np.array([order, order / 12.0, order / 20.0]))
    hits = [index for index, value in enumerate(logs, start=1) if math.floor(value) == math.ceil(value)]
    if not hits:
        raise PracmaError("Argument 'n' is not of the form 2^e, 12*2^e , or 20*2^e.")
    k = hits[0]
    exponent = float(logs[k - 1])
    if k == 1:
        matrix = np.array([[1.0]])
    elif k == 2:
        matrix = np.ones((12, 12))
        matrix[1:, 1:] = Toeplitz(
            np.array([-1, -1, 1, -1, -1, -1, 1, 1, 1, -1, 1.0]),
            np.array([-1, 1, -1, 1, 1, 1, -1, -1, -1, 1, -1.0]),
        )
    else:
        matrix = np.ones((20, 20))
        matrix[1:, 1:] = hankel(
            np.array([-1, -1, 1, 1, -1, -1, -1, -1, 1, -1, 1, -1, 1, 1, 1, 1, -1, -1, 1.0]),
            np.array([1, -1, -1, 1, 1, -1, -1, -1, -1, 1, -1, 1, -1, 1, 1, 1, 1, -1, -1.0]),
        )
    steps = int(exponent) if exponent >= 1 else 0
    seed = np.array([[1.0, 1.0], [1.0, -1.0]])
    for _ in range(steps):
        matrix = kron(seed, matrix)
    return matrix


def randortho(n, type="orthonormal"):
    stopifnot(
        [
            ("is.numeric(n)", is_numeric(n)),
            ("length(n) == 1", length(n) == 1),
            ("floor(n) == ceiling(n)", math.floor(float(np.asarray(n))) == math.ceil(float(np.asarray(n)))),
            ("n >= 1", float(np.asarray(n)) >= 1),
        ]
    )
    order = int(float(np.asarray(n)))
    if order == 1:
        return np.array([[1.0]])
    kind = match_arg(type, ["orthonormal", "unitary"])
    if kind == "orthonormal":
        draw = np.random.standard_normal((order, order)) / math.sqrt(2.0)
    else:
        draw = (np.random.standard_normal((order, order)) + 1j * np.random.standard_normal((order, order))) / math.sqrt(2.0)
    q, r = np.linalg.qr(draw, mode="complete")
    # Match R qr.Q column signs from the diagonal of R: ph = d/|d|.
    diagonal = np.diag(r).astype(complex if np.iscomplexobj(r) else float)
    phase = diagonal / np.abs(diagonal)
    result = q @ np.diag(phase)
    if result.dtype == complex and np.allclose(np.imag(result), 0):
        return np.real(result)
    return result
