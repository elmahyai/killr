"""Row and column weighted means from matrixStats ``rowWeightedMeans``.

The R file does not call ``weightedMean``. A non-missing negative weight is
an error. Zero weights are dropped only when fewer than the original margin
remain, and a missing weight stays in the product.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

_I32_MAX = 2147483647
_I32_NA = -2147483648

_R_NAMES = {
    "na_rm": "na.rm",
    "use_names": "useNames",
}


def rowWeightedMeans(
    x,
    w=None,
    rows=None,
    cols=None,
    na_rm=False,
    use_names=True,
    **_ignored,
):
    """Weighted mean of each row.

    ``x`` is a 2-d array, axis 0 rows and axis 1 columns, in printed order.
    ``w`` has one weight per column. ``rows`` and ``cols`` are 1-based; None
    selects the whole margin. The result is a float64 vector.
    """
    return _weighted_means(x, w, rows, cols, na_rm, use_names, True)


def colWeightedMeans(
    x,
    w=None,
    rows=None,
    cols=None,
    na_rm=False,
    use_names=True,
    **_ignored,
):
    """Weighted mean of each column.

    Arguments match :func:`rowWeightedMeans`, except ``w`` has one weight per
    row. The result length is the number of selected columns.
    """
    return _weighted_means(x, w, rows, cols, na_rm, use_names, False)


def _weighted_means(x, w, rows, cols, na_rm, use_names, by_row: bool):
    na_rm = _flag(na_rm, "na_rm")
    _flag(use_names, "use_names")
    matrix = _as_matrix(x)
    # R stores this length before subsetting and later compares it with the
    # number of weights that were kept.
    margin = int(matrix.shape[1] if by_row else matrix.shape[0])
    weights = None
    if w is not None:
        weights = _weights(w, margin, "columns" if by_row else "rows")
    row_pos = None if rows is None else _positions(rows, int(matrix.shape[0]))
    col_pos = None if cols is None else _positions(cols, int(matrix.shape[1]))
    selected = _take2d(matrix, row_pos, col_pos)
    if weights is not None and by_row and col_pos is not None:
        weights = _take1d(weights, col_pos)
    elif weights is not None and not by_row and row_pos is not None:
        weights = _take1d(weights, row_pos)
    return _reduce(selected, weights, na_rm, by_row, margin)


def _flag(value, name: str) -> bool:
    if type(value) is bool or type(value) is np.bool_:
        return bool(value)
    label = _R_NAMES[name]
    raise ValueError(f"Argument '{label}' must be either TRUE or FALSE")


def _as_matrix(x) -> np.ndarray:
    arr = x if isinstance(x, np.ndarray) else np.asarray(x)
    if arr.ndim != 2:
        klass = _class_name(arr)
        raise ValueError(
            f"Argument 'x' is of class '{klass}', but should be a matrix. "
            f"The use of a '{klass}' is not supported, the correctness of the "
            "result is not guaranteed. Please update your code accordingly."
        )
    if arr.dtype == np.bool_:
        return arr.astype(np.float64)
    if arr.dtype == np.int32:
        out = arr.astype(np.float64)
        out[arr == _I32_NA] = np.nan
        return out
    if np.issubdtype(arr.dtype, np.integer) or np.issubdtype(arr.dtype, np.floating):
        if arr.dtype == np.float64:
            return arr
        return arr.astype(np.float64)
    raise ValueError("'x' must be numeric")


def _class_name(arr: np.ndarray) -> str:
    if arr.ndim > 2:
        return "array"
    if arr.dtype == np.bool_:
        return "logical"
    if np.issubdtype(arr.dtype, np.integer):
        return "integer"
    if np.issubdtype(arr.dtype, np.floating):
        return "numeric"
    if np.issubdtype(arr.dtype, np.complexfloating):
        return "complex"
    if arr.dtype.kind in "SU":
        return "character"
    return "list"


def _weights(w, n: int, margin: str) -> np.ndarray:
    flat = np.ravel(np.asarray(w), order="F")
    if int(flat.size) != n:
        raise ValueError(
            "The length of argument 'w' does not match the number of "
            f"{margin} in 'x': {int(flat.size)} != {n}"
        )
    values = _weight_numeric(flat)
    if np.any(np.isfinite(values) & (values < 0)):
        raise ValueError("Argument 'w' must not contain negative values")
    return values


def _weight_numeric(flat: np.ndarray) -> np.ndarray:
    if flat.dtype == np.bool_:
        raise ValueError("Argument 'w' is not numeric: logical")
    if np.issubdtype(flat.dtype, np.complexfloating):
        raise ValueError("Argument 'w' is not numeric: complex")
    if flat.dtype.kind in "SU":
        raise ValueError("Argument 'w' is not numeric: character")
    if flat.dtype == np.int32:
        out = flat.astype(np.float64)
        out[flat == _I32_NA] = np.nan
        return out
    if np.issubdtype(flat.dtype, np.integer) or np.issubdtype(flat.dtype, np.floating):
        return np.ascontiguousarray(flat, dtype=np.float64)
    if flat.dtype == object:
        return _weight_object(flat)
    raise ValueError("Argument 'w' is not numeric: list")


def _weight_object(flat: np.ndarray) -> np.ndarray:
    out = np.empty(flat.size, dtype=np.float64)
    for i, item in enumerate(flat.tolist()):
        if item is None:
            out[i] = np.nan
            continue
        if isinstance(item, (bool, np.bool_)):
            raise ValueError("Argument 'w' is not numeric: logical")
        if isinstance(item, str):
            raise ValueError("Argument 'w' is not numeric: character")
        if isinstance(item, complex):
            raise ValueError("Argument 'w' is not numeric: complex")
        try:
            out[i] = float(item)
        except (TypeError, ValueError) as exc:
            raise ValueError("Argument 'w' is not numeric: list") from exc
    return out


def _reduce(x, w, na_rm: bool, by_row: bool, margin: int) -> np.ndarray:
    if w is None:
        return _plain_mean(x, na_rm, by_row)
    m = int(x.shape[0] if by_row else x.shape[1])
    if m == 0:
        return np.zeros(0, dtype=np.float64)
    keep = np.isnan(w) | (w != 0)
    kept = int(np.count_nonzero(keep))
    if kept == 0:
        return np.full(m, np.nan, dtype=np.float64)
    if kept < margin:
        w = w[keep]
        x = x[:, keep] if by_row else x[keep, :]
    if na_rm and not np.isnan(x).any():
        na_rm = False
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        if na_rm:
            return _mean_dropping_na(x, w, by_row)
        return _mean_scaled(x, w, by_row)


def _plain_mean(x, na_rm: bool, by_row: bool) -> np.ndarray:
    m = int(x.shape[0] if by_row else x.shape[1])
    if m == 0:
        return np.zeros(0, dtype=np.float64)
    span = int(x.shape[1] if by_row else x.shape[0])
    if span == 0:
        return np.full(m, np.nan, dtype=np.float64)
    axis = 1 if by_row else 0
    if not na_rm:
        return np.sum(x, axis=axis) / span
    valid = ~np.isnan(x)
    total = np.sum(np.where(valid, x, 0.0), axis=axis)
    count = np.sum(valid, axis=axis)
    with np.errstate(divide="ignore", invalid="ignore"):
        return total / count


def _mean_scaled(x, w, by_row: bool) -> np.ndarray:
    scaled = w / np.sum(w)
    if by_row:
        return np.sum(x * scaled, axis=1)
    return np.sum(x * scaled.reshape(-1, 1), axis=0)


def _mean_dropping_na(x, w, by_row: bool) -> np.ndarray:
    missing = np.isnan(x)
    weights = np.empty(x.shape, dtype=np.float64)
    if by_row:
        weights[:] = w
        sums_axis = 1
    else:
        weights[:] = w.reshape(-1, 1)
        sums_axis = 0
    weights[missing] = np.nan
    sums = np.nansum(weights, axis=sums_axis)
    weights[missing] = 0.0
    if by_row:
        weights = weights / sums[:, None]
    else:
        weights = weights / sums
    filled = np.where(missing, 0.0, x)
    return np.sum(weights * filled, axis=sums_axis)


def _take2d(x, row_pos, col_pos) -> np.ndarray:
    if row_pos is None and col_pos is None:
        return x
    if row_pos is None:
        row_pos = np.arange(x.shape[0], dtype=np.int64)
    if col_pos is None:
        col_pos = np.arange(x.shape[1], dtype=np.int64)
    out = np.full((row_pos.size, col_pos.size), np.nan, dtype=np.float64)
    row_ok = row_pos >= 0
    col_ok = col_pos >= 0
    if np.any(row_ok) and np.any(col_ok):
        out[np.ix_(np.flatnonzero(row_ok), np.flatnonzero(col_ok))] = x[
            np.ix_(row_pos[row_ok], col_pos[col_ok])
        ]
    return out


def _take1d(w, pos: np.ndarray) -> np.ndarray:
    out = np.full(pos.shape, np.nan, dtype=np.float64)
    ok = pos >= 0
    if np.any(ok):
        out[ok] = w[pos[ok]]
    return out


def _positions(index, n: int) -> np.ndarray:
    """1-based R ``[`` positions as 0-based indexes. -1 inserts a missing slice."""
    if isinstance(index, (bool, np.bool_)):
        return _logical_positions([bool(index)], n)
    if isinstance(index, (list, tuple)):
        return _positions_sequence(list(index), n)
    if isinstance(index, str):
        raise ValueError("no 'dimnames' attribute for array")
    if isinstance(index, (int, np.integer, float, np.floating)):
        values, warn = _coerce_number(index)
        return _from_coerced(values, warn, n)
    if not isinstance(index, np.ndarray):
        raise ValueError("no 'dimnames' attribute for array")
    if index.ndim == 0:
        if index.size == 0:
            return np.zeros(0, dtype=np.int64)
        return _positions(index.reshape(1)[0], n)
    if index.ndim != 1:
        raise ValueError("incorrect number of dimensions")
    if index.dtype == np.bool_:
        return _logical_positions([bool(item) for item in index.tolist()], n)
    if index.dtype == np.int32:
        values = [None if int(item) == _I32_NA else int(item) for item in index.tolist()]
        return _from_coerced(values, False, n)
    if index.dtype.kind in "SU" or index.dtype == object:
        return _positions_sequence(index.tolist(), n)
    if np.issubdtype(index.dtype, np.integer) or np.issubdtype(index.dtype, np.floating):
        values = []
        warn = False
        for item in index.tolist():
            coerced, one = _coerce_number(item)
            values.extend(coerced)
            warn = warn or one
        return _from_coerced(values, warn, n)
    raise ValueError("no 'dimnames' attribute for array")


def _positions_sequence(items: list, n: int) -> np.ndarray:
    if not items:
        return np.zeros(0, dtype=np.int64)
    saw_bool = False
    saw_number = False
    for item in items:
        if item is None:
            continue
        if isinstance(item, (bool, np.bool_)):
            saw_bool = True
        elif isinstance(item, (int, np.integer, float, np.floating)):
            saw_number = True
        else:
            raise ValueError("no 'dimnames' attribute for array")
    if saw_bool and not saw_number:
        flags = [None if item is None else bool(item) for item in items]
        return _logical_positions(flags, n)
    values = []
    warn = False
    for item in items:
        if item is None:
            values.append(None)
            continue
        if isinstance(item, (bool, np.bool_)):
            values.append(int(bool(item)))
            continue
        coerced, one = _coerce_number(item)
        values.extend(coerced)
        warn = warn or one
    return _from_coerced(values, warn, n)


def _logical_positions(flags: list, n: int) -> np.ndarray:
    length = len(flags)
    if length > n:
        raise ValueError("(subscript) logical subscript too long")
    if length == 0:
        return np.zeros(0, dtype=np.int64)
    selected = []
    for i in range(n):
        bit = flags[i % length]
        if bit is None:
            selected.append(-1)
        elif bit:
            selected.append(i)
    return np.asarray(selected, dtype=np.int64)


def _coerce_number(value) -> tuple[list[int | None], bool]:
    if isinstance(value, (bool, np.bool_)):
        return [int(bool(value))], False
    if isinstance(value, np.int32):
        number = int(value)
        if number == _I32_NA:
            return [None], False
        return [number], False
    if isinstance(value, (int, np.integer)):
        number = int(value)
        if number < -_I32_MAX or number > _I32_MAX:
            return [None], True
        return [number], False
    number = float(value)
    if math.isnan(number):
        return [None], False
    if math.isinf(number):
        return [None], True
    truncated = math.trunc(number)
    if truncated < -_I32_MAX or truncated > _I32_MAX:
        return [None], True
    return [truncated], False


def _from_coerced(values: list[int | None], warn: bool, n: int) -> np.ndarray:
    if warn:
        warnings.warn(
            "NAs introduced by coercion to integer range",
            RuntimeWarning,
            stacklevel=5,
        )
    negative = False
    other = False
    for value in values:
        if value is None or (value is not None and value > 0):
            other = True
        elif value < 0:
            negative = True
    if negative and other:
        raise ValueError("only 0's may be mixed with negative subscripts")
    if negative:
        excluded = set()
        for value in values:
            if value is not None and value < 0 and -value <= n:
                excluded.add(-value)
        kept = [i for i in range(n) if (i + 1) not in excluded]
        return np.asarray(kept, dtype=np.int64)
    selected = []
    for value in values:
        if value is None:
            selected.append(-1)
        elif value == 0:
            continue
        elif value > n:
            raise ValueError("subscript out of bounds")
        else:
            selected.append(value - 1)
    return np.asarray(selected, dtype=np.int64)
