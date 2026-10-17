"""warp_distance, warp_change, and warp_boundary."""

from __future__ import annotations

import math

import numpy as np

from warp.calendar import (
    compute_mday_distance,
    compute_yday_distance,
    floor_div,
    guarded_floor,
    guarded_floor_to_millisecond,
    is_leap_year,
    leap_years_before_and_including_year,
    mday_tables,
)
from warp.errors import WarpError
from warp.time import (
    Date,
    POSIXct,
    POSIXlt,
    as_date_days,
    as_datetime_seconds,
    components_of,
    convert_time_zone,
    day_offset_of,
    epoch_origin,
    month_offset_of,
    year_offset_of,
)

_PERIODS = (
    "year",
    "quarter",
    "month",
    "week",
    "yweek",
    "mweek",
    "day",
    "yday",
    "mday",
    "hour",
    "minute",
    "second",
    "millisecond",
)

_DATE_UNITS = {
    "hour": 24,
    "minute": 1440,
    "second": 86400,
    "millisecond": 86400000,
}

_POSIX_UNITS = {
    "hour": 3600,
    "minute": 60,
    "second": 1,
}


def c_message(where: str, why: str) -> str:
    return f"In C function `{where}()`: {why}"


def _dots(args, fn: str) -> None:
    if not args:
        return
    raise WarpError(
        f"`...` is not empty in `{fn}()`.\n"
        "These dots only exist to allow for future extensions and should be empty.\n"
        "Did you misspecify an argument?"
    )


def _pull_every(every) -> int:
    if isinstance(every, (list, tuple, np.ndarray)):
        raise WarpError(
            c_message("pull_every", f"`every` must have size 1, not {len(every)}")
        )
    if isinstance(every, bool) or every is None:
        kind = "logical" if isinstance(every, bool) else "NULL"
        raise WarpError(
            c_message("pull_every", f"`every` must be integer-ish, not {kind}")
        )
    if isinstance(every, (int, np.integer)):
        value = int(every)
    elif isinstance(every, (float, np.floating)):
        number = float(every)
        if not math.isfinite(number) or number > 2147483647 or number < -2147483648:
            value = None
        else:
            value = int(number)
    else:
        raise WarpError(
            c_message("pull_every", "`every` must be integer-ish, not character")
        )
    if value is None:
        raise WarpError(c_message("validate_every", "`every` must not be `NA`"))
    if value <= 0:
        raise WarpError(
            c_message(
                "validate_every",
                f"`every` must be an integer greater than 0, not {value}",
            )
        )
    return value


def _pull_bool(value, name: str) -> bool:
    if isinstance(value, (list, tuple, np.ndarray)):
        raise WarpError(
            c_message(f"pull_{name}", f"`{name}` must have size 1, not {len(value)}")
        )
    if not isinstance(value, bool):
        raise WarpError(
            c_message(f"pull_{name}", f"`{name}` must be logical, not double")
        )
    return value


def _as_time(value, where: str):
    if isinstance(value, (Date, POSIXct, POSIXlt)):
        return value
    raise WarpError(
        c_message(where, "`x` must inherit from 'Date', 'POSIXct', or 'POSIXlt'.")
    )


def _validate_origin(origin) -> None:
    if origin is None:
        return
    origin = _as_time(origin, "validate_origin")
    if len(origin) != 1:
        raise WarpError(
            c_message(
                "validate_origin",
                f"`origin` must have size 1, not {len(origin)}.",
            )
        )


def _period(period: str) -> str:
    if not isinstance(period, str):
        raise WarpError("`period` must be a single string.")
    if period not in _PERIODS:
        raise WarpError(f"Unknown `period` value '{period}'.")
    return period


def _nan_array(size: int) -> np.ndarray:
    return np.full(size, np.nan, dtype=np.float64)


def _length(value) -> int:
    return len(value)


def _group_offsets(offsets: list[int | None], origin_offset: int | None, every: int):
    out = _nan_array(len(offsets))
    for index, elt in enumerate(offsets):
        if elt is None:
            continue
        if origin_offset is not None:
            elt -= origin_offset
        out[index] = floor_div(elt, every)
    return out


def _origin_year(origin) -> int | None:
    if origin is None:
        return None
    offset = year_offset_of(origin, 0)
    if offset is None:
        raise WarpError(c_message("warp_distance_year", "`origin` cannot be `NA`."))
    return offset


def _origin_month(origin) -> int | None:
    if origin is None:
        return None
    offset = month_offset_of(origin, 0)
    if offset is None:
        raise WarpError(c_message("warp_distance_month", "`origin` cannot be `NA`."))
    return offset


