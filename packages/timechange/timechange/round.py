"""Floor, ceiling, and round, following timechange's civil units."""

import math

import numpy as np

from .civil import Posixct, from_posix, load_zone, lookup, step_day, step_hour, step_minute, step_month, step_second, step_year, to_posix_keeping, weekday

_UNITS = [
    "bimonths", "quarters", "halfyears", "seasons",
    "AH", "ahours",
    "AM", "amins", "aminutes",
    "AS", "asecs", "aseconds",
    "S", "secs", "seconds",
    "M", "mins", "minutes",
    "H", "hours",
    "D", "days",
    "W", "weeks",
    "months",
    "Y", "years",
]
_CANONICAL = [
    "bimonth", "quarter", "halfyear", "season",
    "ahour", "ahour",
    "aminute", "aminute", "aminute",
    "asecond", "asecond", "asecond",
    "second", "second", "second",
    "minute", "minute", "minute",
    "hour", "hour",
    "day", "day",
    "week", "week",
    "month",
    "year", "year",
]
_LIMITS = {
    "asecond": math.inf, "aminute": math.inf, "ahour": math.inf,
    "second": 60, "minute": 60, "hour": 24, "day": 31, "year": math.inf, "week": 1,
    "month": 12, "bimonth": 6, "quarter": 4, "season": 4, "halfyear": 2,
}


def _alpha(char):
    return ("a" <= char <= "z") or ("A" <= char <= "Z") or ("0" <= char <= "9")


def _parse_alphanum(text, start):
    i = start
    while i < len(text) and not _alpha(text[i]):
        i += 1
    track = [True] * len(_UNITS)
    good = len(_UNITS)
    j = 0
    found = -1
    while i < len(text) and good:
        for k, name in enumerate(_UNITS):
            if not track[k]:
                continue
            if j < len(name):
                if text[i] == name[j]:
                    found = k
                else:
                    track[k] = False
                    good -= 1
            else:
                good -= 1
                if good == 0:
                    found = k
        if good:
            i += 1
            j += 1
    return found, i


def _scan_number(text, start):
    i = start
    if i < len(text) and text[i] in "+-":
        i += 1
    saw = False
    while i < len(text) and text[i].isdigit():
        saw = True
        i += 1
    if i < len(text) and text[i] == ".":
        i += 1
        while i < len(text) and text[i].isdigit():
            saw = True
            i += 1
    if not saw:
        return None, start
    if i < len(text) and text[i] in "eE":
        j = i + 1
        if j < len(text) and text[j] in "+-":
            j += 1
        if j < len(text) and text[j].isdigit():
            while j < len(text) and text[j].isdigit():
                j += 1
            i = j
    return float(text[start:i]), i


def parse_units(unit):
    """Parse one rounding unit. Same names as timechange's ``C_parse_unit``."""
    if isinstance(unit, (list, tuple)) and len(unit) > 1:
        unit = unit[0]
    text = str(unit)
    i = 0
    chosen_n, chosen_ix = 0.0, -1
    while i < len(text):
        number, end = _scan_number(text, i)
        parsed_n = number is not None
        if not parsed_n:
            number = -1.0
            end = i
        ix, end = _parse_alphanum(text, end)
        if ix >= 0 and not parsed_n:
            number = 1.0
        if parsed_n and ix < 0:
            raise ValueError(f"Invalid unit specification '{unit}'")
        if ix >= 0 and number != 0:
            if chosen_ix >= 0 and chosen_n != 0:
                raise ValueError(f"Heterogeneous unit in '{unit}'")
            chosen_n, chosen_ix = number, ix
        if end < len(text) and (_alpha(text[end]) and not text[end].isdigit()):
            raise ValueError(f"Invalid unit specification '{unit}'")
        if end == i:
            break
        i = end
    if chosen_ix < 0:
        raise ValueError(f"Invalid unit specification '{unit}'")
    name = _CANONICAL[chosen_ix]
    limit = _LIMITS[name]
    if chosen_n > limit:
        raise ValueError(f"Rounding with {name} > {limit} is not supported")
    return chosen_n, name


def standardise_unit_name(unit):
    return parse_units(unit)[1]


def _floor_n(x, n):
    return math.floor(x / n) * n


def _floor_n1(x, n):
    return math.floor((x - 1) / n) * n


def _ceil_n(x, n):
    return math.floor(x / n) * n + n


def _ceil_n1(x, n):
    return math.floor((x - 1) / n) * n + n


def _fractional(n, label):
    if n < 1 or abs(n - math.floor(n)) > 1e-14:
        raise ValueError(f"Rounding with {label} units ({n:.2f}) is not supported")


