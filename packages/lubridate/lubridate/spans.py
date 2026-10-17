"""Periods, durations, and intervals.

A period keeps years, months, days, hours, minutes, and seconds apart.
Adding one to a date uses timechange with ``roll_month="NA"``. A duration
is a count of seconds, with a year taken as 365.25 days. An interval is a
start instant and a signed length in seconds.
"""

import math

import numpy as np

from timechange import time_add
from timechange.civil import Posixct

from .instants import Date, _as_instant, date, day, hour, minute, month, second, year

YEAR_SECONDS = 60 * 60 * 24 * 365.25
MONTH_SECONDS = YEAR_SECONDS / 12
UNIT_SECONDS = {
    "second": 1.0,
    "minute": 60.0,
    "hour": 3600.0,
    "day": 86400.0,
    "week": 604800.0,
    "month": MONTH_SECONDS,
    "year": YEAR_SECONDS,
}
_NAMES = {
    "s": "second", "sec": "second", "secs": "second", "second": "second", "seconds": "second",
    "m": "minute", "min": "minute", "mins": "minute", "minute": "minute", "minutes": "minute",
    "h": "hour", "hr": "hour", "hour": "hour", "hours": "hour",
    "d": "day", "day": "day", "days": "day",
    "w": "week", "week": "week", "weeks": "week",
    "month": "month", "months": "month",
    "y": "year", "year": "year", "years": "year",
}


def _std(name):
    key = str(name).lower().rstrip("s") if str(name).lower() not in _NAMES else str(name).lower()
    if key in _NAMES:
        return _NAMES[key]
    if key + "s" in _NAMES:
        return _NAMES[key + "s"]
    raise ValueError(f"unknown unit {name}")


def _arr(value, n=None):
    if value is None:
        return None
    array = np.atleast_1d(np.asarray(value, dtype=float))
    if n is None:
        return array
    if array.size == 1 and n != 1:
        return np.repeat(array, n)
    return array


class Period:
    def __init__(self, second=0, minute=0, hour=0, day=0, month=0, year=0):
        parts = [np.atleast_1d(np.asarray(v, dtype=float)) for v in (second, minute, hour, day, month, year)]
        n = max(part.size for part in parts)
        self.second, self.minute, self.hour, self.day, self.month, self.year = [_arr(part, n) for part in parts]

    def __len__(self):
        return int(self.second.size)

    def slots(self):
        return np.column_stack([self.year, self.month, self.day, self.hour, self.minute, self.second])

    def __neg__(self):
        return Period(-self.second, -self.minute, -self.hour, -self.day, -self.month, -self.year)

    def __add__(self, other):
        if isinstance(other, Period):
            return Period(
                self.second + other.second, self.minute + other.minute, self.hour + other.hour,
                self.day + other.day, self.month + other.month, self.year + other.year,
            )
        return NotImplemented

    def __mul__(self, other):
        factor = np.asarray(other, dtype=float)
        return Period(
            self.second * factor, self.minute * factor, self.hour * factor,
            self.day * factor, self.month * factor, self.year * factor,
        )

    def __repr__(self):
        return f"Period(year={self.year.tolist()}, month={self.month.tolist()}, day={self.day.tolist()})"


class Duration:
    def __init__(self, seconds):
        self.seconds = np.atleast_1d(np.asarray(seconds, dtype=float))

    def __len__(self):
        return int(self.seconds.size)

    def __add__(self, other):
        if isinstance(other, Duration):
            return Duration(self.seconds + other.seconds)
        return NotImplemented

    def __neg__(self):
        return Duration(-self.seconds)

    def __mul__(self, other):
        return Duration(self.seconds * np.asarray(other, dtype=float))

    def __truediv__(self, other):
        if isinstance(other, Duration):
            return self.seconds / other.seconds
        return Duration(self.seconds / np.asarray(other, dtype=float))

    def __repr__(self):
        return f"Duration({self.seconds.tolist()})"


class Interval:
    def __init__(self, start, span):
        instant = start if isinstance(start, Posixct) else _as_instant(start)
        self.start = instant
        self.span = np.atleast_1d(np.asarray(span, dtype=float))
        self.tz = instant.tz

    def end(self):
        return Posixct(np.asarray(self.start.seconds, dtype=float) + self.span, self.tz)

    def __repr__(self):
        return f"Interval(start={self.start.seconds.tolist()}, span={self.span.tolist()})"


