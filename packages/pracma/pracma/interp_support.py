"""Private helpers for the pracma interpolation slice."""

from __future__ import annotations

import ctypes
import math
import warnings

import numpy as np

from pracma._util import PracmaError
from pracma.arrays import Norm, conv

_LAPACK = ctypes.CDLL(
    "/usr/lib/x86_64-linux-gnu/openblas-pthread/libopenblasp-r0.3.29.so"
)
_dgeev = _LAPACK.dgeev_
_EPS = float(np.finfo(float).eps)


def stopifnot(ok: bool, expr: str) -> None:
    if not ok:
        raise PracmaError(f"{expr} is not TRUE")


def match_arg(arg, choices):
    """R match.arg. None is the first choice. Quotes are U+201C and U+201D."""
    if arg is None:
        return choices[0]
    if isinstance(arg, (list, tuple)) and arg and all(item in choices for item in arg):
        return choices[0]
    text = str(arg)
    exact = [choice for choice in choices if choice == text]
    if len(exact) == 1:
        return exact[0]
    partial = [choice for choice in choices if choice.startswith(text)]
    if len(partial) == 1:
        return partial[0]
    quoted = ", ".join("\u201c" + choice + "\u201d" for choice in choices)
    raise PracmaError(f"'arg' should be one of {quoted}")


def r_colon(start, end) -> np.ndarray:
    """R's colon. The step is 1, and a backward range counts down."""
    left = float(start)
    right = float(end)
    count = int(math.floor(abs(right - left))) + 1
    if right >= left:
        return left + np.arange(count, dtype=float)
    return left - np.arange(count, dtype=float)


def r_matrix(data, nrow: int, ncol: int) -> np.ndarray:
    """matrix() fills down columns. The result is stored in display order."""
    values = np.asarray(data, dtype=float).reshape(-1)
    if nrow < 0 or ncol < 0:
        raise PracmaError("invalid 'nrow' value (< 0)")
    if nrow * ncol != values.size and values.size != 1 and not (nrow == 0 or ncol == 0):
        if values.size == 0:
            return np.zeros((nrow, ncol))
    if values.size == 1 and nrow * ncol != 1:
        values = np.repeat(values, nrow * ncol)
    if nrow == 0 or ncol == 0:
        return np.zeros((max(nrow, 0), max(ncol, 0)))
    return np.reshape(np.array(values, dtype=float), (nrow, ncol), order="F")


def r_get(values, indices) -> np.ndarray:
    """1-based R subset. Zero is dropped. A positive index past the end is NA."""
    vector = np.asarray(values, dtype=float).reshape(-1)
    picked = []
    for index in np.asarray(indices, dtype=int).reshape(-1):
        if index == 0:
            continue
        if index < 0 or index > vector.size:
            picked.append(np.nan)
        else:
            picked.append(vector[index - 1])
    return np.array(picked, dtype=float)


def r_set(values, indices, replacement) -> np.ndarray:
    """1-based replacement. An index past the end extends the vector."""
    vector = list(np.asarray(values, dtype=float).reshape(-1))
    slots = np.asarray(indices, dtype=int).reshape(-1)
    incoming = np.asarray(replacement, dtype=float).reshape(-1)
    if incoming.size == 1 and slots.size != 1:
        incoming = np.repeat(incoming, slots.size)
    for index, item in zip(slots, incoming):
        if index <= 0:
            continue
        while len(vector) < index:
            vector.append(np.nan)
        vector[index - 1] = float(item)
    return np.array(vector, dtype=float)


def which_index(mask) -> np.ndarray:
    """1-based positions of TRUE values, in storage order."""
    flags = np.asarray(mask, dtype=bool)
    return (np.flatnonzero(flags.reshape(-1)) + 1).astype(int)


def which_arr(mask):
    """1-based row and column of TRUE cells, walking down columns."""
    flags = np.asarray(mask, dtype=bool)
    if flags.ndim != 2:
        raise PracmaError("arr.ind requires a matrix")
    flat = np.flatnonzero(np.ravel(flags, order="F"))
    rows = flat % flags.shape[0] + 1
    cols = flat // flags.shape[0] + 1
    return rows.astype(int), cols.astype(int)


def find_interval(x, vec) -> np.ndarray:
    """R findInterval. 0 when x is left of vec, length(vec) when x is at or past the end."""
    knots = np.asarray(vec, dtype=float).reshape(-1)
    points = np.asarray(x, dtype=float).reshape(-1)
    if knots.size == 0:
        return np.zeros(points.size, dtype=int)
    return np.searchsorted(knots, points, side="right").astype(int)