def _adjust(unit, n):
    if unit == "asecond":
        return "asecond", n
    if unit == "aminute":
        return "asecond", n * 60
    if unit == "ahour":
        return "asecond", n * 3600
    if unit == "second":
        if n > 60:
            raise ValueError("Rounding unit for seconds larger than 60")
        return "second", n
    if unit == "minute":
        if n < 1:
            return "second", n * 60
        if n > 60:
            raise ValueError("Rounding unit for minutes larger than 60")
        _fractional(n, "fractional multi-minute")
        return "minute", n
    if unit == "hour":
        if n < 1:
            return "minute", n * 60
        if n > 24:
            raise ValueError("Rounding unit for hours larger than 24")
        _fractional(n, "fractional multi-hour")
        return "hour", n
    if unit == "day":
        if n < 1:
            return "hour", n * 24
        if n > 31:
            raise ValueError("Rounding unit for days larger than 31")
        _fractional(n, "fractional multi-day")
        return "day", n
    if unit == "season":
        if n != 1:
            raise ValueError("Rounding with fractional or multi-unit seasons not supported")
        return "season", 3
    if unit in ("halfyear", "bimonth", "quarter", "month"):
        scale = {"halfyear": 6, "bimonth": 2, "quarter": 3, "month": 1}[unit]
        n = n * scale
        _fractional(n, "fractional months")
        if n > 12:
            raise ValueError(f"Resulting rounding number of months ({n:.2f}) larger than 12")
        return "month", n
    if unit == "year":
        _fractional(n, "fractional years")
        return "year", n
    if unit == "week":
        if n != 1:
            raise ValueError("Rounding with multi-week or fractional weeks is not supported")
        return "week", n
    raise ValueError(f"Invalid unit {unit}")


def _zero_below(fields, unit):
    year, month, day, hour, minute, second = fields
    if unit == "year":
        return (year, 1, 1, 0, 0, 0)
    if unit == "month":
        return (year, month, 1, 0, 0, 0)
    if unit == "day":
        return (year, month, day, 0, 0, 0)
    if unit == "hour":
        return (year, month, day, hour, 0, 0)
    if unit == "minute":
        return (year, month, day, hour, minute, 0)
    return (year, month, day, hour, minute, second)


def _add_unit(fields, unit, n):
    n = int(n)
    if unit == "year":
        return step_year(_zero_below(fields, "year"), n)
    if unit == "month":
        return step_month(_zero_below(fields, "year"), n)
    if unit == "day":
        return step_day(_zero_below(fields, "month"), n)
    if unit == "hour":
        return step_hour(_zero_below(fields, "day"), n)
    if unit == "minute":
        return step_minute(_zero_below(fields, "hour"), n)
    if unit == "second":
        return step_second(_zero_below(fields, "minute"), n)
    raise ValueError(unit)


def _same(left, right):
    return tuple(int(v) for v in left) == tuple(int(v) for v in right)


def _lookup_roll(zone, fields, old_fields, old_stamp, skipped, repeated, rem=0.0):
    old = lookup(zone, old_fields)
    kind, pre, trans, post = lookup(zone, fields)
    return to_posix_keeping(kind, pre, trans, post, old[0], old[1], old[2], old_stamp, skipped, repeated, rem)


def _next_weekday(fields, target):
    """Strictly after ``fields``, on CCTZ weekday ``target`` (Monday is 0)."""
    for step in range(1, 8):
        candidate = step_day(fields, step)
        if weekday(candidate) == target:
            return candidate
    return fields


def _one_floor(seconds, zone, unit, n, week_start, origin):
    if math.isnan(seconds) or math.isinf(seconds):
        return seconds
    if unit == "asecond":
        return origin + _floor_n(seconds - origin, n)
    fields, rem = from_posix(seconds, zone)
    year, month, day, hour, minute, second = fields
    if unit == "second":
        ds = _floor_n(second + rem, n)
        whole = math.floor(ds)
        extra = ds - whole
        target = _add_unit(fields, "second", whole)
        return _lookup_roll(zone, target, fields, seconds, "boundary", "post", extra)
    if unit == "minute":
        target = _add_unit(fields, "minute", _floor_n(minute, n))
    elif unit == "hour":
        target = _add_unit(fields, "hour", _floor_n(hour, n))
    elif unit == "day":
        target = _add_unit(fields, "day", _floor_n1(day, n))
    elif unit == "week":
        target = step_day(_next_weekday(_zero_below(fields, "day"), week_start - 1), -7)
    elif unit == "season":
        target = _add_unit(fields, "month", _floor_n(month, n) - 1)
    elif unit == "month":
        target = _add_unit(fields, "month", _floor_n1(month, n))
    elif unit == "year":
        target = _add_unit((int(_floor_n(year, n)), 1, 1, 0, 0, 0), "year", 0)
    else:
        raise ValueError(unit)
    return _lookup_roll(zone, target, fields, seconds, "boundary", "post", 0.0)


