"""ISO-8601 ranges and time-based sequences from xts 0.14.3."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

from xts.clock import firstof, lastof
from xts.ordered import XtsError

_TIME_CLASSES = ("Date", "POSIXt", "chron", "dates", "times", "timeDate", "yearmon", "yearqtr", "xtime")
_MISSING = object()


def is_time_based(x) -> bool:
    """True for a Date, POSIXct, yearmon, yearqtr, or another time class."""
    if isinstance(x, (datetime, date)):
        return True
    if isinstance(x, (list, tuple)) and x and isinstance(x[0], (datetime, date)):
        return True
    kind = getattr(x, "time_class", None)
    return kind in _TIME_CLASSES


def time_based(x) -> bool:
    return is_time_based(x)


def _numeric(text: str):
    if text is None or text.strip() == "":
        return None
    return float(text)


def _parse_side(text: str, tz: str, startof: str | None = None) -> dict:
    if text is None or text == "":
        return {}
    basic = re.sub(r"[:\-]", "", text)
    pieces = re.split(r"[ T]", basic, maxsplit=1)
    date_text = pieces[0]
    if startof is not None and len(basic) == 2:
        start_basic = re.sub(r"[:\-]", "", startof)
        if len(start_basic) - len(date_text) >= 4:
            date_text = start_basic[: len(start_basic) - len(date_text)] + date_text
    date_text = f"{date_text:<8}"
    year = _numeric(date_text[0:4])
    month = _numeric(date_text[4:6])
    day = _numeric(date_text[6:8])
    hour = minute = sec = None
    if len(pieces) > 1 and pieces[1] != "":
        clock = f"{pieces[1]:<6}"
        hour = _numeric(clock[0:2])
        minute = _numeric(clock[2:4])
        sec = _numeric(clock[4:])
    payload = {"year": year, "month": month, "day": day, "hour": hour, "minute": minute, "sec": sec, "tz": tz}
    return {key: value for key, value in payload.items() if value is not None}


def _call_bound(function, parts: dict) -> float | None:
    if not parts:
        return None
    return float(function(**parts))


def parse_iso8601(x: str, start=None, end=None, tz: str = "") -> dict:
    """The first and last instants of an ISO-8601 range, in seconds."""
    if "NOW" in x:
        x = x.replace("NOW", datetime.now().strftime("%Y%m%dT%H%M%S"))
    if "TODAY" in x:
        x = x.replace("TODAY", date.today().strftime("%Y%m%d"))
    if re.search(r"/|--|::", x) is None:
        x = f"{x}/{x}"
    intervals = re.split(r"/|--|::", x)
    duration = ""
    duration_left = False
    if len(intervals) == 2:
        if intervals[0].startswith("P"):
            duration = intervals[0]
            duration_left = True
            intervals[0] = ""
        elif intervals[1].startswith("P"):
            duration = intervals[1]
            duration_left = False
            intervals = [intervals[0]]
    first = None
    last = None
    if intervals and intervals[0]:
        first = _call_bound(firstof, _parse_side(intervals[0], tz))
    if len(intervals) == 2:
        last = _call_bound(lastof, _parse_side(intervals[1], tz, intervals[0]))
        if last is None:
            last = _call_bound(lastof, _parse_side(intervals[1], tz))
    if first is None and last is None and not duration and intervals[0] != "":
        return {"first.time": None, "last.time": None}
    if start is not None and first is not None:
        first = max(float(start), first)
    if end is not None and last is not None:
        last = min(float(end), last)
    if duration:
        shift = _duration(duration)
        if duration_left and last is not None:
            first = last - shift
        elif first is not None:
            last = first + shift
    return {"first.time": first, "last.time": last}


def _duration(text: str) -> float:
    body = text.replace("P", "")
    body = re.sub(r"T(.*)M", r"\1m", body)
    numbers = [float(item) for item in re.split(r"[A-Za-z]", body) if item]
    units = list(re.sub(r"[0-9.]", "", body))
    scale = {"Y": 365.25 * 86400, "M": 30 * 86400, "D": 86400, "H": 3600, "m": 60, "S": 1}
    return sum(number * scale[unit] for number, unit in zip(numbers, units))


def _fields(text: str) -> list[float]:
    names = ("year", "month", "day", "hour", "minute", "sec")
    found = []
    for offset, _name in enumerate(names):
        piece = text[offset * 2 : offset * 2 + (4 if offset == 0 else 2)] if offset else text[0:4]
        if offset == 0:
            piece = text[0:4]
        elif offset == 1:
            piece = text[4:6]
        elif offset == 2:
            piece = text[6:8]
        elif offset == 3:
            piece = text[8:10]
        elif offset == 4:
            piece = text[10:12]
        else:
            piece = text[12:14]
        if piece == "":
            break
        found.append(float(piece))
    return found


def _bound(values: list[float], last: bool) -> float:
    if not values:
        return float("nan")
    names = ["year", "month", "day", "hour", "minute", "sec"]
    payload = {name: int(value) if name != "sec" else value for name, value in zip(names, values)}
    if last:
        return float(lastof(**payload))
    return float(firstof(**payload))


def time_based_seq(x: str, retclass=_MISSING, length_out=None):
    """A Date, yearmon, or POSIXct sequence described by ``from/to/by``."""
    text = x.replace("::", "/")
    text = re.sub(r"[-:]", "", text)
    text = text.replace(" ", "")
    parts = text.split("/")
    while len(parts) < 3:
        parts.append(None)
    left, right, by = parts[0], parts[1], parts[2]
    left_values = [] if not left else _fields(left)
    right_values = [] if not right else _fields(right)
    start = _bound(left_values, False) if left_values else None
    stop = _bound(right_values, True) if right_values else None
    resolution_index = max(len(left_values), len(right_values), 1)
    names = ["year", "month", "DSTday", "hour", "mins", "secs"]
    resolution = names[min(resolution_index, 6) - 1]
    if by:
        aliases = {"Y": "year", "m": "month", "d": "DSTday", "H": "hour", "M": "mins", "S": "secs"}
        if by not in aliases:
            raise XtsError(f"'{by}' is not a valid time step")
        resolution = aliases[by]
    if stop is None and length_out is None:
        length_out = 1
    if retclass is None or start is None or stop is None:
        return {"from": start, "to": stop, "by": resolution, "length.out": length_out}
    stamps = _sequence(start, stop, resolution, length_out)
    convert = "Date"
    if resolution_index == 2 or resolution == "month":
        convert = "yearmon"
    if resolution_index > 3 or resolution in {"hour", "mins", "secs"}:
        convert = "POSIXct"
    if retclass is not _MISSING and retclass is not None:
        convert = retclass
    if convert == "POSIXct":
        return stamps
    if convert == "yearmon":
        values = []
        for stamp in stamps:
            moment = datetime.fromtimestamp(stamp, timezone.utc)
            values.append(moment.year + (moment.month - 1) / 12)
        return values
    return [_date_number(stamp) for stamp in stamps]


def time_based_range(x: str) -> list[float]:
    """The numeric start and end of a time range."""
    found = time_based_seq(x, None)
    return [found["from"], found["to"]]


def _date_number(stamp: float) -> int:
    moment = datetime.fromtimestamp(stamp)
    return date(moment.year, moment.month, moment.day).toordinal() - date(1970, 1, 1).toordinal()


def _sequence(start: float, stop: float | None, resolution: str, length_out) -> list[float]:
    if length_out is not None:
        return _sequence_length(start, resolution, int(length_out))
    moment = datetime.fromtimestamp(start)
    end = datetime.fromtimestamp(stop)
    found = []
    guard = 0
    while moment <= end and guard < 100000:
        found.append(moment.timestamp())
        moment = _step(moment, resolution)
        guard += 1
    return found


def _sequence_length(start: float, resolution: str, length_out: int) -> list[float]:
    moment = datetime.fromtimestamp(start)
    found = []
    for _ in range(length_out):
        found.append(moment.timestamp())
        moment = _step(moment, resolution)
    return found


def _step(moment: datetime, resolution: str) -> datetime:
    if resolution == "year":
        return moment.replace(year=moment.year + 1)
    if resolution == "month":
        month = moment.month + 1
        year = moment.year
        if month == 13:
            month = 1
            year += 1
        return moment.replace(year=year, month=month)
    if resolution == "DSTday":
        return moment + timedelta(days=1)
    if resolution == "hour":
        return moment + timedelta(hours=1)
    if resolution == "mins":
        return moment + timedelta(minutes=1)
    if resolution == "secs":
        return moment + timedelta(seconds=1)
    raise XtsError(resolution)
