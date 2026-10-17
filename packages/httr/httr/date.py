"""Parse and print HTTP dates the way httr 1.4.9 does.

The three formats are RFC 1123, RFC 850, and ANSI C asctime. A parsed value is
the GMT instant, in seconds since 1970-01-01. ``http_date`` prints that instant
in the RFC 1123 form.
"""

from __future__ import annotations

import math


_FORMATS = (
    "%a, %d %b %Y %H:%M:%S",
    "%A, %d-%b-%y %H:%M:%S",
    "%a %b %d %H:%M:%S %Y",
)

_WS = frozenset(" \t\n\v\f\r")

_WEEKDAYS = (
    "sunday",
    "saturday",
    "friday",
    "thursday",
    "wednesday",
    "tuesday",
    "monday",
    "sun",
    "sat",
    "fri",
    "thu",
    "wed",
    "tue",
    "mon",
)

_MONTHS = (
    ("september", 9),
    ("november", 11),
    ("december", 12),
    ("february", 2),
    ("january", 1),
    ("october", 10),
    ("august", 8),
    ("march", 3),
    ("april", 4),
    ("june", 6),
    ("july", 7),
    ("may", 5),
    ("sep", 9),
    ("nov", 11),
    ("dec", 12),
    ("feb", 2),
    ("jan", 1),
    ("oct", 10),
    ("aug", 8),
    ("mar", 3),
    ("apr", 4),
    ("jun", 6),
    ("jul", 7),
)

_WDAY_FROM_THURSDAY = ("Thu", "Fri", "Sat", "Sun", "Mon", "Tue", "Wed")
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

_UNSET = object()


class Date:
    """R Date vector. A missing day is None."""

    def __init__(self, days):
        if isinstance(days, (int, float)) and not isinstance(days, bool):
            days = [days]
        stored = []
        for day in days:
            if day is None or (isinstance(day, float) and math.isnan(day)):
                stored.append(None)
            else:
                stored.append(day)
        self.days = stored
        self.classes = ("Date",)

    def __len__(self):
        return len(self.days)


class Character:
    """R character vector. A missing string is None."""

    def __init__(self, values, names=None):
        self.values = list(values)
        self.names = None if names is None else list(names)
        self.classes = ("character",)

    def __len__(self):
        return len(self.values)

    def __iter__(self):
        return iter(self.values)

    def __str__(self):
        if len(self.values) == 1:
            value = self.values[0]
            return "NA" if value is None else value
        return repr(self.values)


class POSIXct:
    """Seconds since 1970-01-01 00:00:00 GMT. A missing instant is None."""

    def __init__(self, seconds, tz="GMT", names=None):
        if isinstance(seconds, (list, tuple)):
            values = list(seconds)
        elif isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
            raise TypeError("POSIXct seconds must be numeric")
        else:
            values = [seconds]
        stored = []
        for value in values:
            if isinstance(value, bool) or (
                value is not None and not isinstance(value, (int, float))
            ):
                raise TypeError("POSIXct seconds must be numeric")
            if value is None:
                stored.append(None)
            else:
                # NaN stays NaN. None is R's NA, and strftime prints them differently.
                stored.append(float(value))
        self.seconds = stored
        self.tz = "" if tz is None else tz
        self.names = None if names is None else list(names)
        self.classes = ("POSIXct", "POSIXt")

    def __len__(self):
        return len(self.seconds)

    def __str__(self):
        shown = [_format_instant(value) for value in self.seconds]
        if len(shown) == 1:
            return shown[0]
        return "[" + ", ".join(shown) + "]"


def parse_http_date(x, failure=_UNSET):
    """Parse RFC 1123, RFC 850, and asctime dates into one POSIXct vector.

    Every element has to match the same format. Otherwise the result is
    ``failure`` repeated ``length(x)`` times. The default failure is a Date NA.
    An empty ``x`` is NULL.
    """
    if failure is _UNSET:
        failure = Date([None])
    items, names = _as_character(x)
    if items is None:
        return None
    for fmt in _FORMATS:
        parsed = [_parse_one(item, fmt) for item in items]
        if all(value is not None for value in parsed):
            return POSIXct(parsed, tz="GMT", names=names)
    return _rep(failure, len(items))


def http_date(x):
    """Format a POSIXt vector as RFC 1123 in GMT.

    Fractional seconds are floored. NULL stays NULL. Anything that is not
    POSIXt raises the same condition as R's ``stopifnot``.
    """
    if x is None:
        return None
    if not _is_posix(x):
        raise ValueError('inherits(x, "POSIXt") is not TRUE')
    return Character([_format_http(value) for value in x.seconds], x.names)


def _as_character(x):
    if x is None:
        return None, None
    if isinstance(x, str):
        return [x], None
    if isinstance(x, (bool, int, float)):
        return [_coerce_element(x)], None
    if isinstance(x, (list, tuple)):
        if len(x) == 0:
            return None, None
        names = getattr(x, "names", None)
        if names is not None and len(names) != len(x):
            names = None
        return [_coerce_element(value) for value in x], names
    raise TypeError("x must be a character vector")


