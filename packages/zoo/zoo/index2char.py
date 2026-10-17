"""Character labels for a zoo index.

Numeric indexes with a frequency that divides the spacing are printed
as ``year(cycle)``. Anything else is ``as.character(round(x, digits))``,
and ``digits`` defaults to ``getOption("digits") - 3``, which is 4.
"""

from __future__ import annotations

import datetime as dt
import math
from typing import Any

import numpy as np

from zoo.index import all_equal_true, as_character_double, numeric_diff, r_round, r_round_values


def index2char(x: Any, frequency: Any = None, digits: Any = None, **kwargs: Any) -> list[str]:
    """Dispatch ``index2char``. Integers use the numeric method."""
    fmt = kwargs.get("format")
    values = _items(x)
    if values and all(isinstance(item, dt.datetime) for item in values):
        return [_format_posix(item, fmt) for item in values]
    if _is_numeric(values):
        return _numeric(values, frequency, 4 if digits is None else digits)
    return [_as_character(item) for item in values]


def _numeric(values: list[Any], frequency: Any, digits: Any) -> list[str]:
    if frequency is None:
        return [as_character_double(r_round(item, digits)) for item in values]
    if len(values) < 1:
        return []
    numbers = [float(item) for item in values]
    delta = numeric_diff(numbers)
    freq = float(frequency)
    if freq > 1.0 and all_equal_true(freq, r_round(freq)):
        freq = float(r_round(freq))
    scaled = [freq * item for item in delta]
    if all_equal_true(scaled, r_round_values(scaled)):
        if freq == 1.0:
            return [as_character_double(r_round(item)) for item in numbers]
        labels = []
        for item in numbers:
            year = math.floor(item)
            cycle = r_round((item - year) * freq) + 1.0
            labels.append(f"{as_character_double(year)}({as_character_double(cycle)})")
        return labels
    return [as_character_double(r_round(item, digits)) for item in numbers]


def _items(x: Any) -> list[Any]:
    if isinstance(x, np.ndarray):
        return list(np.ravel(x, order="F"))
    if isinstance(x, (list, tuple, range)):
        return list(x)
    if x is None:
        return []
    return [x]


def _is_numeric(values: list[Any]) -> bool:
    if not values:
        return True
    for item in values:
        if item is None:
            continue
        if isinstance(item, (bool, np.bool_)):
            return False
        if not isinstance(item, (int, float, np.number)):
            return False
    return True


def _as_character(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, dt.datetime):
        return _format_posix(value, None)
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, (bool, np.bool_)):
        return "TRUE" if bool(value) else "FALSE"
    if isinstance(value, (int, float, np.number)):
        return as_character_double(value)
    return str(value)


def _format_posix(value: dt.datetime, fmt: str | None) -> str:
    if fmt:
        return value.strftime(fmt)
    text = value.strftime("%Y-%m-%d %H:%M:%S")
    if value.microsecond:
        fraction = f"{value.microsecond:06d}".rstrip("0")
        if fraction:
            return f"{text}.{fraction}"
    return text
