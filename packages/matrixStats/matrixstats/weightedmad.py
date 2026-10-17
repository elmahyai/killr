"""Weighted median absolute deviation, ported from matrixStats ``weightedMad``."""

from __future__ import annotations

import math
import struct

import numpy as np

from matrixstats._values import as_logical
from matrixstats.weightedmedian import weightedMedian

# Quiet NaN that R treats as NA_real_.
_R_NA = struct.unpack("<d", struct.pack("<Q", 0x7FF80000000007A2))[0]
_I32_MIN = int(np.iinfo(np.int32).min)


def weightedMad(
    x,
    w=None,
    idxs=None,
    na_rm=False,
    constant=1.4826,
    center=None,
    *,
    low=False,
    high=False,
):
    """Weighted median absolute deviation of a numeric vector.

    Mirrors ``matrixStats::weightedMad``. ``idxs`` is 1-based. ``None`` uses
    every element. When ``w`` is ``None``, ``idxs`` is ignored and the result
    is ``stats::mad``, including ``low`` and ``high``, with the default
    ``constant`` 1.4826. When ``w`` is present, non-positive weights are
    dropped first, so ``-Inf`` is dropped before a positive infinite weight
    keeps only the infinite-weight observations. One observation left returns
    0. The center and the median of absolute deviations are
    ``weightedMedian``.
    """
    na_rm = as_logical(na_rm, "na_rm")
    values = _as_vector(x)
    if w is None:
        low = as_logical(low, "low")
        high = as_logical(high, "high")
        if center is None:
            center = _median(values, na_rm)
        return _mad(values, center, constant, na_rm, low, high)

    weights = _as_vector(w, "w")
    if weights.size != values.size:
        raise ValueError(
            "The number of elements in arguments 'w' and 'x' does not match: "
            f"{weights.size:g} != {values.size:g}"
        )
    if idxs is not None:
        weights = _take(weights, _positions(idxs, weights.size, vector=True))
    constant = _scalar_constant(constant)
    if center is not None:
        center = _scalar_center(center)
    if idxs is not None:
        values = _take(values, _positions(idxs, values.size, vector=True))
    return _weighted(values, weights, na_rm, constant, center)


def rowWeightedMads(
    x,
    w=None,
    rows=None,
    cols=None,
    na_rm=False,
    constant=1.4826,
    center=None,
    use_names=True,
    *,
    low=False,
    high=False,
):
    """Weighted MAD of each row.

    ``x`` is a 2-d array whose axis 0 is rows and axis 1 is columns, matching
    the printed R matrix. ``rows`` and ``cols`` are 1-based; ``None`` selects
    the whole margin. ``w`` weights the columns and is shared by every row.
    A scalar ``center`` is an error. ``use_names`` is accepted and the result
    is a plain float64 vector.
    """
    return _margin(
        x,
        w,
        rows,
        cols,
        na_rm,
        constant,
        center,
        use_names,
        low,
        high,
        by_row=True,
    )


def colWeightedMads(
    x,
    w=None,
    rows=None,
    cols=None,
    na_rm=False,
    constant=1.4826,
    center=None,
    use_names=True,
    *,
    low=False,
    high=False,
):
    """Weighted MAD of each column.

    Arguments match :func:`rowWeightedMads`. ``w`` weights the rows and is
    shared by every column. The result length is the number of selected columns.
    """
    return _margin(
        x,
        w,
        rows,
        cols,
        na_rm,
        constant,
        center,
        use_names,
        low,
        high,
        by_row=False,
    )


def _margin(
    x,
    w,
    rows,
    cols,
    na_rm,
    constant,
    center,
    use_names,
    low,
    high,
    by_row,
):
    constant = _scalar_constant(constant)
    as_logical(use_names, "use_names")
    matrix = _as_matrix(x)
    nrow, ncol = matrix.shape
    if by_row:
        center = _align_center(center, nrow, rows, "rows", "rows")
    else:
        center = _align_center(center, ncol, cols, "columns", "cols")
    if rows is not None or cols is not None:
        matrix = _subset_matrix(matrix, rows, cols)
    if w is not None:
        along = cols if by_row else rows
        if along is not None:
            weights = _as_vector(w, "w")
            w = _take(weights, _positions(along, weights.size, vector=True))
    n = matrix.shape[0] if by_row else matrix.shape[1]
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        piece = matrix[i, :] if by_row else matrix[:, i]
        this_center = None if center is None else float(center[i])
        out[i] = weightedMad(
            piece,
            w=w,
            na_rm=na_rm,
            constant=constant,
            center=this_center,
            low=low,
            high=high,
        )
    return out


