"""Value matching.

``MATCH.default`` is base ``match``, plus the zoo rule that a plain
atomic ``x`` is converted when ``table`` is a Date or a POSIXt.
``NA`` matches ``NA`` and does not match ``NaN``. ``MATCH.times``
truncates chron ``times`` with the same units and ``eps`` as ``trunc.times``.
"""

from __future__ import annotations

import datetime as dt
import math
from typing import Any

import numpy as np

from zoo.times import Times, trunc_times

_EPOCH = dt.date(1970, 1, 1)
_POSIX_EPOCH = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)


def MATCH(x: Any, table: Any, nomatch: Any = None, **kwargs: Any) -> list[Any]:
    """Dispatch ``MATCH``. Numbers, character, Date, and POSIXt are covered."""
    if _is_times(x):
        return MATCH_times(x, table, nomatch=nomatch, **kwargs)
    if _is_date_vector(x):
        return _match_date(x, table, nomatch, **kwargs)
    if _is_posix_vector(x):
        return _match_posix(x, table, nomatch, **kwargs)
    return MATCH_default(x, table, nomatch=nomatch, **kwargs)


def MATCH_default(x: Any, table: Any, nomatch: Any = None, incomparables: Any = None, **kwargs: Any) -> list[Any]:
    """``MATCH.default``. Date and POSIXt tables convert a plain atomic ``x``."""
    del kwargs
    if _plain_atomic(x):
        if _is_date_vector(table):
            x = [_date_to_days(_as_date_numeric(item)) for item in _items(x)]
            table = [_date_to_days(item) for item in _items(table)]
        elif _is_posix_vector(table):
            x = [_posix_seconds(_as_posix_numeric(item)) for item in _items(x)]
            table = [_posix_seconds(item) for item in _items(table)]
    return _match(x, table, nomatch, incomparables)


def MATCH_times(
    x: Any,
    table: Any,
    nomatch: Any = None,
    units: str = "sec",
    eps: float = 1e-10,
    **kwargs: Any,
) -> list[Any]:
    """``MATCH.times`` matches after ``trunc`` on chron ``times`` values."""
    truncated_x = _times_values(trunc_times(x, units=units, eps=eps))
    truncated_table = _times_values(trunc_times(table, units=units, eps=eps))
    return _match(truncated_x, truncated_table, nomatch, kwargs.get("incomparables"))


def _match(x: Any, table: Any, nomatch: Any, incomparables: Any) -> list[Any]:
    missing = _as_integer(nomatch)
    positions: dict[Any, int] = {}
    for offset, item in enumerate(_items(table), start=1):
        key = _key(item)
        if key not in positions:
            positions[key] = offset
    blocked: set[Any] = set()
    if incomparables is not None:
        for item in _items(incomparables):
            blocked.add(_key(item))
    found: list[Any] = []
    for item in _items(x):
        key = _key(item)
        if key in blocked:
            found.append(missing)
        else:
            found.append(positions.get(key, missing))
    return found


def _match_date(x: Any, table: Any, nomatch: Any, **kwargs: Any) -> list[Any]:
    incomparables = kwargs.get("incomparables")
    if not _is_date_vector(table):
        table = [_as_date_numeric(item) for item in _items(table)]
    return _match(
        [_date_to_days(item) for item in _items(x)],
        [_date_to_days(item) for item in _items(table)],
        nomatch,
        None if incomparables is None else [_date_to_days(item) for item in _items(incomparables)],
    )


def _match_posix(x: Any, table: Any, nomatch: Any, **kwargs: Any) -> list[Any]:
    incomparables = kwargs.get("incomparables")
    if not _is_posix_vector(table):
        table = [_as_posix_numeric(item) for item in _items(table)]
    return _match(
        [_posix_seconds(item) for item in _items(x)],
        [_posix_seconds(item) for item in _items(table)],
        nomatch,
        None if incomparables is None else [_posix_seconds(item) for item in _items(incomparables)],
    )


def _items(value: Any) -> list[Any]:
    if isinstance(value, np.ndarray):
        return list(np.ravel(value, order="F"))
    if isinstance(value, (list, tuple, range)):
        return list(value)
    return [value]


def _plain_atomic(value: Any) -> bool:
    items = _items(value)
    if not items:
        return True
    for item in items:
        if item is None:
            continue
        if isinstance(item, (bool, np.bool_)):
            continue
        if isinstance(item, (dt.date, dt.datetime)):
            return False
        if not isinstance(item, (int, float, str, np.number)):
            return False
    return True


def _is_date_vector(value: Any) -> bool:
    items = _items(value)
    if not items:
        return False
    return all(isinstance(item, dt.date) and not isinstance(item, dt.datetime) for item in items)


def _is_posix_vector(value: Any) -> bool:
    items = _items(value)
    if not items:
        return False
    return all(isinstance(item, dt.datetime) for item in items)


def _is_times(value: Any) -> bool:
    if isinstance(value, Times):
        return True
    marker = getattr(value, "class_name", None) or getattr(value, "zoo_class", None)
    if marker == "times":
        return True
    classes = getattr(value, "classes", None)
    return isinstance(classes, (list, tuple)) and "times" in classes


def _times_values(value: Any) -> list[Any]:
    if isinstance(value, Times):
        return value._values.tolist()
    if isinstance(value, np.ndarray):
        return list(np.ravel(value, order="F"))
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _key(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ("na",)
    if isinstance(value, (float, np.floating)) and math.isnan(float(value)):
        return ("nan",)
    if isinstance(value, dt.datetime):
        return ("posix", float(value.timestamp()))
    if isinstance(value, dt.date):
        return ("date", (value - _EPOCH).days)
    if isinstance(value, str):
        return ("str", value)
    if isinstance(value, (bool, np.bool_)):
        return ("num", float(bool(value)))
    if isinstance(value, (int, float, np.number)):
        number = float(value)
        if number == 0.0:
            return ("num", 0.0)
        return ("num", number)
    return ("obj", repr(value))


def _as_integer(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (bool, np.bool_)):
        return int(bool(value))
    if isinstance(value, (int, np.integer)):
        number = int(value)
        if number > 2147483647 or number < -2147483648:
            return None
        return number
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return None
        if number > 2147483647 or number < -2147483648:
            return None
        return int(math.trunc(number))
    raise ValueError("nomatch must be coercible to integer")


def _date_to_days(value: Any) -> float:
    if isinstance(value, dt.datetime):
        value = value.date()
    if isinstance(value, dt.date):
        return float((value - _EPOCH).days)
    return float(value)


def _as_date_numeric(value: Any) -> float:
    """``as.Date(x, origin = '1970-01-01')`` for a number or an ISO string."""
    if isinstance(value, dt.datetime):
        return float((value.date() - _EPOCH).days)
    if isinstance(value, dt.date):
        return float((value - _EPOCH).days)
    if isinstance(value, str):
        parsed = dt.date.fromisoformat(value)
        return float((parsed - _EPOCH).days)
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return float("nan")
    return float(math.trunc(float(value)))


def _posix_seconds(value: Any) -> float:
    if isinstance(value, dt.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=dt.timezone.utc)
        return float(value.timestamp())
    return float(value)


def _as_posix_numeric(value: Any) -> float:
    """``as.POSIXct(x, origin = '1970-01-01')`` for a number of seconds."""
    if isinstance(value, dt.datetime):
        return _posix_seconds(value)
    if isinstance(value, str):
        text = value.replace("T", " ")
        if text.endswith("Z"):
            text = text[:-1]
        parsed = dt.datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return float(parsed.timestamp())
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return float("nan")
    return float(value)
