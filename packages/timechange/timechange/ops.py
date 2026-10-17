"""The ten exported timechange operations."""

import math

import numpy as np

from .civil import (
    Posixct,
    days_in_month,
    from_posix,
    load_zone,
    lookup,
    n_sec,
    step_day,
    step_hour,
    step_minute,
    step_month,
    step_second,
    step_year,
    to_posix,
    to_posix_keeping,
    valid_tz,
    weekday,
    yearday,
)

_MONTH = {"full": "full", "preday": "preday", "last": "preday", "boundary": "boundary",
          "postday": "postday", "first": "postday", "NA": "NA", "NAym": "NAym", "na": "NA"}
_DST = {"pre": "pre", "last": "pre", "boundary": "boundary", "post": "post", "first": "post",
        "NA": "NA", "na": "NA", "xfirst": "xfirst", "xlast": "xlast"}


def _as_seconds(time):
    if isinstance(time, Posixct):
        return time.seconds, time.tz
    array = np.asarray(time, dtype=float)
    return array, "UTC"


def _roll_month(name):
    key = _MONTH.get(name)
    if key is None:
        raise ValueError(f"Invalid roll_month '{name}'")
    return key


def _roll_dst(value, allow_x=False):
    if value is None:
        value = ["post", "pre"]
    if isinstance(value, str):
        value = [value]
    if len(value) == 0 or len(value) > 2:
        raise ValueError("roll_dst must have length 1 or 2")
    if len(value) == 1:
        value = [value[0], value[0]]
    out = []
    for item in value:
        key = _DST.get(item)
        if key is None:
            raise ValueError(f"Invalid roll_dst '{item}'")
        if key in ("xfirst", "xlast") and not allow_x:
            raise ValueError(f"'{key}' dst_roll is not meaningful here")
        out.append(key)
    return out[0], out[1]


def _recycle(value, n):
    if value is None:
        return None
    array = np.atleast_1d(np.asarray(value, dtype=float))
    if array.size == 1:
        return np.repeat(array, n)
    if array.size != n:
        raise ValueError("period length does not match time")
    return array


def time_add(time, periods=None, roll_month="preday", roll_dst=("post", "pre"), **units):
    """Add civil periods. Units are applied from years down to seconds."""
    seconds, tz = _as_seconds(time)
    zone, _ = load_zone(tz)
    month_roll = _roll_month(roll_month)
    skipped, repeated = _roll_dst(roll_dst, allow_x=True)
    periods = dict(periods or {})
    periods.update(units)
    n = seconds.size
    pieces = {name: _recycle(periods.get(name), n) for name in
              ("year", "month", "week", "day", "hour", "minute", "second")}
    out = np.empty(n, dtype=float)
    for i in range(n):
        value = seconds.reshape(-1)[i]
        if math.isnan(value) or math.isinf(value):
            out.reshape(-1)[i] = value
            continue
        fields, rem = from_posix(value, zone)
        original_day = fields[2]
        negative = False
        seen = False
        for name, step in (("year", step_year), ("month", step_month)):
            amount = 0 if pieces[name] is None else pieces[name][i]
            if math.isnan(amount) or amount == 0:
                continue
            if not seen:
                negative = amount < 0
                seen = True
            fields = step(fields, int(amount))
        if fields[2] != original_day and (pieces["year"] is not None or pieces["month"] is not None):
            year, month, day, hour, minute, second = fields
            if month_roll == "preday":
                fields = (year, month, 1, hour, minute, second)
                fields = step_day(fields, -1)
            elif month_roll == "boundary":
                fields = (year, month, 1, 0, 0, 0)
                rem = 0.0
            elif month_roll == "postday":
                fields = (year, month, 1, hour, minute, second)
            elif month_roll == "NA":
                out.reshape(-1)[i] = math.nan
                continue
        for name, step in (("week", lambda f, k: step_day(f, 7 * k)),
                           ("day", step_day), ("hour", step_hour),
                           ("minute", step_minute), ("second", step_second)):
            amount = 0 if pieces[name] is None else pieces[name][i]
            if math.isnan(amount) or amount == 0:
                continue
            if not seen:
                negative = amount < 0
                seen = True
            whole = math.floor(amount) if name == "second" else int(amount)
            if name == "second":
                rem += amount - whole
            fields = step(fields, whole)
        kind, pre, trans, post = lookup(zone, fields)
        posix = to_posix(kind, pre, trans, post, skipped, repeated, negative)
        if math.isnan(posix):
            out.reshape(-1)[i] = math.nan
        else:
            out.reshape(-1)[i] = posix + rem
    return Posixct(out.reshape(seconds.shape), tz)


