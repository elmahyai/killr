"""Weighted variance and standard deviation, ported from matrixStats 1.5.0.

The center is ``sum(w * x) / sum(w)`` after this file's own weight filter.
It is not ``weightedMean``: a weight that is missing or not strictly positive
is dropped here, and a missing weight that remains makes the result missing.
The divisor is ``sum(w) - 1``.
"""

from __future__ import annotations

import math
import struct
import warnings

import numpy as np

from matrixstats._values import as_logical, prepare_idxs

_R_NA_BITS = 0x7FF00000000007A2
_R_NA = np.array([_R_NA_BITS], dtype=np.uint64).view(np.float64)[0]
_INT_MIN = -2147483648
_INT_MAX = 2147483647

_INVALID = (
    "Produced invalid variance estimate, because the weights suggest at most "
    "one effective observation (sum(w) <= 1): %s (wsum = %s)"
)


def weightedVar(x, w=None, idxs=None, na_rm=False, center=None):
    """Weighted sample variance of a numeric vector.

    Mirrors ``matrixStats::weightedVar``. ``idxs`` is 1-based. ``None`` uses
    every element. ``w`` of ``None`` gives every original element weight 1
    and is not subset by ``idxs``. A weight that is not strictly positive is
    dropped. A missing weight that is still present makes the result R's NA.
    ``center`` of ``None`` is ``sum(w * x) / sum(w)`` on the values that
    remain. The divisor is ``sum(w) - 1``.
    """
    na_rm = as_logical(na_rm, "na.rm")
    values = _as_float_1d(x, "x")
    if w is None:
        weights = np.ones(values.size, dtype=np.float64)
        if idxs is not None:
            values = _take(_positions(idxs, values.size, matrix=False), values)
    else:
        weights = _as_float_1d(w, "w")
        if weights.size != values.size:
            raise ValueError(_mismatch(weights.size, values.size))
        if idxs is not None:
            positions = _positions(idxs, values.size, matrix=False)
            values = _take(positions, values)
            weights = _take(positions, weights)
    return _variance(values, weights, na_rm, center)


def weightedSd(x, w=None, idxs=None, na_rm=False, center=None):
    """Weighted sample standard deviation of a numeric vector.

    ``sqrt(weightedVar(...))``. A negative variance, which happens when
    ``sum(w) < 1``, becomes NaN.
    """
    return _square_root(weightedVar(x, w=w, idxs=idxs, na_rm=na_rm, center=center))


def rowWeightedVars(x, w=None, rows=None, cols=None, na_rm=False, center=None, use_names=True):
    """Weighted variance of each row.

    ``x`` is a 2-d array whose axis 0 is rows and axis 1 is columns, matching
    the printed R matrix. ``rows`` and ``cols`` are 1-based. ``None`` selects
    the whole margin. ``w`` has one weight per column and is indexed with
    ``cols``. ``use_names`` is accepted and the result is a plain float64 vector.
    """
    return _margin(x, w, rows, cols, na_rm, center, use_names, by_row=True)


def colWeightedVars(x, w=None, rows=None, cols=None, na_rm=False, center=None, use_names=True):
    """Weighted variance of each column.

    Arguments match :func:`rowWeightedVars`. ``w`` has one weight per row and
    is indexed with ``rows``.
    """
    return _margin(x, w, rows, cols, na_rm, center, use_names, by_row=False)


def rowWeightedSds(x, w=None, rows=None, cols=None, na_rm=False, center=None, use_names=True):
    """Weighted standard deviation of each row.

    ``sqrt(rowWeightedVars(...))``.
    """
    return _square_root(
        rowWeightedVars(
            x, w=w, rows=rows, cols=cols, na_rm=na_rm, center=center, use_names=use_names
        )
    )


def colWeightedSds(x, w=None, rows=None, cols=None, na_rm=False, center=None, use_names=True):
    """Weighted standard deviation of each column.

    ``sqrt(colWeightedVars(...))``.
    """
    return _square_root(
        colWeightedVars(
            x, w=w, rows=rows, cols=cols, na_rm=na_rm, center=center, use_names=use_names
        )
    )


def _margin(x, w, rows, cols, na_rm, center, use_names, by_row: bool):
    matrix = _require_matrix(x)
    as_logical(use_names, "useNames")
    na_rm = as_logical(na_rm, "na.rm")
    row_pos = _margin_positions(rows, matrix.shape[0])
    col_pos = _margin_positions(cols, matrix.shape[1])
    selected = _materialize(matrix, row_pos, col_pos)
    weight_index = cols if by_row else rows
    weights = _maybe_subset_w(w, weight_index)
    return _apply_margin(selected, weights, na_rm, center, by_row)