def _origin_day(origin) -> int | None:
    if origin is None:
        return None
    offset = day_offset_of(origin, 0)
    if offset is None:
        raise WarpError(c_message("warp_distance_day", "`origin` cannot be `NA`."))
    return offset


def _distance_year(value, every: int, origin):
    return _group_offsets(
        [year_offset_of(value, index) for index in range(_length(value))],
        _origin_year(origin),
        every,
    )


def _distance_month(value, every: int, origin):
    return _group_offsets(
        [month_offset_of(value, index) for index in range(_length(value))],
        _origin_month(origin),
        every,
    )


def _distance_day(value, every: int, origin):
    return _group_offsets(
        [day_offset_of(value, index) for index in range(_length(value))],
        _origin_day(origin),
        every,
    )


def _origin_yday(origin):
    if origin is None:
        return 0, 0, False, leap_years_before_and_including_year(0)
    parts = components_of(origin, 0)
    if parts is None:
        raise WarpError(
            c_message("int_date_get_origin_yday_components", "The `origin` cannot be `NA`.")
        )
    _days, year_offset, _month, _day, yday = parts
    return (
        year_offset,
        yday,
        is_leap_year(year_offset + 1970),
        leap_years_before_and_including_year(year_offset),
    )


def _distance_yday(value, every: int, origin):
    if every > 364:
        raise WarpError(
            c_message(
                "warp_distance_yday",
                "The maximum allowed value of `every` for `period = 'yday'` is 364.",
            )
        )
    units_non_leap = (365 - 1) // every + 1
    units_leap = (366 - 1) // every + 1
    origin_year, origin_yday, origin_leap, origin_leaps = _origin_yday(origin)
    out = _nan_array(_length(value))
    for index in range(_length(value)):
        parts = components_of(value, index)
        if parts is None:
            continue
        days, year_offset, _month, _day, yday = parts
        out[index] = compute_yday_distance(
            days,
            year_offset,
            yday,
            origin_year,
            origin_yday,
            origin_leap,
            units_leap,
            units_non_leap,
            origin_leaps,
            every,
        )
    return out


def _origin_mday(origin):
    if origin is None:
        return 0, 0
    parts = components_of(origin, 0)
    if parts is None:
        raise WarpError(
            c_message("int_date_get_origin_mday_components", "The `origin` cannot be `NA`.")
        )
    _days, year_offset, month, _day, _yday = parts
    return year_offset, month


def _distance_mday(value, every: int, origin):
    if every > 30:
        raise WarpError(
            c_message(
                "warp_distance_mday",
                "The maximum allowed value of `every` for `period = 'mday'` is 30.",
            )
        )
    origin_year, origin_month = _origin_mday(origin)
    tables = mday_tables(every, origin_year, origin_month)
    units_leap, units_non_leap, per_leap, per_non_leap, up_to_origin, leaps = tables
    out = _nan_array(_length(value))
    for index in range(_length(value)):
        parts = components_of(value, index)
        if parts is None:
            continue
        _days, year_offset, month, day, _yday = parts
        out[index] = compute_mday_distance(
            day,
            month,
            year_offset,
            origin_year,
            per_leap,
            per_non_leap,
            units_leap,
            units_non_leap,
            up_to_origin,
            leaps,
            every,
        )
    return out


def _distance_clock_date(value: Date, unit: int, every: int, origin):
    origin_offset = None if origin is None else as_date_days(origin)
    out = _nan_array(len(value))
    for index, day in enumerate(value.days):
        if day is None:
            continue
        if origin_offset is not None:
            day -= origin_offset
        out[index] = floor_div(day * unit, every)
    return out


def _distance_clock_posix(seconds, unit: int | None, every: int, origin, millisecond: bool):
    if origin is None:
        origin_offset = None
    else:
        origin_seconds = as_datetime_seconds(origin)[0]
        if origin_seconds is None or not math.isfinite(origin_seconds):
            raise WarpError(
                c_message("origin_to_seconds_from_epoch", "`origin` must be finite.")
            )
        origin_offset = (
            guarded_floor_to_millisecond(origin_seconds)
            if millisecond
            else guarded_floor(origin_seconds)
        )
    out = _nan_array(len(seconds))
    for index, value in enumerate(seconds):
        if value is None or not math.isfinite(value):
            continue
        elt = (
            guarded_floor_to_millisecond(value)
            if millisecond
            else guarded_floor(value)
        )
        if origin_offset is not None:
            elt -= origin_offset
        if unit not in (None, 1):
            elt = floor_div(elt, unit)
        out[index] = floor_div(elt, every)
    return out


