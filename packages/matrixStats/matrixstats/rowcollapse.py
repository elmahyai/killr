"""One cell per row or column, by the same indexing as matrixStats.

``idxs`` is recycled to the margin, then used as a 1-based subscript. For
``rowCollapse`` that subscript picks from ``0:(ncol - 1)``. For ``colCollapse``
it picks from ``1:nrow``. The selected offsets become column-major positions.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

_NA_INT = -2_147_483_648
_INT_MAX = 2_147_483_647

__all__ = ["rowCollapse", "colCollapse"]


class _Index:
    __slots__ = ("kind", "values")

    def __init__(self, kind: str, values: np.ndarray):
        self.kind = kind
        self.values = values


def rowCollapse(x, idxs, rows=None, dim=None, use_names=True):
    """Extract one cell from each row.

    Mirrors ``matrixStats::rowCollapse``. ``idxs`` are 1-based column numbers,
    recycled to the number of rows. ``rows`` is a 1-based row subset; ``None``
    keeps every row. ``dim`` is ``dim.``: a one-dimensional ``x`` is filled in
    column-major order. ``use_names`` is ``useNames`` and does not change the
    numbers.
    """
    return _collapse(x, idxs, rows, dim, use_names, by_row=True)


def colCollapse(x, idxs, cols=None, dim=None, use_names=True):
    """Extract one cell from each column.

    Mirrors ``matrixStats::colCollapse``. ``idxs`` are 1-based row numbers,
    recycled to the number of columns. ``cols`` is a 1-based column subset;
    ``None`` keeps every column. The other arguments match :func:`rowCollapse`.
    """
    return _collapse(x, idxs, cols, dim, use_names, by_row=False)


def _collapse(x, idxs, margin, dim, use_names, by_row: bool):
    if margin is None and dim is None:
        quick = _quick(x, idxs, by_row)
        if quick is not None:
            if use_names is not True:
                _r_condition(use_names)
            return quick
    kind, array, storage = _parse_x(x)
    length_out, dim_numbers = _resolve_dim(kind, array, dim, by_row)
    index = _rep_index(_as_index(idxs), length_out)
    flat, shape = _apply_dim(kind, array, dim_numbers)
    if shape is None:
        if margin is not None:
            raise ValueError("incorrect number of dimensions")
        raise ValueError("argument of length 0")
    if len(shape) < 2:
        if margin is not None:
            raise ValueError("incorrect number of dimensions")
        raise ValueError("NA/NaN argument")

    nrow, ncol = int(shape[0]), int(shape[1])
    rectangular = len(shape) == 2 and flat.size == nrow * ncol
    if margin is not None:
        if not rectangular:
            raise ValueError("incorrect number of dimensions")
        selector = _as_index(margin)
        picked = _margin_positions(nrow if by_row else ncol, selector)
        if by_row:
            flat, nrow = _take_rows(flat, nrow, ncol, picked, _na_value(storage))
        else:
            flat, ncol = _take_cols(flat, nrow, ncol, picked, _na_value(storage))
        index = _subset_index(index, selector)

    result = _pick(flat, nrow, ncol, index, storage, by_row, rectangular or margin is not None)
    _r_condition(use_names)
    return _export(result, storage)


def _quick(x, idxs, by_row: bool):
    """Direct fancy index when every subscript is already in range.

    The general path still handles recycling, zeros, negatives, and ``dim``.
    """
    if not isinstance(x, np.ndarray) or x.ndim != 2:
        return None
    if x.dtype != np.float64 and x.dtype != np.int32:
        return None
    if idxs is None or isinstance(idxs, (bool, np.bool_, str)):
        return None
    index = np.asarray(idxs)
    if index.ndim != 1 or index.dtype == np.bool_ or not np.issubdtype(index.dtype, np.integer):
        return None
    nrow, ncol = x.shape
    if index.shape != ((nrow if by_row else ncol),):
        return None
    if index.dtype == np.int32 and index.size and np.any(index == _NA_INT):
        return None
    if index.size == 0:
        return np.empty(0, dtype=x.dtype)
    smallest = int(index.min())
    largest = int(index.max())
    if smallest < 1 or largest > (ncol if by_row else nrow):
        return None
    chosen = index.astype(np.int64, copy=False) - 1
    if by_row:
        return np.ascontiguousarray(x[np.arange(nrow), chosen])
    return np.ascontiguousarray(x[chosen, np.arange(ncol)])


def _pick(flat, nrow, ncol, index, storage, by_row, rectangular):
    na = _na_value(storage)
    if rectangular and by_row and ncol >= 1:
        fast = _fast_row(flat, nrow, ncol, index, na)
        if fast is not None:
            return fast
    if rectangular and not by_row:
        fast = _fast_col(flat, nrow, ncol, index, na)
        if fast is not None:
            return fast
    if by_row:
        columns = _colon(0, ncol - 1)
        picked = _subset_values(columns, index, np.nan)
        positions = _recycle_add(_scale(nrow, picked), _seq_len(nrow))
    else:
        rows = _seq_len(nrow)
        picked = _subset_values(rows, index, np.nan)
        positions = _recycle_add(_scale(nrow, _colon(0, ncol - 1)), picked)
    return _subset_values(flat, _Index("numeric", positions), na)


def _fast_row(flat, nrow, ncol, index, na):
    if not _plain_positive(index, nrow):
        return None
    trunc = np.trunc(index.values)
    matrix = np.reshape(flat, (nrow, ncol), order="F")
    out = np.empty(nrow, dtype=flat.dtype)
    valid = np.isfinite(trunc) & (trunc <= ncol)
    out[~valid] = na
    if np.any(valid):
        out[valid] = matrix[np.flatnonzero(valid), trunc[valid].astype(np.int64) - 1]
    return out


def _fast_col(flat, nrow, ncol, index, na):
    if not _plain_positive(index, ncol):
        return None
    trunc = np.trunc(index.values)
    matrix = np.reshape(flat, (nrow, ncol), order="F")
    out = np.empty(ncol, dtype=flat.dtype)
    valid = np.isfinite(trunc) & (trunc <= nrow)
    out[~valid] = na
    if np.any(valid):
        out[valid] = matrix[trunc[valid].astype(np.int64) - 1, np.flatnonzero(valid)]
    return out


def _plain_positive(index: _Index, length: int) -> bool:
    """True when every finite index is a positive subscript of this length."""
    if index.kind != "numeric" or index.values.size != length:
        return False
    if index.values.size == 0:
        return True
    trunc = np.trunc(index.values)
    return bool(np.all(np.isnan(trunc) | (trunc >= 1)))


def _parse_x(x):
    if isinstance(x, (bool, np.bool_)):
        return "vector", np.array([bool(x)], dtype=np.int8), "logical"
    if isinstance(x, (int, np.integer)) and not isinstance(x, bool):
        array = np.array([int(x)], dtype=np.int64)
        storage, values = _storage_1d(array)
        return "vector", values, storage
    if isinstance(x, (float, np.floating)):
        return "vector", np.array([float(x)], dtype=np.float64), "double"
    if isinstance(x, str):
        raise ValueError(
            "Argument 'x' must be of type logical, integer or numeric, not 'character'"
        )

    array = np.asarray(x)
    if array.ndim >= 3:
        raise ValueError(_defunct("array"))
    if array.dtype.kind in "SU":
        raise ValueError(
            "Argument 'x' must be of type logical, integer or numeric, not 'character'"
        )
    if np.issubdtype(array.dtype, np.complexfloating):
        raise ValueError(
            "Argument 'x' must be of type logical, integer or numeric, not 'complex'"
        )
    if array.dtype == object:
        raise ValueError(
            "Argument 'x' must be of type logical, integer or numeric, not 'list'"
        )
    kind = "matrix" if array.ndim == 2 else "vector"
    if array.ndim == 0:
        array = array.reshape(1)
    storage, values = _storage(array)
    return kind, values, storage


def _storage(array: np.ndarray):
    if array.dtype == np.bool_:
        return "logical", array.astype(np.int8)
    if np.issubdtype(array.dtype, np.floating):
        if array.dtype == np.float64:
            return "double", array
        return "double", np.asarray(array, dtype=np.float64)
    if np.issubdtype(array.dtype, np.integer):
        return _storage_1d(array) if array.ndim == 1 else _storage_nd(array)
    raise ValueError(
        f"Argument 'x' must be of type logical, integer or numeric, not '{array.dtype.name}'"
    )


def _storage_nd(array: np.ndarray):
    storage, flat = _storage_1d(np.ravel(array, order="F"))
    return storage, np.reshape(flat, array.shape, order="F")


def _storage_1d(array: np.ndarray):
    if np.issubdtype(array.dtype, np.unsignedinteger):
        if array.size and int(array.max()) > _INT_MAX:
            return "double", np.asarray(array, dtype=np.float64)
        return "integer", np.asarray(array, dtype=np.int32)
    if array.dtype == np.int32:
        return "integer", array
    as64 = np.asarray(array, dtype=np.int64)
    if as64.size and (int(as64.min()) < _NA_INT or int(as64.max()) > _INT_MAX):
        return "double", np.asarray(array, dtype=np.float64)
    return "integer", np.asarray(as64, dtype=np.int32)


def _resolve_dim(kind, array, dim, by_row: bool):
    """Return ``(length_out, dim_numbers)``.

    ``length_out`` is ``None`` when ``dim.`` is NULL, ``NaN`` when the margin
    length is missing, and otherwise a non-negative integer. Row collapse
    recycles to ``dim.[1]`` and column collapse to ``dim.[2]``.
    """
    if dim is None:
        if kind == "matrix":
            numbers = np.asarray(array.shape, dtype=np.float64)
            return _length_out_at(numbers, 0 if by_row else 1), numbers
        return None, None
    numbers = _dim_numbers(dim)
    return _length_out_at(numbers, 0 if by_row else 1), numbers


def _length_out_at(numbers: np.ndarray, slot: int):
    if numbers.size <= slot:
        return float("nan")
    first = float(numbers[slot])
    if math.isnan(first):
        return float("nan")
    if not math.isfinite(first) or math.trunc(first) < 0:
        raise ValueError("invalid 'length.out' argument")
    return int(math.trunc(first))


def _dim_numbers(dim) -> np.ndarray:
    if isinstance(dim, (bool, np.bool_)):
        raise ValueError("the dims contain missing values")
    if isinstance(dim, (int, np.integer)) and not isinstance(dim, bool):
        return np.array([float(int(dim))], dtype=np.float64)
    if isinstance(dim, (float, np.floating)):
        return np.array([float(dim)], dtype=np.float64)
    if isinstance(dim, str):
        warnings.warn("NAs introduced by coercion", RuntimeWarning, stacklevel=5)
        raise ValueError("the dims contain missing values")
    array = np.asarray(dim)
    if array.dtype.kind in "SU":
        warnings.warn("NAs introduced by coercion", RuntimeWarning, stacklevel=5)
        raise ValueError("the dims contain missing values")
    if array.size == 0:
        return np.array([], dtype=np.float64)
    if array.dtype == object:
        values = []
        for item in np.ravel(array, order="F"):
            if item is None or (isinstance(item, (float, np.floating)) and math.isnan(float(item))):
                values.append(np.nan)
            elif isinstance(item, (bool, np.bool_)):
                values.append(np.nan)
            elif isinstance(item, (int, np.integer, float, np.floating)):
                values.append(float(item))
            else:
                warnings.warn("NAs introduced by coercion", RuntimeWarning, stacklevel=5)
                raise ValueError("the dims contain missing values")
        return np.array(values, dtype=np.float64)
    return np.ravel(array, order="F").astype(np.float64)


def _apply_dim(kind, array, dim_numbers):
    if dim_numbers is None:
        flat = array.reshape(-1)
        return flat, None
    if dim_numbers.size == 0:
        raise ValueError("length-0 dimension vector is invalid")
    if np.any(~np.isfinite(dim_numbers)):
        raise ValueError("the dims contain missing values")
    dims = np.trunc(dim_numbers).astype(np.int64)
    if np.any(dims < 0):
        raise ValueError("the dims contain negative values")
    product = 1
    for item in dims.tolist():
        product *= int(item)
    flat = np.ravel(array, order="F")
    if product != flat.size:
        raise ValueError(
            f"dims [product {product}] do not match the length of object [{flat.size}]"
        )
    if kind == "vector" and array.ndim == 1:
        flat = np.reshape(array, -1)
    return np.ascontiguousarray(flat), tuple(int(item) for item in dims.tolist())


def _take_rows(flat, nrow, ncol, positions, na):
    new_nrow = int(positions.size)
    if new_nrow == 0 or ncol == 0:
        return np.empty(0, dtype=flat.dtype), new_nrow
    matrix = np.reshape(flat, (nrow, ncol), order="F")
    out = np.empty((new_nrow, ncol), dtype=flat.dtype)
    missing = positions < 0
    keep = ~missing
    if np.any(keep):
        out[keep] = matrix[positions[keep]]
    if np.any(missing):
        out[missing] = na
    return np.ravel(out, order="F"), new_nrow


def _take_cols(flat, nrow, ncol, positions, na):
    new_ncol = int(positions.size)
    if new_ncol == 0 or nrow == 0:
        return np.empty(0, dtype=flat.dtype), new_ncol
    matrix = np.reshape(flat, (nrow, ncol), order="F")
    out = np.empty((nrow, new_ncol), dtype=flat.dtype)
    missing = positions < 0
    keep = ~missing
    if np.any(keep):
        out[:, keep] = matrix[:, positions[keep]]
    if np.any(missing):
        out[:, missing] = na
    return np.ravel(out, order="F"), new_ncol


def _margin_positions(n: int, index: _Index) -> np.ndarray:
    """1-based matrix subscript to 0-based positions. ``-1`` is an NA row."""
    if index.kind == "null":
        return np.array([], dtype=np.int64)
    if index.kind == "character":
        raise ValueError("no 'dimnames' attribute for array")
    if index.kind == "logical":
        flags = index.values
        if flags.size > n:
            raise ValueError("(subscript) logical subscript too long")
        if flags.size == 0:
            return np.array([], dtype=np.int64)
        if flags.size < n:
            flags = np.resize(flags, n)
        chosen = np.flatnonzero(flags != 0)
        out = chosen.astype(np.int64)
        out[flags[chosen] < 0] = -1
        return out
    trunc, is_na, is_zero, is_neg, is_pos = _classify(index.values)
    if np.any(is_neg) and (np.any(is_pos) or np.any(is_na)):
        raise ValueError("only 0's may be mixed with negative subscripts")
    if np.any(is_pos) and np.any(trunc[is_pos] > n):
        raise ValueError("subscript out of bounds")
    if np.any(is_neg):
        keep = np.ones(n, dtype=bool)
        mags = np.abs(trunc[is_neg])
        in_range = (mags >= 1) & (mags <= n)
        if np.any(in_range):
            keep[mags[in_range].astype(np.int64) - 1] = False
        return np.flatnonzero(keep).astype(np.int64)
    chosen = trunc[~is_zero]
    missing = is_na[~is_zero]
    out = np.empty(chosen.size, dtype=np.int64)
    out[missing] = -1
    ok = ~missing
    if np.any(ok):
        out[ok] = chosen[ok].astype(np.int64) - 1
    return out


def _subset_index(data: _Index, selector: _Index) -> _Index:
    if data.kind == "null":
        return data
    picked = _subset_values(data.values, selector, _na_value_for_kind(data.kind))
    return _Index(data.kind, picked)


def _subset_values(values: np.ndarray, index: _Index, na_value):
    if index.kind == "null":
        return np.empty(0, dtype=values.dtype)
    if index.kind == "character":
        out = np.empty(index.values.size, dtype=values.dtype)
        out[:] = na_value
        return out
    if index.kind == "logical":
        return _subset_logical(values, index.values, na_value)
    return _subset_numeric(values, index.values, na_value)


def _subset_numeric(values, raw, na_value):
    n = values.size
    trunc, is_na, is_zero, is_neg, is_pos = _classify(raw)
    if np.any(is_neg) and (np.any(is_pos) or np.any(is_na)):
        raise ValueError("only 0's may be mixed with negative subscripts")
    if np.any(is_neg):
        keep = np.ones(n, dtype=bool)
        mags = np.abs(trunc[is_neg])
        in_range = (mags >= 1) & (mags <= n)
        if np.any(in_range):
            keep[mags[in_range].astype(np.int64) - 1] = False
        return values[keep]
    chosen = trunc[~is_zero]
    out = np.empty(chosen.size, dtype=values.dtype)
    if chosen.size == 0:
        return out
    missing = ~np.isfinite(chosen) | (chosen < 1) | (chosen > n)
    out[missing] = na_value
    ok = ~missing
    if np.any(ok):
        out[ok] = values[chosen[ok].astype(np.int64) - 1]
    return out


def _subset_logical(values, flags, na_value):
    n = int(values.size)
    m = int(flags.size)
    if m == 0:
        return np.empty(0, dtype=values.dtype)
    if m <= n:
        if m < n:
            flags = np.resize(flags, n)
        chosen = np.flatnonzero(flags != 0)
        out = np.empty(chosen.size, dtype=values.dtype)
        if chosen.size == 0:
            return out
        missing = flags[chosen] < 0
        out[missing] = na_value
        ok = ~missing
        if np.any(ok):
            out[ok] = values[chosen[ok]]
        return out
    head = _subset_logical(values, flags[:n], na_value) if n else np.empty(0, dtype=values.dtype)
    extra_n = int(np.count_nonzero(flags[n:] != 0))
    if extra_n == 0:
        return head
    extra = np.empty(extra_n, dtype=values.dtype)
    extra[:] = na_value
    if head.size == 0:
        return extra
    return np.concatenate([head, extra])


def _classify(raw):
    trunc = np.trunc(np.asarray(raw, dtype=np.float64))
    is_na = ~np.isfinite(trunc)
    is_zero = (~is_na) & (trunc == 0)
    is_neg = (~is_na) & (trunc < 0)
    is_pos = (~is_na) & (trunc > 0)
    return trunc, is_na, is_zero, is_neg, is_pos


def _colon(start: int, end: int) -> np.ndarray:
    if start <= end:
        return np.arange(start, end + 1, dtype=np.float64)
    return np.arange(start, end - 1, -1, dtype=np.float64)


def _seq_len(n: int) -> np.ndarray:
    if n <= 0:
        return np.array([], dtype=np.float64)
    return np.arange(1, n + 1, dtype=np.float64)


def _scale(nrow: int, picked: np.ndarray) -> np.ndarray:
    if picked.size == 0:
        return np.array([], dtype=np.float64)
    out = nrow * picked
    overflow = np.isfinite(picked) & ((out > _INT_MAX) | (out <= _NA_INT))
    if np.any(overflow):
        warnings.warn("NAs produced by integer overflow", RuntimeWarning, stacklevel=5)
        out = np.array(out, dtype=np.float64, copy=True)
        out[overflow] = np.nan
    return out


def _recycle_add(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    if left.size == 0 or right.size == 0:
        return np.array([], dtype=np.float64)
    n = max(left.size, right.size)
    if left.size != right.size and n % min(left.size, right.size) != 0:
        warnings.warn(
            "longer object length is not a multiple of shorter object length",
            RuntimeWarning,
            stacklevel=2,
        )
    aa = left if left.size == n else np.resize(left, n)
    bb = right if right.size == n else np.resize(right, n)
    out = aa + bb
    finite = np.isfinite(aa) & np.isfinite(bb)
    overflow = finite & ((out > _INT_MAX) | (out <= _NA_INT))
    missing = ~finite
    if np.any(overflow):
        warnings.warn("NAs produced by integer overflow", RuntimeWarning, stacklevel=5)
    if np.any(overflow) or np.any(missing):
        out = np.array(out, dtype=np.float64, copy=True)
        out[overflow | missing] = np.nan
    return out


def _as_index(idxs) -> _Index:
    if idxs is None:
        return _Index("null", np.array([], dtype=np.float64))
    if isinstance(idxs, (bool, np.bool_)):
        return _Index("logical", np.array([1 if idxs else 0], dtype=np.int8))
    if isinstance(idxs, (int, np.integer)) and not isinstance(idxs, bool):
        return _Index("numeric", np.array([_number(idxs)], dtype=np.float64))
    if isinstance(idxs, (float, np.floating)):
        return _Index("numeric", np.array([_number(idxs)], dtype=np.float64))
    if isinstance(idxs, str):
        return _Index("character", np.array([idxs], dtype=object))
    array = np.asarray(idxs)
    if array.ndim == 0:
        return _as_index(array.item())
    flat = np.ravel(array, order="F")
    if flat.dtype == object:
        return _index_from_object(flat)
    if flat.dtype == np.bool_:
        return _Index("logical", flat.astype(np.int8))
    if flat.dtype.kind in "SU":
        return _Index("character", flat.astype(object))
    if np.issubdtype(flat.dtype, np.floating):
        return _Index("numeric", np.asarray(flat, dtype=np.float64))
    if np.issubdtype(flat.dtype, np.integer):
        values = np.asarray(flat, dtype=np.float64)
        if flat.dtype == np.int32:
            values = values.copy()
            values[flat == _NA_INT] = np.nan
        return _Index("numeric", values)
    raise ValueError("idxs can only be integer, numeric, or logical")


def _index_from_object(flat: np.ndarray) -> _Index:
    items = [flat[i] for i in range(flat.size)]
    if any(isinstance(item, str) for item in items):
        text = []
        for item in items:
            if item is None or _is_nan(item):
                text.append(None)
            else:
                text.append(str(item))
        return _Index("character", np.array(text, dtype=object))
    if all(item is None or isinstance(item, (bool, np.bool_)) or _is_nan(item) for item in items):
        if any(isinstance(item, (bool, np.bool_)) for item in items) or any(
            item is None for item in items
        ):
            flags = np.empty(len(items), dtype=np.int8)
            for i, item in enumerate(items):
                if item is None or _is_nan(item):
                    flags[i] = -1
                else:
                    flags[i] = 1 if item else 0
            return _Index("logical", flags)
    values = np.empty(len(items), dtype=np.float64)
    for i, item in enumerate(items):
        if item is None or _is_nan(item):
            values[i] = np.nan
        elif isinstance(item, (bool, np.bool_)):
            values[i] = 1.0 if item else 0.0
        elif isinstance(item, (int, np.integer, float, np.floating)) and not isinstance(item, bool):
            values[i] = _number(item)
        else:
            raise ValueError("idxs can only be integer, numeric, or logical")
    return _Index("numeric", values)


def _number(value) -> float:
    if isinstance(value, (bool, np.bool_)):
        return 1.0 if value else 0.0
    if isinstance(value, np.integer) and value.dtype == np.int32 and int(value) == _NA_INT:
        return float("nan")
    number = float(value)
    if math.isnan(number):
        return float("nan")
    return number


def _is_nan(value) -> bool:
    if isinstance(value, (float, np.floating)):
        return math.isnan(float(value))
    return False


def _rep_index(index: _Index, length_out) -> _Index:
    if length_out is None:
        warnings.warn(
            "first element used of 'length.out' argument",
            RuntimeWarning,
            stacklevel=5,
        )
        return index
    if isinstance(length_out, float) and math.isnan(length_out):
        return index
    n = int(length_out)
    if index.kind == "null":
        warnings.warn("'x' is NULL so the result will be NULL", RuntimeWarning, stacklevel=5)
        return index
    if n == 0:
        return _Index(index.kind, np.empty(0, dtype=index.values.dtype))
    if index.values.size == 0:
        if index.kind == "numeric":
            return _Index("numeric", np.full(n, np.nan))
        if index.kind == "logical":
            return _Index("logical", np.full(n, -1, dtype=np.int8))
        return _Index("character", np.array([None] * n, dtype=object))
    return _Index(index.kind, np.resize(index.values, n))


def _na_value(storage):
    if storage == "integer":
        return np.int32(_NA_INT)
    if storage == "double":
        return np.float64(np.nan)
    return np.int8(-1)


def _na_value_for_kind(kind: str):
    if kind == "logical":
        return np.int8(-1)
    if kind == "character":
        return None
    return np.float64(np.nan)


def _export(values: np.ndarray, storage: str):
    values = np.ascontiguousarray(values)
    if storage == "logical":
        if values.size and np.any(values < 0):
            out = np.empty(values.shape, dtype=object)
            missing = values < 0
            out[missing] = None
            present = ~missing
            out[present] = values[present].astype(bool)
            return out
        return np.asarray(values, dtype=np.bool_)
    return values


def _r_condition(value) -> bool:
    """R's ``if`` on ``useNames``."""
    if value is None:
        raise ValueError("argument is of length zero")
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, np.integer) and getattr(value, "dtype", None) == np.int32:
        if int(value) == _NA_INT:
            raise ValueError("missing value where TRUE/FALSE needed")
        return int(value) != 0
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        return int(value) != 0
    if isinstance(value, (float, np.floating)):
        if not math.isfinite(float(value)):
            raise ValueError("missing value where TRUE/FALSE needed")
        return float(value) != 0.0
    if isinstance(value, str):
        return len(value) > 0
    array = np.asarray(value)
    if array.size == 0:
        raise ValueError("argument is of length zero")
    if array.size > 1:
        raise ValueError("the condition has length > 1")
    item = array.reshape(-1)[0]
    if hasattr(item, "item"):
        item = item.item()
    return _r_condition(item)


def _defunct(klass: str) -> str:
    return (
        f"[matrixStats] Argument ‘x’ is of class ‘{klass}’, but should be a "
        f"matrix or a vector. The use of a ‘{klass}’ is not supported, the "
        "correctness of the result is not guaranteed. Please update your code accordingly."
    )
