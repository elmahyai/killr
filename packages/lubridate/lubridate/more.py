"""The remaining lubridate exports that sit on instants and spans."""

import math
from datetime import datetime, timezone

import numpy as np

from timechange.civil import Posixct, is_leap

from .instants import (
    Date, _as_instant, am, date, day, dst, floor_date, force_tz, hour, minute,
    month, second, update_posix, with_tz, year, yday,
)
from .spans import (
    Duration, Period, add_period, days, interval, period, rollforward,
)


def make_datetime(year=1970, month=1, day=1, hour=0, minute=0, sec=0, tz="UTC"):
    from timechange import time_update
    parts = [np.atleast_1d(np.asarray(v, dtype=float)) for v in (year, month, day, hour, minute, sec)]
    if min(part.size for part in parts) == 0:
        return Posixct([], tz)
    n = max(part.size for part in parts)
    base = Posixct(np.zeros(n), "UTC")
    return time_update(
        base,
        year=np.resize(parts[0], n), month=np.resize(parts[1], n), mday=np.resize(parts[2], n),
        hour=np.resize(parts[3], n), minute=np.resize(parts[4], n), second=np.resize(parts[5], n),
        tz=tz, roll_month="full",
    )


def make_date(year=1970, month=1, day=1):
    built = make_datetime(year, month, day, tz="UTC")
    return date(built)


def origin():
    return Posixct(0.0, "UTC")


def r_date(length=0):
    return Date(np.full(int(length), np.nan))


def r_posixct(length=0, tz="UTC"):
    base = origin() if tz in ("UTC", "GMT") else force_tz(origin(), tz)
    return Posixct(np.repeat(float(np.asarray(base.seconds).reshape(-1)[0]), int(length)), tz)


NA_DATE = Date(np.nan)
NA_POSIXCT = Posixct(np.nan, "UTC")


def now(tzone=""):
    stamp = datetime.now(timezone.utc).timestamp()
    instant = Posixct(stamp, "UTC")
    if tzone:
        return with_tz(instant, tzone)
    return instant


def today(tzone=""):
    return date(now(tzone or "UTC"))


def decimal_date(when):
    years = np.atleast_1d(np.asarray(year(when), dtype=float))
    start = make_datetime(years, 1, 1, tz=getattr(when, "tz", "UTC"))
    end = make_datetime(years + 1, 1, 1, tz=getattr(when, "tz", "UTC"))
    instant = _as_instant(when)
    sofar = np.asarray(instant.seconds, dtype=float) - start.seconds
    total = end.seconds - start.seconds
    return years + sofar / total


def date_decimal(decimal, tz="UTC"):
    decimal = np.atleast_1d(np.asarray(decimal, dtype=float))
    years = np.trunc(decimal)
    start = make_datetime(years, 1, 1, tz=tz)
    end = make_datetime(years + 1, 1, 1, tz=tz)
    return Posixct(start.seconds + (end.seconds - start.seconds) * (decimal - years), tz)


def week(x):
    return (yday(x) - 1) // 7 + 1


def week_set(x, value):
    return add_period(x, days((np.asarray(value, dtype=float) - week(x)) * 7))


def _other_week(x, week_start):
    from .instants import wday
    years = np.atleast_1d(np.asarray(year(x), dtype=int))
    months = np.atleast_1d(np.asarray(month(x), dtype=int))
    days_ = np.atleast_1d(np.asarray(day(x), dtype=int))
    made = make_date(years, months, days_)
    shift = 4 - np.atleast_1d(np.asarray(wday(x, week_start=week_start), dtype=float))
    moved = Date(made.days + shift)
    # year of the shifted date
    from .instants import date as as_date
    instant = Posixct(moved.days * 86400, "UTC")
    jan1 = make_date(year(instant), 1, 1)
    return 1 + (moved.days - jan1.days) // 7


def isoweek(x):
    return _other_week(x, 1)


def epiweek(x):
    return _other_week(x, 7)


def isoyear(x):
    from .instants import wday
    instant = _as_instant(x)
    shifted = add_period(instant, days(4 - wday(x, week_start=1)))
    return year(shifted)


def epiyear(x):
    from .instants import wday
    instant = _as_instant(x)
    shifted = add_period(instant, days(4 - wday(x, week_start=7)))
    return year(shifted)


def date_set(x, value):
    return update_posix(x, years=year(value), months=month(value), days=day(value))


def qday_set(x, value):
    from .instants import qday
    return add_period(x, days(np.asarray(value, dtype=float) - qday(x)))


def as_date(x, tz=None):
    if isinstance(x, Date):
        return x
    return date(with_tz(x, tz) if tz else x)


