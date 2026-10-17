"""Character coercion and the %+% length rules."""

from __future__ import annotations

import math
from typing import Any


def is_string(value: Any) -> bool:
    return isinstance(value, str)


def character_vector(value: Any) -> list[str | None]:
    """One R character vector. A Python str has length 1, not len(str)."""

    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [_scalar_character(item) for item in value]
    return [_scalar_character(value)]


def _scalar_character(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Inf" if value > 0 else "-Inf"
        if value == int(value) and abs(value) < 2**53:
            return str(int(value))
        return repr(value)
    return str(value)


def require_character(value: Any) -> list[str | None]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)) and all(
        item is None or isinstance(item, str) for item in value
    ):
        return list(value)
    raise TypeError("argument must be a character vector")


def _recycle(columns: list[list[Any]], sep: str) -> list[Any]:
    if not columns:
        return [""]
    if any(len(column) == 0 for column in columns):
        return []
    width = max(len(column) for column in columns)
    rows: list[Any] = []
    for index in range(width):
        parts = []
        for column in columns:
            item = column[0] if len(column) == 1 else column[index]
            if item is None:
                parts.append("NA")
            else:
                parts.append(item)
        rows.append(sep.join(parts))
    return rows


def mypaste(args: tuple[Any, ...], sep: str = " ") -> list[str]:
    columns = [character_vector(arg) for arg in args]
    lengths = {len(column) for column in columns if len(column) != 1}
    if len(lengths) > 1:
        raise ValueError(
            "All character vectors must have the same length (or length 1)"
        )
    rows = _recycle(columns, sep)
    return ["" if row is None else str(row) for row in rows]


def paste0(*args: Any) -> str | list[str]:
    columns = [character_vector(arg) for arg in args]
    rows = _recycle(columns, "")
    if len(rows) == 1:
        return rows[0]
    return rows


def concat(lhs: Any, rhs: Any) -> str | list[str]:
    """R's `%+%`. Lengths must match, or one of them must be 1."""

    left = require_character(lhs)
    right = require_character(rhs)
    if len(left) != len(right) and len(left) != 1 and len(right) != 1:
        raise ValueError(
            "length of the two arguments must match, or one of them must be 1"
        )
    if len(left) == 0 and len(right) == 0:
        return []
    if len(left) == 0 or len(right) == 0:
        return []
    return paste0(left, right)


def one_or_many(rows: list[Any]) -> Any:
    if len(rows) == 1:
        return rows[0]
    return rows
