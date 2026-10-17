"""Instants, component accessors, and the timechange wrappers.

lubridate's week starts on Sunday (7) unless told otherwise. Component
numbers for a POSIXct come from timechange. ``wday`` is one more than
timechange's zero-based weekday.
"""

import math
import warnings
from datetime import datetime, timedelta

import numpy as np

from timechange import (
    time_at_tz,
    time_ceiling,
    time_clock_at_tz,
    time_floor,
    time_force_tz,
    time_get,
    time_round,
    time_update,
)
from timechange.civil import Posixct, days_in_month as _days_in_month, is_leap, load_zone

_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
_MONTHS_ABBR = tuple(name[:3] for name in _MONTHS)
# Index 0 is Sunday, matching lubridate's unlabeled wday before week_start.
_WEEKDAYS = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
_WEEKDAYS_ABBR = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")


class Date:
    """Days since 1970-01-01, the R Date count."""

    def __init__(self, days):
        self.days = np.asarray(days, dtype=float)

    def __repr__(self):
        return f"Date({self.days.tolist()})"


def is_instant(x):
    return isinstance(x, (Posixct, Date))


is_timepoint = is_instant


def is_posixct(x):
    return isinstance(x, Posixct)


def is_posixlt(x):
    return False


def is_posixt(x):
    return isinstance(x, Posixct)


def is_date(x):
    return isinstance(x, Date)


def _as_instant(x):
    if isinstance(x, Date):
        return Posixct(np.asarray(x.days, dtype=float) * 86400.0, "UTC")
    if isinstance(x, Posixct):
        return x
    raise TypeError("expected a POSIXct or Date")


def _component(x, name, week_start=1):
    got = time_get(_as_instant(x), [name], week_start=week_start)
    return got[name]


def year(x):
    return _component(x, "year")


def month(x, label=False, abbr=True, locale=None):
    numbers = _component(x, "month")
    if not label:
        return numbers
    names = _MONTHS_ABBR if abbr else _MONTHS
    return np.array([names[int(v) - 1] if not math.isnan(v) else None for v in np.asarray(numbers).reshape(-1)])


def mday(x):
    return _component(x, "mday")


day = mday


def yday(x):
    return _component(x, "yday")


def wday(x, label=False, abbr=True, week_start=7, locale=None):
    """Weekday. Sunday is 1 when ``week_start`` is 7."""
    numbers = _component(x, "wday", week_start=week_start) + 1
    if not label:
        return numbers
    names = _WEEKDAYS_ABBR if abbr else _WEEKDAYS
    # Levels start on the week start. The numbers are already 1 there.
    if week_start == 7:
        labels = list(names)
    else:
        labels = list(names[week_start:]) + list(names[:week_start])
    return np.array([labels[int(v) - 1] if not math.isnan(v) else None for v in np.asarray(numbers).reshape(-1)])


def hour(x):
    return _component(x, "hour")


def minute(x):
    return _component(x, "minute")


def second(x):
    return _component(x, "second")


def tz(x):
    if isinstance(x, Posixct):
        return x.tz
    return "UTC"


def _set(x, **components):
    return time_update(
        _as_instant(x),
        roll_month="NAym",
        roll_dst=("NA", "post"),
        week_start=7,
        **components,
    )


def year_set(x, value):
    return _set(x, year=value)


def month_set(x, value):
    return _set(x, month=value)


def mday_set(x, value):
    return time_update(_as_instant(x), mday=value, roll_month="full", roll_dst=("NA", "post"), week_start=7)


day_set = mday_set


def yday_set(x, value):
    return time_update(_as_instant(x), yday=value, roll_month="full", roll_dst=("NA", "post"), week_start=7)


def hour_set(x, value):
    return time_update(_as_instant(x), hour=value, roll_month="full", roll_dst=("NA", "post"), week_start=7)


def minute_set(x, value):
    return time_update(_as_instant(x), minute=value, roll_month="full", roll_dst=("NA", "post"), week_start=7)


def second_set(x, value):
    return time_update(_as_instant(x), second=value, roll_month="full", roll_dst=("NA", "post"), week_start=7)


def wday_set(x, value, week_start=7):
    return time_update(
        _as_instant(x), wday=value, roll_month="full", roll_dst=("NA", "post"), week_start=week_start,
    )


