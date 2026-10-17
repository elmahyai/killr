"""Irregular time series."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from tseries._num import approx


def _zone(tz):
    if tz in ("GMT", "UTC", "Etc/GMT", "Etc/UTC"):
        return timezone.utc
    return ZoneInfo(tz)


def _stamp(text, fmt, tz):
    parsed = datetime.strptime(text, fmt)
    return parsed.replace(tzinfo=_zone(tz)).timestamp()


class Irts:
    def __init__(self, time, value):
        self.time = np.asarray(time, dtype=float).reshape(-1)
        value = np.asarray(value, dtype=float)
        if value.ndim == 2 and value.shape[1] == 1:
            value = value.reshape(-1)
        rows = value.shape[0] if value.ndim == 2 else len(value)
        if len(self.time) != rows:
            raise ValueError("time and value have not the same number of rows")
        self.value = value


def irts(time, value):
    return Irts(time, value)


def is_irts(object):
    return isinstance(object, Irts)


def as_irts(object):
    values = np.asarray(object, dtype=float)
    if values.ndim != 2 or values.shape[1] < 2:
        raise ValueError("object has no time column and value columns")
    rest = values[:, 1:]
    if rest.shape[1] == 1:
        rest = rest.reshape(-1)
    return Irts(values[:, 0], rest)


def value(x):
    if not isinstance(x, Irts):
        raise ValueError("method is only for irts objects")
    return x.value


def time_irts(x):
    if not isinstance(x, Irts):
        raise ValueError("method is only for irts objects")
    return x.time


def _local(stamp, tz):
    return datetime.fromtimestamp(float(stamp), _zone(tz))


def weekday(object, tz="GMT"):
    if not isinstance(object, Irts):
        raise ValueError("function is only for irts objects")
    return np.array([(_local(item, tz).weekday() + 1) % 7 for item in object.time], dtype=int)


def daysecond(object, tz="GMT"):
    if not isinstance(object, Irts):
        raise ValueError("function is only for irts objects")
    out = []
    for item in object.time:
        clock = _local(item, tz)
        second = clock.second + clock.microsecond / 1e6
        out.append(3600 * clock.hour + 60 * clock.minute + second)
    return np.array(out, dtype=float)


def is_businessday(object, tz="GMT"):
    if not isinstance(object, Irts):
        raise ValueError("function is only for irts objects")
    days = weekday(object, tz=tz)
    return (days > 0) & (days < 6)


def is_weekend(object, tz="GMT"):
    if not isinstance(object, Irts):
        raise ValueError("function is only for irts objects")
    days = weekday(object, tz=tz)
    return (days == 0) | (days == 6)


def _format_c(number):
    """R ``formatC`` with the default: format ``g`` and 4 significant digits."""
    if number is None or (isinstance(number, float) and number != number):
        return "NA"
    text = format(float(number), ".4g")
    if "e" in text or "E" in text:
        mantissa, exponent = text.lower().split("e")
        sign = "+" if int(exponent) >= 0 else "-"
        return f"{mantissa}e{sign}{abs(int(exponent)):02d}"
    return text


def read_irts(file, format="%Y-%m-%d %H:%M:%S", tz="GMT"):
    rows = []
    for line in Path(file).read_text().splitlines():
        if line.strip():
            rows.append(line.split())
    n_time = len(format.split(" "))
    times = []
    values = []
    for row in rows:
        times.append(_stamp(" ".join(row[:n_time]), format, tz))
        values.append([float(item) for item in row[n_time:]])
    table = np.array(values, dtype=float)
    if table.shape[1] == 1:
        table = table.reshape(-1)
    return Irts(times, table)


def write_irts(object, file="", format="%Y-%m-%d %H:%M:%S", tz="GMT"):
    if not isinstance(object, Irts):
        raise ValueError("object is not an irts")
    lines = []
    for i, stamp in enumerate(object.time):
        clock = _local(stamp, tz).strftime(format)
        if object.value.ndim == 1:
            rendered = _format_c(object.value[i])
        else:
            rendered = " ".join(_format_c(item) for item in object.value[i])
        lines.append(f"{clock} {rendered}")
    text = "\n".join(lines) + "\n"
    if file:
        Path(file).write_text(text)
    return text


def approx_irts(object, time, rule=1):
    if not isinstance(object, Irts):
        raise ValueError("function is only for irts objects")
    grid = np.asarray(time, dtype=float).reshape(-1)
    origin = object.value.reshape(-1, 1) if object.value.ndim == 1 else object.value
    columns = []
    for col in range(origin.shape[1]):
        columns.append([approx(object.time, origin[:, col], point, rule=rule) for point in grid])
    table = np.array(columns, dtype=float).T
    if table.shape[1] == 1:
        table = table.reshape(-1)
    return Irts(grid, table)


def subset_irts(object, i=None, j=None):
    """R ``[.irts``. Indices are 1-based, and a matrix value is not dropped."""
    if not isinstance(object, Irts):
        raise ValueError("method is only for irts objects")
    if object.value.ndim == 1:
        if j is not None:
            raise ValueError("incorrect number of dimensions")
        if i is None:
            return object
        index = np.asarray(i, dtype=int).reshape(-1) - 1
        return Irts(object.time[index], object.value[index])
    rows = slice(None) if i is None else np.asarray(i, dtype=int).reshape(-1) - 1
    cols = slice(None) if j is None else np.asarray(j, dtype=int).reshape(-1) - 1
    taken = np.asarray(object.value[rows][:, cols], dtype=float)
    if taken.ndim == 1:
        taken = taken.reshape(-1, 1)
    return Irts(object.time[rows], taken)