def time_subtract(time, periods=None, roll_month="preday", roll_dst=("pre", "post"), **units):
    periods = {key: -value for key, value in dict(periods or {}).items()}
    for key, value in units.items():
        periods[key] = periods.get(key, 0) - value
    return time_add(time, periods, roll_month=roll_month, roll_dst=roll_dst)


def time_update(time, exact=False, roll_month="preday", roll_dst=("boundary", "post"),
                week_start=1, tz=None, **components):
    """Set absolute civil components, then normalize."""
    seconds, source_tz = _as_seconds(time)
    zone, _ = load_zone(source_tz)
    dest_zone, dest_label = load_zone(source_tz if tz is None else tz)
    month_roll = _roll_month(roll_month)
    skipped, repeated = _roll_dst(roll_dst, allow_x=False)
    n = seconds.size
    names = ("year", "month", "yday", "mday", "wday", "hour", "minute", "second")
    supplied = [name for name in names if components.get(name) is not None]
    day_parts = [name for name in ("yday", "mday", "wday") if name in supplied]
    if len(day_parts) > 1:
        raise ValueError("Conflicting days input, only one of yday, mday and wday must be supplied")
    if "yday" in supplied and ("month" in supplied or "mday" in supplied):
        raise ValueError("Setting `yday` in combination with `month` or `mday` is not supported")
    if "wday" in supplied and ("year" in supplied or "month" in supplied or "mday" in supplied):
        raise ValueError("Setting `yday` in combination with `year`, `month` or `mday` is not supported")
    pieces = {name: _recycle(components.get(name), n) for name in names}
    out = np.empty(n, dtype=float)
    for i in range(n):
        value = seconds.reshape(-1)[i]
        if math.isnan(value) or math.isinf(value):
            out.reshape(-1)[i] = value
            continue
        fields, rem = from_posix(value, zone)
        old_kind, old_pre, old_trans, old_post = lookup(zone, fields)
        year, month, day, hour, minute, second = fields
        requested = {}
        for name in names:
            if pieces[name] is not None and not math.isnan(pieces[name][i]):
                requested[name] = pieces[name][i]
        if "year" in requested:
            year = int(requested["year"])
        if "month" in requested:
            month = int(requested["month"])
        if "mday" in requested:
            day = int(requested["mday"])
        if "hour" in requested:
            hour = int(requested["hour"])
        if "minute" in requested:
            minute = int(requested["minute"])
        if "second" in requested:
            second = int(math.floor(requested["second"]))
            rem = requested["second"] - second
        if month_roll == "NAym" and n_sec(year, month, day, 0, 0, 0)[2] != day:
            out.reshape(-1)[i] = math.nan
            continue
        civil_month = n_sec(year, month, 1, 0, 0, 0)[1]
        if "yday" in requested:
            base = n_sec(year, month, day, 0, 0, 0)
            day = base[2] + int(requested["yday"]) - yearday(base)
            year, month = base[0], base[1]
        if "wday" in requested:
            base = n_sec(year, month, day, 0, 0, 0)
            current = (weekday(base) + 8 - week_start) % 7
            day = base[2] - current - 1 + int(requested["wday"])
            year, month = base[0], base[1]
        fields = n_sec(year, month, day, hour, minute, second)
        if exact:
            invalid = fields != (year, month, day, hour, minute, second)
            if "yday" in requested:
                invalid = yearday(fields) != int(requested["yday"])
            if invalid:
                out.reshape(-1)[i] = math.nan
                continue
        elif "yday" not in requested and "wday" not in requested and fields[2] != day and fields[1] != civil_month:
            if month_roll == "preday":
                fields = step_day((fields[0], fields[1], 1, fields[3], fields[4], fields[5]), -1)
            elif month_roll == "boundary":
                fields = (fields[0], fields[1], 1, 0, 0, 0)
                rem = 0.0
            elif month_roll == "postday":
                fields = (fields[0], fields[1], 1, fields[3], fields[4], fields[5])
            elif month_roll == "NA":
                out.reshape(-1)[i] = math.nan
                continue
        kind, pre, trans, post = lookup(dest_zone, fields)
        posix = to_posix_keeping(
            kind, pre, trans, post, old_kind, old_pre, old_trans, value,
            skipped, repeated, rem,
        )
        out.reshape(-1)[i] = posix
    return Posixct(out.reshape(seconds.shape), dest_label)


