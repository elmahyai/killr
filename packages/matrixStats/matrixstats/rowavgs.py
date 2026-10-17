"""Averages over equal-sized column or row sets, from matrixStats 1.5.0."""

from __future__ import annotations

import math
import warnings

import numpy as np

from matrixstats.anymissing import NA_INTEGER, anyMissing

_INT_MIN = -2147483648
_INT_MAX = 2147483647


def rowAvgsPerColSet(
    X,
    W=None,
    rows=None,
    S=None,
    FUN=None,
    na_rm=None,
    t_fun=False,
    **kwargs,
):
    """Average each column set of ``X`` with ``FUN``.

    Mirrors ``matrixStats::rowAvgsPerColSet``. ``X`` is a 2-d array whose
    axis 0 is rows and axis 1 is columns, matching the printed R matrix.
    ``S`` is a 2-d array of 1-based column indexes; each column of ``S`` is
    one set. Non-finite indexes are dropped, then the remaining values follow
    R ``[`` rules. ``rows`` is a base-R row subscript; ``None`` keeps every
    row. ``na_rm=None`` is R's ``NA``: missing values are removed when ``X``
    or ``S`` has any, and kept otherwise. ``t_fun`` transposes the subset
    before ``FUN``. The result has one row per selected row of ``X`` and one
    column per set. Names are not attached.

    When ``W`` is given, ``FUN`` is called with ``W`` set to a matrix of the
    selected rows and zero columns. The installed function clears the column
    index before it subsets the weights.
    """
    return _row_avgs(X, W, rows, S, FUN, na_rm, t_fun, kwargs, _row_means)


def colAvgsPerRowSet(
    X,
    W=None,
    cols=None,
    S=None,
    FUN=None,
    na_rm=None,
    t_fun=False,
    **kwargs,
):
    """Average each row set of ``X`` by transposing into ``rowAvgsPerColSet``.

    Mirrors ``matrixStats::colAvgsPerRowSet``. ``S`` holds 1-based row
    indexes. The default ``FUN`` is column means, and ``t_fun`` is flipped, so
    the default call averages along the selected rows. The result has one row
    per set and one column per selected column of ``X``.

    ``cols`` subsets columns of ``X``. When ``W`` is ``None``, the same
    subset expression leaves ``W`` empty. When ``W`` is a matrix it is not
    subset by ``cols``.
    """
    x = _as_matrix(X, "X")
    if S is None:
        raise ValueError('argument "S" is missing, with no default')
    sets = _as_matrix(S, "S")
    if FUN is None:
        fun = _col_means
    elif not callable(FUN):
        raise ValueError(f"Argument 'FUN' is not a function: {_mode(sets)}")
    else:
        fun = FUN
    weights = W
    if cols is not None:
        x = _subset(x, cols, axis=1)
        if weights is None:
            weights = None
    flipped = not _as_logical_condition(t_fun)
    transposed_x = np.transpose(x)
    transposed_w = None if weights is None else np.transpose(weights)
    averaged = _row_avgs(
        transposed_x,
        transposed_w,
        None,
        sets,
        fun,
        na_rm,
        flipped,
        kwargs,
        _row_means,
    )
    return np.transpose(averaged)


def _row_avgs(X, W, rows, S, FUN, na_rm, t_fun, kwargs, default_fun):
    x = _as_matrix(X, "X")
    has_w = W is not None
    if has_w:
        weights = _as_matrix(W, "W")
        if weights.shape != x.shape:
            raise ValueError(
                "Argument 'W' and 'X' have different dimensions: "
                f"{_dim_text(weights)} != {_dim_text(x)}"
            )
        if not _is_numeric(weights):
            raise ValueError(f"Argument 'W' is not numeric: {_mode(weights)}")
    else:
        weights = None
    if S is None:
        raise ValueError('argument "S" is missing, with no default')
    sets = _as_matrix(S, "S")
    if FUN is None:
        fun = default_fun
    elif not callable(FUN):
        raise ValueError(f"Argument 'FUN' is not a function: {_mode(sets)}")
    else:
        fun = FUN
    if rows is not None:
        picked = _r_positions(rows, x.shape[0])
        x = _take(x, picked, axis=0)
        if has_w:
            weights = _take(weights, picked, axis=0)
    transpose = _as_logical_condition(t_fun)
    na_flag = _resolve_na_rm(na_rm, x, sets)
    nrow = x.shape[0]
    n_sets = sets.shape[1]
    if n_sets == 0:
        if nrow > 1:
            raise ValueError("Internal error: dimX[1] > 1L")
        return np.empty((nrow, 0), dtype=np.float64)
    columns = []
    for index in range(n_sets):
        finite = _drop_nonfinite(sets[:, index])
        picked = _r_positions(finite, x.shape[1])
        subset = _take(x, picked, axis=1)
        if transpose:
            subset = np.transpose(subset).copy()
        values = _call_fun(fun, subset, na_flag, weights if has_w else None, kwargs)
        flat = np.ravel(np.asarray(values), order="F")
        if flat.size != nrow:
            raise ValueError("Internal error: length(Zjj) != dimX[1L]")
        columns.append(flat)
    return _bind_columns(columns, nrow, n_sets)