def as_datetime(x, tz=None):
    instant = _as_instant(x)
    if tz:
        return with_tz(instant, tz)
    return instant


def reclass_date(new, orig):
    if isinstance(orig, Date):
        return date(new)
    return new


def reclass_timespan(new, orig):
    return new


def format_iso8601(x, usetz=False, precision=None):
    instant = x if isinstance(x, Posixct) else None
    if isinstance(x, Date):
        instant = Posixct(x.days * 86400, "UTC")
        precision = precision or "ymd"
    if isinstance(x, Period):
        return f"P{int(x.year[0])}Y{int(x.month[0])}M{int(x.day[0])}DT{int(x.hour[0])}H{int(x.minute[0])}M{x.second[0]}S"
    if isinstance(x, Duration):
        return f"PT{float(x.seconds[0])}S"
    def _one(value):
        return int(np.asarray(value, dtype=float).reshape(-1)[0])

    parts = {
        "year": year(instant), "month": month(instant), "mday": day(instant),
        "hour": hour(instant), "minute": minute(instant), "second": second(instant),
    }
    text = f"{_one(parts['year']):04d}-{_one(parts['month']):02d}-{_one(parts['mday']):02d}"
    if precision in (None, "ymdhms", "ymdhm", "ymdh"):
        if not isinstance(x, Date):
            text += f"T{_one(parts['hour']):02d}:{_one(parts['minute']):02d}:{_one(parts['second']):02d}"
    if usetz == "Z":
        text += "Z"
    elif usetz and isinstance(x, Posixct):
        text += x.tz
    return text


def cyclic_encoding(x, periods, encoders=("sin", "cos"), week_start=7):
    from .instants import ceiling_date
    instant = _as_instant(x)
    columns = []
    names = []
    for name in periods:
        beg = floor_date(instant, name, week_start=week_start).seconds
        end = ceiling_date(instant, name, week_start=week_start).seconds
        width = end - beg
        safe = np.where(width == 0, 1, width)
        angle = np.where(width == 0, 0, 2 * math.pi * (instant.seconds - beg) / safe)
        for encoder in encoders:
            fn = np.sin if encoder == "sin" else np.cos
            columns.append(fn(angle))
            names.append(f"{encoder}.{name}")
    return np.column_stack(columns)


def _pretty_unit(span):
    if span > 3600 * 24 * 365:
        return "year"
    if span > 3600 * 24 * 30:
        return "month"
    if span > 3600 * 24:
        return "day"
    if span > 3600:
        return "hour"
    if span > 60:
        return "min"
    return "sec"


def _pretty_length(diff, n, unit):
    table = {
        "sec": (1, [1, 2, 5, 10, 15, 30, 60]),
        "min": (60, [1, 2, 5, 10, 15, 30, 60]),
        "hour": (3600, [1, 2, 3, 4, 6, 8, 12, 24]),
        "month": (3600 * 24 * 30, [1, 2, 3, 4, 6, 12]),
    }
    if unit in table:
        scale, lengths = table[unit]
        lengths = np.asarray(lengths, dtype=float)
        fit = np.abs(diff / scale - lengths * n)
        return float(lengths[int(np.argmin(fit))])
    span = diff / (3600 * 24 * (365 if unit == "year" else 1))
    return _r_pretty_step(span, n)


def _r_pretty_step(span, n):
    """Second break of R ``pretty(1:span, n)``, which is the bin length."""
    if span <= 1:
        return 1.0
    rough = span / max(n, 1)
    exp = math.floor(math.log10(rough))
    base = 10 ** exp
    errors = [abs(rough - base * c) for c in (1, 2, 5, 10)]
    return float(base * (1, 2, 5, 10)[int(np.argmin(errors))])


def _seq_breaks(start, end, step, unit, tz):
    from timechange import time_add
    name = {"sec": "second", "min": "minute", "hour": "hour", "day": "day", "month": "month", "year": "year"}[unit]
    out = []
    cur = float(start)
    for _ in range(10000):
        if cur > float(end) + 1e-6:
            break
        out.append(cur)
        nxt = time_add(Posixct(cur, tz), **{name: step}, roll_month="full", roll_dst=("boundary", "post"))
        nxt_s = float(np.asarray(nxt.seconds, dtype=float).reshape(-1)[0])
        if nxt_s <= cur:
            break
        cur = nxt_s
    return Posixct(np.asarray(out, dtype=float), tz)


