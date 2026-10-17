"""chron ``times`` values for zoo matching.

``times`` stores time-of-day as a fraction of a day. Parsing follows
``chron::times`` h:m:s strings and integer-second arithmetic where possible.
"""

from __future__ import annotations

import math
import re
from typing import Any

import numpy as np

_TIME_RE = re.compile(
    r"^\s*(?P<h>\d+):(?P<m>\d+):(?P<s>\d+(?:\.\d+)?)\s*$|"
    r"^\s*(?P<h2>\d+):(?P<m2>\d+)\s*$"
)

_UNIT_ALIASES: dict[str, float] = {
    "s": 1.0 / 86400.0,
    "sec": 1.0 / 86400.0,
    "second": 1.0 / 86400.0,
    "seconds": 1.0 / 86400.0,
    "min": 1.0 / 1440.0,
    "minute": 1.0 / 1440.0,
    "minutes": 1.0 / 1440.0,
    "hour": 1.0 / 24.0,
    "hours": 1.0 / 24.0,
    "day": 1.0,
    "days": 1.0,
}
_UNIT_CANONICAL = ("sec", "min", "hour", "day")


class Times:
    """Fraction-of-day chron ``times`` vector."""

    class_name = "times"

    def __init__(self, values: Any) -> None:
        array = np.asarray(values, dtype=float).reshape(-1)
        self._values = array

    def __iter__(self):
        return iter(self._values.tolist())

    def __len__(self) -> int:
        return int(self._values.size)


def times(value: Any) -> Times | list[Times]:
    """Construct chron ``times`` from strings or numeric fractions of a day."""
    if isinstance(value, (list, tuple, np.ndarray)):
        if value and isinstance(value[0], str):
            return Times([_parse_time_string(str(item)) for item in value])
        return Times(value)
    if isinstance(value, str):
        return Times([_parse_time_string(value)])
    return Times([float(value)])


def trunc_times(value: Any, units: str = "sec", eps: float = 1e-10) -> Any:
    """``trunc`` for ``times``: floor to ``units`` with chron ``eps``."""
    increment = _unit_increment(units)
    if isinstance(value, Times):
        out = [_trunc_fraction(number, increment, eps) for number in value._values.tolist()]
        return Times(out)
    if isinstance(value, (list, tuple)):
        return [trunc_times(item, units=units, eps=eps) for item in value]
    return _trunc_fraction(float(value), increment, eps)


def _parse_time_string(text: str) -> float:
    match = _TIME_RE.match(text)
    if not match:
        raise ValueError(f"format h:m:s may be incorrect: {text!r}")
    if match.group("h") is not None:
        hours = int(match.group("h"))
        minutes = int(match.group("m"))
        seconds = float(match.group("s"))
    else:
        hours = int(match.group("h2"))
        minutes = int(match.group("m2"))
        seconds = 0.0
    whole_seconds = int(seconds)
    fraction = seconds - whole_seconds
    total = hours * 3600 + minutes * 60 + whole_seconds
    return (total + fraction) / 86400.0


def _unit_increment(units: str) -> float:
    key = units.strip().lower()
    if key in _UNIT_ALIASES:
        return _UNIT_ALIASES[key]
    matches = [name for name in _UNIT_CANONICAL if name.startswith(key) or key.startswith(name)]
    if len(matches) == 1:
        return _UNIT_ALIASES[matches[0]]
    if len(matches) > 1:
        exact = [name for name in matches if name.startswith(key)]
        if len(exact) == 1:
            return _UNIT_ALIASES[exact[0]]
    raise ValueError(f"units {units!r} is not a valid chron trunc unit")


def _trunc_fraction(value: float, increment: float, eps: float) -> float:
    if math.isnan(value):
        return value
    scaled = (value + eps) / increment
    return math.floor(scaled) * increment
