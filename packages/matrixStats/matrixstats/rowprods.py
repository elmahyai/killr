"""Row and column products, ported from matrixStats ``rowProds`` and ``colProds``."""

from __future__ import annotations

import math

import numpy as np

from matrixstats.product import product

INT_MIN = -2_147_483_648
INT_MAX = 2_147_483_647
_NA_BITS = (
    np.uint64(0x7FF00000000007A2),
    np.uint64(0x7FF80000000007A2),
)

__all__ = ["rowProds", "colProds"]


def rowProds(
    x,
    rows=None,
    cols=None,
    na_rm=False,
    method="direct",
    dim=None,
    use_names=True,
):
    """Product of each row.

    Mirrors ``matrixStats::rowProds``. ``rows`` and ``cols`` are 1-based.
    ``None`` uses every row or column. ``na_rm`` is ``na.rm``. ``dim`` is
    ``dim.``: a one-dimensional ``x`` is filled in column-major order. The
    default ``method`` is ``"direct"`` (a running product). ``"expSumLog"``
    calls :func:`matrixstats.product.product`. A missing double is NaN. An
    empty product is 1. The result is a plain float64 vector.
    """
    return _products(x, rows, cols, na_rm, method, dim, use_names, by_row=True)


def colProds(
    x,
    rows=None,
    cols=None,
    na_rm=False,
    method="direct",
    dim=None,
    use_names=True,
):
    """Product of each column.

    Mirrors ``matrixStats::colProds``. Arguments match :func:`rowProds`.
    """
    return _products(x, rows, cols, na_rm, method, dim, use_names, by_row=False)


def _products(x, rows, cols, na_rm, method, dim, use_names, by_row):
    matrix, kind = _prepare(x, dim)
    row_at = _resolve(rows, matrix.shape[0])
    col_at = _resolve(cols, matrix.shape[1])
    n_out = matrix.shape[0] if row_at is None else len(row_at)
    if not by_row:
        n_out = matrix.shape[1] if col_at is None else len(col_at)
    if n_out == 0:
        return np.zeros(0, dtype=np.float64)

    method_name = _method_name(method)
    _check_flag(na_rm, "na_rm")
    if method_name == "expSumLog":
        if kind == "logical":
            raise ValueError("Argument 'x' cannot be logical")
        result = _exp_products(matrix, kind, row_at, col_at, bool(na_rm), by_row)
    else:
        result = _direct_products(matrix, kind, row_at, col_at, bool(na_rm), by_row)
    _check_flag(use_names, "use_names")
    return result


def _direct_products(matrix, kind, row_at, col_at, na_rm, by_row):
    data = _as_float(matrix, kind)
    sub = _subset(data, row_at, col_at, np.nan)
    return _prod_axis(sub, 1 if by_row else 0, na_rm)


def _prod_axis(sub, axis, na_rm):
    """Running product in extended precision, matching base::prod.

    R multiplies in long double and stores the result as double, so a
    product that underflows double becomes 0 instead of a subnormal.
    """
    if na_rm:
        sub = np.where(np.isnan(sub), 1.0, sub)
    if sub.shape[axis] == 0:
        length = sub.shape[0] if axis == 1 else sub.shape[1]
        return np.ones(length, dtype=np.float64)
    with np.errstate(invalid="ignore", over="ignore", under="ignore"):
        scanned = np.cumprod(np.asarray(sub, dtype=np.longdouble), axis=axis)
        last = scanned[:, -1] if axis == 1 else scanned[-1, :]
        return np.asarray(last, dtype=np.float64)


def _exp_products(matrix, kind, row_at, col_at, na_rm, by_row):
    missing = np.nan if kind == "float" else INT_MIN
    sub = _subset(matrix, row_at, col_at, missing)
    if by_row:
        n = sub.shape[0]
        vectors = (sub[i, :] for i in range(n))
    else:
        n = sub.shape[1]
        vectors = (sub[:, j] for j in range(n))
    out = np.empty(n, dtype=np.float64)
    for i, vector in enumerate(vectors):
        out[i] = _finish(product(vector, na_rm=na_rm))
    return out


def _finish(value):
    number = np.float64(value)
    if number.view(np.uint64) in _NA_BITS:
        return np.float64(np.nan)
    return number


def _as_float(matrix, kind):
    if kind == "int":
        out = matrix.astype(np.float64)
        missing = matrix == INT_MIN
        if np.any(missing):
            out[missing] = np.nan
        return out
    if matrix.dtype == np.bool_:
        return matrix.astype(np.float64)
    return np.asarray(matrix, dtype=np.float64)