def _row_means(x, na_rm=False):
    """Base ``rowMeans``: one mean per row, with ``NaN`` for an empty row."""
    values = np.asarray(x, dtype=np.float64)
    if values.ndim == 1:
        values = values.reshape(-1, 1)
    nrow, ncol = values.shape
    if ncol == 0:
        return np.full(nrow, np.nan)
    if _truthy(na_rm):
        present = ~np.isnan(values)
        count = present.sum(axis=1)
        total = np.where(present, values, 0.0).sum(axis=1)
        out = np.full(nrow, np.nan)
        ok = count > 0
        out[ok] = total[ok] / count[ok]
        return out
    return values.sum(axis=1) / ncol


def _col_means(x, na_rm=False):
    """Base ``colMeans``: one mean per column, with ``NaN`` for an empty column."""
    values = np.asarray(x, dtype=np.float64)
    if values.ndim == 1:
        values = values.reshape(1, -1)
    nrow, ncol = values.shape
    if nrow == 0:
        return np.full(ncol, np.nan)
    if _truthy(na_rm):
        present = ~np.isnan(values)
        count = present.sum(axis=0)
        total = np.where(present, values, 0.0).sum(axis=0)
        out = np.full(ncol, np.nan)
        ok = count > 0
        out[ok] = total[ok] / count[ok]
        return out
    return values.sum(axis=0) / nrow


def _call_fun(fun, subset, na_flag, weights, kwargs):
    try:
        if weights is None:
            return fun(subset, na_rm=na_flag, **kwargs)
        empty = weights[:, :0]
        return fun(subset, W=empty, na_rm=na_flag, **kwargs)
    except TypeError as exc:
        if weights is not None and "W" in str(exc):
            raise ValueError("unused argument (W = Wjj)") from exc
        raise


def _bind_columns(columns, nrow, n_sets):
    dtype = np.result_type(*[column.dtype for column in columns])
    out = np.empty((nrow, n_sets), dtype=dtype)
    for index, column in enumerate(columns):
        out[:, index] = column
    if out.shape != (nrow, n_sets):
        raise ValueError("Internal error: dim(Z) != c(dimX[1L], nbrOfSets)")
    return out


def _resolve_na_rm(na_rm, x, sets):
    if _is_missing(na_rm):
        return bool(anyMissing(x) or anyMissing(sets))
    if _length(na_rm) == 0:
        raise ValueError("argument is of length zero")
    if _length(na_rm) > 1:
        raise ValueError("the condition has length > 1")
    value = _scalar(na_rm)
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return value


def _truthy(na_rm):
    if isinstance(na_rm, (bool, np.bool_)):
        return bool(na_rm)
    if isinstance(na_rm, (int, np.integer)) and not isinstance(na_rm, (bool, np.bool_)):
        return int(na_rm) != 0
    if isinstance(na_rm, (float, np.floating)):
        if np.isnan(na_rm):
            raise ValueError("missing value where TRUE/FALSE needed")
        return float(na_rm) != 0.0
    raise ValueError("missing value where TRUE/FALSE needed")


def _as_logical_condition(value):
    if value is None or _length(value) == 0:
        raise ValueError("argument is of length zero")
    if _length(value) > 1:
        raise ValueError("the condition has length > 1")
    scalar = _scalar(value)
    if isinstance(scalar, (bool, np.bool_)):
        return bool(scalar)
    if isinstance(scalar, (int, np.integer)) and not isinstance(scalar, (bool, np.bool_)):
        return int(scalar) != 0
    if isinstance(scalar, (float, np.floating)):
        if np.isnan(scalar):
            raise ValueError("missing value where TRUE/FALSE needed")
        return float(scalar) != 0.0
    raise ValueError("missing value where TRUE/FALSE needed")


