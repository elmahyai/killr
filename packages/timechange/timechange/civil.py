"""CCTZ civil time and zoneinfo lookups.

Integer division truncates toward zero, matching the C++ in timechange's
copy of CCTZ. Time zones come from the system zoneinfo data through
``zoneinfo``. A few abbreviations are fixed offsets, the same table
timechange keeps when the name is not a zoneinfo file.
"""

import math
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np

FIXED = {
    "GMT": 0,
    "CEST": 2,
    "CET": 1,
    "EDT": -4,
    "EEST": 3,
    "EET": 2,
    "EST": -5,
    "PDT": -7,
    "PST": -8,
    "WEST": 1,
    "WET": 0,
}

UTC_NAMES = {"UTC", "GMT", "Etc/UTC", "Etc/GMT", "GMT-0", "GMT+0", "GMT0"}


def _div(a, b):
    """C++ integer division, toward zero."""
    if a < 0:
        return -((-a) // b)
    return a // b


def _mod(a, b):
    return a - _div(a, b) * b


def is_leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def days_in_month(year, month):
    lengths = (-1, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    return lengths[month] + (month == 2 and is_leap(year))


def _year_index(year, month):
    yi = (year + (month > 2)) % 400
    return yi + 400 if yi < 0 else yi


def _days_per_century(yi):
    return 36524 + (yi == 0 or yi > 300)


def _days_per_4years(yi):
    return 1460 + (yi == 0 or yi > 300 or (yi - 1) % 100 < 96)


def _days_per_year(year, month):
    return 366 if is_leap(year + (month > 2)) else 365


def n_day(year, month, day, extra, hour, minute, second):
    """CCTZ ``n_day``: normalize a year, month, and possibly huge day count."""
    ey = _mod(year, 400)
    origin = ey
    ey += _div(extra, 146097) * 400
    extra = _mod(extra, 146097)
    if extra < 0:
        ey -= 400
        extra += 146097
    ey += _div(day, 146097) * 400
    day = _mod(day, 146097) + extra
    if day > 0:
        if day > 146097:
            ey += 400
            day -= 146097
    else:
        if day > -365:
            ey -= 1
            day += _days_per_year(ey, month)
        else:
            ey -= 400
            day += 146097
    if day > 365:
        yi = _year_index(ey, month)
        while True:
            span = _days_per_century(yi)
            if day <= span:
                break
            day -= span
            ey += 100
            yi += 100
            if yi >= 400:
                yi -= 400
        while True:
            span = _days_per_4years(yi)
            if day <= span:
                break
            day -= span
            ey += 4
            yi += 4
            if yi >= 400:
                yi -= 400
        while True:
            span = _days_per_year(ey, month)
            if day <= span:
                break
            day -= span
            ey += 1
    if day > 28:
        while True:
            span = days_in_month(ey, month)
            if day <= span:
                break
            day -= span
            month += 1
            if month > 12:
                ey += 1
                month = 1
    return (year + (ey - origin), month, int(day), hour, minute, second)


def n_mon(year, month, day, extra, hour, minute, second):
    if month != 12:
        year += _div(month, 12)
        month = _mod(month, 12)
        if month <= 0:
            year -= 1
            month += 12
    return n_day(year, month, day, extra, hour, minute, second)


def n_hour(year, month, day, extra, hour, minute, second):
    extra += _div(hour, 24)
    hour = _mod(hour, 24)
    if hour < 0:
        extra -= 1
        hour += 24
    return n_mon(year, month, day, extra, hour, minute, second)


def n_min(year, month, day, hour, extra_hour, minute, second):
    extra_hour += _div(minute, 60)
    minute = _mod(minute, 60)
    if minute < 0:
        extra_hour -= 1
        minute += 60
    return n_hour(
        year,
        month,
        day,
        _div(hour, 24) + _div(extra_hour, 24),
        _mod(hour, 24) + _mod(extra_hour, 24),
        minute,
        second,
    )


def n_sec(year, month, day, hour, minute, second):
    if 0 <= second < 60:
        if 0 <= minute < 60:
            if 0 <= hour < 24:
                if 1 <= day <= 28 and 1 <= month <= 12:
                    return (year, month, day, hour, minute, second)
                return n_mon(year, month, day, 0, hour, minute, second)
            return n_hour(year, month, day, _div(hour, 24), _mod(hour, 24), minute, second)
        return n_min(year, month, day, hour, _div(minute, 60), _mod(minute, 60), second)
    carry = _div(second, 60)
    second = _mod(second, 60)
    if second < 0:
        carry -= 1
        second += 60
    return n_min(
        year,
        month,
        day,
        hour,
        _div(minute, 60) + _div(carry, 60),
        _mod(minute, 60) + _mod(carry, 60),
        second,
    )


def step_second(fields, n):
    year, month, day, hour, minute, second = fields
    return n_sec(year, month, day, hour, minute + _div(n, 60), second + _mod(n, 60))


def step_minute(fields, n):
    year, month, day, hour, minute, second = fields
    return n_min(year, month, day, hour + _div(n, 60), 0, minute + _mod(n, 60), second)


def step_hour(fields, n):
    year, month, day, hour, minute, second = fields
    return n_hour(year, month, day + _div(n, 24), 0, hour + _mod(n, 24), minute, second)


def step_day(fields, n):
    year, month, day, hour, minute, second = fields
    return n_day(year, month, day, n, hour, minute, second)


def step_month(fields, n):
    year, month, day, hour, minute, second = fields
    return n_mon(year + _div(n, 12), month + _mod(n, 12), day, 0, hour, minute, second)


def step_year(fields, n):
    year, month, day, hour, minute, second = fields
    return (year + n, month, day, hour, minute, second)


def yearday(fields):
    year, month, day, *_ = n_sec(*fields)
    count = day
    for month_i in range(1, month):
        count += days_in_month(year, month_i)
    return count


def weekday(fields):
    """Monday is 0, matching CCTZ."""
    year, month, day, *_ = n_sec(*fields)
    return datetime(year, month, day).weekday()


def local_tz():
    env = os.environ.get("TZ")
    if env:
        return env
    current = datetime.now().astimezone().tzinfo
    key = getattr(current, "key", None)
    return key or "UTC"


def load_zone(name):
    """Return ``(zone, label)``. An empty name is the local zone."""
    if name is None or name == "":
        name = local_tz()
    if name in FIXED and name not in UTC_NAMES:
        offset = FIXED[name]
        return timezone(timedelta(hours=offset), name), name
    try:
        if name in UTC_NAMES:
            return ZoneInfo("UTC"), name
        return ZoneInfo(name), name
    except ZoneInfoNotFoundError:
        if name in FIXED:
            offset = FIXED[name]
            return timezone(timedelta(hours=offset), name), name
        raise ValueError(f'CCTZ: Unrecognized tzone: "{name}"') from None


def valid_tz(name):
    try:
        load_zone(name if name else local_tz())
    except ValueError:
        return False
    return True


def _stamp(zone, year, month, day, hour, minute, second, fold):
    civil = datetime(year, month, day, hour, minute, second)
    aware = civil.replace(tzinfo=zone, fold=fold)
    return aware.timestamp()


def _roundtrip(zone, stamp):
    shown = datetime.fromtimestamp(stamp, zone)
    return (shown.year, shown.month, shown.day, shown.hour, shown.minute, shown.second)


def lookup(zone, fields):
    """CCTZ ``civil_lookup``: kind, pre, trans, post, in POSIX seconds."""
    year, month, day, hour, minute, second = n_sec(*fields)
    target = (year, month, day, hour, minute, second)
    earlier = _stamp(zone, year, month, day, hour, minute, second, 0)
    later = _stamp(zone, year, month, day, hour, minute, second, 1)
    ok_early = _roundtrip(zone, earlier) == target
    ok_late = _roundtrip(zone, later) == target
    if ok_early and ok_late and abs(earlier - later) > 0.5:
        pre, post = (earlier, later) if earlier < later else (later, earlier)
        return "repeated", pre, post, post
    if ok_early or ok_late:
        stamp = earlier if ok_early else later
        return "unique", stamp, stamp, stamp
    pre = max(earlier, later)
    post = min(earlier, later)
    # The transition is the first instant whose civil time is past the gap.
    trans = pre
    probe = post
    for _ in range(4):
        mid = (probe + trans) / 2
        if _roundtrip(zone, mid)[3:] == (0, 0, 0) and mid != probe:
            trans = mid
        else:
            probe = mid
    # Walk forward from the post-offset instant to the offset change.
    trans = post
    step = 60
    previous = _offset(zone, post)
    for _ in range(180):
        nxt = trans + step
        if _offset(zone, nxt) != previous:
            trans = nxt
            break
        trans = nxt
    while trans > post and _offset(zone, trans - 1) != previous:
        trans -= 1
    return "skipped", pre, trans, post


def _offset(zone, stamp):
    return datetime.fromtimestamp(stamp, zone).utcoffset()


def to_posix(kind, pre, trans, post, skipped, repeated, negative=False):
    """``civil_lookup_to_posix``. Skipped pre/post are swapped relative to CCTZ."""
    if kind == "skipped":
        if skipped == "pre":
            return post
        if skipped == "boundary":
            return trans
        if skipped == "post":
            return pre
        if skipped == "xfirst":
            return pre if negative else post
        if skipped == "xlast":
            return post if negative else pre
        if skipped == "NA":
            return math.nan
    if kind == "repeated":
        if repeated == "pre":
            return pre
        if repeated == "boundary":
            return trans
        if repeated == "post":
            return post
        if repeated == "xfirst":
            return post if negative else pre
        if repeated == "xlast":
            return pre if negative else post
        if repeated == "NA":
            return math.nan
    return pre


def to_posix_keeping(kind, pre, trans, post, old_kind, old_pre, old_trans, old_stamp, skipped, repeated, remainder):
    """The two-argument lookup used by update and force_tz."""
    if kind == "repeated":
        if repeated == "boundary":
            remainder = 0.0
        if old_kind == "repeated":
            chosen = post if old_stamp >= old_trans else pre
            return chosen + remainder
    elif kind == "skipped" and repeated == "boundary":
        remainder = 0.0
    value = to_posix(kind, pre, trans, post, skipped, repeated)
    if math.isnan(value):
        return value
    return value + remainder


def from_posix(seconds, zone):
    secs = math.floor(seconds)
    rem = seconds - secs
    shown = datetime.fromtimestamp(secs, zone)
    return (shown.year, shown.month, shown.day, shown.hour, shown.minute, shown.second), rem


class Posixct:
    """Seconds since the Unix epoch, with one time-zone name."""

    def __init__(self, seconds, tz="UTC"):
        self.seconds = np.asarray(seconds, dtype=float)
        self.tz = "UTC" if tz in UTC_NAMES else tz

    def __len__(self):
        return int(self.seconds.size)

    def __repr__(self):
        return f"Posixct({self.seconds.tolist()}, tz={self.tz!r})"