def _apply_margin(matrix, weights, na_rm, center, by_row: bool):
    data = matrix if by_row else np.swapaxes(matrix, 0, 1)
    data = np.ascontiguousarray(data, dtype=np.float64)
    n_out, n_in = data.shape
    if n_out == 0:
        proto_w = np.ones(n_in, dtype=np.float64) if weights is None else weights
        if weights is not None and proto_w.size != n_in:
            raise ValueError(_mismatch(int(proto_w.size), n_in))
        _variance(np.zeros(n_in, dtype=np.float64), proto_w, na_rm, center)
        return np.zeros(0, dtype=np.float64)
    if weights is not None and weights.size != n_in:
        raise ValueError(_mismatch(int(weights.size), n_in))
    if _fast_ok(data, weights, center):
        return _fast_vars(data, weights)
    out = np.empty(n_out, dtype=np.float64)
    ones = None if weights is not None else np.ones(n_in, dtype=np.float64)
    for i in range(n_out):
        _store(out, i, _variance(data[i], ones if weights is None else weights, na_rm, center))
    return out


def _fast_ok(data, weights, center) -> bool:
    if center is not None or np.isnan(data).any():
        return False
    if weights is None:
        return True
    return bool(np.all(np.isfinite(weights)) and np.all(weights > 0))


def _fast_vars(data, weights):
    n_out, n_in = data.shape
    if n_in <= 1:
        return _na_vector(n_out)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        if weights is None:
            wsum = float(n_in)
            centers = np.sum(data, axis=1) / wsum
            resid = data - centers[:, None]
            sigma2 = np.sum(resid * resid, axis=1) / (wsum - 1.0)
        else:
            wsum = float(np.sum(weights))
            centers = data @ weights / wsum
            resid = data - centers[:, None]
            sigma2 = (resid * resid) @ weights / (wsum - 1.0)
    sigma2 = np.asarray(sigma2, dtype=np.float64).copy()
    if wsum <= 1.0:
        for value in sigma2:
            _warn_invalid(float(value), wsum, missing=False)
    return sigma2


def _variance(x, w, na_rm, center):
    if x.size == w.size:
        keep = np.isnan(w) | (w > 0)
        if not np.all(keep):
            x = x[keep]
            w = w[keep]
    if na_rm:
        keep = ~np.isnan(x)
        if x.size != w.size or not np.all(keep):
            positions = np.flatnonzero(keep)
            x = x[keep]
            w = _take(positions, w)
    elif np.isnan(x).any():
        return _R_NA
    if np.isnan(w).any():
        return _R_NA
    if x.size == w.size:
        infinite = np.isinf(w)
        if np.any(infinite):
            x = x[infinite]
            w = np.ones(x.size, dtype=np.float64)
    if x.size <= 1:
        return _R_NA
    return _finish(x, w, center)


def _finish(x, w, center):
    wsum = float(np.sum(w))
    center_missing = False
    if center is None:
        if x.size == w.size:
            center_value = float(np.sum(w * x) / wsum)
            resid = x - center_value
        else:
            center_value = _sum_product(w, x) / wsum
            resid = x - center_value
    else:
        center_arr = _as_float_1d(center, "center")
        center_missing = bool(np.isnan(center_arr).any())
        resid = _subtract(x, center_arr)
    if center_missing:
        numer = math.nan
    elif resid.size == 0:
        numer = 0.0
    elif resid.size == w.size:
        numer = float(np.sum(w * resid * resid))
    else:
        numer = _sum_product(w, resid * resid)
    if center_missing:
        if wsum <= 1.0:
            _warn_invalid(math.nan, wsum, missing=True)
        return _R_NA
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        sigma2 = float(np.divide(numer, wsum - 1.0))
    if wsum <= 1.0:
        _warn_invalid(sigma2, wsum, missing=False)
    if math.isnan(sigma2):
        return np.float64(np.nan)
    return np.float64(sigma2)


def _square_root(variance):
    array = np.asarray(variance, dtype=np.float64)
    scalar = not isinstance(variance, np.ndarray) or variance.ndim == 0
    flat = np.array(array, dtype=np.float64, copy=True).reshape(-1)
    warned = False
    bits = flat.view(np.uint64)
    for i, value in enumerate(flat):
        if _is_r_na(value):
            bits[i] = np.uint64(_R_NA_BITS)
        elif math.isnan(value):
            flat[i] = np.nan
        elif value < 0.0:
            if not warned:
                _warn("NaNs produced")
                warned = True
            flat[i] = np.nan
        else:
            flat[i] = math.sqrt(float(value))
    if scalar:
        return flat[0]
    return flat.reshape(array.shape)


def _subtract(x, center):
    if center.size == 1:
        return x - float(center[0])
    if center.size == 0 or x.size == 0:
        return np.zeros(0, dtype=np.float64)
    n = max(x.size, center.size)
    if n % x.size != 0 or n % center.size != 0:
        _warn("longer object length is not a multiple of shorter object length")
    return np.resize(x, n) - np.resize(center, n)