def _distance_clock(value, period: str, every: int, origin):
    if isinstance(value, POSIXlt):
        value = POSIXct(as_datetime_seconds(value), value.tz)
    if isinstance(value, Date):
        return _distance_clock_date(value, _DATE_UNITS[period], every, origin)
    unit = None if period == "millisecond" else _POSIX_UNITS[period]
    return _distance_clock_posix(
        value.seconds,
        unit,
        every,
        origin,
        millisecond=period == "millisecond",
    )


def _distance(value, period: str, every: int, origin) -> np.ndarray:
    if period == "quarter":
        return _distance_month(value, every * 3, origin)
    if period == "week":
        return _distance_day(value, every * 7, origin)
    if period == "yweek":
        if every > 52:
            raise WarpError(
                c_message(
                    "warp_distance_yweek",
                    "The maximum allowed value of `every` for `period = 'yweek'` is 52.",
                )
            )
        return _distance_yday(value, every * 7, origin)
    if period == "mweek":
        if every > 4:
            raise WarpError(
                c_message(
                    "warp_distance_mweek",
                    "The maximum allowed value of `every` for `period = 'mweek'` is 4.",
                )
            )
        return _distance_mday(value, every * 7, origin)
    if period == "year":
        return _distance_year(value, every, origin)
    if period == "month":
        return _distance_month(value, every, origin)
    if period == "day":
        return _distance_day(value, every, origin)
    if period == "yday":
        return _distance_yday(value, every, origin)
    if period == "mday":
        return _distance_mday(value, every, origin)
    return _distance_clock(value, period, every, origin)


def warp_distance(x, period, *args, every=1, origin=None) -> np.ndarray:
    """Distances from `origin`, in groups of `every` periods."""
    _dots(args, "warp_distance")
    every_value = _pull_every(every)
    period_name = _period(period)
    value = _as_time(x, "warp_distance")
    _validate_origin(origin)
    if origin is None:
        origin = epoch_origin(value)
    else:
        origin = _as_time(origin, "validate_origin")
        value = convert_time_zone(value, origin)
    return _distance(value, period_name, every_value, origin)


def _equal(current: float, previous: float) -> bool:
    if math.isnan(current):
        return math.isnan(previous)
    return current == previous


def _change_from_distances(distances: np.ndarray, last: bool, endpoint: bool) -> np.ndarray:
    size = int(distances.shape[0])
    if size == 0:
        return np.array([], dtype=np.float64)
    if size == 1:
        return np.array([1.0], dtype=np.float64)

    out = []
    if last:
        if endpoint and _equal(float(distances[0]), float(distances[1])):
            out.append(1.0)
    else:
        out.append(1.0)

    adjustment = 0 if last else 1
    previous = float(distances[0])
    for index in range(1, size):
        current = float(distances[index])
        if _equal(current, previous):
            continue
        out.append(float(index + adjustment))
        previous = current

    if last:
        out.append(float(size))
    elif endpoint and _equal(float(distances[size - 2]), float(distances[size - 1])):
        out.append(float(size))
    return np.asarray(out, dtype=np.float64)


def warp_change(x, period, *args, every=1, origin=None, last=True, endpoint=False) -> np.ndarray:
    """1-based locations where the distance changes."""
    _dots(args, "warp_change")
    last_value = _pull_bool(last, "last")
    endpoint_value = _pull_bool(endpoint, "endpoint")
    distances = warp_distance(x, period, every=every, origin=origin)
    return _change_from_distances(distances, last_value, endpoint_value)


class Boundary:
    """A start/stop data frame. Both columns are 1-based doubles."""

    def __init__(self, start: np.ndarray, stop: np.ndarray):
        self.start = start
        self.stop = stop

    def __len__(self) -> int:
        return int(self.start.shape[0])

    def __repr__(self) -> str:
        return f"Boundary(start={self.start.tolist()}, stop={self.stop.tolist()})"


def warp_boundary(x, period, *args, every=1, origin=None) -> Boundary:
    """Start and stop locations of each distance group."""
    _dots(args, "warp_boundary")
    stops = warp_change(x, period, every=every, origin=origin, last=True, endpoint=False)
    size = int(stops.shape[0])
    if size == 0:
        starts = np.array([], dtype=np.float64)
    elif size == 1:
        starts = np.array([1.0], dtype=np.float64)
    else:
        starts = np.empty(size, dtype=np.float64)
        starts[0] = 1.0
        starts[1:] = stops[:-1] + 1.0
    return Boundary(starts, stops)
