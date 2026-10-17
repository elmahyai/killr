"""Convert dates to ratetable internal form (survival::ratetableDate)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import numpy as np

_EPOCH_ORDINAL = date(1970, 1, 1).toordinal()
_DAYS_1960_TO_1970 = 3653.0


class RtableDate:
    """Numeric day vector tagged like R's ``rtabledate`` class."""

    __slots__ = ("values",)
    class_ = "rtabledate"

    def __init__(self, values: Any) -> None:
        self.values = np.asarray(values, dtype=float).reshape(-1)


def _rtfun(x: Any) -> RtableDate:
    return RtableDate(x)


def _days_since_1970(value: date | datetime) -> float:
    if isinstance(value, datetime):
        value = value.date()
    return float(value.toordinal() - _EPOCH_ORDINAL)


def _origin_date(origin: Any) -> date:
    if isinstance(origin, dict):
        year = origin["year"]
        month = origin["month"]
        day = origin["day"]
    else:
        year = origin.year
        month = origin.month
        day = origin.day
    return date(int(year), int(month), int(day))


def _class_label(x: Any) -> str | None:
    klass = getattr(x, "class_", None)
    if klass is None:
        return None
    if isinstance(klass, str):
        return klass.split(".")[0]
    if isinstance(klass, (list, tuple)) and klass:
        first = klass[0]
        return str(first).split(".")[0] if isinstance(first, str) else str(first)
    return None


def _numeric_values(x: Any) -> np.ndarray:
    if isinstance(x, np.ndarray):
        return np.asarray(x, dtype=float).reshape(-1)
    if hasattr(x, "values") and isinstance(getattr(x, "values"), np.ndarray):
        return np.asarray(x.values, dtype=float).reshape(-1)
    return np.asarray(x, dtype=float).reshape(-1)


def ratetableDate(x: Any) -> Any:
    """Map assorted date representations to ratetable day numerics."""
    if isinstance(x, RtableDate):
        return x

    label = _class_label(x)
    if label == "rtabledate":
        return x

    if label == "date":
        return _rtfun(_numeric_values(x) - _DAYS_1960_TO_1970)

    if label in ("chron", "dates"):
        origin = getattr(x, "origin", None)
        if origin is None:
            raise ValueError("chron object must have an origin attribute")
        base = _days_since_1970(_origin_date(origin))
        return _rtfun(base + _numeric_values(x))

    if isinstance(x, date) and not isinstance(x, datetime):
        return _rtfun(_days_since_1970(x))

    if isinstance(x, datetime):
        return _rtfun(_days_since_1970(x))

    if label in ("Date", "POSIXt", "POSIXct", "POSIXlt"):
        if isinstance(x, (list, tuple)):
            items = x
        elif isinstance(x, np.ndarray):
            items = x.tolist()
        else:
            items = [_numeric_values(x)]
        out: list[float] = []
        for item in items:
            if isinstance(item, datetime):
                out.append(_days_since_1970(item))
            elif isinstance(item, date):
                out.append(_days_since_1970(item))
            else:
                out.append(float(item))
        return _rtfun(out)

    if isinstance(x, np.ndarray):
        if x.dtype.kind == "M":
            days = (
                x.astype("datetime64[D]").astype(np.int64)
                - np.datetime64("1970-01-01", "D").astype(np.int64)
            ).astype(float)
            return _rtfun(days)
        if np.issubdtype(x.dtype, np.integer):
            return _rtfun(x.astype(float) - _DAYS_1960_TO_1970)
        return x

    if isinstance(x, (list, tuple)):
        if not x:
            return x
        first = x[0]
        if isinstance(first, (date, datetime)):
            return _rtfun([_days_since_1970(v) for v in x])
        if isinstance(first, (bool, np.bool_)):
            return np.asarray(x, dtype=float)
        if isinstance(first, (int, np.integer)):
            return _rtfun(np.asarray(x, dtype=float) - _DAYS_1960_TO_1970)
        return np.asarray(x, dtype=float)

    if isinstance(x, (bool, np.bool_)):
        return float(x)

    if isinstance(x, (int, np.integer)) and not isinstance(x, (bool, np.bool_)):
        return _rtfun(float(x) - _DAYS_1960_TO_1970)

    if isinstance(x, (float, np.floating)):
        return float(x)

    return x
