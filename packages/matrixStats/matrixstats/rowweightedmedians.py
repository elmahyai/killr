"""Row and column weighted medians, ported from matrixStats."""

from __future__ import annotations

import math
import struct
import warnings

import numpy as np

from matrixstats._values import as_logical
from matrixstats.weightedmedian import weightedMedian

_NA_BITS = np.uint64(0x7FF00000000007A2)
_NA_POS = np.int64(np.iinfo(np.int64).min)
_I32_MIN = -2_147_483_648
_I32_MAX = 2_147_483_647
_TYPE_ERROR = "Argument 'x' must be of type logical, integer or numeric, not '{kind}'"


def rowWeightedMedians(
    x,
    w=None,
    rows=None,
    cols=None,
    na_rm=False,
    use_names=True,
    interpolate=None,
    ties=None,
    idxs=None,
):
    """Weighted median of each row.

    Mirrors ``matrixStats::rowWeightedMedians``. ``rows`` and ``cols`` are
    1-based. ``None`` uses every row or column. ``na_rm`` is ``na.rm``.
    ``w`` of ``None`` follows ``rowMedians``. Otherwise each selected row is
    passed to :func:`matrixstats.weightedmedian.weightedMedian` with ``w``,
    ``na_rm``, ``interpolate``, ``ties``, and ``idxs``.
    """
    return _weighted_medians(
        x, w, rows, cols, na_rm, use_names, interpolate, ties, idxs, by_row=True
    )


def colWeightedMedians(
    x,
    w=None,
    rows=None,
    cols=None,
    na_rm=False,
    use_names=True,
    interpolate=None,
    ties=None,
    idxs=None,
):
    """Weighted median of each column.

    Mirrors ``matrixStats::colWeightedMedians``. Arguments match
    :func:`rowWeightedMedians`. ``w`` has one weight per row.
    """
    return _weighted_medians(
        x, w, rows, cols, na_rm, use_names, interpolate, ties, idxs, by_row=False
    )


def _weighted_medians(x, w, rows, cols, na_rm, use_names, interpolate, ties, idxs, by_row):
    as_logical(use_names, "use_names")
    na_rm = as_logical(na_rm, "na_rm")
    matrix = _as_matrix(x)
    if w is None:
        weights = None
    else:
        margin = "columns" if by_row else "rows"
        length = matrix.shape[1] if by_row else matrix.shape[0]
        weights = _as_weights(w, length, margin)

    row_pos = _positions(rows, matrix.shape[0], "rows")
    col_pos = _positions(cols, matrix.shape[1], "cols")
    if rows is not None or cols is not None:
        matrix = _take(matrix, row_pos, col_pos)
    if weights is not None:
        if by_row and cols is not None:
            weights = _take_vec(weights, col_pos)
        elif not by_row and rows is not None:
            weights = _take_vec(weights, row_pos)
        return _apply_weighted(matrix, weights, na_rm, interpolate, ties, idxs, by_row)
    return _apply_unweighted(matrix, na_rm, by_row)


def _apply_weighted(matrix, weights, na_rm, interpolate, ties, idxs, by_row):
    count = matrix.shape[0] if by_row else matrix.shape[1]
    if count == 0:
        return np.empty(0, dtype=np.float64)
    result = np.empty(count, dtype=np.float64)
    bits = result.view(np.uint64)
    for i in range(count):
        line = matrix[i] if by_row else matrix[:, i]
        value = weightedMedian(
            line,
            w=weights,
            idxs=idxs,
            na_rm=na_rm,
            interpolate=interpolate,
            ties=ties,
        )
        bits[i] = _float_bits(value)
    return result


def _apply_unweighted(matrix, na_rm, by_row):
    count = matrix.shape[0] if by_row else matrix.shape[1]
    result = np.empty(count, dtype=np.float64)
    bits = result.view(np.uint64)
    for i in range(count):
        line = matrix[i] if by_row else matrix[:, i]
        bits[i] = _median_bits(np.asarray(line, dtype=np.float64).reshape(-1), na_rm)
    return result


def _median_bits(values, na_rm):
    """Bits of the rowMedians result for one margin.

    An empty margin, or nothing left after ``na_rm``, is plain NaN. A missing
    value with ``na_rm`` false is R's NA. An even count averages the two
    central sorted values.
    """
    if na_rm:
        values = values[~np.isnan(values)]
        if values.size == 0:
            return _float_bits(float("nan"))
    elif values.size == 0:
        return _float_bits(float("nan"))
    elif np.isnan(values).any():
        return _NA_BITS
    values = np.sort(values)
    kk = int(values.size)
    mid = kk // 2
    if kk % 2 == 1:
        return _float_bits(float(values[mid]))
    with np.errstate(invalid="ignore"):
        averaged = (values[mid - 1] + values[mid]) / 2.0
    return _float_bits(float(averaged))


