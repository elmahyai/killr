"""Shared checks and base-R operations for the pracma linear-algebra ports."""

from __future__ import annotations

import math
import warnings

import numpy as np

from pracma._util import PracmaError

_EPS = float(np.finfo(float).eps)


def stopifnot(checks):
    for label, ok in checks:
        if not ok:
            raise PracmaError(f"{label} is not TRUE")


def match_arg(arg, choices):
    if arg is None:
        return choices[0]
    if isinstance(arg, (list, tuple)) and list(arg) == list(choices):
        return choices[0]
    text = arg if isinstance(arg, str) else None
    if text is None:
        raise PracmaError(_match_message(choices))
    matches = [choice for choice in choices if choice.startswith(text)]
    if len(matches) == 1:
        return matches[0]
    raise PracmaError(_match_message(choices))


def _match_message(choices):
    quoted = ", ".join(f"“{choice}”" for choice in choices)
    return f"'arg' should be one of {quoted}"


def warn(message):
    warnings.warn(message, stacklevel=3)


def is_numeric(value):
    if isinstance(value, (bool, np.bool_)):
        return False
    if isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, (bool, np.bool_)):
        return True
    if isinstance(value, (complex, np.complexfloating)):
        return False
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return True
        return all(is_numeric(item) or _is_numeric_row(item) for item in value)
    if isinstance(value, np.ndarray):
        if value.dtype == object or value.dtype == bool:
            return False
        return np.issubdtype(value.dtype, np.number) and not np.issubdtype(value.dtype, np.complexfloating)
    return False


def _is_numeric_row(item):
    if isinstance(item, (list, tuple)):
        return all(is_numeric(entry) for entry in item)
    return False


def is_complex(value):
    if isinstance(value, (complex, np.complexfloating)):
        return True
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return False
        return any(is_complex(item) for item in value) and all(
            is_numeric(item) or is_complex(item) or _is_numeric_row(item) for item in value
        )
    if isinstance(value, np.ndarray):
        return np.issubdtype(value.dtype, np.complexfloating)
    return False


def is_number(value):
    return is_numeric(value) or is_complex(value)


def is_matrix(value):
    if isinstance(value, np.ndarray):
        return value.ndim == 2
    if isinstance(value, (list, tuple)) and value and isinstance(value[0], (list, tuple)):
        return True
    return False


def is_vector(value):
    if is_matrix(value):
        return False
    if isinstance(value, (list, tuple, np.ndarray)):
        array = np.asarray(value)
        return array.ndim <= 1
    return isinstance(value, (int, float, complex, np.number)) and not isinstance(value, (bool, np.bool_))


def length(value):
    if value is None:
        return 0
    if isinstance(value, (int, float, complex, np.number)) and not isinstance(value, (bool, np.bool_)):
        return 1
    return int(np.asarray(value).size)


def as_float_matrix(value, complex_ok=False):
    dtype = complex if complex_ok and (is_complex(value) or _has_complex(value)) else float
    array = np.array(value, dtype=dtype, copy=True)
    if array.ndim == 0:
        array = array.reshape(1, 1)
    elif array.ndim == 1:
        array = array.reshape(-1, 1)
    return array


def _has_complex(value):
    try:
        return np.iscomplexobj(value)
    except Exception:
        return False


def as_vector(value, complex_ok=False):
    dtype = complex if complex_ok and _has_complex(value) else float
    if value is None:
        return np.array([], dtype=dtype)
    array = np.array(value, dtype=dtype, copy=True).reshape(-1)
    return array


def column_vector(value):
    """R matrix(c(v), ncol = 1) for an atomic vector."""
    data = as_vector(value, complex_ok=True)
    if data.size == 0:
        return np.zeros((0, 1))
    return data.reshape(-1, 1)


def ensure_matrix(value, complex_ok=False):
    if is_vector(value):
        return column_vector(value)
    return as_float_matrix(value, complex_ok=complex_ok)


def frobenius(value):
    array = np.asarray(value, dtype=complex if _has_complex(value) else float)
    if array.size == 0:
        return 0.0
    return float(np.linalg.norm(np.ravel(array)))


def _r_round_scalar(value, places):
    """R round: scale the fractional part, and round a half to even."""
    if not math.isfinite(value):
        return value
    sign = -1.0 if math.copysign(1.0, value) < 0 else 1.0
    magnitude = abs(value)
    if places == 0:
        return sign * float(round(magnitude))
    scale = 10.0 ** places
    whole = math.floor(magnitude)
    fraction = (magnitude - whole) * scale
    nearest = float(round(fraction))
    return sign * (whole + nearest / scale)