def _weighted(x, w, na_rm, constant, center):
    keep = np.isnan(w) | (w > 0)
    if not np.all(keep):
        x = x[keep]
        w = w[keep]
    if na_rm:
        keep = ~np.isnan(x)
        x = x[keep]
        w = w[keep]
    elif x.size and np.isnan(x).any():
        return _R_NA
    if w.size and np.isnan(w).any():
        return _R_NA
    if w.size and np.isinf(w).any():
        x = x[np.isinf(w)]
        w = np.ones(x.size, dtype=np.float64)
    n = int(x.size)
    if n == 0:
        return _R_NA
    if n == 1:
        return 0.0
    if center is None:
        center = weightedMedian(x, w, na_rm=False)
    dev = np.abs(x - center)
    sigma = weightedMedian(dev, w, na_rm=False)
    return float(constant) * float(sigma)


def _mad(x, center, constant, na_rm, low, high):
    """``stats::mad`` after ``weightedMad`` has already chosen ``center``."""
    if na_rm:
        x = x[~np.isnan(x)]
    n = int(x.size)
    const = np.asarray(constant, dtype=np.float64).reshape(-1)
    if (low or high) and n % 2 == 0:
        if low and high:
            raise ValueError("'low' and 'high' cannot be both TRUE")
        n2 = n // 2 + (1 if high else 0)
        dev = _abs_dev(x, center)
        if n2 < 1 or n2 > dev.size:
            raise ValueError(f"'partial' index {n2} outside bounds")
        stat = float(np.sort(dev)[n2 - 1])
    else:
        stat = _median(_abs_dev(x, center), na_rm=False)
    return _scale(const, stat)


def _median(x, na_rm):
    """``stats::median`` for a numeric vector with no names."""
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    if na_rm:
        x = x[~np.isnan(x)]
    elif x.size and np.isnan(x).any():
        return _R_NA
    n = int(x.size)
    if n == 0:
        return _R_NA
    ordered = np.sort(x)
    half = (n + 1) // 2
    if n % 2 == 1:
        return float(ordered[half - 1])
    return float((ordered[half - 1] + ordered[half]) / 2.0)


def _abs_dev(x, center):
    """``abs(x - center)`` with R's recycling rule."""
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    center = np.asarray(center, dtype=np.float64).reshape(-1)
    if x.size == 0 or center.size == 0:
        return np.empty(0, dtype=np.float64)
    n = max(x.size, center.size)
    if x.size != n:
        x = np.resize(x, n)
    if center.size != n:
        center = np.resize(center, n)
    return np.abs(x - center)


def _scale(constant, stat):
    if constant.size == 0:
        return np.empty(0, dtype=np.float64)
    if constant.size == 1:
        if isinstance(stat, float) and math.isnan(stat):
            return _R_NA
        return float(constant[0]) * float(stat)
    if isinstance(stat, float) and math.isnan(stat):
        return np.full(constant.size, _R_NA)
    return np.asarray(constant * float(stat), dtype=np.float64)


def _scalar_constant(constant):
    if isinstance(constant, (bool, np.bool_)):
        raise ValueError("Argument 'constant' is not numeric: logical")
    if isinstance(constant, str):
        raise ValueError("Argument 'constant' is not numeric: character")
    if isinstance(constant, complex):
        raise ValueError("Argument 'constant' is not numeric: complex")
    try:
        values = np.asarray(constant)
    except (TypeError, ValueError) as exc:
        raise ValueError("Argument 'constant' is not numeric: character") from exc
    if values.dtype == np.bool_:
        raise ValueError("Argument 'constant' is not numeric: logical")
    if values.dtype.kind in "SU":
        raise ValueError("Argument 'constant' is not numeric: character")
    if values.dtype.kind == "c":
        raise ValueError("Argument 'constant' is not numeric: complex")
    if not np.issubdtype(values.dtype, np.number):
        raise ValueError(f"Argument 'constant' is not numeric: {values.dtype.name}")
    flat = np.ravel(values)
    if flat.size != 1:
        raise ValueError(f"Argument 'constant' is not a scalar: {flat.size:g}")
    return float(flat[0])


