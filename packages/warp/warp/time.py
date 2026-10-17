"""Date, POSIXct, and POSIXlt values, and the time-zone relabel warp uses."""

from __future__ import annotations

import math
import warnings
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import numpy as np

from warp.calendar import convert_days_to_components, days_before_year_since_1900
from warp.errors import WarpError

_EPOCH = date(1970, 1, 1).toordinal()


def c_message(where: str, why: str) -> str:
    return f"In C function `{where}()`: {why}"


def _is_missing(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and not math.isfinite(value):
        return True
    if isinstance(value, np.floating) and not np.isfinite(value):
        return True
    return False


def _as_sequence(values):
    if isinstance(values, str):
        return [values]
    if isinstance(values, (Date, POSIXct, POSIXlt)):
        raise WarpError(
            c_message(
                "warp_distance",
                "`x` must inherit from 'Date', 'POSIXct', or 'POSIXlt'.",
            )
        )
    if isinstance(values, np.ndarray):
        return values.tolist()
    if isinstance(values, (list, tuple)):
        return list(values)
    return [values]


def date_to_days(value) -> int | None:
    if _is_missing(value):
        return None
    if isinstance(value, str):
        year, month, day = (int(part) for part in value.split("-"))
        return date(year, month, day).toordinal() - _EPOCH
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.toordinal() - _EPOCH
    if isinstance(value, bool):
        raise WarpError(
            c_message("date_get_day_offset", "Unknown `Date` type logical.")
        )
    if isinstance(value, int):
        return value
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if not math.isfinite(number):
            return None
        return int(number)
    raise WarpError(
        c_message("warp_distance", "`x` must inherit from 'Date', 'POSIXct', or 'POSIXlt'.")
    )


class Date:
    """Days since 1970-01-01. A fractional day is truncated toward zero."""

    def __init__(self, days):
        self.days = [date_to_days(value) for value in _as_sequence(days)]
        self.tz = "UTC"
        self.kind = "date"

    def __len__(self) -> int:
        return len(self.days)


class POSIXct:
    """Seconds since 1970-01-01 00:00:00 UTC, labeled with `tz`."""

    def __init__(self, seconds, tz: str | None = "UTC"):
        parsed = []
        for value in _as_sequence(seconds):
            if _is_missing(value):
                parsed.append(None)
            elif isinstance(value, str):
                parsed.append(_parse_posixct(value, tz if tz else ""))
            elif isinstance(value, bool):
                raise WarpError(
                    c_message(
                        "posixct_warp_distance_hour",
                        "Unknown `POSIXct` type logical.",
                    )
                )
            elif isinstance(value, (int, float, np.integer, np.floating)):
                parsed.append(float(value))
            else:
                raise WarpError(
                    c_message(
                        "warp_distance",
                        "`x` must inherit from 'Date', 'POSIXct', or 'POSIXlt'.",
                    )
                )
        self.seconds = parsed
        self.tz = "" if tz is None else tz
        self.kind = "posixct"

    def __len__(self) -> int:
        return len(self.seconds)


class POSIXlt:
    """Broken-down local time. `year` is years since 1900 and `mon` is 0-11."""

    def __init__(
        self,
        year,
        mon,
        mday,
        hour=0,
        minute=0,
        second=0,
        yday=None,
        tz: str | None = "UTC",
        isdst=-1,
    ):
        years = _as_sequence(year)
        size = len(years)
        self.year = [_optional_int(value) for value in years]
        self.mon = _align(_as_sequence(mon), size)
        self.mday = _align(_as_sequence(mday), size)
        self.hour = _align(_as_sequence(hour), size)
        self.minute = _align(_as_sequence(minute), size)
        self.second = _align_float(_as_sequence(second), size)
        self.tz = "" if tz is None else tz
        self.isdst = _align(_as_sequence(isdst), size)
        if yday is None:
            self.yday = [_yday_from_civil(item) for item in self._rows()]
        else:
            self.yday = _align(_as_sequence(yday), size)
        self.kind = "posixlt"

    def _rows(self):
        for index, year in enumerate(self.year):
            yield (
                year,
                self.mon[index],
                self.mday[index],
                self.hour[index],
                self.minute[index],
                self.second[index],
                self.isdst[index],
            )

    def __len__(self) -> int:
        return len(self.year)


def _optional_int(value):
    if _is_missing(value):
        return None
    return int(value)


def _align(values, size):
    if len(values) == 1 and size != 1:
        values = values * size
    if len(values) != size:
        raise WarpError(
            c_message("validate_origin", f"`origin` must have size 1, not {len(values)}.")
        )
    return [_optional_int(value) for value in values]


def _align_float(values, size):
    if len(values) == 1 and size != 1:
        values = values * size
    if len(values) != size:
        raise WarpError(
            c_message("validate_origin", f"`origin` must have size 1, not {len(values)}.")
        )
    out = []
    for value in values:
        if _is_missing(value):
            out.append(None)
        else:
            out.append(float(value))
    return out


def _yday_from_civil(row) -> int | None:
    year, mon, mday, *_rest = row
    if year is None or mon is None or mday is None:
        return None
    civil = date(year + 1900, mon + 1, mday)
    return civil.timetuple().tm_yday - 1


def _zone(tz: str):
    if tz in ("UTC", "GMT"):
        return timezone.utc
    if tz == "":
        return datetime.now().astimezone().tzinfo
    return ZoneInfo(tz)


def _parse_posixct(text: str, tz: str) -> float:
    if " " in text:
        day, clock = text.split(" ", 1)
    else:
        day, clock = text, "00:00:00"
    year, month, day_n = (int(part) for part in day.split("-"))
    parts = clock.split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    second = float(parts[2]) if len(parts) > 2 else 0.0
    whole = int(second)
    micro = int(round((second - whole) * 1_000_000))
    stamp = datetime(year, month, day_n, hour, minute, whole, micro, _zone(tz))
    return stamp.timestamp()


def printable_zone(tz: str) -> str:
    return "local" if tz == "" else tz


def zone_of(value: Date | POSIXct | POSIXlt) -> str:
    return value.tz


def epoch_origin(value: Date | POSIXct | POSIXlt):
    """1970-01-01 00:00:00 in `value`'s zone, or None when that is UTC."""
    tz = zone_of(value)
    if tz in ("UTC", "GMT"):
        return None
    instant = datetime.fromtimestamp(0, _zone(tz))
    offset = instant.utcoffset()
    if offset is None or offset.total_seconds() == 0:
        return None
    return POSIXct([-offset.total_seconds()], tz)


def convert_time_zone(value, origin):
    left = zone_of(value)
    right = zone_of(origin)
    if left == right:
        return value
    warnings.warn(
        f"`x` ({printable_zone(left)}) and `origin` ({printable_zone(right)}) "
        "do not have the same time zone. "
        "Converting `x` to the time zone of `origin`. "
        "It is highly advised to provide `x` and `origin` with the same time zone.",
        UserWarning,
        stacklevel=3,
    )
    seconds = as_datetime_seconds(value)
    return POSIXct(seconds, right)


def as_datetime_seconds(value: Date | POSIXct | POSIXlt) -> list[float | None]:
    if isinstance(value, Date):
        return [None if day is None else float(day) * 86400.0 for day in value.days]
    if isinstance(value, POSIXct):
        return list(value.seconds)
    return [_posixlt_to_seconds(value, index) for index in range(len(value))]


def _posixlt_to_seconds(value: POSIXlt, index: int) -> float | None:
    year = value.year[index]
    if year is None or value.mon[index] is None or value.mday[index] is None:
        return None
    second = 0.0 if value.second[index] is None else value.second[index]
    whole = int(math.trunc(second))
    micro = int(round((second - whole) * 1_000_000))
    fold = 1 if value.isdst[index] == 0 else 0
    stamp = datetime(
        year + 1900,
        value.mon[index] + 1,
        value.mday[index],
        0 if value.hour[index] is None else value.hour[index],
        0 if value.minute[index] is None else value.minute[index],
        whole,
        micro,
        _zone(value.tz),
        fold=fold,
    )
    return stamp.timestamp()


def civil_of_seconds(seconds: float, tz: str) -> tuple[int, int, int, int]:
    """Local (year offset from 1970, month 0-11, day 0-30, yday)."""
    stamp = datetime.fromtimestamp(seconds, _zone(tz))
    yday = stamp.timetuple().tm_yday - 1
    return stamp.year - 1970, stamp.month - 1, stamp.day - 1, yday


def ymd_to_days(year: int, month: int, day: int) -> int:
    """`month` and `day` are 1-based."""
    return date(year, month, day).toordinal() - _EPOCH


def as_date_days(value: Date | POSIXct | POSIXlt) -> int:
    if len(value) != 1:
        raise WarpError(
            c_message("validate_origin", f"`origin` must have size 1, not {len(value)}.")
        )
    if isinstance(value, Date):
        day = value.days[0]
        if day is None:
            raise WarpError(
                c_message("origin_to_days_from_epoch", "`origin` must not be `NA`.")
            )
        return day
    if isinstance(value, POSIXct):
        seconds = value.seconds[0]
        if seconds is None or not math.isfinite(seconds):
            raise WarpError(
                c_message("origin_to_days_from_epoch", "`origin` must not be `NA`.")
            )
        year, month, day, _yday = civil_of_seconds(seconds, value.tz)
        return ymd_to_days(year + 1970, month + 1, day + 1)
    year = value.year[0]
    mon = value.mon[0]
    mday = value.mday[0]
    if year is None or mon is None or mday is None:
        raise WarpError(
            c_message("origin_to_days_from_epoch", "`origin` must not be `NA`.")
        )
    return ymd_to_days(year + 1900, mon + 1, mday)


def year_offset_of(value: Date | POSIXct | POSIXlt, index: int) -> int | None:
    if isinstance(value, Date):
        day = value.days[index]
        if day is None:
            return None
        return convert_days_to_components(day)[0]
    if isinstance(value, POSIXct):
        seconds = value.seconds[index]
        if seconds is None or not math.isfinite(seconds):
            return None
        return civil_of_seconds(seconds, value.tz)[0]
    year = value.year[index]
    if year is None:
        return None
    return year - 70


def month_offset_of(value: Date | POSIXct | POSIXlt, index: int) -> int | None:
    if isinstance(value, Date):
        day = value.days[index]
        if day is None:
            return None
        year_offset, month, _day, _yday = convert_days_to_components(day)
        return year_offset * 12 + month
    if isinstance(value, POSIXct):
        seconds = value.seconds[index]
        if seconds is None or not math.isfinite(seconds):
            return None
        year_offset, month, _day, _yday = civil_of_seconds(seconds, value.tz)
        return year_offset * 12 + month
    year = value.year[index]
    month = value.mon[index]
    if year is None or month is None:
        return None
    return (year - 70) * 12 + month


def day_offset_of(value: Date | POSIXct | POSIXlt, index: int) -> int | None:
    if isinstance(value, Date):
        return value.days[index]
    if isinstance(value, POSIXct):
        seconds = value.seconds[index]
        if seconds is None or not math.isfinite(seconds):
            return None
        year_offset, _month, _day, yday = civil_of_seconds(seconds, value.tz)
        return days_before_year_since_1900(year_offset + 70) + yday
    year = value.year[index]
    yday = value.yday[index]
    if year is None or yday is None:
        return None
    return days_before_year_since_1900(year) + yday


def components_of(value: Date | POSIXct | POSIXlt, index: int):
    """(days, year offset, month 0-11, day 0-30, yday) or None."""
    if isinstance(value, Date):
        day = value.days[index]
        if day is None:
            return None
        year_offset, month, day_of_month, yday = convert_days_to_components(day)
        return day, year_offset, month, day_of_month, yday
    if isinstance(value, POSIXct):
        seconds = value.seconds[index]
        if seconds is None or not math.isfinite(seconds):
            return None
        year_offset, month, day_of_month, yday = civil_of_seconds(seconds, value.tz)
        days = days_before_year_since_1900(year_offset + 70) + yday
        return days, year_offset, month, day_of_month, yday
    year = value.year[index]
    if year is None or value.mon[index] is None or value.yday[index] is None:
        return None
    year_offset = year - 70
    month = value.mon[index]
    yday = value.yday[index]
    day_of_month = 0 if value.mday[index] is None else value.mday[index] - 1
    days = days_before_year_since_1900(year) + yday
    return days, year_offset, month, day_of_month, yday