def _as_matrix(x):
    if isinstance(x, (str, bytes)):
        raise ValueError("Argument 'x' should be a matrix")
    array = np.asarray(x)
    if array.ndim != 2:
        raise ValueError("Argument 'x' should be a matrix")
    if array.dtype.kind in "SU":
        raise ValueError(_TYPE_ERROR.format(kind="character"))
    if array.dtype.kind == "c":
        raise ValueError(_TYPE_ERROR.format(kind="complex"))
    if array.dtype == object:
        return _floats_from_object(array, "x")
    if array.dtype == np.bool_:
        return np.array(array, dtype=np.float64, copy=True)
    if array.dtype == np.int32:
        mask = np.asarray(array) == np.iinfo(np.int32).min
        values = np.array(array, dtype=np.float64, copy=True)
        values.view(np.uint64)[mask] = _NA_BITS
        return values
    if np.issubdtype(array.dtype, np.integer) or np.issubdtype(array.dtype, np.floating):
        return np.array(array, dtype=np.float64, copy=True)
    raise ValueError(_TYPE_ERROR.format(kind=array.dtype.name))


def _as_weights(w, n, margin):
    if isinstance(w, (bool, np.bool_)):
        raise ValueError("Argument 'w' is not numeric: logical")
    if isinstance(w, (str, bytes)):
        raise ValueError("Argument 'w' is not numeric: character")
    array = np.asarray(w)
    if array.dtype == np.bool_ or (
        array.dtype == object and array.size and _all_logical(array)
    ):
        raise ValueError("Argument 'w' is not numeric: logical")
    if array.dtype.kind in "SU":
        raise ValueError("Argument 'w' is not numeric: character")
    if array.dtype.kind == "c":
        raise ValueError("Argument 'w' is not numeric: complex")
    if array.dtype == object:
        values = _floats_from_object(np.ravel(array, order="F"), "w")
    elif array.dtype == np.int32:
        flat = np.ravel(array, order="F")
        values = np.array(flat, dtype=np.float64, copy=True)
        values.view(np.uint64)[flat == np.iinfo(np.int32).min] = _NA_BITS
    elif np.issubdtype(array.dtype, np.integer) or np.issubdtype(array.dtype, np.floating):
        values = np.array(np.ravel(array, order="F"), dtype=np.float64, copy=True)
    else:
        raise ValueError(f"Argument 'w' is not numeric: {array.dtype.name}")
    if values.ndim != 1:
        values = np.ravel(values, order="F")
    if values.size != n:
        raise ValueError(
            "The length of argument 'w' does not match the number of "
            f"{margin} in 'x': {values.size} != {n}"
        )
    if np.any((values < 0) & ~np.isnan(values)):
        raise ValueError("Argument 'w' must not contain negative values")
    return np.ascontiguousarray(values, dtype=np.float64)


def _floats_from_object(array, argument):
    flat = np.ravel(np.asarray(array), order="F")
    values = np.empty(flat.shape, dtype=np.float64)
    bits = values.view(np.uint64)
    for i, value in enumerate(flat):
        if value is None:
            bits[i] = _NA_BITS
            continue
        if isinstance(value, (bool, np.bool_)):
            if argument == "w":
                raise ValueError("Argument 'w' is not numeric: logical")
            values[i] = 1.0 if value else 0.0
            continue
        if isinstance(value, str):
            kind = "character"
            if argument == "w":
                raise ValueError(f"Argument 'w' is not numeric: {kind}")
            raise ValueError(_TYPE_ERROR.format(kind=kind))
        if isinstance(value, np.int32) and int(value) == _I32_MIN:
            bits[i] = _NA_BITS
            continue
        try:
            values[i] = float(value)
        except (TypeError, ValueError) as exc:
            if argument == "w":
                raise ValueError("Argument 'w' is not numeric: list") from exc
            raise ValueError(_TYPE_ERROR.format(kind="list")) from exc
    if array.ndim == 2:
        return np.reshape(values, array.shape, order="F")
    return values


def _all_logical(array):
    for value in np.ravel(array):
        if value is None or isinstance(value, (bool, np.bool_)):
            continue
        return False
    return True