def _subset(matrix, row_at, col_at, missing):
    if row_at is None and col_at is None:
        return matrix
    if not _contains_na(row_at) and not _contains_na(col_at):
        sub = matrix
        if row_at is not None:
            sub = sub[np.asarray(row_at, dtype=np.intp), :]
        if col_at is not None:
            sub = sub[:, np.asarray(col_at, dtype=np.intp)]
        return sub

    nrow = matrix.shape[0] if row_at is None else len(row_at)
    ncol = matrix.shape[1] if col_at is None else len(col_at)
    out = np.empty((nrow, ncol), dtype=matrix.dtype)
    for i in range(nrow):
        row = i if row_at is None else row_at[i]
        if row is None:
            out[i, :] = missing
            continue
        if col_at is None:
            out[i, :] = matrix[row, :]
            continue
        for j, col in enumerate(col_at):
            if col is None:
                out[i, j] = missing
            else:
                out[i, j] = matrix[row, col]
    return out


def _contains_na(positions):
    return positions is not None and any(pos is None for pos in positions)


def _method_name(method):
    if method is None:
        raise ValueError("argument is of length zero")
    if isinstance(method, (str, np.str_)):
        name = str(method)
    elif isinstance(method, (bytes, bytearray)):
        name = method.decode()
    elif isinstance(method, np.ndarray) and method.dtype.kind in "SU":
        if method.size == 0:
            raise ValueError("missing value where TRUE/FALSE needed")
        name = str(method.reshape(-1)[0])
    elif isinstance(method, (list, tuple)):
        if len(method) == 0:
            raise ValueError("missing value where TRUE/FALSE needed")
        name = method[0]
        if isinstance(name, (str, np.str_)):
            name = str(name)
    else:
        name = method
    if isinstance(name, float) and math.isnan(name):
        raise ValueError("missing value where TRUE/FALSE needed")
    if name == "expSumLog":
        return "expSumLog"
    if name == "direct":
        return "direct"
    raise ValueError(f"Unknown value of argument 'method': {name}")


def _check_flag(value, name):
    if isinstance(value, (bool, np.bool_)):
        return
    raise TypeError(f"Argument '{name}' must be either TRUE or FALSE")


def _prepare(x, dim):
    values = np.asarray(x)
    if values.dtype == object:
        kind, values = _from_object(values)
    elif values.dtype == np.bool_:
        kind = "logical"
    elif np.issubdtype(values.dtype, np.integer):
        kind = "int"
        values = values.astype(np.int64, copy=False)
    elif np.issubdtype(values.dtype, np.floating):
        kind = "float"
        values = values.astype(np.float64, copy=False)
    elif values.dtype.kind in "SU":
        raise ValueError(
            "Argument 'x' must be of type logical, integer or numeric, not 'character'"
        )
    else:
        raise ValueError(
            "Argument 'x' must be of type logical, integer or numeric, not "
            f"'{values.dtype.name}'"
        )

    if values.ndim == 0:
        values = values.reshape(1)
    if dim is None:
        if values.ndim > 2:
            raise ValueError("Argument 'x' must be a matrix or a vector")
        if values.ndim != 2:
            raise ValueError("Argument 'dim' must be an integer vector of length two")
        return np.array(values, copy=False, subok=False), kind

    nrow, ncol = _parse_dim(dim, int(values.size))
    if values.ndim == 1:
        flat = np.ascontiguousarray(values)
        return np.reshape(flat, (nrow, ncol), order="F"), kind
    if values.shape == (nrow, ncol):
        return np.array(values, copy=False, subok=False), kind
    flat = np.ravel(np.array(values, copy=False, subok=False), order="F")
    return np.reshape(flat, (nrow, ncol), order="F"), kind


def _parse_dim(dim, size):
    dim_arr = np.asarray(dim)
    if dim_arr.ndim == 0 or dim_arr.size != 2 or not np.issubdtype(dim_arr.dtype, np.integer):
        raise ValueError("Argument 'dim' must be an integer vector of length two")
    if dim_arr.ndim > 1:
        raise ValueError("Argument 'dim' must be an integer vector of length two")
    nrow = int(dim_arr.reshape(-1)[0])
    ncol = int(dim_arr.reshape(-1)[1])
    if nrow < 0:
        raise ValueError(
            f"Argument 'dim' specifies a negative number of rows (dim[1]): {nrow}"
        )
    if ncol < 0:
        raise ValueError(
            f"Argument 'dim' specifies a negative number of columns (dim[2]): {ncol}"
        )
    if nrow * ncol != size:
        raise ValueError(
            "Argument 'dim' does not match length of argument 'x': "
            f"{nrow} * {ncol} != {size}"
        )
    return nrow, ncol