class Difftime:
    def __init__(self, seconds, units="secs"):
        self.seconds = np.atleast_1d(np.asarray(seconds, dtype=float))
        self.units = units


def is_period(x):
    return isinstance(x, Period)


def is_duration(x):
    return isinstance(x, Duration)


def is_interval(x):
    return isinstance(x, Interval)


def is_difftime(x):
    return isinstance(x, Difftime)


def is_timespan(x):
    return isinstance(x, (Period, Duration, Interval, Difftime))


def period(num=None, units="second", **pieces):
    if isinstance(num, str) or (isinstance(num, (list, tuple)) and num and isinstance(num[0], str)):
        return parse_period(num)
    built = _period_from_units(pieces) if pieces else None
    numbered = None
    if num is not None and np.size(num):
        numbered = _period_from_units({_std(units): num})
    if built is None:
        return numbered if numbered is not None else Period()
    if numbered is None:
        return built
    return built + numbered


def _period_from_units(pieces):
    slots = {name: 0.0 for name in ("second", "minute", "hour", "day", "week", "month", "year")}
    for name, value in pieces.items():
        slots[_std(name)] = slots[_std(name)] + np.asarray(value, dtype=float)
    day = slots["day"] + 7 * slots["week"]
    return Period(slots["second"], slots["minute"], slots["hour"], day, slots["month"], slots["year"])


def parse_period(text):
    texts = np.atleast_1d(np.asarray(text, dtype=object))
    rows = []
    for item in texts.reshape(-1):
        rows.append(_one_period(str(item)))
    stacked = np.array(rows, dtype=float)
    return Period(stacked[:, 0], stacked[:, 1], stacked[:, 2], stacked[:, 3], stacked[:, 4], stacked[:, 5])


def _one_period(text):
    """Parse ``2y 3m 4d`` and ISO ``P1Y2M``. Weeks land in the day slot."""
    slots = np.zeros(6)  # second minute hour day month year
    token = ""
    number = ""
    iso_date = True
    body = text.strip()
    if body.startswith("P"):
        body = body[1:]
    for char in body + " ":
        if char == "T":
            iso_date = False
            continue
        if char.isdigit() or char in "+-.":
            if token and number:
                _store_period(slots, number, token, iso_date)
                token, number = "", ""
            number += char
        elif char.isalpha():
            token += char
        elif number and token:
            _store_period(slots, number, token, iso_date)
            token, number = "", ""
    if number and token:
        _store_period(slots, number, token, iso_date)
    return slots


def _store_period(slots, number, token, iso_date):
    value = float(number) if number not in ("", "+", "-") else 1.0
    name = token.lower()
    if name in ("m",) and iso_date and token == "M":
        unit = "month"
    elif name in ("m", "min", "mins", "minute", "minutes"):
        unit = "minute" if token != "M" or not iso_date else "month"
    else:
        unit = _std(name if name != "m" else ("month" if iso_date else "minute"))
    whole = math.copysign(math.floor(abs(value)), value) if unit != "second" else value
    frac = value - whole if unit != "second" else 0.0
    index = {"second": 0, "minute": 1, "hour": 2, "day": 3, "week": 3, "month": 4, "year": 5}[unit]
    if unit == "week":
        slots[3] += whole * 7
    else:
        slots[index] += whole
    if frac:
        slots[0] += frac * UNIT_SECONDS[unit]


def seconds(x=1):
    return period(second=x)


def minutes(x=1):
    return period(minute=x)


def hours(x=1):
    return period(hour=x)


def days(x=1):
    return period(day=x)


def weeks(x=1):
    return period(week=x)


def years(x=1):
    return period(year=x)


def milliseconds(x=1):
    return seconds(np.asarray(x, dtype=float) / 1000)


def microseconds(x=1):
    return seconds(np.asarray(x, dtype=float) / 1_000_000)


def nanoseconds(x=1):
    return seconds(np.asarray(x, dtype=float) / 1e9)


def picoseconds(x=1):
    return seconds(np.asarray(x, dtype=float) / 1e12)


