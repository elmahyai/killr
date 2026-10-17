"""Elementwise ``x OP y`` and ``t(t(x) OP y)``, ported from matrixStats."""

from __future__ import annotations

import warnings

import numpy as np
import xopy as _xopy

_INT_MIN = -2_147_483_648
_INT_MAX = 2_147_483_647
_OVERFLOW = (
    "Integer overflow. Detected one or more elements whose absolute values "
    "were out of the range [-2147483647,2147483647] that can be used to for "
    "integers. Such values are set to NA_integer_."
)

__all__ = ["x_OP_y", "t_tx_OP_y"]


def x_OP_y(
    x,
    y,
    OP,
    xrows=None,
    xcols=None,
    yidxs=None,
    commute=False,
    na_rm=False,
):
    """Apply ``OP`` with ``y`` recycled in column-major order.

    Mirrors ``matrixStats::x_OP_y``. ``OP`` is ``"+"``, ``"-"``, ``"*"``,
    ``"/"``, or the integers 1 through 4. ``xrows``, ``xcols``, and ``yidxs``
    are 1-based. ``None`` selects every position. ``commute`` calculates
    ``y OP x``. ``na_rm`` is ``na.rm`` and changes only addition and
    multiplication.
    """
    return _op(x, y, OP, xrows, xcols, yidxs, commute, na_rm, by_row=False)


def t_tx_OP_y(
    x,
    y,
    OP,
    xrows=None,
    xcols=None,
    yidxs=None,
    commute=False,
    na_rm=False,
):
    """Apply ``OP`` with ``y`` recycled in row-major order.

    Mirrors ``matrixStats::t_tx_OP_y``, which is ``t(t(x) OP y)``. Arguments
    match :func:`x_OP_y`. ``commute`` calculates ``t(y OP t(x))``.
    """
    return _op(x, y, OP, xrows, xcols, yidxs, commute, na_rm, by_row=True)


def _op(x, y, OP, xrows, xcols, yidxs, commute, na_rm, by_row):
    op = _parse_op(OP)
    commute = _flag(commute, "commute")
    na_rm = _flag(na_rm, "na.rm")
    matrix, x_integer = _prepare_matrix(x)
    vector, y_integer = _prepare_vector(y)
    row_index, row_kind = _coerce_index(xrows, "xrows")
    col_index, col_kind = _coerce_index(xcols, "xcols")
    y_index, y_kind = _coerce_index(yidxs, "yidxs")
    if x_integer and y_integer:
        values, overflow = _xopy.apply_i32_i32(
            matrix,
            vector,
            op,
            by_row,
            commute,
            na_rm,
            row_index,
            row_kind,
            col_index,
            col_kind,
            y_index,
            y_kind,
        )
    elif x_integer:
        values, overflow = _xopy.apply_i32_f64(
            matrix,
            vector,
            op,
            by_row,
            commute,
            na_rm,
            row_index,
            row_kind,
            col_index,
            col_kind,
            y_index,
            y_kind,
        )
    elif y_integer:
        values, overflow = _xopy.apply_f64_i32(
            matrix,
            vector,
            op,
            by_row,
            commute,
            na_rm,
            row_index,
            row_kind,
            col_index,
            col_kind,
            y_index,
            y_kind,
        )
    else:
        values, overflow = _xopy.apply_f64_f64(
            matrix,
            vector,
            op,
            by_row,
            commute,
            na_rm,
            row_index,
            row_kind,
            col_index,
            col_kind,
            y_index,
            y_kind,
        )
    if overflow:
        warnings.warn(_OVERFLOW, RuntimeWarning, stacklevel=3)
    return values


def _parse_op(op):
    if isinstance(op, str):
        code = {"+": 1, "-": 2, "*": 3, "/": 4}.get(op)
        if code is None:
            raise ValueError(f"Unknown value of argument 'OP': '{op}'")
        return code
    if isinstance(op, (bool, np.bool_)):
        raise ValueError("Unknown value on argument 'OP': 1L")
    if isinstance(op, (int, np.integer)):
        code = int(op)
    elif isinstance(op, (float, np.floating)):
        if not np.isfinite(float(op)):
            raise ValueError("Unknown value on argument 'OP': NA")
        code = int(op)
    else:
        arr = np.asarray(op)
        if arr.ndim == 0 or arr.size == 1:
            return _parse_op(arr.reshape(-1)[0].item())
        raise ValueError("Unknown value of argument 'OP'")
    if code not in (1, 2, 3, 4):
        raise ValueError(f"Unknown value on argument 'OP': {code}L")
    return code


def _flag(value, r_name):
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        number = int(value)
        if number == _INT_MIN:
            raise ValueError(f"Argument '{r_name}' must be either TRUE or FALSE")
        return number != 0
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if not np.isfinite(number):
            raise ValueError(f"Argument '{r_name}' must be either TRUE or FALSE")
        return number != 0.0
    arr = np.asarray(value)
    if arr.ndim > 1 or arr.size != 1:
        raise ValueError(f"Argument '{r_name}' must be a single value")
    item = arr.reshape(-1)[0]
    if isinstance(item, (bool, np.bool_)) or (
        arr.dtype == np.bool_ or np.issubdtype(arr.dtype, np.integer)
    ):
        return _flag(item.item() if hasattr(item, "item") else item, r_name)
    if np.issubdtype(arr.dtype, np.floating):
        return _flag(float(item), r_name)
    raise ValueError(f"Argument '{r_name}' must be a logical")


def _prepare_matrix(x):
    values = np.asarray(x)
    if values.ndim == 0:
        values = values.reshape(1)
    if values.ndim != 2:
        raise ValueError("Argument 'dim.' must be an integer vector of length two")
    integer, values = _coerce_atomic(values, "x")
    return _contiguous_2d(values), integer


def _prepare_vector(y):
    values = np.asarray(y)
    if values.ndim == 0:
        values = values.reshape(1)
    elif values.ndim == 2:
        values = np.ravel(np.asfortranarray(values), order="F")
    elif values.ndim != 1:
        raise ValueError("Argument 'y' must be a matrix or a vector")
    integer, values = _coerce_atomic(values, "y")
    return np.ascontiguousarray(values), integer


def _coerce_atomic(values, name):
    if values.dtype == np.bool_:
        return True, values.astype(np.int32)
    if np.issubdtype(values.dtype, np.integer):
        return True, _as_i32(values, name)
    if np.issubdtype(values.dtype, np.floating):
        return False, values.astype(np.float64, copy=False)
    raise ValueError(
        "Argument "
        f"'{name}' must be of type logical, integer or numeric, not "
        f"'{_type_name(values.dtype)}'"
    )


def _as_i32(values, name):
    if values.dtype == np.int32:
        return values
    if np.issubdtype(values.dtype, np.unsignedinteger):
        if values.size and np.any(values > _INT_MAX):
            raise ValueError(
                f"Argument '{name}' integer values do not fit in a 32-bit integer"
            )
        return values.astype(np.int32)
    wide = values.astype(np.int64, copy=False)
    if values.size and (np.any(wide < _INT_MIN) or np.any(wide > _INT_MAX)):
        raise ValueError(
            f"Argument '{name}' integer values do not fit in a 32-bit integer"
        )
    return wide.astype(np.int32)


def _type_name(dtype):
    if dtype.kind in ("U", "S"):
        return "character"
    if dtype.kind == "c":
        return "complex"
    return dtype.name


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
