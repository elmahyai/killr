"""Ordering permutations.

``ORDER`` follows the R generic. ``ORDER.default`` is base ``order``:
a stable sort, one-based positions, and ``na.last`` kept apart from
``decreasing``. ``NA`` and ``NaN`` are both missing. Signed zeros tie.
"""

from __future__ import annotations

import datetime as dt
import locale
import math
from typing import Any

import numpy as np

_EPOCH = dt.date(1970, 1, 1)
_LOCALE_READY = False


def ORDER(x: Any, *args: Any, na_last: Any = True, decreasing: Any = False, **kwargs: Any) -> list[int]:
    """Dispatch ``ORDER``. Plain values use the default method."""
    if "na.last" in kwargs:
        na_last = kwargs.pop("na.last")
    return ORDER_default(x, *args, na_last=na_last, decreasing=decreasing)


def ORDER_default(
    x: Any,
    *args: Any,
    na_last: Any = True,
    decreasing: Any = False,
    **kwargs: Any,
) -> list[int]:
    """Stable one-based order, the same rules as base ``order``."""
    if "na.last" in kwargs:
        na_last = kwargs.pop("na.last")
    columns = [_column(x)] + [_column(arg) for arg in args]
    width = len(columns[0])
    for column in columns[1:]:
        if len(column) != width:
            raise ValueError("argument lengths differ")
    flags = _decreasing_flags(decreasing, len(columns))
    missing_mode = _missing_mode(na_last)
    indexes = list(range(width))
    if missing_mode == "drop":
        indexes = [
            i
            for i in indexes
            if not any(_is_missing(column[i]) for column in columns)
        ]

    def key(i: int) -> tuple[Any, ...]:
        parts: list[Any] = []
        for column, reverse in zip(columns, flags):
            value = column[i]
            missing = _is_missing(value)
            if missing_mode == "last":
                parts.append(1 if missing else 0)
            elif missing_mode == "first":
                parts.append(0 if missing else 1)
            else:
                parts.append(0)
            if missing:
                parts.append((0, 0.0))
            else:
                parts.append(_token(value, reverse))
        return tuple(parts)

    indexes.sort(key=key)
    return [i + 1 for i in indexes]


def ORDER_chron(x: Any, *args: Any, na_last: Any = True, decreasing: Any = False, **kwargs: Any) -> list[int]:
    """``ORDER.chron`` is ``order(as.numeric(x))`` and does not import chron."""
    if "na.last" in kwargs:
        na_last = kwargs.pop("na.last")
    numbers = [_as_float(value) for value in _column(x)]
    return ORDER_default(numbers, *args, na_last=na_last, decreasing=decreasing)


def _column(value: Any) -> list[Any]:
    if isinstance(value, np.ndarray):
        return list(np.ravel(value, order="F"))
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, range):
        return list(value)
    return [value]


def _decreasing_flags(decreasing: Any, count: int) -> list[bool]:
    if isinstance(decreasing, (bool, np.bool_)):
        return [bool(decreasing)] * count
    if isinstance(decreasing, (list, tuple, np.ndarray)):
        flags = [bool(item) for item in list(decreasing)]
        if len(flags) == 1:
            return flags * count
        if len(flags) != count:
            raise ValueError("argument lengths differ")
        return flags
    return [bool(decreasing)] * count


def _missing_mode(na_last: Any) -> str:
    if na_last is None:
        return "drop"
    if isinstance(na_last, float) and math.isnan(na_last):
        return "drop"
    if isinstance(na_last, (np.floating,)) and np.isnan(na_last):
        return "drop"
    if bool(na_last):
        return "last"
    return "first"


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (float, np.floating)):
        return bool(math.isnan(float(value)))
    return False


def _as_float(value: Any) -> float:
    if _is_missing(value):
        return float("nan")
    if isinstance(value, dt.datetime):
        return float(value.timestamp())
    if isinstance(value, dt.date):
        return float((value - _EPOCH).days)
    if isinstance(value, (bool, np.bool_)):
        return float(bool(value))
    number = float(value)
    if number == 0.0:
        return 0.0
    return number


def _token(value: Any, reverse: bool) -> tuple[Any, ...]:
    if isinstance(value, str):
        _ensure_locale()
        return ("text", _Text(value, reverse))
    return ("num", _Num(_as_float(value), reverse))


def _ensure_locale() -> None:
    global _LOCALE_READY
    if _LOCALE_READY:
        return
    if locale.getlocale(locale.LC_COLLATE)[0] is None:
        try:
            locale.setlocale(locale.LC_COLLATE, "")
        except locale.Error:
            pass
    _LOCALE_READY = True


class _Num:
    def __init__(self, value: float, reverse: bool) -> None:
        self.value = value
        self.reverse = reverse

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Num) and self.value == other.value and self.reverse == other.reverse

    def __lt__(self, other: _Num) -> bool:
        if not isinstance(other, _Num):
            return NotImplemented
        if self.reverse:
            return self.value > other.value
        return self.value < other.value


class _Text:
    def __init__(self, value: str, reverse: bool) -> None:
        self.value = value
        self.reverse = reverse

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, _Text)
            and locale.strcoll(self.value, other.value) == 0
            and self.reverse == other.reverse
        )

    def __lt__(self, other: _Text) -> bool:
        if not isinstance(other, _Text):
            return NotImplemented
        compared = locale.strcoll(self.value, other.value)
        if self.reverse:
            return compared > 0
        return compared < 0