def zapsmall(x, digits: int = 7):
    values = np.array(x, copy=True)
    if values.size == 0:
        return values
    finite = np.abs(values[np.isfinite(values)])
    if finite.size == 0:
        return values
    largest = float(np.max(finite))
    if largest > 0:
        places = max(0, int(digits) - int(math.log10(largest)) - 1)
    else:
        places = int(digits)
    return np.round(values, places)


def r_character_double(value: float) -> str:
    """R as.character for one double."""
    if math.isnan(value):
        return "NA"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == 0.0:
        return "0"
    negative = value < 0
    scientific = format(abs(value), ".14e")
    mantissa, exponent_text = scientific.split("e")
    exponent = int(exponent_text)
    whole, frac = mantissa.split(".")
    frac = frac.rstrip("0")
    mant = whole if frac == "" else f"{whole}.{frac}"
    digits = whole + frac
    sci = f"{mant}e{exponent:+03d}"
    if exponent >= 0:
        point = len(whole) + exponent
        if point >= len(digits):
            fixed = digits + ("0" * (point - len(digits)))
        else:
            fixed = digits[:point] + "." + digits[point:]
    else:
        zeros = -exponent - len(whole)
        if zeros >= 0:
            fixed = "0." + ("0" * zeros) + digits
        else:
            point = len(digits) + zeros
            fixed = digits[:point] + "." + digits[point:]
    if negative:
        sci = "-" + sci
        fixed = "-" + fixed
    if len(sci) < len(fixed):
        return sci
    return fixed


def format_c(value: float, digits: int = 7) -> str:
    """formatC(..., format = 'g') after the leading spaces are removed."""
    if math.isnan(value):
        return "NA"
    return format(float(value), f".{int(digits)}g")


def is_numeric_value(value) -> bool:
    if value is None or isinstance(value, (bool, np.bool_, str, bytes)):
        return False
    if isinstance(value, (int, float, np.integer, np.floating)):
        return True
    if isinstance(value, (complex, np.complexfloating)):
        return False
    array = np.asarray(value)
    if array.dtype == object or array.dtype == bool:
        return False
    return np.issubdtype(array.dtype, np.number) and not np.issubdtype(array.dtype, np.complexfloating)


def is_number_or_complex(value) -> bool:
    if value is None or isinstance(value, (bool, np.bool_, str, bytes)):
        return False
    if isinstance(value, (int, float, complex, np.integer, np.floating, np.complexfloating)):
        return True
    array = np.asarray(value)
    if array.dtype == object or array.dtype == bool:
        return False
    return np.issubdtype(array.dtype, np.number)


def as_vector(value, complex_ok: bool = False) -> np.ndarray:
    """A 1-d numeric vector. A matrix stays rejected by the caller via ndim."""
    if value is None:
        return np.array([], dtype=complex if complex_ok else float)
    if isinstance(value, (str, bytes, bool, np.bool_)):
        raise PracmaError("value must be numeric")
    array = np.asarray(value)
    if array.dtype == object or array.dtype == bool:
        raise PracmaError("value must be numeric")
    if np.iscomplexobj(array):
        if not complex_ok:
            raise PracmaError("value must be numeric")
        return np.array(array, dtype=complex).reshape(-1)
    if not np.issubdtype(array.dtype, np.number):
        raise PracmaError("value must be numeric")
    return np.array(array, dtype=float).reshape(-1)


def is_r_vector(value) -> bool:
    if value is None or isinstance(value, (str, bytes)):
        return False
    if isinstance(value, (int, float, complex, np.integer, np.floating, np.complexfloating)):
        return True
    if isinstance(value, (bool, np.bool_)):
        return False
    array = np.asarray(value)
    return array.ndim <= 1


def is_r_matrix(value) -> bool:
    if isinstance(value, (str, bytes)) or value is None:
        return False
    array = np.asarray(value)
    return array.ndim == 2


def flatten_c(matrix) -> np.ndarray:
    array = np.asarray(matrix)
    if array.ndim == 0:
        return array.reshape(1)
    if array.ndim == 1:
        return array
    return np.ravel(array, order="F")


def pad_zeros(values, count: int) -> np.ndarray:
    """c(values, zeros(1, count)). A non-positive count adds nothing."""
    vector = np.asarray(values).reshape(-1)
    extra = int(math.floor(count))
    if extra <= 0:
        return vector.copy()
    pad = np.zeros(extra, dtype=vector.dtype)
    return np.concatenate([vector, pad])