def _is_missing(value):
    if value is None:
        return True
    if isinstance(value, (float, np.floating)) and np.isnan(value):
        return True
    if isinstance(value, np.ndarray) and value.size == 1:
        item = value.reshape(-1)[0]
        return isinstance(item, (float, np.floating)) and bool(np.isnan(item))
    return False


def _length(value):
    if value is None or isinstance(value, (bool, np.bool_, str)):
        return 1
    if isinstance(value, np.generic):
        return 1
    if isinstance(value, (int, float)):
        return 1
    return int(np.size(value))


def _scalar(value):
    if isinstance(value, np.ndarray):
        return value.reshape(-1)[0]
    if isinstance(value, (list, tuple)):
        return value[0]
    return value


def _as_matrix(value, name):
    if isinstance(value, np.ndarray):
        array = value
    else:
        array = np.asarray(value)
    if getattr(array, "ndim", None) != 2:
        raise ValueError(f"Argument '{name}' is not a matrix: {_r_class(value)}")
    return array


def _dim_text(array):
    return f"{array.shape[0]}x{array.shape[1]}"


def _is_numeric(array):
    return array.dtype.kind in "iuf"


def _mode(array):
    kind = array.dtype.kind
    if kind == "b":
        return "logical"
    if kind in "iuf":
        return "numeric"
    if kind == "c":
        return "complex"
    if kind in "SUO":
        return "character"
    return kind


def _r_class(value):
    if isinstance(value, np.ndarray):
        kind = value.dtype.kind
        if kind == "b":
            return "logical"
        if kind in "iu":
            return "integer"
        if kind == "f":
            return "numeric"
        if kind == "c":
            return "complex"
        if kind in "SUO":
            return "character"
        return value.dtype.name
    if isinstance(value, bool):
        return "logical"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "numeric"
    if isinstance(value, str):
        return "character"
    if isinstance(value, (list, tuple)):
        return "list"
    return type(value).__name__


def _subset(array, index, axis):
    return _take(array, _r_positions(index, array.shape[axis]), axis)


def _take(array, positions, axis):
    positions = list(positions)
    missing = any(item is None for item in positions)
    if axis == 0:
        if not positions:
            return array[:0, :]
        if not missing:
            return array[np.asarray(positions, dtype=np.intp), :]
        return _take_missing(array, positions, axis=0)
    if not positions:
        return array[:, :0]
    if not missing:
        return array[:, np.asarray(positions, dtype=np.intp)]
    return _take_missing(array, positions, axis=1)


def _take_missing(array, positions, axis):
    count = len(positions)
    use_float = array.dtype.kind != "i" or array.dtype.itemsize < 4
    if axis == 0:
        shape = (count, array.shape[1])
    else:
        shape = (array.shape[0], count)
    if use_float:
        source = np.asarray(array, dtype=np.float64)
        out = np.empty(shape, dtype=np.float64)
        fill = np.nan
    else:
        source = array
        out = np.empty(shape, dtype=array.dtype)
        fill = NA_INTEGER
    for place, position in enumerate(positions):
        if axis == 0:
            if position is None:
                out[place, :] = fill
            else:
                out[place, :] = source[position, :]
        elif position is None:
            out[:, place] = fill
        else:
            out[:, place] = source[:, position]
    return out


def _drop_nonfinite(column):
    values = np.asarray(column).reshape(-1)
    if values.dtype == np.bool_:
        return values
    if values.dtype.kind == "f":
        return values[np.isfinite(values)]
    if values.dtype.kind == "i":
        return values[values != NA_INTEGER]
    if values.dtype == object:
        return [item for item in values.tolist() if _is_finite_index(item)]
    return values


def _is_finite_index(item):
    if item is None:
        return False
    if isinstance(item, (bool, np.bool_)):
        return True
    if isinstance(item, (int, np.integer)) and not isinstance(item, (bool, np.bool_)):
        return int(item) != NA_INTEGER
    if isinstance(item, (float, np.floating)):
        return bool(np.isfinite(item))
    return False