def zapsmall(value, digits=7):
    array = np.array(value, dtype=float, copy=True)
    finite = np.isfinite(array)
    if not np.any(finite):
        return array
    mx = float(np.max(np.abs(array[finite])))
    raw = float(digits) if mx <= 0 else max(0.0, digits - math.log10(mx))
    places = int(round(raw))
    rounded = np.vectorize(_r_round_scalar)(array, places)
    return rounded.astype(float)


def array_ind(index, shape):
    """1-based column-major position, matching R arrayInd."""
    offset = int(index) - 1
    rows = int(shape[0])
    return offset % rows + 1, offset // rows + 1


def which_max(values):
    """1-based index of the first maximum, column-major for matrices."""
    flat = np.ravel(np.asarray(values), order="F")
    if flat.size == 0:
        return 0
    return int(np.argmax(flat)) + 1


def matmul(left, right):
    a = np.asarray(left)
    b = np.asarray(right)
    if a.ndim == 1:
        a = a.reshape(1, -1) if b.ndim == 2 and b.shape[0] != a.shape[0] else a.reshape(-1, 1)
    if b.ndim == 1:
        b = b.reshape(-1, 1)
    return a @ b


def r_solve(a, b=None):
    matrix = np.asarray(a)
    if b is None:
        return np.linalg.solve(matrix, np.eye(matrix.shape[0], dtype=matrix.dtype))
    rhs = np.asarray(b)
    if rhs.ndim == 1:
        return np.linalg.solve(matrix, rhs)
    return np.linalg.solve(matrix, rhs)


def linpack_qr(a, tol=1e-7):
    """LINPACK dqrdc2, the default behind base::qr."""
    original = np.array(a, dtype=float, copy=True)
    if original.ndim == 1:
        original = original.reshape(-1, 1)
    n, p = original.shape
    x = original.copy()
    qraux = np.zeros(p)
    work = np.zeros(p)
    pivot = np.arange(1, p + 1)
    for j in range(p):
        qraux[j] = float(np.linalg.norm(x[:, j]))
        work[j] = qraux[j]
    lup = min(n, p)
    k = p
    col = 0
    while col < lup:
        if col >= k:
            break
        if not (qraux[col] > tol * work[col]):
            if col != k - 1:
                x[:, [col, k - 1]] = x[:, [k - 1, col]]
                qraux[col], qraux[k - 1] = qraux[k - 1], qraux[col]
                work[col], work[k - 1] = work[k - 1], work[col]
                pivot[col], pivot[k - 1] = pivot[k - 1], pivot[col]
            k -= 1
            continue
        nrmxl = float(np.linalg.norm(x[col:, col]))
        if nrmxl != 0.0:
            if x[col, col] != 0.0:
                nrmxl = math.copysign(nrmxl, x[col, col])
            x[col:, col] = x[col:, col] / nrmxl
            x[col, col] = 1.0 + x[col, col]
            for j in range(col + 1, p):
                dot = float(np.dot(x[col:, col], x[col:, j]))
                t = -dot / x[col, col]
                x[col:, j] = x[col:, j] + t * x[col:, col]
                if j < k and qraux[j] != 0.0:
                    tt = 1.0 - (abs(x[col, j]) / qraux[j]) ** 2
                    tt = max(tt, 0.0)
                    check = 1.0 + 0.05 * tt * (qraux[j] / work[j]) ** 2
                    if check == 1.0:
                        qraux[j] = float(np.linalg.norm(x[col + 1 :, j])) if col + 1 < n else 0.0
                    else:
                        qraux[j] = qraux[j] * math.sqrt(tt)
            qraux[col] = x[col, col]
            x[col, col] = -nrmxl
        else:
            qraux[col] = 0.0
        col += 1
    rank = k if col >= k else col
    return x, qraux, pivot, int(rank)


def linpack_q(x, qraux, rank):
    n = x.shape[0]
    result = np.eye(n)
    for col in range(int(rank) - 1, -1, -1):
        if qraux[col] == 0.0:
            continue
        reflector = x[col:, col].copy()
        reflector[0] = qraux[col]
        dots = reflector @ result[col:, :]
        scale = -dots / reflector[0]
        result[col:, :] = result[col:, :] + np.outer(reflector, scale)
    return result


def svd_full(a):
    matrix = np.asarray(a, dtype=complex if _has_complex(a) else float)
    u, s, vh = np.linalg.svd(matrix, full_matrices=True)
    return u, s, vh.conj().T


def eps_of(value):
    from pracma.elementary import eps

    return float(eps(value))
