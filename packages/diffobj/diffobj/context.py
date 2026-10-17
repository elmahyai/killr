"""Console height and the auto-context settings object."""

from __future__ import annotations

import math
import os

from diffobj.options import gdo

_MISSING = object()


def console_lines() -> int:
    """``LINES`` when it is a positive integer, otherwise 48."""

    text = os.environ.get("LINES", "")
    try:
        value = int(text)
    except ValueError:
        return 48
    if value < -2147483647 or value > 2147483647:
        return 48
    if value > 0:
        return value
    return 48


class AutoContext:
    """Limits passed to a diff as ``context=auto_context(...)``."""

    def __init__(self, min: int, max: int):
        self.min = min
        self.max = max

    def __repr__(self) -> str:
        return f"AutoContext(min={self.min}, max={self.max})"


def _integer_slot(value, name: str, allow_negative: bool) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(name, allow_negative)
    if isinstance(value, float):
        if not math.isfinite(value) or value != round(value):
            _fail(name, allow_negative)
        value = int(value)
    if value < -2147483647 or value > 2147483647:
        _fail(name, allow_negative)
    if not allow_negative and value < 0:
        _fail(name, allow_negative)
    return int(value)


def _fail(name: str, allow_negative: bool) -> None:
    if allow_negative:
        raise ValueError("Argument `max` must be integer(1L) and not NA")
    raise ValueError("Argument `min` must be integer(1L) and greater than zero")


def auto_context(min=_MISSING, max=_MISSING) -> AutoContext:
    """Bounds for the automatic context calculation."""

    if min is _MISSING:
        min = gdo("context.auto.min")
    if max is _MISSING:
        max = gdo("context.auto.max")
    return AutoContext(
        _integer_slot(min, "min", allow_negative=False),
        _integer_slot(max, "max", allow_negative=True),
    )