def repmat(a, n, m=None):
    if a is None or np.asarray(a).size == 0:
        return np.array([])
    if not is_number_or_complex(a):
        raise PracmaError("Argument 'a' must be a numeric or complex.")
    if m is None:
        m = n
    if not is_numeric_value(n) or not is_numeric_value(m):
        raise PracmaError("Arguments 'n' and 'm' must be single integers.")
    n_arr = np.asarray(n)
    m_arr = np.asarray(m)
    if n_arr.size != 1 or m_arr.size != 1:
        raise PracmaError("Arguments 'n' and 'm' must be single integers.")
    rows = max(math.floor(float(n_arr.reshape(-1)[0])), 0)
    cols = max(math.floor(float(m_arr.reshape(-1)[0])), 0)
    block = np.asarray(a)
    if block.ndim <= 1:
        block = np.reshape(block, (1, block.size))
    if rows <= 0 or cols <= 0:
        return np.zeros((rows, cols))
    return np.kron(np.ones((rows, cols)), block)


def toeplitz(a, b=None) -> np.ndarray:
    column = np.asarray(a, dtype=float).reshape(-1)
    row = column if b is None else np.asarray(b, dtype=float).reshape(-1)
    if column.size and row.size and column[0] != row[0]:
        warnings.warn("First elements of vectors 'a', 'b' are not equal.", stacklevel=2)
    out = np.empty((column.size, row.size), dtype=float)
    if row.size:
        out[0, :] = row
    if column.size:
        out[:, 0] = column
    for i in range(1, column.size):
        if row.size > 1:
            out[i, 1:] = out[i - 1, :-1]
    return out


def pinv(A, tol=None) -> np.ndarray:
    matrix = np.asarray(A, dtype=float)
    if matrix.ndim != 2:
        raise PracmaError("A must be a matrix")
    if tol is None:
        tol = _EPS ** (2.0 / 3.0)
    u, singular, vt = np.linalg.svd(matrix, full_matrices=False)
    if singular.size == 0:
        return np.zeros((matrix.shape[1], matrix.shape[0]))
    keep = singular > max(float(tol) * float(singular[0]), 0.0)
    if not np.any(keep):
        return np.zeros((matrix.shape[1], matrix.shape[0]))
    return (vt[keep].T * (1.0 / singular[keep])) @ u[:, keep].T


def nullspace(M):
    if not is_numeric_value(M):
        raise PracmaError("Argument 'M' must be a numeric matrix.")
    matrix = np.asarray(M, dtype=float)
    if matrix.ndim <= 1:
        matrix = matrix.reshape(-1, 1)
    _u, singular, vt = np.linalg.svd(matrix, full_matrices=True)
    if singular.size == 0:
        rank = 0
    else:
        tol = max(matrix.shape) * float(np.max(singular)) * _EPS
        rank = int(np.sum(singular > tol))
    if rank == matrix.shape[1]:
        return None
    basis = vt[rank:].T
    if basis.size == 0:
        return None
    return basis


def _dgeev_values(matrix: np.ndarray):
    source = np.array(matrix, dtype=np.float64, order="F")
    n = source.shape[0]
    wr = np.zeros(n, dtype=np.float64)
    wi = np.zeros(n, dtype=np.float64)
    vl = np.zeros(1, dtype=np.float64)
    vr = np.zeros(1, dtype=np.float64)
    job = ctypes.c_char(b"N")
    n_c = ctypes.c_int(n)
    one = ctypes.c_int(1)
    info = ctypes.c_int(0)
    query = np.zeros(1, dtype=np.float64)
    lwork = ctypes.c_int(-1)
    _dgeev(
        ctypes.byref(job),
        ctypes.byref(job),
        ctypes.byref(n_c),
        source.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        ctypes.byref(n_c),
        wr.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        wi.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        vl.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        ctypes.byref(one),
        vr.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        ctypes.byref(one),
        query.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        ctypes.byref(lwork),
        ctypes.byref(info),
    )
    work = np.zeros(max(int(query[0]), 1), dtype=np.float64)
    source = np.array(matrix, dtype=np.float64, order="F")
    lwork = ctypes.c_int(work.size)
    _dgeev(
        ctypes.byref(job),
        ctypes.byref(job),
        ctypes.byref(n_c),
        source.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        ctypes.byref(n_c),
        wr.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        wi.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        vl.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        ctypes.byref(one),
        vr.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        ctypes.byref(one),
        work.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        ctypes.byref(lwork),
        ctypes.byref(info),
    )
    if info.value != 0:
        raise PracmaError("LAPACK dgeev failed")
    return wr, wi