def time_get(time, components=None, week_start=1):
    """Civil components of each instant. ``wday`` is 0 for the week start."""
    if components is None:
        components = ["year", "month", "yday", "mday", "wday", "hour", "minute", "second"]
    seconds, tz = _as_seconds(time)
    zone, _ = load_zone(tz)
    columns = {}
    for name in components:
        if name not in {"year", "month", "yday", "mday", "day", "wday", "hour", "minute", "second"}:
            raise ValueError(f"Invalid datetime component '{name}'")
        columns[name] = np.empty(seconds.size, dtype=float)
    for i, value in enumerate(seconds.reshape(-1)):
        if math.isnan(value) or math.isinf(value):
            for column in columns.values():
                column.reshape(-1)[i] = value
            continue
        fields, rem = from_posix(value, zone)
        year, month, day, hour, minute, second = fields
        values = {
            "year": year, "month": month, "yday": yearday(fields), "mday": day,
            "day": day, "wday": (weekday(fields) + 8 - week_start) % 7,
            "hour": hour, "minute": minute, "second": second + rem,
        }
        for name, column in columns.items():
            column.reshape(-1)[i] = values[name]
    return {name: columns[name].reshape(seconds.shape) for name in components}


def time_force_tz(time, tz, roll_dst=("boundary", "post"), tzout=None):
    """Keep the clock time and change the zone.

    ``tz`` may be one name or one name per instant. ``tzout`` is the zone
    stored on the result when the names differ.
    """
    seconds, source = _as_seconds(time)
    source_zone, _ = load_zone(source)
    names = np.atleast_1d(np.asarray(tz, dtype=object)).reshape(-1)
    if names.size == 1:
        names = np.repeat(names, seconds.size)
    elif names.size != seconds.size:
        raise ValueError("tz length does not match time")
    label = str(names[0] if tzout is None else tzout)
    skipped, repeated = _roll_dst(roll_dst, allow_x=False)
    out = np.empty(seconds.size, dtype=float)
    cache = {}
    for i, value in enumerate(seconds.reshape(-1)):
        if math.isnan(value) or math.isinf(value):
            out.reshape(-1)[i] = value
            continue
        dest_name = str(names[i])
        if dest_name not in cache:
            cache[dest_name] = load_zone(dest_name)[0]
        fields, rem = from_posix(value, source_zone)
        old = lookup(source_zone, fields)
        kind, pre, trans, post = lookup(cache[dest_name], fields)
        out.reshape(-1)[i] = to_posix_keeping(
            kind, pre, trans, post, old[0], old[1], old[2], value,
            skipped, repeated, rem,
        )
    return Posixct(out.reshape(seconds.shape), label)


def time_at_tz(time, tz):
    """Keep the instant and change the zone attribute."""
    seconds, _ = _as_seconds(time)
    try:
        _, label = load_zone(tz)
    except ValueError:
        label = "UTC"
    return Posixct(seconds, label)


def time_clock_at_tz(time, tz=None, units="secs"):
    """Seconds, or hours, since local midnight."""
    seconds, source = _as_seconds(time)
    zone, _ = load_zone(source if tz is None else tz)
    out = np.empty(seconds.size, dtype=float)
    for i, value in enumerate(seconds.reshape(-1)):
        if math.isnan(value) or math.isinf(value):
            out.reshape(-1)[i] = value
            continue
        fields, rem = from_posix(value, zone)
        midnight = (fields[0], fields[1], fields[2], 0, 0, 0)
        kind, pre, trans, post = lookup(zone, midnight)
        clock = value - pre + rem
        out.reshape(-1)[i] = clock / 3600 if units == "hours" else clock
    return out.reshape(seconds.shape)


def valid_timezone(name):
    return valid_tz(name)