def _r_positions(index, length):
    """1-based R ``[`` positions as 0-based indexes. ``None`` inserts a missing slice."""
    kind, data = _flatten_index(index)
    if kind == "logical":
        return _logical_positions(data, length)
    coerced = _coerce_integers(data, from_double=(kind == "double"))
    return _numeric_positions(coerced, length)


def _flatten_index(index):
    if isinstance(index, np.ndarray) and index.ndim == 0:
        return _flatten_index(index.item())
    if isinstance(index, (bool, np.bool_)):
        return "logical", [bool(index)]
    if isinstance(index, (int, np.integer)) and not isinstance(index, (bool, np.bool_)):
        return "integer", [int(index)]
    if isinstance(index, (float, np.floating)):
        return "double", [float(index)]
    if isinstance(index, (list, tuple)):
        return _from_sequence(index)
    array = np.asarray(index)
    if array.dtype == object:
        return _from_sequence(np.ravel(array, order="F").tolist())
    flat = np.ravel(array, order="F")
    if flat.size == 0:
        if flat.dtype == np.bool_:
            return "logical", []
        if flat.dtype.kind == "f":
            return "double", []
        return "integer", []
    if flat.dtype == np.bool_:
        return "logical", [bool(item) for item in flat]
    if flat.dtype.kind == "f":
        return "double", [float(item) for item in flat]
    if flat.dtype.kind in "iu":
        return "integer", [int(item) for item in flat]
    raise ValueError("subscript out of bounds")


def _from_sequence(seq):
    if len(seq) == 0:
        return "integer", []
    if all(item is None or isinstance(item, (bool, np.bool_)) for item in seq):
        flags = [None if item is None else bool(item) for item in seq]
        return "logical", flags
    values = []
    double = False
    for item in seq:
        if item is None or (isinstance(item, (float, np.floating)) and np.isnan(item)):
            values.append(None)
            if isinstance(item, (float, np.floating)):
                double = True
            continue
        if isinstance(item, (bool, np.bool_)):
            values.append(1.0 if item else 0.0)
            double = True
            continue
        if isinstance(item, (int, np.integer)):
            values.append(int(item))
            continue
        if isinstance(item, (float, np.floating)):
            values.append(float(item))
            double = True
            continue
        raise ValueError("subscript out of bounds")
    if double:
        floated = []
        for item in values:
            floated.append(None if item is None else float(item))
        return "double", floated
    return "integer", values


def _logical_positions(flags, length):
    if len(flags) > length:
        raise ValueError("(subscript) logical subscript too long")
    if len(flags) == 0:
        return []
    width = len(flags)
    out = []
    for index in range(length):
        bit = flags[index % width]
        if bit is None:
            out.append(None)
        elif bit:
            out.append(index)
    return out


def _coerce_integers(values, from_double):
    warned = False
    out = []
    for value in values:
        if value is None:
            out.append(None)
            continue
        if from_double:
            number = float(value)
            if math.isnan(number):
                out.append(None)
                continue
            if math.isinf(number):
                warned = _warn_range(warned)
                out.append(None)
                continue
            trunc = math.trunc(number)
        else:
            trunc = int(value)
        if trunc < _INT_MIN or trunc > _INT_MAX or trunc == _INT_MIN:
            if from_double or trunc != _INT_MIN:
                warned = _warn_range(warned)
            out.append(None)
            continue
        out.append(trunc)
    return out


def _warn_range(warned):
    if not warned:
        warnings.warn(
            "NAs introduced by coercion to integer range",
            RuntimeWarning,
            stacklevel=4,
        )
    return True


def _numeric_positions(values, length):
    has_neg = False
    has_pos = False
    has_na = False
    for value in values:
        if value is None:
            has_na = True
        elif value < 0:
            has_neg = True
        elif value > 0:
            has_pos = True
    if has_neg and (has_pos or has_na):
        raise ValueError("only 0's may be mixed with negative subscripts")
    if has_neg:
        banned = set()
        for value in values:
            if value is None or value == 0:
                continue
            magnitude = -value
            if 1 <= magnitude <= length:
                banned.add(magnitude)
        return [index for index in range(length) if (index + 1) not in banned]
    out = []
    for value in values:
        if value is None:
            out.append(None)
            continue
        if value == 0:
            continue
        if value > length:
            raise ValueError("subscript out of bounds")
        out.append(value - 1)
    return out