def tz_set(x, value):
    return force_tz(x, value)


def quarter(x, with_year=False, fiscal_start=1):
    months = month(x)
    if fiscal_start != 1:
        months = (months - fiscal_start) % 12 + 1
    q = np.floor((months - 1) / 3) + 1
    if not with_year:
        return q
    return year(x) + (q - 1) / 4


def semester(x, with_year=False):
    half = np.floor((month(x) - 1) / 6) + 1
    if not with_year:
        return half
    return year(x) + (half - 1) / 2


def am(x):
    return hour(x) < 12


def pm(x):
    return np.logical_not(am(x))


def dst(x):
    instant = _as_instant(x)
    zone, _ = load_zone(instant.tz)
    out = np.empty(instant.seconds.size, dtype=bool)
    for i, value in enumerate(np.asarray(instant.seconds).reshape(-1)):
        if math.isnan(value):
            out.reshape(-1)[i] = False
            continue
        shown = datetime.fromtimestamp(math.floor(value), zone)
        shift = shown.dst()
        out.reshape(-1)[i] = shift not in (None, timedelta(0))
    return out.reshape(instant.seconds.shape)


def leap_year(x):
    return np.vectorize(is_leap)(year(x)).astype(bool)


def days_in_month(x):
    years = year(x)
    months = month(x)
    out = np.empty(np.asarray(years).size, dtype=float)
    for i, (y, m) in enumerate(zip(np.asarray(years).reshape(-1), np.asarray(months).reshape(-1))):
        out[i] = _days_in_month(int(y), int(m))
    return out.reshape(np.asarray(years).shape)


def date(x):
    """The civil date, as days since 1970-01-01."""
    instant = _as_instant(x)
    parts = time_get(instant, ["year", "month", "mday"])
    origin = datetime(1970, 1, 1).toordinal()
    days = []
    years = np.asarray(parts["year"]).reshape(-1)
    months = np.asarray(parts["month"]).reshape(-1)
    mdays = np.asarray(parts["mday"]).reshape(-1)
    for y, m, d in zip(years, months, mdays):
        days.append(datetime(int(y), int(m), int(d)).toordinal() - origin)
    return Date(np.asarray(days, dtype=float).reshape(instant.seconds.shape))


def qday(x):
    floored = floor_date(x, "quarter")
    return (date(x).days - date(floored).days) + 1


def force_tz(time, tzone="", roll_dst=("NA", "post")):
    return time_force_tz(_as_instant(time), tzone, roll_dst=roll_dst)


def force_tzs(time, tzones, tzone_out="UTC", roll_dst=("NA", "post")):
    return time_force_tz(_as_instant(time), tzones, roll_dst=roll_dst, tzout=tzone_out)


def with_tz(time, tzone=""):
    try:
        load_zone(tzone if tzone else None)
    except ValueError:
        warnings.warn(f"Unrecognized time zone '{tzone}'", stacklevel=2)
    return time_at_tz(_as_instant(time), tzone if tzone else "UTC")


def local_time(dt, tz=None, units="secs"):
    return time_clock_at_tz(_as_instant(dt), tz, units)


def floor_date(x, unit="seconds", week_start=7):
    return time_floor(_as_instant(x), unit, week_start=week_start)


def ceiling_date(x, unit="seconds", change_on_boundary=None, week_start=7):
    if change_on_boundary is None:
        change_on_boundary = isinstance(x, Date)
    return time_ceiling(
        _as_instant(x), unit, change_on_boundary=change_on_boundary, week_start=week_start,
    )


def round_date(x, unit="second", week_start=7):
    return time_round(_as_instant(x), unit, week_start=week_start)


def update_posix(x, week_start=7, roll_dst=("NA", "post"), roll_month="full", **components):
    """``update.POSIXt``. Plural argument names are the singular component."""
    names = {
        "years": "year", "months": "month", "days": "mday", "mdays": "mday",
        "ydays": "yday", "wdays": "wday", "hours": "hour", "minutes": "minute",
        "seconds": "second",
    }
    mapped = {}
    for key, value in components.items():
        mapped[names.get(key, key)] = value
    return time_update(
        _as_instant(x),
        roll_month=roll_month,
        roll_dst=roll_dst,
        week_start=week_start,
        **mapped,
    )