def _scalar_center(center):
    if isinstance(center, (bool, np.bool_)):
        values = np.array([1.0 if center else 0.0])
    else:
        values = np.asarray(center, dtype=np.float64).reshape(-1)
    if values.size != 1:
        raise ValueError(
            f"Argument 'center' is not a scalar or NULL: {values.size:g}"
        )
    return float(values[0])


def _align_center(center, n_margin, index, stop_word, defunct_word):
    if center is None:
        return None
    if isinstance(center, (bool, np.bool_)):
        values = np.array([1.0 if center else 0.0])
    else:
        values = _as_vector(center, "center")
    if values.size != n_margin:
        if values.size == 1 and index is None:
            raise ValueError(
                "[matrixStats (>= 0.58.0)] Argument 'center' should be of the "
                f"same length as number of {defunct_word} of 'x'. Use of a "
                f"scalar value is defunct: {values.size:g} != {n_margin:g} "
                "(See also ?matrixStats::matrixStats.options)"
            )
        raise ValueError(
            "Argument 'center' should be of the same length as number of "
            f"{stop_word} of 'x': {values.size:g} != {n_margin:g}"
        )
    if index is not None:
        values = _take(values, _positions(index, values.size, vector=True))
    return values


def _as_vector(x, name="x"):
    if isinstance(x, (bool, np.bool_)):
        return np.array([1.0 if bool(x) else 0.0], dtype=np.float64)
    if isinstance(x, (int, np.integer)) and not isinstance(x, bool):
        return np.array([float(x)], dtype=np.float64)
    if isinstance(x, (float, np.floating)):
        value = float(x)
        return np.array([value], dtype=np.float64)
    array = np.asarray(x)
    if array.dtype.kind in "SU":
        raise ValueError(f"Argument '{name}' is not numeric or logical: character")
    if np.issubdtype(array.dtype, np.complexfloating):
        raise ValueError(f"Argument '{name}' is not numeric or logical: complex")
    if array.dtype == object:
        return _from_object(array, name)
    if array.ndim == 0:
        array = array.reshape(1)
    elif array.ndim > 1:
        array = np.ravel(array, order="F")
    else:
        array = np.ravel(array)
    return _storage_to_float(array, name)


def _as_matrix(x):
    array = np.asarray(x)
    if array.ndim != 2:
        raise ValueError("invalid 'length' argument")
    if array.dtype.kind in "SU":
        raise ValueError("Argument 'x' is not numeric or logical: character")
    if np.issubdtype(array.dtype, np.complexfloating):
        raise ValueError("Argument 'x' is not numeric or logical: complex")
    if array.dtype == object:
        flat = _from_object(np.ravel(array, order="C"), "x")
        return flat.reshape(array.shape)
    return _storage_to_float(array, "x")


def _storage_to_float(array, name):
    if array.dtype == np.bool_:
        out = np.zeros(array.shape, dtype=np.float64)
        out[array] = 1.0
        return out
    if np.issubdtype(array.dtype, np.floating):
        return np.array(array, dtype=np.float64, copy=True)
    if np.issubdtype(array.dtype, np.integer):
        out = np.array(array, dtype=np.float64, copy=True)
        if array.dtype == np.int32:
            out[array == _I32_MIN] = np.nan
        return out
    raise ValueError(f"Argument '{name}' is not numeric or logical: {array.dtype.name}")


def _from_object(array, name):
    flat = np.ravel(array, order="F")
    out = np.empty(flat.size, dtype=np.float64)
    for i, value in enumerate(flat):
        if value is None:
            out[i] = np.nan
        elif isinstance(value, (bool, np.bool_)):
            out[i] = 1.0 if value else 0.0
        elif isinstance(value, (int, np.integer, float, np.floating)):
            number = float(value)
            if isinstance(value, (int, np.integer)) and int(value) == _I32_MIN:
                number = np.nan
            out[i] = number
        else:
            mode = "character" if isinstance(value, str) else type(value).__name__
            raise ValueError(f"Argument '{name}' is not numeric or logical: {mode}")
    return out


def _subset_matrix(x, rows, cols):
    nrow, ncol = x.shape
    row_pos = np.arange(nrow) if rows is None else _positions(rows, nrow, vector=False)
    col_pos = np.arange(ncol) if cols is None else _positions(cols, ncol, vector=False)
    out = np.full((row_pos.size, col_pos.size), np.nan, dtype=np.float64)
    for i, row in enumerate(row_pos):
        if row < 0:
            continue
        for j, col in enumerate(col_pos):
            if col < 0:
                continue
            out[i, j] = x[row, col]
    return out