def _is_symmetric(array: np.ndarray) -> bool:
    scale = max(1.0, float(np.max(np.abs(array))))
    return float(np.max(np.abs(array - array.T))) <= 100 * _EPS * scale


def eig_values(a):
    """R eigen values.

    A symmetric matrix uses the symmetric solver, ordered by decreasing value.
    Any other real matrix uses DGEEV from the system OpenBLAS, then a selection
    sort that moves a strictly larger modulus forward and keeps equal moduli
    in that DGEEV order.
    """
    if a is None or np.asarray(a).size == 0:
        return np.zeros((0, 0))
    array = np.asarray(a, dtype=float)
    if array.size == 1 and array.ndim <= 1:
        return np.array(array, dtype=float).reshape(-1)
    if array.ndim != 2 or array.shape[0] != array.shape[1]:
        raise PracmaError("non-square matrix in 'eigen'")
    if _is_symmetric(array):
        return np.linalg.eigvalsh(array)[::-1]
    wr, wi = _dgeev_values(array)
    n = wr.size
    for i in range(n - 1):
        modulus = math.hypot(float(wr[i]), float(wi[i]))
        chosen = i
        for j in range(i + 1, n):
            other = math.hypot(float(wr[j]), float(wi[j]))
            if other > modulus:
                chosen = j
                modulus = other
        if chosen != i:
            wr[i], wr[chosen] = wr[chosen], wr[i]
            wi[i], wi[chosen] = wi[chosen], wi[i]
    if np.all(wi == 0):
        return np.array(wr, dtype=float, copy=True)
    return wr + 1j * wi


def compan(p) -> np.ndarray:
    coeffs = np.asarray(p)
    if np.iscomplexobj(coeffs):
        coeffs = np.array(coeffs, dtype=complex).reshape(-1)
    else:
        coeffs = np.array(coeffs, dtype=float).reshape(-1)
    if coeffs.size == 0:
        return np.array([])
    while coeffs.size >= 2 and coeffs[0] == 0:
        coeffs = coeffs[1:]
    n = coeffs.size
    if n <= 1:
        return np.array([])
    if n == 2:
        return np.array([-coeffs[1] / coeffs[0]])
    matrix = np.zeros((n - 1, n - 1), dtype=float if not np.iscomplexobj(coeffs) else complex)
    for i in range(1, n - 1):
        matrix[i, i - 1] = 1
    matrix[0, :] = -coeffs[1:] / coeffs[0]
    return matrix


def deconv(b, a):
    if b is None or np.asarray(b).size == 0:
        return {"q": np.array([0.0]), "r": np.array([])}
    left = np.asarray(b)
    right = np.asarray(a)
    if np.iscomplexobj(left) or np.iscomplexobj(right):
        left = np.array(left, dtype=complex).reshape(-1)
        right = np.array(right, dtype=complex).reshape(-1)
    else:
        left = np.array(left, dtype=float).reshape(-1)
        right = np.array(right, dtype=float).reshape(-1)
    if right.size and right[0] == 0:
        raise PracmaError("First element of argument 'a' must be nonzero.")
    if left.size < right.size:
        return {"q": np.array([0.0]), "r": left}
    quotient = []
    while left.size >= right.size:
        scale = left[0] / right[0]
        pad = np.concatenate([np.array([scale]), np.zeros(left.size - right.size, dtype=left.dtype)])
        left = left - conv(right, pad).astype(left.dtype, copy=False)
        quotient.append(scale)
        left = left[1:]
    if not quotient:
        quotient = [0.0]
    return {"q": np.array(quotient), "r": left}


def qr_solve(A, b) -> np.ndarray:
    matrix = np.asarray(A, dtype=float)
    target = np.asarray(b, dtype=float).reshape(-1)
    if matrix.ndim == 1:
        matrix = matrix.reshape(-1, 1)
    solution, _residuals, _rank, _sv = np.linalg.lstsq(matrix, target, rcond=None)
    return np.asarray(solution, dtype=float).reshape(-1)


