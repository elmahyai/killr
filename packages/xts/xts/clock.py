"""Clock helpers from xts 0.14.3: firstof, lastof, align.time, and endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from xts.ordered import XtsError

_ON = (
    "years",
    "quarters",
    "months",
    "weeks",
    "days",
    "hours",
    "minutes",
    "seconds",
    "milliseconds",
    "microseconds",
    "ms",
    "us",
)
_MONTH_LENGTHS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def align_time(x, n: int = 60):
    """Round each timestamp up to the next multiple of ``n`` seconds."""
    if n <= 0:
        raise XtsError("'n' must be positive")
    return [_align(float(value), n) for value in x]


def firstof(year=1970, month=1, day=1, hour=0, minute=0, sec=0, tz: str = "") -> float:
    """The first instant of a period, as seconds since the epoch."""
    return _stamp(int(year), int(month), int(day), int(hour), int(minute), float(sec), tz)


def lastof(year=1970, month=12, day=None, hour=23, minute=59, sec=59, subsec=0.99999, tz: str = "") -> float:
    """The last instant of a period, as seconds since the epoch."""
    year = int(year)
    month = int(month)
    if day is None:
        if month == 2 and _leap(year):
            day = 29
        else:
            day = _MONTH_LENGTHS[month - 1]
    second = float(sec)
    if year >= 1970:
        second += float(subsec)
    if year == 1969 and month == 12 and day == 31 and hour == 23 and minute == 59 and second == 59 and (tz == "" or tz.upper() in {"UTC", "GMT"}):
        second -= 1
    return _stamp(year, month, int(day), int(hour), int(minute), second, tz)


def endpoints(x, on: str = "months", k: int = 1) -> list[int]:
    """Positions of the last observation in each period. The vector starts at 0."""
    if k < 1:
        raise XtsError("'k' must be > 0")
    stored = getattr(x, "index", None)
    if isinstance(stored, (list, tuple)):
        seconds = [float(value) for value in stored]
    else:
        seconds = [float(value) for value in x]
    count = len(seconds)
    if on in ("secs", "mins"):
        on = on[:3]
    on = _match_arg(on, _ON, "on")
    parts = [_parts(value) for value in seconds]
    if on == "years":
        buckets = [part[0] // k + 1 for part in parts]
        return _which_changes(buckets, count)
    if on == "quarters":
        buckets = [part[0] * 100 + 190000 + part[1] // 3 + 1 for part in parts]
        found = _which_changes(buckets, count)
        return _include_last(found, k) if k > 1 else found
    if on == "months":
        buckets = [part[0] * 100 + 190000 + part[1] for part in parts]
        found = _endpoint_values(buckets, 1, 1, True)
        return _include_last(found, k) if k > 1 else found
    if on == "weeks":
        return _endpoint_values([value + 3 * 86400 for value in seconds], 604800, k, True)
    if on == "days":
        buckets = [part[0] * 1000 + 1900000 + part[2] for part in parts]
        return _endpoint_values(buckets, 1, k, True)
    if on == "hours":
        return _endpoint_values(seconds, 3600, k, True)
    if on == "minutes":
        return _endpoint_values(seconds, 60, k, True)
    if on == "seconds":
        return _endpoint_values(seconds, 1, k, True)
    if on in ("ms", "milliseconds"):
        return _endpoint_values([value * 1e3 for value in seconds], 1, k, True)
    return _endpoint_values([value * 1e6 for value in seconds], 1, k, True)


def nseconds(x) -> int:
    return len(endpoints(x, on="seconds")) - 1


def nminutes(x) -> int:
    return len(endpoints(x, on="minutes")) - 1


def nhours(x) -> int:
    return len(endpoints(x, on="hours")) - 1


def ndays(x) -> int:
    return len(endpoints(x, on="days")) - 1


def nweeks(x) -> int:
    return len(endpoints(x, on="weeks")) - 1


def nmonths(x) -> int:
    return len(endpoints(x, on="months")) - 1


def nquarters(x) -> int:
    return len(endpoints(x, on="quarters")) - 1


def nyears(x) -> int:
    return len(endpoints(x, on="years")) - 1


def _align(value: float, n: int) -> float:
    return value + (n - value % n)


def _stamp(year: int, month: int, day: int, hour: int, minute: int, sec: float, tz: str) -> float:
    whole = int(sec)
    fraction = sec - whole
    if tz in ("", "UTC", "GMT"):
        zone = timezone.utc if tz else None
        moment = datetime(year, month, day, hour, minute, whole, tzinfo=zone)
        if zone is None:
            return moment.timestamp() + fraction
        return moment.timestamp() + fraction
    raise XtsError(f"timezone {tz!r} is not supported")


def _leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _parts(seconds: float) -> tuple[int, int, int]:
    """POSIXlt year (since 1900), month (0-11), and yday (0-based), in UTC."""
    moment = datetime.fromtimestamp(seconds, timezone.utc)
    return moment.year - 1900, moment.month - 1, moment.timetuple().tm_yday - 1


def _which_changes(buckets: list[int], count: int) -> list[int]:
    found = [0]
    found.extend(index + 1 for index in range(len(buckets) - 1) if buckets[index + 1] != buckets[index])
    found.append(count)
    return found


def _include_last(found: list[int], k: int) -> list[int]:
    positions = list(range(0, len(found), k))
    if positions[-1] != len(found) - 1:
        positions.append(len(found) - 1)
    return [found[index] for index in positions]


def _endpoint_values(values, on: int, k: int, addlast: bool) -> list[int]:
    """The positive-time branch of endpoints.c."""
    count = len(values)
    if count == 0:
        return [0, 0]
    found = [0]
    previous = int(values[0]) // on // k
    for index in range(1, count):
        current = int(values[index]) // on // k
        if current != previous:
            found.append(index)
        previous = current
    if addlast and found[-1] != count:
        found.append(count)
    return found


def _match_arg(value: str, choices: tuple[str, ...], name: str) -> str:
    if value in choices:
        return value
    matches = [choice for choice in choices if choice.startswith(value)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise XtsError(f"'{name}' should be one of {', '.join(repr(choice) for choice in choices)}")
    raise XtsError(f"'{name}' matched more than one choice")
