"""Row and column ranks, ported from matrixStats."""

from __future__ import annotations

import numpy as np
import rowranks as _rowranks

_INT_MIN = -2_147_483_648
_INT_MAX = 2_147_483_647
_TIES = ("average", "first", "last", "random", "max", "min", "dense")

__all__ = ["rowRanks", "colRanks"]


def rowRanks(x, rows=None, cols=None, ties_method="max", dim=None, use_names=True):
    """Rank the values in each row.

    Mirrors ``matrixStats::rowRanks``. ``rows`` and ``cols`` are 1-based.
    ``None`` uses every row or column. ``ties_method`` is ``ties.method``.
    The default is ``max``. ``dim`` is ``dim.``: a one-dimensional ``x`` is
    filled in column-major order. Average ties return float64. Every other
    method returns int32, and a missing value is R's integer NA. ``use_names``
    does not change the numbers.
    """
    return _ranks(x, rows, cols, ties_method, dim, use_names, True, True)


def colRanks(
    x,
    rows=None,
    cols=None,
    ties_method="max",
    dim=None,
    preserve_shape=False,
    use_names=True,
):
    """Rank the values in each column.

    Mirrors ``matrixStats::colRanks``. Arguments match :func:`rowRanks`.
    ``preserve_shape`` is ``preserveShape``. When it is false the result is
    transposed, so a column of ranks becomes a row.
    """
    return _ranks(
        x,
        rows,
        cols,
        ties_method,
        dim,
        use_names,
        False,
        _flag(preserve_shape, "preserveShape"),
    )


def _ranks(x, rows, cols, ties_method, dim, use_names, by_row, preserve_shape):
    _flag(use_names, "useNames")
    ties = _ties_code(ties_method)
    matrix, integer = _prepare_matrix(x, dim)
    row_index, row_kind = _coerce_index(rows, "rows")
    col_index, col_kind = _coerce_index(cols, "cols")
    if integer:
        ranked = _rowranks.row_ranks_i32(
            matrix, ties, by_row, row_index, row_kind, col_index, col_kind
        )
    else:
        ranked = _rowranks.row_ranks_f64(
            matrix, ties, by_row, row_index, row_kind, col_index, col_kind
        )
    if preserve_shape:
        return ranked
    return np.ascontiguousarray(ranked.T)


def _ties_code(ties_method):
    text = _ties_text(ties_method)
    code = _charmatch(text, _TIES)
    if code == 0:
        raise ValueError(f"Unknown value of argument 'ties.method': {text}")
    return code


def _ties_text(value):
    if value is None:
        return "max"
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise ValueError("argument is of length zero")
        return _ties_text(value[0])
    array = np.asarray(value)
    if array.dtype.kind in "SU":
        if array.size == 0:
            raise ValueError("argument is of length zero")
        return str(array.reshape(-1)[0])
    raise ValueError(f"Unknown value of argument 'ties.method': {value}")


def _charmatch(text, table):
    exact = [index for index, name in enumerate(table, 1) if name == text]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return 0
    if text == "":
        return 0
    partial = [index for index, name in enumerate(table, 1) if name.startswith(text)]
    if len(partial) == 1:
        return partial[0]
    return 0


def _flag(value, r_name):
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        number = int(value)
        if number in (0, 1):
            return bool(number)
        raise ValueError(f"Argument '{r_name}' must be either TRUE or FALSE")
    arr = np.asarray(value)
    if arr.ndim > 1 or arr.size != 1:
        raise ValueError(f"Argument '{r_name}' must be a single value")
    item = arr.reshape(-1)[0]
    if isinstance(item, (bool, np.bool_)) or (
        arr.dtype == np.bool_ or np.issubdtype(arr.dtype, np.integer)
    ):
        return _flag(item.item() if hasattr(item, "item") else item, r_name)
    raise ValueError(f"Argument '{r_name}' must be a logical")


def _prepare_matrix(x, dim):
    values = np.asarray(x)
    if values.ndim == 0:
        values = values.reshape(1)
    if values.ndim > 2:
        raise ValueError("Argument 'x' must be a matrix or a vector")
    if values.dtype == np.bool_:
        raise ValueError("Argument 'x' cannot be logical")
    if np.issubdtype(values.dtype, np.integer):
        integer = True
        values = _as_i32(values)
    elif np.issubdtype(values.dtype, np.floating):
        integer = False
        values = values.astype(np.float64, copy=False)
    else:
        raise ValueError(
            "Argument 'x' must be of type logical, integer or numeric, not "
            f"'{_type_name(values.dtype)}'"
        )

    if dim is None:
        if values.ndim != 2:
            raise ValueError("Argument 'dim.' must be an integer vector of length two")
        return _contiguous_2d(values), integer

    nrow, ncol = _parse_dim(dim, int(values.size))
    if values.ndim == 1:
        flat = np.ascontiguousarray(values)
        return np.reshape(flat, (nrow, ncol), order="F"), integer
    if values.shape == (nrow, ncol):
        return _contiguous_2d(values), integer
    flat = np.ravel(np.asfortranarray(values), order="F")
    return np.reshape(flat, (nrow, ncol), order="F"), integer