def duration(num=None, units="seconds", **pieces):
    if isinstance(num, str):
        return as_duration(parse_period(num))
    total = 0.0
    if num is not None and np.size(num):
        total = total + np.asarray(num, dtype=float) * UNIT_SECONDS[_std(units)]
    for name, value in pieces.items():
        total = total + np.asarray(value, dtype=float) * UNIT_SECONDS[_std(name)]
    return Duration(total)


def dseconds(x=1):
    return Duration(x)


def dminutes(x=1):
    return Duration(np.asarray(x, dtype=float) * 60)


def dhours(x=1):
    return Duration(np.asarray(x, dtype=float) * 3600)


def ddays(x=1):
    return Duration(np.asarray(x, dtype=float) * 86400)


def dweeks(x=1):
    return Duration(np.asarray(x, dtype=float) * UNIT_SECONDS["week"])


def dmonths(x=1):
    return Duration(np.asarray(x, dtype=float) * MONTH_SECONDS)


def dyears(x=1):
    return Duration(np.asarray(x, dtype=float) * YEAR_SECONDS)


def dmilliseconds(x=1):
    return Duration(np.asarray(x, dtype=float) / 1000)


def dmicroseconds(x=1):
    return Duration(np.asarray(x, dtype=float) / 1_000_000)


def dnanoseconds(x=1):
    return Duration(np.asarray(x, dtype=float) / 1e9)


def dpicoseconds(x=1):
    return Duration(np.asarray(x, dtype=float) / 1e12)


def period_to_seconds(x):
    return (
        x.second + 60 * x.minute + 3600 * x.hour + 86400 * x.day
        + MONTH_SECONDS * x.month + YEAR_SECONDS * x.year
    )


def seconds_to_period(x):
    span = np.atleast_1d(np.asarray(x, dtype=float))
    sign = np.sign(span)
    sign = np.where(sign == 0, 1, sign)
    rest = np.abs(span)
    day = np.floor(rest / 86400)
    rest = rest % 86400
    hour = np.floor(rest / 3600)
    rest = rest % 3600
    minute = np.floor(rest / 60)
    second = rest % 60
    return Period(second * sign, minute * sign, hour * sign, day * sign, 0, 0)


def add_period(instant, per):
    return time_add(
        _as_instant(instant),
        year=per.year, month=per.month, day=per.day,
        hour=per.hour, minute=per.minute, second=per.second,
        roll_month="NA", roll_dst=("NA", "pre"),
    )


def interval(start, end=None, tzone=None):
    if isinstance(start, str) and end is None:
        left, _, right = start.partition("/")
        if right.startswith("P"):
            begin = _stamp(left, tzone or "UTC")
            return Interval(begin, period_to_seconds(parse_period(right)))
        if left.startswith("P"):
            finish = _stamp(right, tzone or "UTC")
            span = -period_to_seconds(parse_period(left))
            return Interval(Posixct(finish.seconds + span, finish.tz), -span)
        begin = _stamp(left, tzone or "UTC")
        finish = _stamp(right, tzone or "UTC")
        return Interval(begin, finish.seconds - begin.seconds)
    start_i = _as_instant(start)
    end_i = _as_instant(end)
    if tzone:
        from .instants import with_tz
        start_i = with_tz(start_i, tzone)
        end_i = with_tz(end_i, tzone)
    span = np.asarray(end_i.seconds, dtype=float) - np.asarray(start_i.seconds, dtype=float)
    return Interval(start_i, span)


def _stamp(text, tz):
    from .parse import ymd_hms
    return ymd_hms(text, tz=tz)


def int_start(interval_):
    return interval_.start


def int_start_set(interval_, value):
    value = _as_instant(value)
    span = (np.asarray(interval_.start.seconds, dtype=float) + interval_.span) - np.asarray(value.seconds, dtype=float)
    return Interval(value, span)


def int_end(interval_):
    return interval_.end()


def int_end_set(interval_, value):
    value = _as_instant(value)
    return Interval(interval_.start, np.asarray(value.seconds, dtype=float) - np.asarray(interval_.start.seconds, dtype=float))


def int_length(interval_):
    return interval_.span


def int_flip(interval_):
    return Interval(interval_.end(), -interval_.span)


def int_standardize(interval_):
    negative = interval_.span < 0
    if not np.any(negative):
        return interval_
    flipped = int_flip(interval_)
    start = np.where(negative, flipped.start.seconds, interval_.start.seconds)
    span = np.where(negative, flipped.span, interval_.span)
    return Interval(Posixct(start, interval_.tz), span)


