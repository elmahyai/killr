"""zoo's as.Date: a default origin for numbers, and dates from a ts.

The numeric method is the reason this generic exists. A plain number is days
from 1970-01-01. The origin string "0000-00-00" is the day before 1 January
of year 0.
"""

from __future__ import annotations

import math
import re
from typing import Any

import numpy as np

# R's NA_real_: the quiet NaN whose low 32 bits are 1954.
R_NA_BITS = np.uint64(0x7FF80000000007A2)
R_NA = np.array([R_NA_BITS], dtype=np.uint64).view(np.float64)[0]

_DATE_ERROR = "character string is not in a standard unambiguous format"
_CONVERT_ERROR = "do not know how to convert 'x' to class \u201cDate\u201d"
_TS_ERROR = "unable to convert ts time to Date class"

_MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _div_trunc(a: int, b: int) -> int:
    """C integer division, toward zero. Python // floors."""
    quot, rem = divmod(int(a), int(b))
    if rem and ((int(a) < 0) != (int(b) < 0)):
        quot += 1
    return quot


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def days_from_civil(year: int, month: int, day: int) -> int:
    """Proleptic Gregorian days since 1970-01-01, with astronomical year 0."""
    year -= 1 if month <= 2 else 0
    era = _div_trunc(year if year >= 0 else year - 399, 400)
    yoe = year - era * 400
    doy = (153 * (month - 3 if month > 2 else month + 9) + 2) // 5 + day - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468


def civil_from_days(z: int) -> tuple[int, int, int]:
    z = int(z) + 719468
    era = _div_trunc(z if z >= 0 else z - 146096, 146097)
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    year = yoe + era * 400
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    day = doy - (153 * mp + 2) // 5 + 1
    month = mp + 3 if mp < 10 else mp - 9
    if month <= 2:
        year += 1
    return int(year), int(month), int(day)


def is_r_na(x: Any) -> np.ndarray:
    arr = np.array(x, dtype=np.float64, copy=True, ndmin=1)
    bits = arr.view(np.uint64)
    return (bits == R_NA_BITS).reshape(arr.shape)


def na_bit(x: Any) -> bool:
    flags = is_r_na(x).reshape(-1)
    return bool(flags.size and flags[0])


def _month_length(year: int, month: int) -> int:
    if month == 2 and _is_leap(year):
        return 29
    if not 1 <= month <= 12:
        return 0
    return _MONTH_DAYS[month - 1]


def _valid_ymd(year: int, month: int, day: int) -> bool:
    if not 1 <= month <= 12:
        return False
    return 1 <= day <= _month_length(year, month)


class RDate(np.ndarray):
    """Days since 1970-01-01, the storage of an R Date. Fractions are kept."""

    def __new__(cls, days: Any) -> RDate:
        arr = np.array(days, dtype=np.float64, copy=True, ndmin=1)
        return arr.view(cls)

    def __array_finalize__(self, obj: Any) -> None:
        return None


def format_date(day: Any) -> str:
    value = float(np.asarray(day, dtype=np.float64).reshape(-1)[0])
    if na_bit(value):
        return "NA"
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    year, month, day_of = civil_from_days(math.trunc(value))
    return f"{year}-{month:02d}-{day_of:02d}"


def format_dates(days: Any) -> list[str]:
    arr = np.asarray(days, dtype=np.float64).reshape(-1)
    return [format_date(value) for value in arr]


def _parse_iso(text: str) -> int:
    text = text.strip()
    # paste() of a negative year is "-1-1-1", which base as.Date rejects.
    if text.startswith("-"):
        raise ValueError(_DATE_ERROR)
    matched = re.fullmatch(r"(\d+)[-/](\d+)[-/](\d+)", text)
    if matched is None:
        raise ValueError(_DATE_ERROR)
    year = int(matched.group(1))
    month = int(matched.group(2))
    day = int(matched.group(3))
    if not _valid_ymd(year, month, day):
        raise ValueError(_DATE_ERROR)
    return days_from_civil(year, month, day)