def _positions(index, n, name):
    if index is None:
        return np.arange(n, dtype=np.int64)
    if isinstance(index, (bool, np.bool_)):
        return _logical_positions(np.array([1 if index else 0], dtype=np.int8), n)
    if isinstance(index, (int, np.integer)) and not isinstance(index, bool):
        return _numeric_positions([index], n)
    if isinstance(index, (float, np.floating)):
        return _numeric_positions([float(index)], n)

    array = np.asarray(index)
    if array.ndim == 0:
        array = array.reshape(1)
    if array.ndim != 1:
        array = np.ravel(array, order="F")
    else:
        array = np.ravel(array)
    if array.dtype.kind in "SU":
        raise ValueError("no 'dimnames' attribute for array")
    if array.dtype == object:
        if _all_logical(array):
            flags = np.empty(array.size, dtype=np.int8)
            for i, value in enumerate(array):
                if value is None:
                    flags[i] = -1
                else:
                    flags[i] = 1 if value else 0
            return _logical_positions(flags, n)
        return _numeric_positions(list(array), n)
    if array.dtype == np.bool_:
        flags = np.where(array, np.int8(1), np.int8(0))
        return _logical_positions(flags, n)
    if np.issubdtype(array.dtype, np.integer) or np.issubdtype(array.dtype, np.floating):
        return _numeric_positions(array, n)
    raise ValueError(f"Argument '{name}' must be integer, numeric, or logical")


def _logical_positions(flags, n):
    length = int(flags.size)
    if length > n:
        raise ValueError("(subscript) logical subscript too long")
    if length == 0:
        return np.empty(0, dtype=np.int64)
    chosen = []
    for i in range(n):
        flag = int(flags[i % length])
        if flag > 0:
            chosen.append(i)
        elif flag < 0:
            chosen.append(int(_NA_POS))
    if not chosen:
        return np.empty(0, dtype=np.int64)
    return np.asarray(chosen, dtype=np.int64)


def _numeric_positions(values, n):
    converted = []
    warn = False
    for value in values:
        item, bad = _r_subscript_int(value)
        warn = warn or bad
        converted.append(item)
    if warn:
        warnings.warn(
            "NAs introduced by coercion to integer range",
            RuntimeWarning,
            stacklevel=4,
        )
    has_negative = False
    has_positive = False
    has_na = False
    for item in converted:
        if item is None:
            has_na = True
        elif item < 0:
            has_negative = True
        elif item > 0:
            has_positive = True
    if has_negative and (has_positive or has_na):
        raise ValueError("only 0's may be mixed with negative subscripts")
    if has_negative:
        excluded = set()
        for item in converted:
            if item is not None and item < 0:
                kept = -item
                if 1 <= kept <= n:
                    excluded.add(kept)
        return np.asarray([i for i in range(n) if (i + 1) not in excluded], dtype=np.int64)
    chosen = []
    for item in converted:
        if item is None:
            chosen.append(int(_NA_POS))
        elif item == 0:
            continue
        elif item < 1 or item > n:
            raise ValueError("subscript out of bounds")
        else:
            chosen.append(item - 1)
    if not chosen:
        return np.empty(0, dtype=np.int64)
    return np.asarray(chosen, dtype=np.int64)


def _r_subscript_int(value):
    if isinstance(value, (bool, np.bool_)):
        return (1 if value else 0), False
    if value is None:
        return None, False
    if isinstance(value, np.int32) and int(value) == _I32_MIN:
        return None, False
    if isinstance(value, (int, np.integer)):
        iv = int(value)
        if iv <= _I32_MIN or iv > _I32_MAX:
            return None, True
        return iv, False
    try:
        fv = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("no 'dimnames' attribute for array") from exc
    if math.isnan(fv):
        return None, False
    if (not math.isfinite(fv)) or fv <= _I32_MIN or fv >= _I32_MAX + 1:
        return None, True
    return int(math.trunc(fv)), False


def _take(matrix, row_pos, col_pos):
    if row_pos.size == 0 or col_pos.size == 0:
        return np.empty((row_pos.size, col_pos.size), dtype=np.float64)
    row_na = row_pos < 0
    col_na = col_pos < 0
    if not np.any(row_na) and not np.any(col_na):
        return np.array(matrix[np.ix_(row_pos, col_pos)], dtype=np.float64, copy=True)
    out = np.empty((row_pos.size, col_pos.size), dtype=np.float64)
    out.view(np.uint64)[:] = _NA_BITS
    good_r = np.flatnonzero(~row_na)
    good_c = np.flatnonzero(~col_na)
    if good_r.size and good_c.size:
        out[np.ix_(good_r, good_c)] = matrix[np.ix_(row_pos[good_r], col_pos[good_c])]
    return out


def _take_vec(values, pos):
    out = np.empty(pos.size, dtype=np.float64)
    if pos.size == 0:
        return out
    out.view(np.uint64)[:] = _NA_BITS
    good = pos >= 0
    out[good] = values[pos[good]]
    return out


def _float_bits(value):
    return struct.unpack("<Q", struct.pack("<d", float(value)))[0]