def int_shift(interval_, by):
    if isinstance(by, Duration):
        moved = Posixct(interval_.start.seconds + by.seconds, interval_.tz)
        return Interval(moved, interval_.span)
    if isinstance(by, Period):
        return interval(add_period(interval_.start, by), add_period(interval_.end(), by))
    raise TypeError("by is not a recognized timespan object")


def int_overlaps(int1, int2):
    a = int_standardize(int1)
    b = int_standardize(int2)
    return (a.start.seconds <= b.start.seconds + b.span) & (b.start.seconds <= a.start.seconds + a.span)


def int_aligns(int1, int2):
    a = int_standardize(int1)
    b = int_standardize(int2)
    return (a.start.seconds == b.start.seconds) | ((a.start.seconds + a.span) == (b.start.seconds + b.span))


def int_diff(times):
    instant = _as_instant(times)
    seconds = np.asarray(instant.seconds, dtype=float)
    return Interval(Posixct(seconds[:-1], instant.tz), np.diff(seconds))


def intersect(x, y):
    a = int_standardize(x)
    b = int_standardize(y)
    starts = np.maximum(a.start.seconds, b.start.seconds)
    ends = np.minimum(a.start.seconds + a.span, b.start.seconds + b.span)
    spans = ends - starts
    empty = ends < starts
    spans = np.where(empty, np.nan, spans)
    starts = np.where(empty, np.nan, starts)
    return Interval(Posixct(starts, x.tz), spans)


def union(x, y):
    a = int_standardize(x)
    b = int_standardize(y)
    starts = np.minimum(a.start.seconds, b.start.seconds)
    ends = np.maximum(a.start.seconds + a.span, b.start.seconds + b.span)
    return Interval(Posixct(starts, x.tz), ends - starts)


def setdiff(x, y):
    a = int_standardize(x)
    b = int_standardize(y)
    starts = np.array(a.start.seconds, dtype=float, copy=True)
    ends = a.start.seconds + a.span
    last = b.start.seconds + b.span
    first = b.start.seconds
    move_start = (last + 1 >= a.start.seconds) & (last + 1 <= a.start.seconds + a.span)
    move_end = (first - 1 >= a.start.seconds) & (first - 1 <= a.start.seconds + a.span)
    starts = np.where(move_start, last, starts)
    ends = np.where(move_end, first, ends)
    return Interval(Posixct(starts, x.tz), ends - starts)


def within(a, b):
    if isinstance(a, Interval):
        left = int_standardize(a)
        right = int_standardize(b)
        start_in = left.start.seconds >= right.start.seconds
        end_in = (left.start.seconds + left.span) <= (right.start.seconds + right.span)
        return start_in & end_in
    instant = _as_instant(a)
    right = int_standardize(b)
    delta = np.asarray(instant.seconds, dtype=float) - right.start.seconds
    return (delta <= right.span) & (delta >= 0)


def as_period(x, unit=None):
    if isinstance(x, str):
        return parse_period(x)
    if isinstance(x, (bool, np.bool_)):
        return as_period(float(x), unit)
    if isinstance(x, Period):
        return _period_in_unit(x, unit)
    if isinstance(x, Duration):
        return _duration_to_period(x)
    if isinstance(x, Interval):
        chosen = "year" if unit is None else _std(unit)
        if chosen == "year":
            return _interval_to_period(x)
        if chosen == "month":
            got = _interval_to_period(x)
            return Period(got.second, got.minute, got.hour, got.day, got.month + 12 * got.year, 0)
        return _seconds_to_unit_period(x.span, chosen)
    if isinstance(x, Difftime):
        return seconds_to_period(x.seconds)
    chosen = "second" if unit is None else _std(unit)
    return period(**{chosen: x})


def _period_in_unit(x, unit):
    if unit is None or _std(unit) == "year":
        return x
    chosen = _std(unit)
    if chosen == "month":
        return Period(x.second, x.minute, x.hour, x.day, x.month + 12 * x.year, 0)
    return _seconds_to_unit_period(period_to_seconds(x), chosen)


