"""Input preparation shared by the public gower wrappers."""

from __future__ import annotations

import sys
from collections.abc import Mapping
from typing import Any

import numpy as np

import gower_kernel

NA_INT = np.iinfo(np.int32).min


def _is_factor(column: Any) -> bool:
    dtype = getattr(column, "dtype", None)
    return bool(getattr(dtype, "categories", None) is not None)


def _column_values(column: Any) -> list[Any]:
    if hasattr(column, "to_list"):
        return column.to_list()
    if hasattr(column, "tolist"):
        values = column.tolist()
        return values if isinstance(values, list) else list(values)
    return list(column)


def _is_nan(value: Any) -> bool:
    try:
        return bool(np.isnan(value))
    except (TypeError, ValueError):
        return False


def _is_na(value: Any) -> bool:
    """True for None, NaN and pandas NA (pandas is checked only when loaded)."""
    if value is None:
        return True
    pd = sys.modules.get("pandas")
    if pd is not None and value is pd.NA:
        return True
    return _is_nan(value)


def _storage_kind(column: Any, values: list[Any]) -> str:
    """numpy kind of a column: from its dtype when it has one, otherwise from
    its non-missing values, so None or pd.NA does not turn a logical or
    integer column into strings."""
    kind = getattr(getattr(column, "dtype", None), "kind", None)
    if kind in ("b", "i", "u", "f", "c"):
        return kind
    present = [value for value in values if not _is_na(value)]
    return np.asarray(present).dtype.kind if present else "O"


def _encode_column(column: Any) -> tuple[str, np.ndarray | list[str | None], bool]:
    """Convert one Python column to the storage representation used by Rust."""
    factor = _is_factor(column)
    values = _column_values(column)

    if factor:
        categories = list(column.dtype.categories)
        lookup = {value: i + 1 for i, value in enumerate(categories)}
        encoded = np.array(
            [NA_INT if _is_na(value) else lookup[value] for value in values],
            dtype=np.int32,
        )
        return "int", encoded, True

    kind = _storage_kind(column, values)
    # R stores NA of a logical or integer column as INT_MIN, but dispatches on
    # the column type: logical -> gower_logi, integer -> gower_int.
    if kind == "b":
        return "lgl", np.array(
            [NA_INT if _is_na(value) else int(bool(value)) for value in values],
            dtype=np.int32,
        ), False
    if kind in ("i", "u"):
        return "int", np.array(
            [NA_INT if _is_na(value) else int(value) for value in values],
            dtype=np.int32,
        ), False
    if kind == "f":
        return "dbl", np.array(
            [np.nan if _is_na(value) else float(value) for value in values],
            dtype=np.float64,
        ), False
    if kind == "c":
        raise TypeError("complex columns are not supported")
    return "str", [
        None if _is_na(value) else str(value) for value in values
    ], False


def _columns(data: Any) -> list[Any]:
    if isinstance(data, Mapping):
        return list(data.values())
    names = getattr(data, "columns", None)
    if names is not None and not isinstance(data, np.ndarray):
        return [data[name] for name in names]
    arr = np.asarray(data)
    if arr.ndim != 2:
        raise TypeError("x and y must be two-dimensional data or column mappings")
    return [arr[:, i] for i in range(arr.shape[1])]


def _prepare_data(data: Any) -> tuple[list[tuple[str, Any]], list[bool]]:
    columns = _columns(data)
    if not columns:
        raise ValueError("x and y must have at least one column")
    encoded = [_encode_column(column) for column in columns]
    lengths = {len(column[1]) for column in encoded}
    if len(lengths) != 1 or 0 in lengths:
        raise ValueError("x and y must have at least one row and equal column lengths")
    return [(kind, values) for kind, values, _ in encoded], [factor for _, _, factor in encoded]


def prepare(
    x: Any,
    y: Any | None,
    pair_x: Any | None,
    pair_y: Any | None,
    eps: float,
    weights: Any | None,
) -> tuple[
    list[tuple[str, Any]],
    list[tuple[str, Any]],
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    float,
]:
    if y is None:
        y = x
    xc, x_factors = _prepare_data(x)
    yc, _ = _prepare_data(y)
    nx, ny = len(xc), len(yc)
    px = np.arange(1, nx + 1, dtype=np.int64) if pair_x is None else np.asarray(pair_x, dtype=np.int64)
    py = np.arange(1, ny + 1, dtype=np.int64) if pair_y is None else np.asarray(pair_y, dtype=np.int64)
    if px.ndim != 1 or py.ndim != 1 or len(px) != len(py):
        raise ValueError("pair_x and pair_y must have equal lengths")
    if np.any(px < 1) or np.any(px > nx):
        raise ValueError("pair_x contains a column outside x")
    if np.any(py < 0) or np.any(py > ny):
        raise ValueError("pair_y contains a column outside y")
    if len(np.unique(px)) != len(px):
        raise ValueError("pair_x must not contain duplicate columns")
    pair0 = np.full(nx, -1, dtype=np.int64)
    factors = np.zeros(nx, dtype=np.int32)
    ranges = np.zeros(nx, dtype=np.float64)
    for x_index, y_index in zip(px, py):
        j = int(x_index - 1)
        factors[j] = int(x_factors[j])
        if y_index:
            pair0[j] = int(y_index - 1)
            ranges[j] = gower_kernel.xy_range(xc[j], yc[int(y_index - 1)])
    if weights is None:
        w = np.ones(nx, dtype=np.float64)
    else:
        w = np.asarray(weights, dtype=np.float64)
        if w.ndim != 1 or len(w) != len(px):
            raise ValueError("weights must have one value per paired column")
        expanded = np.zeros(nx, dtype=np.float64)
        for j, value in zip(px, w):
            expanded[int(j - 1)] = value
        w = expanded
    return xc, yc, ranges, pair0, factors, w, float(eps)