def _parse_format(text: str, fmt: str) -> int:
    """A small strptime for the pieces as.Date.numeric forwards."""
    regex: list[str] = []
    order: list[str] = []
    i = 0
    while i < len(fmt):
        if fmt[i] == "%" and i + 1 < len(fmt):
            code = fmt[i : i + 2]
            group = {"%Y": r"(-?\d+)", "%y": r"(\d+)", "%m": r"(\d+)", "%d": r"(\d+)"}.get(code)
            if code == "%%":
                regex.append("%")
            elif group is None:
                raise ValueError(_DATE_ERROR)
            else:
                regex.append(group)
                order.append(code)
            i += 2
        else:
            regex.append(re.escape(fmt[i]))
            i += 1
    if not order:
        raise ValueError(_DATE_ERROR)
    matched = re.fullmatch("".join(regex), text.strip())
    if matched is None:
        raise ValueError(_DATE_ERROR)
    parts = {code: int(value) for code, value in zip(order, matched.groups())}
    year = parts.get("%Y")
    if year is None and "%y" in parts:
        yy = parts["%y"]
        year = 1900 + yy if yy >= 69 else 2000 + yy
    month = parts.get("%m", 1)
    day = parts.get("%d", 1)
    if year is None or not _valid_ymd(int(year), month, day):
        raise ValueError(_DATE_ERROR)
    return days_from_civil(int(year), month, day)


def parse_date(text: str, fmt: str | None = None) -> int:
    if fmt:
        return _parse_format(text, fmt)
    return _parse_iso(text)


def _is_ts(x: Any) -> bool:
    return type(x).__name__ == "Ts" or getattr(x, "r_class", None) == "ts"


def _is_plain_numeric(x: Any) -> bool:
    if _is_ts(x) or isinstance(x, (str, bytes, RDate)):
        return False
    if type(x).__name__ in {"Yearmon", "Yearqtr", "Factor", "DataFrame", "Zoo", "Ts"}:
        return False
    if isinstance(x, (bool, np.bool_)):
        return False
    if isinstance(x, (int, float, np.integer, np.floating)):
        return True
    if isinstance(x, np.ndarray) and np.issubdtype(x.dtype, np.number) and not np.issubdtype(x.dtype, np.complexfloating):
        if type(x).__name__ not in {"RDate", "Yearmon", "Yearqtr"}:
            return True
    if isinstance(x, (list, tuple)) and x and not isinstance(x[0], (str, bytes)):
        if all(v is None or isinstance(v, (int, float, np.integer, np.floating, bool)) for v in x):
            # A list of booleans is logical, which is not numeric in R.
            if all(isinstance(v, (bool, np.bool_)) for v in x):
                return False
            return True
    if isinstance(x, (list, tuple)) and len(x) == 0:
        return True
    return False


def _as_float_vector(x: Any) -> np.ndarray:
    if isinstance(x, np.ndarray):
        return np.array(x, dtype=np.float64, copy=True).reshape(-1)
    if isinstance(x, (list, tuple)):
        out = np.empty(len(x), dtype=np.float64)
        for i, value in enumerate(x):
            if value is None:
                out[i] = R_NA
            else:
                out[i] = value
        return out
    if x is None:
        return np.array([R_NA], dtype=np.float64)
    return np.array([x], dtype=np.float64)


def as_date_numeric(x: Any, origin: Any = "1970-01-01", fmt: str | None = None, **_ignored: Any) -> RDate:
    """Days added to origin. A missing origin is 1970-01-01."""
    if origin == "0000-00-00":
        origin_days = float(parse_date("0000-01-01") - 1)
    else:
        origin_date = as_date(origin, fmt=fmt)
        origin_arr = np.asarray(origin_date, dtype=np.float64).reshape(-1)
        if origin_arr.size != 1:
            origin_days = origin_arr
        else:
            origin_days = float(origin_arr[0])
    values = _as_float_vector(x)
    out = np.array(origin_days, dtype=np.float64) + values
    na = is_r_na(values)
    # Keep R's NA payload; a plain NaN stays a plain NaN.
    out = np.array(out, dtype=np.float64, copy=True)
    if np.any(na):
        out[na] = values[na]
    return out.view(RDate)