def approx(x, y, xout, method: str = "linear"):
    """stats::approx with rule = 1, f = 0, and ties = mean."""
    knots = np.array(x, dtype=float).reshape(-1)
    values = np.array(y, dtype=float).reshape(-1)
    points = np.array(xout, dtype=float).reshape(-1)
    if knots.size == 0:
        return np.full(points.shape, np.nan)
    order = np.argsort(knots, kind="mergesort")
    knots = knots[order]
    values = values[order]
    unique, inverse = np.unique(knots, return_inverse=True)
    if unique.size != knots.size:
        summed = np.zeros(unique.size)
        counts = np.zeros(unique.size)
        for index, group in enumerate(inverse):
            summed[group] += values[index]
            counts[group] += 1
        knots = unique
        values = summed / counts
    out = np.full(points.shape, np.nan)
    if knots.size == 1:
        out[points == knots[0]] = values[0]
        return out
    index = find_interval(points, knots)
    inside = (index >= 1) & (points <= knots[-1])
    if method == "constant":
        chosen = np.minimum(index, knots.size) - 1
        out[inside] = values[chosen[inside]]
        return out
    left = np.clip(index - 1, 0, knots.size - 2)
    span = knots[left + 1] - knots[left]
    weight = np.zeros(points.shape)
    np.divide(points - knots[left], span, out=weight, where=span != 0)
    out[inside] = values[left[inside]] + weight[inside] * (
        values[left[inside] + 1] - values[left[inside]]
    )
    at_end = points == knots[-1]
    out[at_end] = values[-1]
    return out


def fact(n):
    if not is_numeric_value(n):
        raise PracmaError("Argument 'n' must be a numeric vector or matrix.")
    array = np.asarray(n, dtype=float)
    shape = array.shape
    values = np.floor(array.reshape(-1))
    out = np.ones(values.size)
    out[values > 170] = np.inf
    out[values < 0] = np.nan
    out[np.isnan(values)] = np.nan
    wanted = np.where((values > 0) & (values <= 170))[0]
    if wanted.size:
        targets = values[wanted]
        running = 1.0
        filled = np.zeros(targets.size)
        for k in range(1, int(np.max(targets)) + 1):
            running *= k
            filled[targets == k] = running
        out[wanted] = filled
    return out.reshape(shape) if shape else out.reshape(-1)


def fderiv(f, x, n=1, h=0, method="central"):
    if x is None or np.asarray(x).size == 0:
        return np.array([])
    if not is_numeric_value(x):
        raise PracmaError("Argument 'x' must be a number or a numeric vector.")
    order = math.floor(float(n))
    if order < 0:
        raise PracmaError("The order of the derivative, 'n', can only be between 0 and 8.")
    if order > 8:
        warnings.warn("Numerical derivatives of order 'n > 8' will be very inexact.", stacklevel=2)
    method = match_arg(method, ["central", "forward", "backward"])
    points = np.asarray(x, dtype=float).reshape(-1)

    def call(at):
        return np.asarray(f(at), dtype=float).reshape(-1)

    if call(points).size != points.size:
        raise PracmaError("Function 'f' must first be vectorized: Vectorize(f).")
    if order == 0:
        return call(points)
    step = float(h)
    if step == 0:
        step = _EPS ** (1.0 / (order + 2))
    if method == "central":
        if order == 1:
            return (call(points + step) - call(points - step)) / (2 * step)
        if order == 2:
            return (call(points + step) - 2 * call(points) + call(points - step)) / step**2
        if order == 3:
            return (
                call(points + 2 * step) - 2 * call(points + step) + 2 * call(points - step) - call(points - 2 * step)
            ) / (2 * step**3)
        if order == 4:
            return (
                call(points + 2 * step)
                - 4 * call(points + step)
                + 6 * call(points)
                - 4 * call(points - step)
                + call(points - 2 * step)
            ) / step**4
        nodes = r_colon(order / 2, -order / 2)
        weights = ((-1) ** np.arange(order + 1)) * np.array([math.comb(order, k) for k in range(order + 1)])
        total = np.zeros(points.shape)
        for weight, node in zip(weights, nodes):
            total = total + weight * call(node * step + 0 * points if points.size == 1 else node * step + points * 0 + node * 0)
            # call at the shifted scalar or vector
        # The R formula is sum(weights * f(nodes * h)) / h^n for a scalar x.
        # Recompute plainly so a vector x is shifted at each node.
        total = np.zeros(points.size)
        for weight, node in zip(weights, nodes):
            total = total + weight * call(points + node * step)
        return total / step**order
    if method == "forward":
        if order == 1:
            return (-call(points + 2 * step) + 4 * call(points + step) - 3 * call(points)) / (2 * step)
        if order == 2:
            return (-call(points + 3 * step) + 4 * call(points + 2 * step) - 5 * call(points + step) + 2 * call(points)) / step**2
        nodes = r_colon(order, 0)
        weights = ((-1) ** np.arange(order + 1)) * np.array([math.comb(order, k) for k in range(order + 1)])
        total = np.zeros(points.size)
        for weight, node in zip(weights, nodes):
            total = total + weight * call(points + node * step)
        return total / step**order
    if order == 1:
        return (3 * call(points) - 4 * call(points - step) + call(points - 2 * step)) / (2 * step)
    if order == 2:
        return (2 * call(points) - 5 * call(points - step) + 4 * call(points - 2 * step) - call(points - 3 * step)) / step**2
    nodes = r_colon(0, -order)
    weights = ((-1) ** np.arange(order + 1)) * np.array([math.comb(order, k) for k in range(order + 1)])
    total = np.zeros(points.size)
    for weight, node in zip(weights, nodes):
        total = total + weight * call(points + node * step)
    return total / step**order