def _coerce_element(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if math.isinf(value):
            return "Inf" if value > 0 else "-Inf"
        return format(value, ".15g")
    raise TypeError("x must be a character vector")


def _rep(failure, times):
    if failure is None:
        return None
    if isinstance(failure, Date):
        return Date(list(failure.days) * times)
    if isinstance(failure, Character):
        return Character(list(failure.values) * times)
    if isinstance(failure, str):
        return Character([failure] * times)
    if isinstance(failure, bool):
        return [failure] * times
    if isinstance(failure, (int, float)):
        if isinstance(failure, float) and math.isnan(failure):
            return [None] * times
        return [failure] * times
    if isinstance(failure, (list, tuple)):
        return list(failure) * times
    raise TypeError("failure cannot be repeated")


def _is_posix(value):
    classes = getattr(value, "classes", None)
    if not classes or "POSIXt" not in classes:
        return False
    return hasattr(value, "seconds")


def _parse_one(text, fmt):
    if text is None:
        return None
    i = 0
    size = len(text)
    j = 0
    limit = len(fmt)
    year = month = day = hour = minute = second = None
    while j < limit:
        if fmt[j] in _WS:
            while i < size and text[i] in _WS:
                i += 1
            while j < limit and fmt[j] in _WS:
                j += 1
            continue
        if fmt[j] == "%":
            spec = fmt[j + 1]
            j += 2
            if spec in ("a", "A"):
                end = _match_weekday(text, i)
                if end is None:
                    return None
                i = end
            elif spec in ("b", "B"):
                found = _match_month(text, i)
                if found is None:
                    return None
                month, i = found
            elif spec in ("d", "e", "H", "M", "S", "Y", "y"):
                width = 4 if spec == "Y" else 2
                found = _read_int(text, i, width)
                if found is None:
                    return None
                number, i = found
                if spec in ("d", "e"):
                    day = number
                elif spec == "H":
                    hour = number
                elif spec == "M":
                    minute = number
                elif spec == "S":
                    second = number
                elif spec == "Y":
                    year = number
                else:
                    # POSIX %y: 00-68 are 2000-2068 and 69-99 are 1969-1999.
                    year = number + (2000 if number <= 68 else 1900)
            else:
                return None
            continue
        if i >= size or text[i] != fmt[j]:
            return None
        i += 1
        j += 1
    if None in (year, month, day, hour, minute, second):
        return None
    return _to_instant(year, month, day, hour, minute, second)


def _match_weekday(text, start):
    for name in _WEEKDAYS:
        end = start + len(name)
        if end <= len(text) and text[start:end].lower() == name:
            return end
    return None


def _match_month(text, start):
    for name, number in _MONTHS:
        end = start + len(name)
        if end <= len(text) and text[start:end].lower() == name:
            return number, end
    return None


def _read_int(text, start, width):
    i = start
    size = len(text)
    while i < size and text[i] == " ":
        i += 1
    begin = i
    while i < size and text[i].isdigit() and i - begin < width:
        i += 1
    if i == begin:
        return None
    return int(text[begin:i]), i


def _leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _month_days(year, month):
    if month == 2:
        return 29 if _leap(year) else 28
    if month in (4, 6, 9, 11):
        return 30
    if 1 <= month <= 12:
        return 31
    return 0


def _to_instant(year, month, day, hour, minute, second):
    if not 1 <= month <= 12:
        return None
    if not 1 <= day <= _month_days(year, month):
        return None
    # 24:00:00 is the next midnight. Second 60 rolls into the next minute.
    if not (0 <= minute <= 59 and 0 <= second <= 60 and 0 <= hour <= 24):
        return None
    if second == 60:
        second = 0
        minute += 1
    if minute == 60:
        minute = 0
        hour += 1
    if hour >= 24:
        if hour != 24 or minute != 0 or second != 0:
            return None
        hour = 0
        day += 1
        if day > _month_days(year, month):
            day = 1
            month += 1
            if month == 13:
                month = 1
                year += 1
    days = _days_from_civil(year, month, day)
    return days * 86400 + hour * 3600 + minute * 60 + second


def _days_from_civil(year, month, day):
    """Proleptic Gregorian days since 1970-01-01. Year 0 is the year before 1."""
    year -= month <= 2
    era = (year if year >= 0 else year - 399) // 400
    yoe = year - era * 400
    doy = (153 * (month + (-3 if month > 2 else 9)) + 2) // 5 + day - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468


def _civil_from_days(z):
    z += 719468
    era = (z if z >= 0 else z - 146096) // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    year = yoe + era * 400
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    day = doy - (153 * mp + 2) // 5 + 1
    month = mp + 3 if mp < 10 else mp - 9
    year += month <= 2
    return year, month, day


def _format_http(value):
    if value is None:
        return None
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    whole = math.floor(value)
    days, second_of_day = divmod(int(whole), 86400)
    year, month, day = _civil_from_days(days)
    hour, minute_second = divmod(second_of_day, 3600)
    minute, second = divmod(minute_second, 60)
    weekday = _WDAY_FROM_THURSDAY[days % 7]
    # R's %Y is not zero-padded, so year 999 is "999" and year 0 is "0".
    return (
        f"{weekday}, {day:02d} {_MONTH_ABBR[month - 1]} {year} "
        f"{hour:02d}:{minute:02d}:{second:02d} GMT"
    )


def _format_instant(value):
    if value is None:
        return "NA"
    if isinstance(value, float) and math.isnan(value):
        return "NA"
    if isinstance(value, float) and math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    whole = math.floor(value)
    days, second_of_day = divmod(int(whole), 86400)
    year, month, day = _civil_from_days(days)
    hour, minute_second = divmod(second_of_day, 3600)
    minute, second = divmod(minute_second, 60)
    if hour == 0 and minute == 0 and second == 0 and float(value) == whole:
        return f"{year}-{month:02d}-{day:02d} GMT"
    return f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d} GMT"