def _one_ceiling(seconds, zone, unit, n, week_start, change, origin):
    if math.isnan(seconds) or math.isinf(seconds):
        return seconds
    if unit == "asecond":
        posix = origin + _ceil_n(seconds - origin, n)
        if (not change) and (seconds - math.floor(seconds) == 0) and (posix - n) == seconds:
            return seconds
        return posix
    fields, rem = from_posix(seconds, zone)
    year, month, day, hour, minute, second = fields
    on_boundary = rem == 0 and not change
    extra = 0.0
    if unit == "second":
        ds = _ceil_n(second + rem, n)
        if ds > 60:
            full = math.floor(ds / 60) * 60
            ds = _ceil_n(ds - full, n)
            fields = step_second(fields, int(full))
        whole = math.floor(ds)
        extra = ds - whole
        target = _add_unit(fields, "second", whole)
        back_unit, back_n = "second", n
    elif unit == "minute":
        dm = _ceil_n(minute, n)
        if dm > 60:
            full = math.floor(dm / 60) * 60
            dm = _ceil_n(dm - full, n)
            fields = step_second(fields, int(full) * 60)
        target = _add_unit(fields, "minute", dm)
        back_unit, back_n = "minute", n
    elif unit == "hour":
        target = _add_unit(fields, "hour", _ceil_n(hour, n))
        if target[3] > 0 and (target[2], target[1], target[0]) != (day, month, year):
            target = step_hour(target, int(_ceil_n(target[3], n) - target[3]))
        back_unit, back_n = "hour", n
    elif unit == "day":
        target = _add_unit(fields, "day", _ceil_n1(day, n))
        if target[2] > 1 and (target[1], target[0]) != (month, year):
            target = step_day(target, int(_ceil_n(target[2], n) - target[2] + 1))
        back_unit, back_n = "day", n
    elif unit == "week":
        target = _next_weekday(_zero_below(fields, "day"), week_start - 1)
        back_unit, back_n = "day", 7
    elif unit == "season":
        target = _add_unit(fields, "month", _ceil_n(month, n) - 1)
        back_unit, back_n = "month", n
    elif unit == "month":
        target = _add_unit(fields, "month", _ceil_n1(month, n))
        if target[1] > 1 and target[0] != year:
            target = step_month(target, int(_ceil_n1(target[1], n) - target[1] + 1))
        back_unit, back_n = "month", n
    elif unit == "year":
        target = (int(_ceil_n(year, n)), 1, 1, 0, 0, 0)
        back_unit, back_n = "year", n
    else:
        raise ValueError(unit)
    if on_boundary and extra == 0:
        if back_unit == "year":
            earlier = (int(target[0] - back_n), 1, 1, 0, 0, 0)
        elif back_unit == "month":
            earlier = step_month(target, -int(back_n))
        elif back_unit == "day":
            earlier = step_day(target, -int(back_n))
        elif back_unit == "hour":
            earlier = step_hour(target, -int(back_n))
        elif back_unit == "minute":
            earlier = step_minute(target, -int(back_n))
        else:
            earlier = step_second(target, -int(back_n))
        original = (year, month, day, hour, minute, int(second))
        if _same(original, earlier):
            return seconds
    return _lookup_roll(zone, target, fields, seconds, "boundary", "pre", extra)


def _apply(time, unit, week_start, origin, change, how):
    if isinstance(time, Posixct):
        seconds, tz = time.seconds, time.tz
    else:
        seconds, tz = np.asarray(time, dtype=float), "UTC"
    zone, label = load_zone(tz)
    n, name = parse_units(unit)
    kind, n = _adjust(name, n)
    origin_arr = np.atleast_1d(np.asarray(0 if origin is None else origin, dtype=float))
    out = np.empty(seconds.size, dtype=float)
    flat = seconds.reshape(-1)
    for i, value in enumerate(flat):
        orig = origin_arr[i] if origin_arr.size == flat.size else origin_arr[0]
        if how == "floor":
            out.reshape(-1)[i] = _one_floor(float(value), zone, kind, n, week_start, float(orig))
        else:
            out.reshape(-1)[i] = _one_ceiling(float(value), zone, kind, n, week_start, change, float(orig))
    return Posixct(out.reshape(seconds.shape), label), kind


def time_floor(time, unit="seconds", week_start=1, origin=0):
    result, _ = _apply(time, unit, week_start, origin, False, "floor")
    return result


def time_ceiling(time, unit="seconds", change_on_boundary=False, week_start=1, origin=0):
    result, _ = _apply(time, unit, week_start, origin, change_on_boundary, "ceiling")
    return result


def time_round(time, unit="second", week_start=1, origin=0):
    above, _ = _apply(time, unit, week_start, origin, True, "ceiling")
    below, _ = _apply(time, unit, week_start, origin, False, "floor")
    mid = above.seconds * 0 + (time.seconds if isinstance(time, Posixct) else np.asarray(time, dtype=float))
    choose_above = (above.seconds - mid) <= (mid - below.seconds)
    choose_above = np.where(np.isnan(choose_above), False, choose_above)
    out = np.where(choose_above, above.seconds, below.seconds)
    return Posixct(out, above.tz)