def _pretty_point(seconds, unit, length, tz, start):
    from .instants import ceiling_date, floor_date
    instant = Posixct(float(seconds), tz)
    if unit in ("day", "year"):
        return float(np.asarray((floor_date if start else ceiling_date)(instant, unit).seconds).reshape(-1)[0])
    parent = {"sec": "min", "min": "hour", "hour": "day", "month": "year"}[unit]
    parent_name = {"min": "minute", "hour": "hour", "day": "day", "year": "year"}[parent]
    lower = float(np.asarray(floor_date(instant, parent_name).seconds).reshape(-1)[0])
    upper = float(np.asarray(ceiling_date(instant, parent_name).seconds).reshape(-1)[0])
    points = np.asarray(_seq_breaks(lower, upper, length, unit, tz).seconds, dtype=float)
    chosen = points[points <= seconds] if start else points[points >= seconds]
    if chosen.size == 0:
        return float(lower if start else upper)
    return float(chosen[int(np.argmin(np.abs(chosen - seconds)))])


def pretty_dates(x, n):
    instant = _as_instant(x)
    seconds = np.asarray(instant.seconds, dtype=float)
    start, end = float(np.min(seconds)), float(np.max(seconds))
    diff = end - start
    unit = _pretty_unit(diff / n)
    length = _pretty_length(diff, n, unit)
    left = _pretty_point(start, unit, length, instant.tz, True)
    right = _pretty_point(end, unit, length, instant.tz, False)
    return _seq_breaks(left, right, length, unit, instant.tz)


_MONTH_FULL = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
_MONTH_ABBR = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_WDAY_FULL = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_WDAY_ABBR = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _template_to_tokens(template):
    import re
    text = str(template)
    pieces = []
    while text:
        matched = False
        for name in _MONTH_FULL:
            if text.lower().startswith(name.lower()):
                pieces.append("%B")
                text = text[len(name):]
                matched = True
                break
        if matched:
            continue
        for name in _MONTH_ABBR:
            if text.lower().startswith(name.lower()):
                pieces.append("%b")
                text = text[len(name):]
                matched = True
                break
        if matched:
            continue
        for name in _WDAY_FULL:
            if text.lower().startswith(name.lower()):
                pieces.append("%A")
                text = text[len(name):]
                matched = True
                break
        if matched:
            continue
        found = re.match(r"(\d{1,2}):(\d{2}):(\d{2})", text)
        if found:
            pieces.extend(["%H", ":", "%M", ":", "%S"])
            text = text[found.end():]
            continue
        found = re.match(r"(\d{1,2}):(\d{2})", text)
        if found:
            pieces.extend(["%H", ":", "%M"])
            text = text[found.end():]
            continue
        found = re.match(r"\d{4}", text)
        if found:
            pieces.append("%Y")
            text = text[4:]
            continue
        found = re.match(r"\d{1,2}", text)
        if found:
            pieces.append("%d")
            text = text[found.end():]
            continue
        pieces.append(text[0])
        text = text[1:]
    return pieces


def _apply_tokens(instant, tokens):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    zone = ZoneInfo(instant.tz or "UTC")
    out = []
    seconds = np.atleast_1d(np.asarray(instant.seconds, dtype=float))
    for stamp_s in seconds:
        when = datetime.fromtimestamp(float(stamp_s), zone)
        rendered = []
        for token in tokens:
            if token == "%B":
                rendered.append(_MONTH_FULL[when.month - 1])
            elif token == "%b":
                rendered.append(_MONTH_ABBR[when.month - 1])
            elif token == "%A":
                rendered.append(_WDAY_FULL[when.weekday()])
            elif token == "%Y":
                rendered.append(f"{when.year:04d}")
            elif token == "%d":
                rendered.append(f"{when.day:02d}")
            elif token == "%H":
                rendered.append(f"{when.hour:02d}")
            elif token == "%M":
                rendered.append(f"{when.minute:02d}")
            elif token == "%S":
                rendered.append(f"{when.second:02d}")
            else:
                rendered.append(token)
        out.append("".join(rendered))
    return out[0] if len(out) == 1 else out


def stamp(x, orders=None, quiet=True, exact=False):
    import re
    tokens = re.findall(r"%[A-Za-z]|.", orders) if exact else _template_to_tokens(x)

    def _format(when):
        instant = when if isinstance(when, Posixct) else _as_instant(when)
        return _apply_tokens(instant, tokens)

    return _format


def stamp_date(x):
    return stamp(x)


def stamp_time(x):
    return stamp(x)


def fit_to_timeline(lt, class_="POSIXct", simple=False):
    return _as_instant(lt)


def time_length_export(x, unit="second"):
    from .spans import time_length
    return time_length(x, unit)