def _as_i32(values):
    if values.dtype == np.int32:
        return values
    if np.issubdtype(values.dtype, np.unsignedinteger):
        if values.size and np.any(values > _INT_MAX):
            raise ValueError(
                "Argument 'x' integer values do not fit in a 32-bit integer"
            )
        return values.astype(np.int32)
    wide = values.astype(np.int64, copy=False)
    if values.size and (np.any(wide < _INT_MIN) or np.any(wide > _INT_MAX)):
        raise ValueError(
            "Argument 'x' integer values do not fit in a 32-bit integer"
        )
    return wide.astype(np.int32)


def _type_name(dtype):
    if dtype.kind in ("U", "S"):
        return "character"
    if dtype.kind == "c":
        return "complex"
    return dtype.name


def _parse_dim(dim, length):
    vals = np.asarray(dim)
    if vals.ndim == 0:
        vals = vals.reshape(1)
    if vals.ndim != 1 or vals.size != 2 or not (
        np.issubdtype(vals.dtype, np.integer) or np.issubdtype(vals.dtype, np.floating)
    ):
        raise ValueError("Argument 'dim.' must be an integer vector of length two")
    nums = []
    for raw in np.asarray(vals, dtype=np.float64).reshape(-1):
        if not np.isfinite(raw) or raw > _INT_MAX or raw < _INT_MIN:
            nums.append(_INT_MIN)
        else:
            nums.append(int(np.trunc(raw)))
    nrow, ncol = nums
    if nrow < 0:
        raise ValueError(
            f"Argument 'dim.' specifies a negative number of rows (dim.[1]): {nrow}"
        )
    if ncol < 0:
        raise ValueError(
            f"Argument 'dim.' specifies a negative number of columns (dim.[2]): {ncol}"
        )
    if nrow * ncol != length:
        raise ValueError(
            "Argument 'dim.' does not match length of argument 'x': "
            f"{nrow} * {ncol} != {length}"
        )
    return nrow, ncol


def _contiguous_2d(values):
    if values.flags.c_contiguous or values.flags.f_contiguous:
        return values
    return np.ascontiguousarray(values)


def _coerce_index(index, name):
    if index is None:
        return None, "all"
    logical = _logical_codes(index, name)
    if logical is not None:
        return np.ascontiguousarray(logical, dtype=np.int8), "logical"
    if isinstance(index, (int, np.integer)) and not isinstance(index, bool):
        return np.asarray([int(index)], dtype=np.int64), "int"
    if isinstance(index, float):
        return np.asarray([float(index)], dtype=np.float64), "real"
    if isinstance(index, (list, tuple)) and any(v is None for v in index):
        return (
            np.ascontiguousarray(
                [np.nan if v is None else float(v) for v in index],
                dtype=np.float64,
            ),
            "real",
        )

    arr = np.asarray(index)
    if arr.ndim == 0:
        arr = arr.reshape(1)
    if arr.ndim != 1:
        raise ValueError(f"Argument '{name}' must be a vector")
    if arr.dtype == object:
        if any(v is None for v in arr.reshape(-1)):
            return (
                np.ascontiguousarray(
                    [np.nan if v is None else float(v) for v in arr.reshape(-1)],
                    dtype=np.float64,
                ),
                "real",
            )
        raise ValueError("idxs can only be integer, numeric, or logical")
    if np.issubdtype(arr.dtype, np.integer):
        return np.ascontiguousarray(arr, dtype=np.int64), "int"
    if np.issubdtype(arr.dtype, np.floating):
        return np.ascontiguousarray(arr, dtype=np.float64), "real"
    raise ValueError("idxs can only be integer, numeric, or logical")


def _logical_codes(index, name):
    if isinstance(index, (bool, np.bool_)):
        return np.array([1 if index else 0], dtype=np.int8)
    if isinstance(index, np.ndarray) and index.dtype == np.bool_:
        array = np.atleast_1d(index)
        if array.ndim != 1:
            raise ValueError(f"Argument '{name}' must be a vector")
        return np.ascontiguousarray(array, dtype=np.int8)
    if isinstance(index, (list, tuple)):
        values = list(index)
    else:
        return None
    if not values or not all(_is_logical_mark(v) for v in values):
        return None
    codes = np.empty(len(values), dtype=np.int8)
    for i, value in enumerate(values):
        if value is None:
            codes[i] = -1
        else:
            codes[i] = 1 if value else 0
    return codes


def _is_logical_mark(value):
    return value is None or isinstance(value, (bool, np.bool_))