def _seconds_to_unit_period(secs, unit):
    secs = np.atleast_1d(np.asarray(secs, dtype=float))
    sign = np.where(secs < 0, -1.0, 1.0)
    rest = np.abs(secs)
    if unit == "second":
        return Period(rest * sign, 0, 0, 0, 0, 0)
    minute = np.floor(rest / 60) if unit == "minute" else np.floor((rest % 3600) / 60)
    second = rest % 60
    if unit == "minute":
        return Period(second * sign, np.floor(rest / 60) * sign, 0, 0, 0, 0)
    hour = np.floor(rest / 3600) if unit == "hour" else np.floor((rest % 86400) / 3600)
    if unit == "hour":
        return Period(second * sign, (np.floor(rest / 60) % 60) * sign, hour * sign, 0, 0, 0)
    day = np.floor(rest / 86400)
    return Period(second * sign, (np.floor((rest % 86400) / 60) % 60) * sign, hour * sign, day * sign, 0, 0)


def _duration_to_period(x):
    rest = np.abs(x.seconds)
    sign = np.where(np.sign(x.seconds) == 0, 1, np.sign(x.seconds))
    year = np.floor(rest / YEAR_SECONDS)
    rest = rest % YEAR_SECONDS
    day = np.floor(rest / 86400)
    rest = rest % 86400
    hour = np.floor(rest / 3600)
    rest = rest % 3600
    minute = np.floor(rest / 60)
    second = rest % 60
    return Period(second * sign, minute * sign, hour * sign, day * sign, 0, year * sign)


_MONTH_LENGTH = np.array([0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])


def _posixlt_month_length(month_1based, full_year):
    """Length used by ``as.period`` on an interval.

    lubridate passes the POSIXlt year, which counts from 1900, into its leap
    test. February 2000 is therefore 28 days and February 1900 is 29.
    """
    month_1based = np.asarray(month_1based, dtype=int)
    posixlt_year = np.asarray(full_year, dtype=int) - 1900
    length = _MONTH_LENGTH[month_1based]
    leap = (month_1based == 2) & ((posixlt_year % 4 == 0) & ((posixlt_year % 100 != 0) | (posixlt_year % 400 == 0)))
    return np.where(leap, 29, length)


def _interval_to_period(x):
    start = x.start
    end = x.end()

    def comp(fn, obj):
        return np.atleast_1d(np.asarray(fn(obj), dtype=float))

    sy, sm, sd = comp(year, start), comp(month, start), comp(day, start)
    sh, smin, ss = comp(hour, start), comp(minute, start), comp(second, start)
    ey, em, ed = comp(year, end), comp(month, end), comp(day, end)
    eh, emin, es = comp(hour, end), comp(minute, end), comp(second, end)
    negative = np.atleast_1d(np.asarray(x.span, dtype=float)) < 0
    per_s = np.where(negative, ss - es, es - ss)
    per_m = np.where(negative, smin - emin, emin - smin)
    per_h = np.where(negative, sh - eh, eh - sh)
    per_d = np.where(negative, sd - ed, ed - sd)
    per_mo = np.where(negative, sm - em, em - sm)
    per_y = np.where(negative, sy - ey, ey - sy)

    nsecs = per_s < 0
    per_s = np.where(nsecs, per_s + 60, per_s)
    per_m = np.where(nsecs, per_m - 1, per_m)
    per_s = np.where(negative, -per_s, per_s)

    nmins = per_m < 0
    per_m = np.where(nmins, per_m + 60, per_m)
    per_h = np.where(nmins, per_h - 1, per_h)
    per_m = np.where(negative, -per_m, per_m)

    nhous = per_h < 0
    per_h = np.where(nhous, per_h + 24, per_h)
    per_h = np.where(negative, -per_h, per_h)

    ndays = (~negative) & (per_d < 0)
    if np.any(ndays):
        end_mon0 = em - 1
        pmonth = np.where(end_mon0 == 0, 1, end_mon0)
        prev = _posixlt_month_length(pmonth, ey)
        per_d = np.where(ndays, np.maximum(prev - sd, 0) + ed, per_d)
        per_mo = np.where(ndays, per_mo - 1, per_mo)
    ndays = negative & (per_d < 0)
    if np.any(ndays):
        this = _posixlt_month_length(em, ey)
        per_d = np.where(ndays, np.maximum(this - ed, 0) + sd, per_d)
        per_mo = np.where(ndays, per_mo - 1, per_mo)
    per_d = np.where(nhous, per_d - 1, per_d)
    per_d = np.where(negative, -per_d, per_d)

    nmons = per_mo < 0
    per_mo = np.where(nmons, per_mo + 12, per_mo)
    per_y = np.where(nmons, per_y - 1, per_y)
    per_mo = np.where(negative, -per_mo, per_mo)
    per_y = np.where(negative, -per_y, per_y)
    return Period(per_s, per_m, per_h, per_d, per_mo, per_y)