def fnorm(f, g, x1, x2, p=2, npoints=100):
    stopifnot(is_numeric_value(x1) and np.asarray(x1).size == 1, "is.numeric(x1) && length(x1) == 1")
    stopifnot(is_numeric_value(x2) and np.asarray(x2).size == 1 and float(x1) < float(x2), "is.numeric(x2)")
    grid = np.linspace(float(x1), float(x2), int(npoints))
    left = np.asarray(f(grid), dtype=float).reshape(-1)
    right = np.asarray(g(grid), dtype=float).reshape(-1)
    if left.size != npoints or right.size != npoints:
        raise PracmaError("Arguments 'f' and 'g' must be vectorized functions.")
    return Norm(left - right, p)


def nelder_mead(func, start, maxit: int = 500, reltol: float = 1e-8) -> np.ndarray:
    """Nelder-Mead with R's initial step of one tenth of the largest |parameter|."""
    origin = np.array(start, dtype=float).reshape(-1)
    n = origin.size
    step = 0.0
    for value in origin:
        step = max(step, 0.1 * abs(float(value)))
    if step == 0.0:
        step = 0.1
    simplex = [origin.copy()]
    for j in range(n):
        vertex = origin.copy()
        trial = step
        while vertex[j] == origin[j]:
            vertex[j] = origin[j] + trial
            trial *= 10.0
        simplex.append(vertex)
    scores = [float(func(vertex)) for vertex in simplex]
    alpha, gamma, rho, sigma = 1.0, 2.0, 0.5, 0.5
    for _ in range(maxit):
        order = list(np.argsort(scores, kind="mergesort"))
        simplex = [simplex[i] for i in order]
        scores = [scores[i] for i in order]
        best = scores[0]
        worst = scores[-1]
        spread = max(float(np.max(np.abs(vertex - simplex[0]))) for vertex in simplex)
        if spread <= reltol or abs(worst - best) <= reltol * (abs(best) + reltol) and spread <= 1e-8:
            break
        centroid = np.mean(simplex[:-1], axis=0)
        reflected = centroid + alpha * (centroid - simplex[-1])
        score_r = float(func(reflected))
        if best <= score_r < scores[-2]:
            simplex[-1] = reflected
            scores[-1] = score_r
            continue
        if score_r < best:
            expanded = centroid + gamma * (reflected - centroid)
            score_e = float(func(expanded))
            if score_e < score_r:
                simplex[-1] = expanded
                scores[-1] = score_e
            else:
                simplex[-1] = reflected
                scores[-1] = score_r
            continue
        contracted = centroid + rho * (simplex[-1] - centroid)
        score_c = float(func(contracted))
        if score_c < worst:
            simplex[-1] = contracted
            scores[-1] = score_c
            continue
        for i in range(1, n + 1):
            simplex[i] = simplex[0] + sigma * (simplex[i] - simplex[0])
            scores[i] = float(func(simplex[i]))
    return simplex[int(np.argmin(scores))]


def convolve_open(x, y) -> np.ndarray:
    """stats::convolve(x, rev(y), type = 'open', conj = TRUE), which is conv(x, y)."""
    left = np.asarray(x, dtype=float).reshape(-1)
    right = np.asarray(y, dtype=float).reshape(-1)
    if left.size == 0 or right.size == 0:
        return np.array([])
    return np.convolve(left, right, mode="full")