def _sum_product(a, b) -> float:
    if a.size == 0 or b.size == 0:
        return 0.0
    if a.size == b.size:
        return float(np.sum(a * b))
    n = max(a.size, b.size)
    if n % a.size != 0 or n % b.size != 0:
        _warn("longer object length is not a multiple of shorter object length")
    return float(np.sum(np.resize(a, n) * np.resize(b, n)))


def _warn_invalid(sigma2: float, wsum: float, missing: bool) -> None:
    shown = "NA" if missing else _r_g(sigma2)
    _warn(_INVALID % (shown, _r_g(wsum)))


def _r_g(value: float) -> str:
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0.0 else "-Inf"
    return format(float(value), ".6g")


_warn_line = 0


def _warn(message: str) -> None:
    # A fresh line number keeps identical messages from being shown only once.
    global _warn_line
    _warn_line += 1
    warnings.warn_explicit(message, UserWarning, __file__, _warn_line)


def _is_r_na(value) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    if not math.isnan(number):
        return False
    bits = struct.unpack("<Q", struct.pack("<d", number))[0]
    low = bits & 0xFFFFFFFF
    high = bits >> 32
    return low == 0x7A2 and high in (0x7FF00000, 0x7FF80000)


def _store(out, index: int, value) -> None:
    if _is_r_na(value):
        out.view(np.uint64)[index] = np.uint64(_R_NA_BITS)
    else:
        out[index] = value


def _na_vector(n: int) -> np.ndarray:
    out = np.empty(n, dtype=np.uint64)
    out.fill(np.uint64(_R_NA_BITS))
    return out.view(np.float64)


def _mismatch(w_len: int, x_len: int) -> str:
    return (
        "The number of elements in arguments 'w' and 'x' does not match: "
        f"{w_len:.0f} != {x_len:.0f}"
    )


def _maybe_subset_w(w, index):
    if w is None:
        return None
    weights = _as_float_1d(w, "w")
    if index is None:
        return weights
    return _take(_positions(index, weights.size, matrix=False), weights)


def _margin_positions(index, n: int) -> np.ndarray:
    if index is None:
        return np.arange(n, dtype=np.int64)
    return _positions(index, n, matrix=True)


def _materialize(matrix, row_pos, col_pos):
    if row_pos.size == 0 or col_pos.size == 0:
        return np.zeros((row_pos.size, col_pos.size), dtype=np.float64)
    if np.any(row_pos < 0) or np.any(col_pos < 0):
        out = np.full((row_pos.size, col_pos.size), np.nan, dtype=np.float64)
        row_ok = row_pos >= 0
        col_ok = col_pos >= 0
        if row_ok.any() and col_ok.any():
            out[np.ix_(np.flatnonzero(row_ok), np.flatnonzero(col_ok))] = matrix[
                np.ix_(row_pos[row_ok], col_pos[col_ok])
            ]
        return out
    return np.asarray(matrix[np.ix_(row_pos, col_pos)], dtype=np.float64)


def _take(positions, values) -> np.ndarray:
    positions = np.asarray(positions, dtype=np.int64).reshape(-1)
    out = np.empty(positions.size, dtype=np.float64)
    if positions.size == 0:
        return out
    valid = (positions >= 0) & (positions < values.size)
    out[~valid] = np.nan
    if np.any(valid):
        out[valid] = values[positions[valid]]
    return out


def _positions(idxs, n: int, matrix: bool) -> np.ndarray:
    kind, raw = prepare_idxs(idxs)
    if kind == "none":
        return np.arange(n, dtype=np.int64)
    if kind == "logical":
        return _logical_positions(raw, n, matrix)
    return _numeric_positions(raw, n, matrix, from_double=kind == "double")


def _logical_positions(flags, n: int, matrix: bool) -> np.ndarray:
    flags = np.asarray(flags, dtype=np.int8).reshape(-1)
    length = int(flags.size)
    if length == 0:
        return np.zeros(0, dtype=np.int64)
    if matrix and length > n:
        raise ValueError("(subscript) logical subscript too long")
    if length < n:
        reps = (n + length - 1) // length
        flags = np.tile(flags, reps)[:n]
        length = n
    chosen = np.flatnonzero(flags != 0)
    if chosen.size == 0:
        return np.zeros(0, dtype=np.int64)
    positions = chosen.astype(np.int64, copy=True)
    na = (flags[chosen] < 0) | (chosen >= n)
    positions[na] = -1
    return positions