def _take(values, positions):
    if positions.size == 0:
        return np.empty(0, dtype=np.float64)
    out = np.empty(positions.size, dtype=np.float64)
    missing = positions < 0
    out[missing] = np.nan
    if not np.all(missing):
        out[~missing] = values[positions[~missing]]
    return out


def _positions(index, n, *, vector):
    """1-based R ``[`` positions as 0-based integers. ``-1`` inserts a missing value."""
    kind, raw = _classify_index(index)
    if kind == "logical":
        return _logical_positions(raw, n, vector)
    return _numeric_positions(raw, n, vector)


def _classify_index(index):
    if isinstance(index, (bool, np.bool_)):
        return "logical", np.array([1 if index else 0], dtype=np.int8)
    if isinstance(index, (int, np.integer)) and not isinstance(index, bool):
        return "numeric", np.array([float(index)], dtype=np.float64)
    if isinstance(index, (float, np.floating)):
        return "numeric", np.array([float(index)], dtype=np.float64)

    array = np.asarray(index)
    if array.ndim == 0:
        array = array.reshape(1)
    else:
        array = np.ravel(array, order="F")
    if array.dtype == np.bool_:
        flags = np.zeros(array.shape, dtype=np.int8)
        flags[array] = 1
        return "logical", flags
    if array.dtype == object:
        return _object_index(array)
    if array.dtype == np.int32:
        values = array.astype(np.float64)
        values[array == _I32_MIN] = np.nan
        return "numeric", values
    if np.issubdtype(array.dtype, np.integer) or np.issubdtype(array.dtype, np.floating):
        return "numeric", np.asarray(array, dtype=np.float64)
    raise ValueError("idxs can only be integer, numeric, or logical")


def _object_index(array):
    logical = True
    flags = np.empty(array.size, dtype=np.int8)
    numbers = np.empty(array.size, dtype=np.float64)
    for i, value in enumerate(array):
        if value is None:
            flags[i] = 2
            numbers[i] = np.nan
            continue
        if isinstance(value, (bool, np.bool_)):
            flags[i] = 1 if value else 0
            numbers[i] = 1.0 if value else 0.0
            continue
        logical = False
        if isinstance(value, (int, np.integer)):
            number = float(value)
            if int(value) == _I32_MIN:
                number = np.nan
            numbers[i] = number
        elif isinstance(value, (float, np.floating)):
            numbers[i] = float(value)
        else:
            raise ValueError("idxs can only be integer, numeric, or logical")
    if logical:
        return "logical", flags
    return "numeric", numbers


def _logical_positions(flags, n, vector):
    if flags.size == 0:
        return np.empty(0, dtype=np.int64)
    if not vector and flags.size > n:
        raise ValueError("(subscript) logical subscript too long")
    if flags.size < n:
        flags = np.resize(flags, n)
    positions = []
    for i, flag in enumerate(flags):
        if flag == 0:
            continue
        if flag == 2 or i >= n:
            positions.append(-1)
        else:
            positions.append(i)
    if not positions:
        return np.empty(0, dtype=np.int64)
    return np.asarray(positions, dtype=np.int64)


def _numeric_positions(values, n, vector):
    truncated = []
    has_negative = False
    has_positive = False
    has_missing = False
    for value in values:
        if not math.isfinite(float(value)):
            truncated.append(None)
            has_missing = True
            continue
        try:
            item = int(math.trunc(float(value)))
        except OverflowError:
            item = 10**18 if float(value) > 0 else -(10**18)
        truncated.append(item)
        if item < 0:
            has_negative = True
        elif item > 0:
            has_positive = True
    if has_negative:
        if has_positive or has_missing:
            raise ValueError("only 0's may be mixed with negative subscripts")
        drop = set()
        for item in truncated:
            if item is None or item == 0:
                continue
            position = -item
            if 1 <= position <= n:
                drop.add(position)
        kept = [i for i in range(n) if (i + 1) not in drop]
        return np.asarray(kept, dtype=np.int64)
    positions = []
    for item in truncated:
        if item is None:
            positions.append(-1)
            continue
        if item == 0:
            continue
        if item > n or item < 1:
            if vector:
                positions.append(-1)
            else:
                raise ValueError("subscript out of bounds")
            continue
        positions.append(item - 1)
    if not positions:
        return np.empty(0, dtype=np.int64)
    return np.asarray(positions, dtype=np.int64)
