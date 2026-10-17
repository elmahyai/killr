"""Shared sentinels and the small R helpers the backports share."""

from __future__ import annotations

import math
import re


class BackportError(Exception):
    """An error raised with the same message R would stop on."""


class NAType:
    """R's NA. None remains NULL."""

    def __repr__(self) -> str:
        return "NA"

    def __bool__(self) -> bool:
        raise BackportError("missing value where TRUE/FALSE needed")


NA = NAType()
_MISSING = object()


def is_na(value) -> bool:
    if value is NA:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def is_null(value) -> bool:
    return value is None


def is_true(value) -> bool:
    return value is True


def match_arg(arg, choices):
    options = tuple(choices)
    if isinstance(arg, (list, tuple)):
        if len(arg) == 0:
            raise BackportError("'arg' must be of length 1")
        arg = arg[0]
    if arg in options:
        return arg
    if not isinstance(arg, str):
        raise BackportError("'arg' must be a character string")
    hits = [item for item in options if item.startswith(arg)]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        listed = ", ".join(repr(item) for item in options)
        raise BackportError(f"'{arg}' should be one of {listed}")
    raise BackportError(f"'{arg}' matches more than one of the choices")


def as_character(value):
    """R as.character for the scalars and vectors these backports receive."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [_one_character(item) for item in value]
    return [_one_character(value)]


def _one_character(value) -> str | NAType:
    if value is NA or (isinstance(value, float) and math.isnan(value)):
        return NA
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value)
    return str(value)


def recycle(left, right):
    if len(left) == 0 or len(right) == 0:
        return [], []
    width = max(len(left), len(right))
    return (
        [left[i % len(left)] for i in range(width)],
        [right[i % len(right)] for i in range(width)],
    )


def length_of(value) -> int:
    """R length: a string is one value, NULL is zero, a list is its count."""
    if value is None:
        return 0
    if isinstance(value, str) or is_na(value) or isinstance(value, (bool, int, float)):
        return 1
    if isinstance(value, dict):
        return len(value)
    try:
        return len(value)
    except TypeError:
        return 1


_TRIM = re.compile(r"^[ \t\r\n]+|[ \t\r\n]+$")


def trimws(x, which=("both", "left", "right")):
    side = match_arg(which, ("both", "left", "right"))
    values = x if isinstance(x, (list, tuple)) else [x]
    cleaned = [_trim_one(item, side) for item in values]
    if isinstance(x, (list, tuple)):
        return cleaned
    return cleaned[0] if cleaned else []


def _trim_one(value, side):
    if is_na(value):
        return NA
    text = value if isinstance(value, str) else _one_character(value)
    if text is NA:
        return NA
    if side == "left":
        return re.sub(r"^[ \t\r\n]+", "", text)
    if side == "right":
        return re.sub(r"[ \t\r\n]+$", "", text)
    return re.sub(r"[ \t\r\n]+$", "", re.sub(r"^[ \t\r\n]+", "", text))