def as_duration(x):
    if isinstance(x, Duration):
        return x
    if isinstance(x, Period):
        return Duration(period_to_seconds(x))
    if isinstance(x, Interval):
        return Duration(x.span)
    if isinstance(x, Difftime):
        return Duration(x.seconds)
    return Duration(x)


def as_interval(x, start=None):
    if isinstance(x, Interval):
        return x
    span = as_duration(x).seconds
    origin = _as_instant(start) if start is not None else Posixct(0, "UTC")
    return Interval(origin, span)


def as_difftime(tim, units="secs"):
    return Difftime(as_duration(tim).seconds, units)


def make_difftime(num=None, units="auto", **pieces):
    seconds = 0.0
    if num is not None:
        seconds = seconds + np.asarray(num, dtype=float)
    lengths = {"second": 1, "minute": 60, "hour": 3600, "day": 86400, "week": 604800}
    for name, value in pieces.items():
        seconds = seconds + np.asarray(value, dtype=float) * lengths[_std(name)]
    return Difftime(seconds, units)


def time_length(x, unit="second"):
    chosen = _std(unit)
    if isinstance(x, Interval) and chosen in ("year", "month"):
        periods = as_period(x, unit=chosen)
        int_part = np.atleast_1d(np.asarray(getattr(periods, chosen), dtype=float))
        sign = np.where(np.atleast_1d(np.asarray(x.span, dtype=float)) < 0, -1.0, 1.0)
        prev = add_with_rollback(
            x.start, period(**{chosen: int_part}), roll_to_first=True, preserve_hms=False,
        )
        nxt = add_with_rollback(
            x.start, period(**{chosen: int_part + sign}), roll_to_first=True, preserve_hms=False,
        )
        end = x.end()
        sofar = np.asarray(end.seconds, dtype=float) - np.asarray(prev.seconds, dtype=float)
        total = np.asarray(nxt.seconds, dtype=float) - np.asarray(prev.seconds, dtype=float)
        return int_part + sign * sofar / total
    return np.asarray(as_duration(x).seconds, dtype=float) / UNIT_SECONDS[chosen]


def mplus(e1, e2):
    return add_with_rollback(e1, e2)


def mminus(e1, e2):
    return add_with_rollback(e1, -e2)


def add_with_rollback(e1, e2, roll_to_first=False, preserve_hms=True):
    months = np.asarray(e2.month, dtype=float) + 12 * np.asarray(e2.year, dtype=float)
    shifted = _add_months(e1, months)
    rolled = np.asarray(day(shifted), dtype=float) < np.asarray(day(e1), dtype=float)
    if np.any(rolled):
        fixed = rollbackward(shifted, roll_to_first=roll_to_first, preserve_hms=preserve_hms)
        seconds = np.where(rolled, fixed.seconds, shifted.seconds)
        shifted = Posixct(seconds, shifted.tz)
    rest = Period(e2.second, e2.minute, e2.hour, e2.day, 0, 0)
    if np.any(rest.slots() != 0):
        return add_period(shifted, rest)
    return shifted


def _add_months(instant, months):
    instant = _as_instant(instant)
    return time_add(instant, month=months, roll_month="full", roll_dst=("boundary", "post"))


def rollbackward(dates, roll_to_first=False, preserve_hms=True):
    return _roll(dates, roll_to_first, preserve_hms, forward=False)


rollback = rollbackward


def rollforward(dates, roll_to_first=False, preserve_hms=True):
    return _roll(dates, roll_to_first, preserve_hms, forward=True)


def _roll(dates, roll_to_first, preserve_hms, forward):
    from .instants import day_set, hour_set, minute_set, second_set
    dates = day_set(dates, 1)
    if not preserve_hms:
        dates = second_set(minute_set(hour_set(dates, 0), 0), 0)
    if forward:
        dates = add_period(dates, period(month=1))
    if roll_to_first:
        return dates
    return add_period(dates, period(day=-1))