def _r_char_number(value: Any) -> str:
    number = float(value)
    if math.isnan(number):
        return "NA"
    if math.isinf(number):
        return "Inf" if number > 0 else "-Inf"
    if number == math.trunc(number) and abs(number) < 1e16:
        return str(int(math.trunc(number)))
    return format(number, ".15g")


def as_date_ts(x: Any, offset: float = 0, **_ignored: Any) -> RDate:
    """Annual, quarterly, or monthly ts times as the first of the month."""
    if not _is_ts(x):
        raise TypeError("as.Date.ts expects a ts")
    from zoo.as_zoo import ts_cycle, ts_time

    time_x = np.asarray(ts_time(x), dtype=np.float64) + float(offset)
    frequency = float(x.frequency)
    if frequency == 1:
        texts = [f"{_r_char_number(t)}-1-1" for t in time_x]
    elif frequency == 4:
        years = np.floor(time_x + 0.001)
        cycle = ts_cycle(x)
        months = 3 * (cycle - 1) + 1
        texts = [
            f"{_r_char_number(year)}-{_r_char_number(month)}-1"
            for year, month in zip(years, months)
        ]
    elif frequency == 12:
        years = np.floor(time_x + 0.001)
        cycle = ts_cycle(x)
        texts = [
            f"{_r_char_number(year)}-{_r_char_number(month)}-1"
            for year, month in zip(years, cycle)
        ]
    else:
        raise ValueError(_TS_ERROR)
    return as_date(texts)


def _as_date_character(x: Any, fmt: str | None = None) -> RDate:
    if isinstance(x, str):
        texts = [x]
    else:
        texts = [None if value is None else str(value) for value in x]
    days = []
    for text in texts:
        if text is None or text == "NA":
            days.append(R_NA)
        else:
            days.append(parse_date(text, fmt))
    return RDate(days)


def as_date(x: Any, *args: Any, **kwargs: Any) -> RDate:
    """Dispatch zoo's as.Date. Plain numbers use the numeric method."""
    fmt = kwargs.pop("format", None)
    if fmt is not None and "fmt" not in kwargs:
        kwargs["fmt"] = fmt
    if args:
        if _is_plain_numeric(x):
            if "origin" not in kwargs:
                kwargs["origin"] = args[0]
                args = args[1:]
        elif _is_ts(x):
            if "offset" not in kwargs:
                kwargs["offset"] = args[0]
                args = args[1:]
    if args:
        raise TypeError("unused arguments to as.Date")
    if isinstance(x, RDate):
        return RDate(np.asarray(x, dtype=np.float64))
    if _is_plain_numeric(x):
        origin = kwargs.pop("origin", "1970-01-01")
        return as_date_numeric(x, origin=origin, **kwargs)
    if _is_ts(x):
        offset = kwargs.pop("offset", 0)
        return as_date_ts(x, offset=offset)
    if isinstance(x, str) or (
        isinstance(x, (list, tuple)) and (len(x) == 0 or isinstance(x[0], str))
    ):
        return _as_date_character(x, kwargs.get("fmt"))
    if type(x).__name__ in {"Yearmon", "Yearqtr"} or getattr(x, "r_class", None) in {
        "yearmon",
        "yearqtr",
    }:
        raise TypeError(
            f"as.Date method for class '{type(x).__name__}' is not available"
        )
    # Ordered factors carry class ordered, factor. Base converts via the labels.
    if getattr(x, "r_mode", None) == "factor":
        labels = []
        levels = list(getattr(x, "levels", ()))
        for code in np.asarray(x).reshape(-1):
            if int(code) == -2147483648:
                labels.append(None)
            else:
                labels.append(levels[int(code) - 1])
        return _as_date_character(labels, kwargs.get("fmt"))
    raise ValueError(_CONVERT_ERROR)