def _numeric_positions(raw, n: int, matrix: bool, from_double: bool) -> np.ndarray:
    values = np.asarray(raw).reshape(-1)
    codes = []
    warn = False
    for value in values:
        code, coerced = _one_index(value, from_double)
        warn = warn or coerced
        codes.append(code)
    if matrix and warn:
        _warn("NAs introduced by coercion to integer range")
    has_neg = False
    has_pos = False
    has_na = False
    for code in codes:
        if code is None:
            has_na = True
        elif code < 0:
            has_neg = True
        elif code > 0:
            has_pos = True
    if has_neg and (has_pos or has_na):
        raise ValueError("only 0's may be mixed with negative subscripts")
    if has_neg:
        drop = np.zeros(n, dtype=bool)
        for code in codes:
            if code is None or code >= 0:
                continue
            mag = -code
            if 1 <= mag <= n:
                drop[mag - 1] = True
        return np.flatnonzero(~drop).astype(np.int64, copy=False)
    out = []
    for code in codes:
        if code is None:
            out.append(-1)
        elif code == 0:
            continue
        elif code > n:
            if matrix:
                raise ValueError("subscript out of bounds")
            out.append(-1)
        else:
            out.append(code - 1)
    return np.asarray(out, dtype=np.int64)


def _one_index(value, from_double: bool):
    if from_double:
        number = float(value)
        if math.isnan(number):
            return None, False
        if not math.isfinite(number) or abs(number) > _INT_MAX:
            return None, True
        return int(math.trunc(number)), False
    number = int(value)
    if number == _INT_MIN:
        return None, False
    if number > _INT_MAX or number < -_INT_MAX:
        return None, True
    return number, False


def _require_matrix(x) -> np.ndarray:
    if isinstance(x, (list, tuple)):
        array = np.array(x, dtype=object) if _object_matrix(x) else np.asarray(x)
    elif isinstance(x, str):
        raise ValueError("dim(X) must have a positive length")
    else:
        array = np.asarray(x)
    if array.ndim != 2:
        raise ValueError("dim(X) must have a positive length")
    return _matrix_to_float(array)


def _object_matrix(x) -> bool:
    return any(isinstance(row, (list, tuple)) and any(item is None or isinstance(item, str) for item in row) for row in x)


def _matrix_to_float(array: np.ndarray) -> np.ndarray:
    if array.dtype == object:
        flat = _from_sequence(array.reshape(-1).tolist(), "x")
        return flat.reshape(array.shape)
    if array.dtype.kind in "SU":
        raise ValueError("Argument 'x' is not numeric or logical: character")
    if array.dtype == bool:
        out = np.zeros(array.shape, dtype=np.float64)
        out[array] = 1.0
        return out
    if np.issubdtype(array.dtype, np.number):
        return np.asarray(array, dtype=np.float64)
    raise ValueError(f"Argument 'x' is not numeric or logical: {array.dtype.name}")


def _as_float_1d(x, argument: str) -> np.ndarray:
    if x is None:
        return np.array([np.nan], dtype=np.float64)
    if isinstance(x, str):
        raise ValueError(f"Argument '{argument}' is not numeric or logical: character")
    if isinstance(x, (bool, np.bool_)):
        return np.array([1.0 if bool(x) else 0.0], dtype=np.float64)
    if isinstance(x, (int, np.integer)) and not isinstance(x, bool):
        return np.array([float(x)], dtype=np.float64)
    if isinstance(x, (float, np.floating)):
        return np.array([float(x)], dtype=np.float64)
    if isinstance(x, (list, tuple)):
        return _from_sequence(list(x), argument)
    array = np.asarray(x)
    if array.dtype.kind in "SU":
        raise ValueError(f"Argument '{argument}' is not numeric or logical: character")
    if array.dtype == object:
        return _from_sequence(array.ravel(order="F").tolist(), argument)
    if array.ndim == 0:
        array = array.reshape(1)
    else:
        array = np.ravel(array, order="F")
    if array.dtype == bool:
        out = np.zeros(array.shape, dtype=np.float64)
        out[array] = 1.0
        return out
    if np.issubdtype(array.dtype, np.number):
        return np.ascontiguousarray(array, dtype=np.float64)
    raise ValueError(f"Argument '{argument}' is not numeric or logical: {array.dtype.name}")


def _from_sequence(seq, argument: str) -> np.ndarray:
    out = np.empty(len(seq), dtype=np.float64)
    for i, value in enumerate(seq):
        if value is None:
            out[i] = np.nan
        elif isinstance(value, str):
            raise ValueError(f"Argument '{argument}' is not numeric or logical: character")
        elif isinstance(value, (bool, np.bool_)):
            out[i] = 1.0 if value else 0.0
        elif isinstance(value, (int, np.integer, float, np.floating)):
            out[i] = float(value)
        else:
            raise ValueError(
                f"Argument '{argument}' is not numeric or logical: {type(value).__name__}"
            )
    return out
