"""IDate and ITime. The calendar parts are the datatable crate, from src/idatetime.c."""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta

import datatable_core

from datatable._util import NA_INTEGER, DataTableError, as_sequence, is_na
from datatable.frame import DataTable

_EPOCH = date(1970, 1, 1)
_TIME_FORMATS = (
    "%H:%M:%S",
    "%H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d",
)


class ITime:
    """Seconds since midnight. A negative value is wrapped into the day."""

    def __init__(self, seconds):
        self.seconds = list(seconds)

    def __iter__(self):
        return iter(self.seconds)


def _day_number(value: date) -> int:
    return (value - _EPOCH).days


def _parse_date(text: str) -> date | None:
    if text == "":
        return None
    head = text.split(" ", 1)[0].replace("/", "-")
    try:
        return date.fromisoformat(head)
    except ValueError as exc:
        raise DataTableError(f"character string is not in a standard unambiguous format: {text}") from exc


def as_idate(x, origin="1970-01-01"):
    """Days since 1970-01-01, or since origin when x is numeric."""
    values = as_sequence(x)
    if isinstance(x, str) or any(isinstance(item, str) for item in values):
        out = []
        for item in values:
            if is_na(item) or item == "":
                out.append(None)
            elif isinstance(item, str):
                parsed = _parse_date(item)
                out.append(None if parsed is None else _day_number(parsed))
            elif isinstance(item, (int, float)) and not isinstance(item, bool):
                out.append(int(item))
            else:
                raise DataTableError("as.IDate cannot convert this value")
        return out
    base = 0
    if origin != "1970-01-01":
        base = _day_number(_parse_date(str(origin)))
    out = []
    for item in values:
        if is_na(item):
            out.append(None)
        else:
            out.append(base + int(item))
    return out


def _parse_time(text: str) -> int | None:
    if text == "":
        return None
    cleaned = text
    if "." in text:
        cleaned = text.split(".", 1)[0]
    for fmt in _TIME_FORMATS:
        try:
            parsed = datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
        return parsed.hour * 3600 + parsed.minute * 60 + parsed.second
    raise DataTableError(f"character string is not in a standard unambiguous format: {text}")


def as_itime(x, ms="truncate"):
    """Seconds since midnight, wrapped into one day."""
    if ms not in ("truncate", "nearest", "ceil"):
        raise DataTableError("Valid options for ms are 'truncate', 'nearest', and 'ceil'.")
    values = as_sequence(x)
    seconds = []
    for item in values:
        if is_na(item) or item == "":
            seconds.append(None)
            continue
        if isinstance(item, str):
            seconds.append(_parse_time(item))
            continue
        number = float(item)
        if ms == "nearest":
            number = int(round(number))
        elif ms == "ceil":
            number = int(math.ceil(number))
        else:
            number = int(number)
        seconds.append(number % 86400)
    return ITime(seconds)


def _parts(x, part: str):
    days = as_idate(x)
    coded = [NA_INTEGER if item is None else int(item) for item in days]
    raw = datatable_core.convert_date_py(coded, part)
    out = []
    for item in raw:
        if item != item:
            out.append(None)
        elif part in ("yearmon", "yearqtr"):
            out.append(float(item))
        else:
            out.append(int(item))
    return out


def year(x):
    return _parts(x, "year")


def month(x):
    return _parts(x, "month")


def mday(x):
    return _parts(x, "mday")


def yday(x):
    return _parts(x, "yday")


def wday(x):
    return _parts(x, "wday")


def quarter(x):
    return _parts(x, "quarter")


def week(x):
    """Legacy week number: yday %/% 7 + 1."""
    return _parts(x, "week")


def yearmon(x):
    """Year plus a fraction of the month. January is the whole year."""
    return _parts(x, "yearmon")


def yearqtr(x):
    """Year plus a fraction of the quarter."""
    return _parts(x, "yearqtr")


def _as_date(day: int) -> date:
    return _EPOCH + timedelta(days=int(day))


def isoweek(x):
    """ISO week, the same numbering as R's %V."""
    out = []
    for item in as_idate(x):
        out.append(None if item is None else _as_date(item).isocalendar().week)
    return out


def isoyear(x):
    """ISO year, the same numbering as R's %G."""
    out = []
    for item in as_idate(x):
        out.append(None if item is None else _as_date(item).isocalendar().year)
    return out


def _clock(x):
    if isinstance(x, ITime):
        return x.seconds
    if isinstance(x, str) or (isinstance(x, list) and x and isinstance(x[0], str)):
        return as_itime(x).seconds
    return [None if is_na(item) else int(item) % 86400 for item in as_sequence(x)]


def hour(x):
    return [None if item is None else (item // 3600) % 24 for item in _clock(x)]


def minute(x):
    return [None if item is None else (item // 60) % 60 for item in _clock(x)]


def second(x):
    return [None if item is None else item % 60 for item in _clock(x)]


def idatetime(x):
    """A two-column table: idate days and itime seconds."""
    return DataTable([as_idate(x), list(as_itime(x))], ["idate", "itime"])