def _from_object(values):
    items = list(values.reshape(-1))
    if items and all(_is_bool_or_none(item) for item in items):
        out = np.empty(values.shape, dtype=np.float64)
        for index, item in np.ndenumerate(values):
            if item is None:
                out[index] = np.nan
            else:
                out[index] = 1.0 if item else 0.0
        return "logical", out
    try:
        out = np.empty(values.shape, dtype=np.float64)
        for index, item in np.ndenumerate(values):
            out[index] = np.nan if item is None else item
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Argument 'x' must be of type logical, integer or numeric, not 'character'"
        ) from exc
    return "float", out


def _is_bool_or_none(value):
    return value is None or isinstance(value, (bool, np.bool_))


def _resolve(index, n):
    if index is None:
        return None
    kind, values = _coerce_index(index)
    if kind == "logical":
        return _resolve_logical(values, n)
    if kind == "real":
        values = [_trunc_index(value) for value in values]
    else:
        values = [None if int(value) == INT_MIN else int(value) for value in values]
    return _resolve_ints(values, n)


def _trunc_index(value):
    if not math.isfinite(value) or value > INT_MAX or value <= INT_MIN:
        return None
    return int(math.trunc(value))


def _resolve_ints(idxs, n):
    if not idxs:
        return []
    state = 0
    for idx in idxs:
        if idx is None or idx > 0:
            if state < 0:
                raise ValueError("only 0's may be mixed with negative subscripts")
            if idx is not None and idx > n:
                raise ValueError("subscript out of bounds")
            state = 1
        elif idx < 0:
            if state > 0:
                raise ValueError("only 0's may be mixed with negative subscripts")
            state = -1
    if state < 0:
        drop = [False] * n
        for idx in idxs:
            if idx is None or idx >= 0:
                continue
            excl = -idx
            if 1 <= excl <= n:
                drop[excl - 1] = True
        return [pos for pos in range(n) if not drop[pos]]
    chosen = []
    for idx in idxs:
        if idx == 0:
            continue
        chosen.append(None if idx is None else idx - 1)
    return chosen


def _resolve_logical(flags, n):
    nidxs = len(flags)
    if nidxs == 0:
        return []
    if nidxs > n:
        raise ValueError("(subscript) logical subscript too long")
    last_part = n % nidxs
    count1 = 0
    count2 = 0
    na_count = 0
    for ii, flag in enumerate(flags):
        if flag != 0:
            if flag < 0:
                na_count += 1
            if ii < last_part:
                count1 += 1
            else:
                count2 += 1
    count = count1 + count2
    if na_count == 0 and count == nidxs:
        return list(range(n))

    first = []
    for ii, flag in enumerate(flags):
        if flag != 0:
            first.append(None if flag < 0 else ii)
    chosen = list(first)
    kk = nidxs
    while kk + nidxs <= n:
        for item in first:
            chosen.append(None if item is None else item + kk)
        kk += nidxs
    for item in first[:count1]:
        chosen.append(None if item is None else item + kk)
    return chosen


def _coerce_index(index):
    if isinstance(index, (bool, np.bool_)):
        return "logical", np.array([1 if index else 0], dtype=np.int8)
    if isinstance(index, (int, np.integer)):
        return "int", np.array([int(index)], dtype=np.int64)
    if isinstance(index, float):
        return "real", np.array([float(index)], dtype=np.float64)

    if isinstance(index, (list, tuple)):
        logical = _logical_codes(index)
        if logical is not None:
            return "logical", logical
        if any(item is None for item in index):
            values = [math.nan if item is None else item for item in index]
            array = np.asarray(values, dtype=np.float64)
            return "real", array.reshape(-1)

    array = np.asarray(index)
    if isinstance(array, np.matrix):
        array = array.A
    if array.ndim == 0:
        array = array.reshape(1)
    if array.ndim > 1:
        array = np.ravel(array, order="F")
    if array.dtype == object:
        logical = _logical_codes(list(array.reshape(-1)))
        if logical is not None:
            return "logical", logical
        values = [math.nan if item is None else item for item in array.reshape(-1)]
        array = np.asarray(values, dtype=np.float64)
    if array.dtype == np.bool_:
        return "logical", np.ascontiguousarray(array, dtype=np.int8)
    if np.issubdtype(array.dtype, np.integer):
        return "int", np.ascontiguousarray(array, dtype=np.int64)
    if np.issubdtype(array.dtype, np.floating):
        return "real", np.ascontiguousarray(array, dtype=np.float64)
    raise ValueError("idxs can only be integer, numeric, or logical")


def _logical_codes(values):
    if not values or not all(_is_bool_or_none(value) or _is_nan(value) for value in values):
        return None
    if not any(isinstance(value, (bool, np.bool_)) or value is None for value in values):
        return None
    codes = np.empty(len(values), dtype=np.int8)
    for i, value in enumerate(values):
        if value is None or _is_nan(value):
            codes[i] = -1
        else:
            codes[i] = 1 if value else 0
    return codes


def _is_nan(value):
    return isinstance(value, float) and math.isnan(value)
