"""Monthly yearmon values from zoo.

A yearmon is a numeric vector. January of year y is y, February is y + 1/12,
and so on. ``yearmon`` stores ``floor(12 * x + 0.0001) / 12``.
"""

from __future__ import annotations

import calendar
import datetime as dt
import math
import re
import warnings
from typing import Any

import numpy as np


_MONTH_ABBR = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)
_MONTH_FULL = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
_MONTH_NAMES = tuple(
    (name.lower(), index)
    for index, name in enumerate(_MONTH_FULL, start=1)
) + tuple((name.lower(), index) for index, name in enumerate(_MONTH_ABBR, start=1))
_MONTH_NAMES_LONG_FIRST = tuple(sorted(_MONTH_NAMES, key=lambda item: len(item[0]), reverse=True))

_EXTERNAL = {
    "dates": "chron",
    "mondate": "mondate",
    "timeDate": "timeDate",
    "jul": "tis",
    "ti": "tis",
    "date": "date",
}


def _trunc_div(a: int, b: int) -> int:
    """Integer division toward zero, matching the civil-date algorithm."""
    if a < 0:
        return -((-a) // b)
    return a // b


def days_from_civil(year: int, month: int, day: int) -> int:
    """Days since 1970-01-01 in the proleptic Gregorian calendar."""
    year -= month <= 2
    if year >= 0:
        era = year // 400
    else:
        era = _trunc_div(year - 399, 400)
    yoe = year - era * 400
    doy = (153 * (month + (-3 if month > 2 else 9)) + 2) // 5 + day - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468


def civil_from_days(z: int) -> tuple[int, int, int]:
    """Calendar date for a day count since 1970-01-01."""
    z = int(z) + 719468
    if z >= 0:
        era = z // 146097
    else:
        era = _trunc_div(z - 146096, 146097)
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    year = yoe + era * 400
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    day = doy - (153 * mp + 2) // 5 + 1
    month = mp + (3 if mp < 10 else -9)
    year += month <= 2
    return int(year), int(month), int(day)


def _local_zone() -> dt.tzinfo:
    tz = dt.datetime.now().astimezone().tzinfo
    if tz is None:
        return dt.timezone.utc
    return tz


class RDate:
    """Days since 1970-01-01, the numeric value of an R Date."""

    r_class = "Date"

    def __init__(self, days: Any):
        self.days = np.asarray(days, dtype=np.float64).reshape(-1).copy()

    def __len__(self) -> int:
        return int(self.days.size)

    def __repr__(self) -> str:
        return f"RDate({self.days.tolist()})"

    def __array__(self, dtype: Any = None, copy: bool | None = None) -> np.ndarray:
        if dtype is None:
            return self.days
        return self.days.astype(dtype)


class Yearmon:
    """Numeric vector with class yearmon."""

    r_class = "yearmon"

    def __init__(self, values: Any, names: Any = None):
        self.value = np.asarray(values, dtype=np.float64).reshape(-1).copy()
        if names is None:
            self.names = None
        else:
            named = list(names)
            self.names = named if len(named) == self.value.size else None

    def __len__(self) -> int:
        return int(self.value.size)

    def __repr__(self) -> str:
        return f"yearmon({self.value.tolist()})"

    def __str__(self) -> str:
        if self.value.size == 0:
            return "yearmon of length 0"
        parts = ["NA" if item is None else item for item in format_yearmon(self)]
        return " ".join(parts)

    def __array__(self, dtype: Any = None, copy: bool | None = None) -> np.ndarray:
        if dtype is None:
            return self.value
        return self.value.astype(dtype)

    def __iter__(self):
        for item in self.value:
            yield float(item)

    def __getitem__(self, key: Any) -> Yearmon:
        taken = self.value[key]
        out = Yearmon(np.atleast_1d(taken))
        if self.names is not None and isinstance(key, (int, np.integer)):
            out.names = [self.names[int(key)]]
        return out

    def __setitem__(self, key: Any, value: Any) -> None:
        coerced = as_yearmon(value).value
        self.value[key] = coerced if coerced.size != 1 else coerced[0]

    def __neg__(self) -> np.ndarray:
        return -self.value

    def __pos__(self) -> Any:
        raise TypeError('argument "e2" is missing, with no default')

    def __add__(self, other: Any) -> Yearmon:
        return _ops(other, self, np.add)

    def __radd__(self, other: Any) -> Yearmon:
        return _ops(other, self, np.add)

    def __sub__(self, other: Any) -> Any:
        if isinstance(other, Yearmon):
            left, right = _recycle(self.value, other.value)
            return left - right
        if _foreign_class(other):
            raise TypeError(
                "can only subtract yearmon objects and numbers from yearmon objects"
            )
        left, right = _recycle(self.value, _plain_numeric(other))
        return yearmon(left - right)

    def __rsub__(self, other: Any) -> Any:
        raise TypeError("Can only subtract from yearmon objects")

    def __mul__(self, other: Any) -> Yearmon:
        return _ops(other, self, np.multiply)

    def __rmul__(self, other: Any) -> Yearmon:
        return _ops(other, self, np.multiply)

    def __truediv__(self, other: Any) -> Yearmon:
        return _ops(other, self, np.divide)

    def __rtruediv__(self, other: Any) -> Yearmon:
        return _ops(self, other, np.divide)

    def __floordiv__(self, other: Any) -> Yearmon:
        return _ops(other, self, np.floor_divide)

    def __rfloordiv__(self, other: Any) -> Yearmon:
        return _ops(self, other, np.floor_divide)

    def __mod__(self, other: Any) -> Yearmon:
        return _ops(other, self, np.remainder)

    def __rmod__(self, other: Any) -> Yearmon:
        return _ops(self, other, np.remainder)

    def __pow__(self, other: Any) -> Yearmon:
        return _ops(other, self, np.power)

    def __rpow__(self, other: Any) -> Yearmon:
        return _ops(self, other, np.power)

    def __eq__(self, other: Any) -> np.ndarray:
        return _compare(self, other, lambda a, b: a == b)

    def __ne__(self, other: Any) -> np.ndarray:
        return _compare(self, other, lambda a, b: a != b)

    def __lt__(self, other: Any) -> np.ndarray:
        return _compare(self, other, lambda a, b: a < b)

    def __le__(self, other: Any) -> np.ndarray:
        return _compare(self, other, lambda a, b: a <= b)

    def __gt__(self, other: Any) -> np.ndarray:
        return _compare(self, other, lambda a, b: a > b)

    def __ge__(self, other: Any) -> np.ndarray:
        return _compare(self, other, lambda a, b: a >= b)

    def __and__(self, other: Any) -> np.ndarray:
        return _logic(self, other, "and")

    def __rand__(self, other: Any) -> np.ndarray:
        return _logic(self, other, "and")

    def __or__(self, other: Any) -> np.ndarray:
        return _logic(self, other, "or")

    def __ror__(self, other: Any) -> np.ndarray:
        return _logic(self, other, "or")

    __hash__ = None


def _is_yearqtr(x: Any) -> bool:
    return getattr(x, "r_class", None) == "yearqtr"


def _foreign_class(x: Any) -> bool:
    if isinstance(x, (str, bytes, RDate, dt.date, dt.datetime)):
        return True
    if _is_yearqtr(x):
        return True
    kind = getattr(x, "r_class", None)
    return kind not in (None, "yearmon")


def _reject_external(x: Any, generic: str) -> None:
    kind = getattr(x, "r_class", None)
    if kind in _EXTERNAL:
        package = _EXTERNAL[kind]
        raise TypeError(
            f"{generic}.{kind} needs the {package} package, which is not translated"
        )


def _external_error(generic: str, kind: str) -> TypeError:
    package = _EXTERNAL[kind]
    return TypeError(f"{generic}.{kind} needs the {package} package, which is not translated")


def as_yearmon_dates(x: Any = None, *args: Any, **kwargs: Any) -> Any:
    raise _external_error("as.yearmon", "dates")


def as_yearmon_mondate(x: Any = None, *args: Any, **kwargs: Any) -> Any:
    raise _external_error("as.yearmon", "mondate")


def as_yearmon_timeDate(x: Any = None, *args: Any, **kwargs: Any) -> Any:
    raise _external_error("as.yearmon", "timeDate")


def as_yearmon_jul(x: Any = None, *args: Any, **kwargs: Any) -> Any:
    raise _external_error("as.yearmon", "jul")


def as_yearmon_ti(x: Any = None, *args: Any, **kwargs: Any) -> Any:
    raise _external_error("as.yearmon", "ti")


def as_yearmon_date_package(x: Any = None, *args: Any, **kwargs: Any) -> Any:
    raise _external_error("as.yearmon", "date")


def _as_1d(x: Any) -> np.ndarray:
    if isinstance(x, Yearmon):
        return x.value.copy()
    if _is_yearqtr(x):
        return np.asarray(x.value, dtype=np.float64).reshape(-1).copy()
    if isinstance(x, RDate):
        return x.days.copy()
    return np.asarray(x, dtype=np.float64).reshape(-1)


def _plain_numeric(x: Any) -> np.ndarray:
    if isinstance(x, (list, tuple)):
        return np.asarray([np.nan if item is None else item for item in x], dtype=np.float64).reshape(-1)
    return np.asarray(x, dtype=np.float64).reshape(-1)


def _recycle(left: np.ndarray, right: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    left = np.asarray(left, dtype=np.float64).reshape(-1)
    right = np.asarray(right, dtype=np.float64).reshape(-1)
    if left.size == 0 or right.size == 0:
        return left[:0], right[:0]
    n = max(left.size, right.size)
    if n % left.size != 0 or n % right.size != 0:
        warnings.warn(
            "longer object length is not a multiple of shorter object length",
            RuntimeWarning,
            stacklevel=2,
        )
    if left.size != n:
        left = np.resize(left, n)
    if right.size != n:
        right = np.resize(right, n)
    return left, right


def _ops(other: Any, self: Yearmon, op: Any) -> Yearmon:
    left = as_yearmon(self).value
    right = as_yearmon(other).value
    left, right = _recycle(left, right)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return yearmon(op(left, right))


def _compare(self: Yearmon, other: Any, op: Any) -> np.ndarray:
    left, right = _recycle(as_yearmon(self).value, as_yearmon(other).value)
    out = np.empty(left.size, dtype=object)
    for i, (ai, bi) in enumerate(zip(left, right)):
        if np.isnan(ai) or np.isnan(bi):
            out[i] = None
        else:
            out[i] = bool(op(ai, bi))
    return out


def _logic(self: Yearmon, other: Any, how: str) -> np.ndarray:
    left, right = _recycle(as_yearmon(self).value, as_yearmon(other).value)
    out = np.empty(left.size, dtype=object)
    for i, (ai, bi) in enumerate(zip(left, right)):
        a_false = np.isfinite(ai) and ai == 0
        b_false = np.isfinite(bi) and bi == 0
        a_true = np.isfinite(ai) and ai != 0
        b_true = np.isfinite(bi) and bi != 0
        if how == "and":
            if a_false or b_false:
                out[i] = False
            elif np.isnan(ai) or np.isnan(bi):
                out[i] = None
            else:
                out[i] = True
        elif a_true or b_true:
            out[i] = True
        elif a_false and b_false:
            out[i] = False
        else:
            out[i] = None
    return out


def yearmon(x: Any) -> Yearmon:
    """Snap a numeric year fraction onto month boundaries."""
    if isinstance(x, Yearmon):
        arr = x.value
        names = x.names
    else:
        arr = _plain_numeric(x)
        names = None
    snapped = np.floor(12.0 * arr + 0.0001) / 12.0
    return Yearmon(snapped, names)


def _character_items(x: Any) -> list[str | None]:
    if isinstance(x, str):
        return [x]
    if isinstance(x, (list, tuple)):
        items: list[str | None] = []
        for item in x:
            if item is None or (isinstance(item, float) and math.isnan(item)):
                items.append(None)
            else:
                items.append(str(item))
        return items
    arr = np.asarray(x)
    items = []
    for item in arr.reshape(-1):
        if item is None or (isinstance(item, float) and math.isnan(item)):
            items.append(None)
        else:
            text = str(item)
            if text == "nan":
                items.append(None)
            else:
                items.append(text)
    return items


def _is_character(x: Any) -> bool:
    if isinstance(x, str):
        return True
    if isinstance(x, (bytes, Yearmon, RDate, dt.date)):
        return False
    if _is_yearqtr(x):
        return False
    if isinstance(x, np.ndarray) and x.dtype.kind in "SU":
        return True
    if isinstance(x, (list, tuple)) and x:
        return all(isinstance(item, str) or item is None for item in x)
    return False


def _is_integer_input(x: Any) -> bool:
    if isinstance(x, bool) or (isinstance(x, np.generic) and np.issubdtype(type(x), np.bool_)):
        return False
    if isinstance(x, (int, np.integer)):
        return True
    if isinstance(x, np.ndarray) and np.issubdtype(x.dtype, np.integer):
        return True
    if isinstance(x, (list, tuple)) and x:
        return all(isinstance(item, int) and not isinstance(item, bool) for item in x)
    return False


def _skip_ws(text: str, index: int) -> int:
    while index < len(text) and text[index] in " \t":
        index += 1
    return index


def _read_digits(text: str, index: int, max_digits: int) -> tuple[int, int] | None:
    index = _skip_ws(text, index)
    start = index
    while index < len(text) and text[index].isdigit() and index - start < max_digits:
        index += 1
    if index == start:
        return None
    return index, int(text[start:index])


def _parse_date(text: str | None, fmt: str) -> tuple[int, int, int] | None:
    if text is None:
        return None
    index = 0
    year = month = day = None
    cursor = 0
    while cursor < len(fmt):
        if fmt[cursor] == "%" and cursor + 1 < len(fmt):
            code = fmt[cursor + 1]
            cursor += 2
            if code == "%":
                if index >= len(text) or text[index] != "%":
                    return None
                index += 1
            elif code == "d":
                read = _read_digits(text, index, 2)
                if read is None or not 1 <= read[1] <= 31:
                    return None
                index, day = read
            elif code == "m":
                index2 = _skip_ws(text, index)
                read = _read_digits(text, index2, 2)
                if read is None:
                    return None
                index, value = read
                digits = index - index2
                if digits == 2 and (value < 1 or value > 12):
                    return None
                if value < 1 or value > 12:
                    return None
                month = value
            elif code == "Y":
                read = _read_digits(text, index, 4)
                if read is None:
                    return None
                index, year = read
            elif code == "y":
                read = _read_digits(text, index, 2)
                if read is None:
                    return None
                index, yy = read
                if yy <= 68:
                    year = 2000 + yy
                else:
                    year = 1900 + yy
            elif code in "bB":
                index = _skip_ws(text, index)
                lowered = text[index:].lower()
                matched = None
                for name, number in _MONTH_NAMES_LONG_FIRST:
                    if lowered.startswith(name):
                        matched = (index + len(name), number)
                        break
                if matched is None:
                    return None
                index, month = matched
            else:
                return None
        else:
            if index >= len(text) or text[index] != fmt[cursor]:
                return None
            index += 1
            cursor += 1
    if text[index:].strip() != "":
        return None
    if year is None or month is None or day is None:
        return None
    if not _valid_ymd(year, month, day):
        return None
    return year, month, day


def _valid_ymd(year: int, month: int, day: int) -> bool:
    if month < 1 or month > 12 or day < 1:
        return False
    if month == 2:
        leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
        limit = 29 if leap else 28
    else:
        limit = calendar.mdays[month]
    return day <= limit


def _short_format(fmt: str) -> bool:
    if re.search(r"%[mbByY%]", fmt) is None:
        return False
    stripped = re.sub(r"%[mbByY%]", "", fmt)
    return re.search(r"%", stripped) is None


def as_yearmon_character(x: Any, format: str = "", *args: Any, **kwargs: Any) -> Yearmon:
    items = _character_items(x)
    present = [item for item in items if item is not None]
    if not present:
        return Yearmon(np.full(len(items), np.nan))
    if format == "":
        counts = []
        for item in items:
            if item is None:
                continue
            counts.append(item.count("-"))
        if len(set(counts)) != 1:
            raise ValueError("yearmon variable can only have one format")
        dashes = counts[0]
        if dashes == 0:
            format = "%B %Y"
        elif dashes == 1:
            format = "%Y-%m"
        else:
            format = "%Y-%m-%d"
    short = _short_format(format)
    values = np.empty(len(items), dtype=np.float64)
    for i, item in enumerate(items):
        if item is None:
            values[i] = np.nan
            continue
        if short:
            parsed = _parse_date("01-" + item, "%d-" + format)
        else:
            parsed = _parse_date(item, format)
        if parsed is None:
            values[i] = np.nan
        else:
            year, month, _day = parsed
            values[i] = yearmon(year + (month - 1) / 12.0).value[0]
    return Yearmon(values)


def as_yearmon_integer(x: Any, *args: Any, **kwargs: Any) -> Yearmon:
    """Integer coercion keeps the numeric value and does not snap months."""
    return Yearmon(_plain_numeric(x))


def _from_year_month(year: int, month: int) -> Yearmon:
    """month is 1-based."""
    return yearmon(float(year) + (month - 1) / 12.0)


def as_yearmon_Date(x: Any, *args: Any, **kwargs: Any) -> Yearmon:
    if isinstance(x, RDate):
        days = x.days
    elif isinstance(x, dt.date) and not isinstance(x, dt.datetime):
        days = np.array([days_from_civil(x.year, x.month, x.day)], dtype=np.float64)
    elif isinstance(x, np.ndarray) and np.issubdtype(x.dtype, np.datetime64):
        days = x.astype("datetime64[D]").astype(np.int64).astype(np.float64).reshape(-1)
    elif isinstance(x, (list, tuple)):
        nums = []
        for item in x:
            if item is None:
                nums.append(np.nan)
            elif isinstance(item, RDate):
                nums.extend(item.days.tolist())
            elif isinstance(item, dt.datetime):
                raise TypeError("POSIXt dates belong in as.yearmon.POSIXt")
            elif isinstance(item, dt.date):
                nums.append(float(days_from_civil(item.year, item.month, item.day)))
            else:
                nums.append(float(item))
        days = np.asarray(nums, dtype=np.float64)
    else:
        days = _plain_numeric(x)
    out = np.empty(days.size, dtype=np.float64)
    for i, day in enumerate(days):
        if np.isnan(day):
            out[i] = np.nan
            continue
        year, month, _day = civil_from_days(math.trunc(float(day)))
        out[i] = yearmon(1900.0 + (year - 1900) + (month - 1) / 12.0).value[0]
    return Yearmon(out)


def as_yearmon_POSIXt(x: Any, *args: Any, **kwargs: Any) -> Yearmon:
    if isinstance(x, dt.datetime):
        stamps = [x]
    elif isinstance(x, (list, tuple)):
        stamps = list(x)
    else:
        stamps = [x]
    out = np.empty(len(stamps), dtype=np.float64)
    for i, item in enumerate(stamps):
        if item is None or (isinstance(item, float) and math.isnan(item)):
            out[i] = np.nan
            continue
        if isinstance(item, dt.datetime):
            stamp = item
        else:
            raise TypeError("as.yearmon.POSIXt expects a datetime")
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=_local_zone())
        gmt = stamp.astimezone(dt.timezone.utc)
        out[i] = yearmon(1900.0 + (gmt.year - 1900) + (gmt.month - 1) / 12.0).value[0]
    return Yearmon(out)


def _as_numeric_scalar(x: Any) -> float:
    if x is None:
        return np.nan
    if isinstance(x, bool):
        return 1.0 if x else 0.0
    if isinstance(x, (int, float, np.number)):
        return float(x)
    if isinstance(x, Yearmon) or _is_yearqtr(x):
        values = x.value
        if values.size != 1:
            raise ValueError("as.numeric of a length-n object is not a scalar")
        return float(values[0])
    if isinstance(x, str):
        try:
            return float(x)
        except ValueError:
            return np.nan
    return float(x)


def as_numeric(x: Any) -> np.ndarray:
    if isinstance(x, Yearmon) or _is_yearqtr(x):
        return x.value.copy()
    if isinstance(x, RDate):
        return x.days.copy()
    if isinstance(x, bool):
        return np.array([1.0 if x else 0.0])
    if isinstance(x, str):
        number = _as_numeric_scalar(x)
        if math.isnan(number):
            warnings.warn("NAs introduced by coercion", RuntimeWarning, stacklevel=2)
        return np.array([number])
    if isinstance(x, (list, tuple)):
        warned = False
        nums = []
        for item in x:
            if isinstance(item, str):
                try:
                    nums.append(float(item))
                except ValueError:
                    nums.append(np.nan)
                    warned = True
            elif item is None:
                nums.append(np.nan)
            elif isinstance(item, bool):
                nums.append(1.0 if item else 0.0)
            else:
                nums.append(float(item))
        if warned:
            warnings.warn("NAs introduced by coercion", RuntimeWarning, stacklevel=2)
        return np.asarray(nums, dtype=np.float64)
    if isinstance(x, np.ndarray) and x.dtype.kind in "SUO":
        return as_numeric(x.tolist())
    return _plain_numeric(x)


def as_yearmon_default(x: Any, *args: Any, **kwargs: Any) -> Yearmon:
    """Coerce with as.numeric, then with the numeric method."""
    return as_yearmon(as_numeric(x))


def as_yearmon_yearqtr(x: Any, frac: Any = 0, *args: Any, **kwargs: Any) -> Yearmon:
    frac_arr = np.asarray(frac, dtype=np.float64).reshape(-1)
    if frac_arr.size != 1:
        raise ValueError("the condition has length > 1")
    if float(frac_arr[0]) == 0.0:
        return yearmon(np.asarray(x.value, dtype=np.float64))
    from zoo.yearqtr import as_date_yearqtr

    return as_yearmon(as_date_yearqtr(x, frac=float(frac_arr[0])))


def as_yearmon(x: Any = None, *args: Any, **kwargs: Any) -> Yearmon:
    """Dispatch as.yearmon on the class of x."""
    if x is None:
        return Yearmon(np.array([], dtype=np.float64))
    _reject_external(x, "as.yearmon")
    if _is_yearqtr(x):
        frac = kwargs.get("frac", args[0] if args else 0)
        return as_yearmon_yearqtr(x, frac=frac)
    if isinstance(x, Yearmon):
        return as_yearmon_default(x)
    if isinstance(x, dt.datetime) or (
        isinstance(x, (list, tuple)) and x and isinstance(x[0], dt.datetime)
    ):
        return as_yearmon_POSIXt(x)
    if isinstance(x, RDate) or (
        isinstance(x, dt.date) and not isinstance(x, dt.datetime)
    ):
        return as_yearmon_Date(x)
    if isinstance(x, (list, tuple)) and x and isinstance(x[0], dt.date):
        return as_yearmon_Date(x)
    if isinstance(x, np.ndarray) and np.issubdtype(x.dtype, np.datetime64):
        return as_yearmon_Date(x)
    if _is_character(x) or (
        isinstance(x, (list, tuple)) and any(isinstance(item, str) for item in x)
    ):
        format = kwargs.get("format", args[0] if args else "")
        return as_yearmon_character(x, format=format)
    if isinstance(x, bool) or (
        isinstance(x, np.generic) and np.issubdtype(type(x), np.bool_)
    ):
        return as_yearmon_default(x)
    if _is_integer_input(x):
        return as_yearmon_integer(x)
    if isinstance(x, (float, np.floating, np.ndarray, list, tuple, int)):
        return yearmon(x)
    return as_yearmon_default(x)


def sys_yearmon() -> Yearmon:
    """Year and month of the local calendar today."""
    today = dt.date.today()
    return _from_year_month(today.year, today.month)


def _bad_date() -> ValueError:
    return ValueError("character string is not in a standard unambiguous format")


def as_date_from_year_fraction(x: Any, frac: Any = 0, end_offset: int = 32) -> RDate:
    """Date at frac through a yearmon month or a yearqtr quarter."""
    values = np.asarray(x, dtype=np.float64).reshape(-1)
    if values.size == 0 or bool(np.all(np.isnan(values))):
        if values.size == 0:
            return RDate(np.array([], dtype=np.float64))
        return RDate(np.full(values.shape, np.nan))
    year = np.floor(values + 0.001)
    month = np.floor(12.0 * (values - year) + 1.0 + 0.5 + 0.001)
    start = np.full(values.shape, np.nan)
    end = np.full(values.shape, np.nan)
    for i in range(values.size):
        if np.isnan(year[i]):
            continue
        if not np.isfinite(year[i]) or not np.isfinite(month[i]):
            raise _bad_date()
        yi = int(year[i])
        mi = int(month[i])
        if mi < 1 or mi > 12 or yi < 0 or yi > 9999:
            raise _bad_date()
        origin = days_from_civil(yi, mi, 1)
        _yy, _mm, dd = civil_from_days(origin + end_offset)
        start[i] = origin
        end[i] = origin + end_offset - dd
    frac_arr = np.asarray(frac, dtype=np.float64).reshape(-1)
    if frac_arr.size == 0:
        return RDate(np.array([], dtype=np.float64))
    n = max(int(start.size), int(frac_arr.size))
    if start.size and frac_arr.size and (n % start.size != 0 or n % frac_arr.size != 0):
        warnings.warn(
            "longer object length is not a multiple of shorter object length",
            RuntimeWarning,
            stacklevel=2,
        )
    start = np.resize(start, n)
    end = np.resize(end, n)
    frac_arr = np.resize(frac_arr, n)
    result = (1.0 - frac_arr) * start + frac_arr * end
    return RDate(result)


def as_date_yearmon(x: Any, frac: Any = 0, *args: Any, **kwargs: Any) -> RDate:
    """Date frac of the way through each month. 0 is the first day."""
    if isinstance(x, Yearmon):
        values = x.value
    else:
        values = _plain_numeric(x)
    return as_date_from_year_fraction(values, frac=frac, end_offset=32)


def _strftime_date(day: float, fmt: str) -> str | None:
    if not np.isfinite(day):
        return None
    year, month, day_of = civil_from_days(math.trunc(float(day)))
    pieces = {
        "b": _MONTH_ABBR[month - 1],
        "B": _MONTH_FULL[month - 1],
        "m": f"{month:02d}",
        "d": f"{day_of:02d}",
        "Y": str(year),
        "y": f"{year % 100:02d}",
        "%": "%",
    }
    out = []
    cursor = 0
    while cursor < len(fmt):
        if fmt[cursor] == "%" and cursor + 1 < len(fmt):
            code = fmt[cursor + 1]
            cursor += 2
            if code not in pieces:
                raise ValueError(f"unsupported format code %{code}")
            out.append(pieces[code])
        else:
            out.append(fmt[cursor])
            cursor += 1
    return "".join(out)


def format_yearmon(x: Any, format: str = "%b %Y", *args: Any, **kwargs: Any) -> list[str | None]:
    if not isinstance(x, Yearmon):
        x = as_yearmon(x)
    if len(x) == 0:
        return []
    dates = as_date_yearmon(x, frac=0)
    formatted = [_strftime_date(day, format) for day in dates.days]
    return formatted


def as_character_yearmon(x: Any, *args: Any, **kwargs: Any) -> list[str | None]:
    return format_yearmon(x, *args, **kwargs)


def as_numeric_yearmon(x: Any, *args: Any, **kwargs: Any) -> np.ndarray:
    if not isinstance(x, Yearmon):
        x = as_yearmon(x)
    return x.value.copy()


def as_list_yearmon(x: Any, *args: Any, **kwargs: Any) -> list[Yearmon]:
    if not isinstance(x, Yearmon):
        x = as_yearmon(x)
    return [x[i] for i in range(len(x))]


def as_data_frame_yearmon(
    x: Any, row_names: Any = None, optional: bool = False, *args: Any, **kwargs: Any
) -> dict[str, Any]:
    if not isinstance(x, Yearmon):
        x = as_yearmon(x)
    nrows = len(x)
    if row_names is None:
        if nrows == 0:
            row_names = []
        elif x.names is not None and len(x.names) == nrows and len(set(x.names)) == nrows:
            row_names = list(x.names)
        elif optional:
            row_names = [""] * nrows
        else:
            row_names = list(range(1, nrows + 1))
    column = Yearmon(x.value)
    frame: dict[str, Any] = {"row.names": row_names, "yearmon": column}
    if not optional:
        frame["names"] = ["x"]
    return frame


def c_yearmon(*args: Any) -> Yearmon:
    if not args:
        return Yearmon(np.array([], dtype=np.float64))
    parts = [as_numeric(arg) for arg in args]
    return as_yearmon(np.concatenate(parts))


def cycle_yearmon(x: Any, *args: Any, **kwargs: Any) -> np.ndarray:
    values = as_numeric_yearmon(x)
    return np.round(12.0 * np.remainder(values, 1.0)) + 1.0


def is_numeric_yearmon(x: Any) -> bool:
    return False


def mean_yearmon(x: Any, trim: float = 0.0, na_rm: bool = False, *args: Any, **kwargs: Any) -> Yearmon:
    values = as_numeric_yearmon(x)
    if na_rm:
        values = values[~np.isnan(values)]
    if values.size == 0:
        return yearmon(np.array([np.nan]))
    if trim:
        ordered = np.sort(values[~np.isnan(values)] if not na_rm else values)
        # na already removed when na_rm; otherwise mean of a vector containing NA is NA
        if np.any(np.isnan(values)):
            return yearmon(np.array([np.nan]))
        k = int(math.floor(trim * ordered.size))
        if k:
            ordered = ordered[k : ordered.size - k]
        if ordered.size == 0:
            return yearmon(np.array([np.nan]))
        return yearmon(np.array([float(np.mean(ordered))]))
    return yearmon(np.array([float(np.mean(values))]))


def _summary_values(args: tuple[Any, ...], na_rm: bool) -> np.ndarray:
    parts = [as_numeric_yearmon(arg) for arg in args]
    if not parts:
        return np.array([], dtype=np.float64)
    return np.concatenate(parts)


def min_yearmon(*args: Any, na_rm: bool = False) -> Yearmon:
    values = _summary_values(args, na_rm)
    if na_rm:
        values = values[~np.isnan(values)]
    if values.size == 0 or np.any(np.isnan(values)):
        return Yearmon(np.array([np.nan]))
    return Yearmon(np.array([np.min(values)]))


def max_yearmon(*args: Any, na_rm: bool = False) -> Yearmon:
    values = _summary_values(args, na_rm)
    if na_rm:
        values = values[~np.isnan(values)]
    if values.size == 0 or np.any(np.isnan(values)):
        return Yearmon(np.array([np.nan]))
    return Yearmon(np.array([np.max(values)]))


def sum_yearmon(*args: Any, **kwargs: Any) -> Any:
    raise TypeError("sum not defined for yearmon objects")


def prod_yearmon(*args: Any, **kwargs: Any) -> Any:
    raise TypeError("prod not defined for yearmon objects")


def range_yearmon(*args: Any, na_rm: bool = False) -> Yearmon:
    values = _summary_values(args, na_rm)
    if not na_rm and np.any(np.isnan(values)):
        return yearmon(np.array([np.nan, np.nan]))
    if na_rm:
        values = values[~np.isnan(values)]
    if values.size == 0:
        return yearmon(np.array([np.inf, -np.inf]))
    return yearmon(np.array([np.min(values), np.max(values)]))


def unique_yearmon(x: Any, *args: Any, **kwargs: Any) -> Yearmon:
    values = as_numeric_yearmon(x)
    kept: list[float] = []
    seen_nan = False
    for value in values:
        if np.isnan(value):
            if not seen_nan:
                seen_nan = True
                kept.append(np.nan)
            continue
        if any(value == previous for previous in kept if not np.isnan(previous)):
            continue
        kept.append(float(value))
    if not kept:
        return Yearmon(np.array([], dtype=np.float64))
    return as_yearmon(np.asarray(kept, dtype=np.float64))


def xtfrm_yearmon(x: Any) -> np.ndarray:
    return as_numeric_yearmon(x)


def diff_yearmon(x: Any, lag: int = 1, differences: int = 1, *args: Any, **kwargs: Any) -> np.ndarray:
    values = as_numeric_yearmon(x)
    out = values
    for _ in range(int(differences)):
        if out.size <= lag:
            return np.array([], dtype=np.float64)
        out = out[lag:] - out[:-lag]
    return np.asarray(out, dtype=np.float64)


def match_yearmon(x: Any, table: Any, nomatch: Any = None, *args: Any, **kwargs: Any) -> list[Any]:
    left = np.floor(12.0 * as_numeric_yearmon(as_yearmon(x)) + 0.001)
    right = np.floor(12.0 * as_numeric_yearmon(as_yearmon(table)) + 0.001)
    found: list[Any] = []
    for value in left:
        if np.isnan(value):
            found.append(None)
            continue
        index = None
        for j, other in enumerate(right):
            if other == value:
                index = j + 1
                break
        found.append(nomatch if index is None else index)
    return found


def months_yearmon(x: Any, abbreviate: bool = False, *args: Any, **kwargs: Any) -> list[str | None]:
    dates = as_date_yearmon(x if isinstance(x, Yearmon) else as_yearmon(x))
    names = _MONTH_ABBR if abbreviate else _MONTH_FULL
    out: list[str | None] = []
    for day in dates.days:
        if not np.isfinite(day):
            out.append(None)
            continue
        _year, month, _day = civil_from_days(math.trunc(float(day)))
        out.append(names[month - 1])
    return out


def quarters_yearmon(x: Any, abbreviate: bool = False, *args: Any, **kwargs: Any) -> list[str | None]:
    dates = as_date_yearmon(x if isinstance(x, Yearmon) else as_yearmon(x))
    out: list[str | None] = []
    for day in dates.days:
        if not np.isfinite(day):
            out.append(None)
            continue
        _year, month, _day = civil_from_days(math.trunc(float(day)))
        out.append(f"Q{(month - 1) // 3 + 1}")
    return out


def print_yearmon(x: Any) -> str:
    if not isinstance(x, Yearmon):
        x = as_yearmon(x)
    if len(x) == 0:
        return "yearmon of length 0"
    return str(x)


def axis_yearmon(*args: Any, **kwargs: Any) -> Any:
    raise NotImplementedError("axis.yearmon is not translated")


def as_posixct_yearmon(x: Any, tz: str = "", *args: Any, **kwargs: Any) -> np.ndarray:
    """Seconds at midnight of as.Date.yearmon, labeled with tz."""
    dates = as_date_yearmon(x)
    seconds = dates.days * 86400.0
    seconds = np.asarray(seconds, dtype=np.float64)
    if tz in ("", "GMT", "UTC"):
        return seconds
    raise NotImplementedError(f"as.POSIXct.yearmon timezone {tz!r} is not translated")
