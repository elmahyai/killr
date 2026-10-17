"""Character conversion, quoting, and the glue vector."""

from __future__ import annotations

import datetime as _datetime
import math
import re
from typing import Any

_NAMED_ESCAPES = {
    7: "\\a",
    8: "\\b",
    9: "\\t",
    10: "\\n",
    11: "\\v",
    12: "\\f",
    13: "\\r",
}


class NAType:
    """R's missing value, distinct from ``None`` (R's NULL)."""

    def __repr__(self) -> str:
        return "NA"

    def __str__(self) -> str:
        return "NA"

    def __eq__(self, other: object) -> bool:
        return other is self

    def __hash__(self) -> int:
        return id(self)


NA = NAType()

_IDENT = re.compile(r"[A-Za-z_\.][A-Za-z0-9_\.]*")


class Glue:
    """A character vector with glue's class."""

    def __init__(self, values: tuple[Any, ...] | list[Any]):
        self.values = tuple(values)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Glue):
            return self.values == other.values
        if isinstance(other, str):
            return len(self.values) == 1 and self.values[0] == other
        if isinstance(other, (list, tuple)):
            return self.values == tuple(other)
        return NotImplemented

    def __iter__(self):
        return iter(self.values)

    def __len__(self) -> int:
        return len(self.values)

    def __getitem__(self, index):
        got = self.values[index]
        if isinstance(index, slice):
            return Glue(got)
        return Glue((got,))

    def __str__(self) -> str:
        return "\n".join("NA" if item is NA else str(item) for item in self.values)

    def __repr__(self) -> str:
        shown = ["NA" if item is NA else item for item in self.values]
        return f"Glue({shown!r})"

    def __add__(self, other: object) -> Glue:
        from glue.interpolate import glue_data

        return glue_data({"e1": self, "e2": other}, "{e1}{e2}", envir={})

    def __radd__(self, other: object) -> Glue:
        from glue.interpolate import glue_data

        return glue_data({"e1": other, "e2": self}, "{e1}{e2}", envir={})


class SQL(str):
    """A string that SQL quoting leaves unchanged."""


class Id:
    """A qualified identifier: schema, table, and column, in that order."""

    def __init__(self, *parts: str, **named: str | None):
        ordered: list[str] = []
        for key in ("database", "db", "cluster", "catalog", "schema"):
            value = named.pop(key, None)
            if value is not None:
                ordered.append(value)
        ordered.extend(parts)
        for key in ("table", "column"):
            value = named.pop(key, None)
            if value is not None:
                ordered.append(value)
        if named:
            extra = next(iter(named))
            raise TypeError(f"unexpected Id component {extra}")
        if not all(isinstance(part, str) for part in ordered):
            raise TypeError("All elements of Id must be strings.")
        self.parts = tuple(ordered)

    def __repr__(self) -> str:
        return f"Id({', '.join(repr(part) for part in self.parts)})"


def r_character_double(value: float) -> str:
    """Match R's as.character for a double."""

    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == 0.0:
        return "0"
    negative = value < 0
    scientific = format(abs(value), ".14e")
    mantissa, exponent_text = scientific.split("e")
    exponent = int(exponent_text)
    whole, frac = mantissa.split(".")
    frac = frac.rstrip("0")
    mant = whole if frac == "" else f"{whole}.{frac}"
    digits = whole + frac
    sci = f"{mant}e{exponent:+03d}"
    if exponent >= 0:
        point = len(whole) + exponent
        if point >= len(digits):
            fixed = digits + ("0" * (point - len(digits)))
        else:
            fixed = digits[:point] + "." + digits[point:]
    else:
        zeros = -exponent - len(whole)
        if zeros >= 0:
            fixed = "0." + ("0" * zeros) + digits
        else:
            point = len(digits) + zeros
            fixed = digits[:point] + "." + digits[point:]
    if negative:
        sci = "-" + sci
        fixed = "-" + fixed
    if len(sci) < len(fixed):
        return sci
    return fixed


def r_character(value: Any) -> Any:
    """One R as.character result. ``NA`` stays missing."""

    if value is NA or value is None:
        return NA
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value):
            return NA
        return r_character_double(value)
    if isinstance(value, _datetime.datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, _datetime.date):
        return value.isoformat()
    if isinstance(value, Glue):
        if len(value.values) == 1:
            return r_character(value.values[0])
        return NA
    return str(value)


def character_vector(value: Any) -> tuple[Any, ...] | None:
    """R as.character of a scalar or an atomic vector.

    ``None`` as the whole value is NULL. ``None`` inside a list is missing.
    """

    if value is None:
        return None
    if isinstance(value, Glue):
        return value.values
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        pieces: list[Any] = []
        for item in value:
            if item is None or item is NA:
                pieces.append(NA)
            elif isinstance(item, (list, tuple, Glue)):
                nested = character_vector(item)
                if nested is None:
                    return None
                pieces.extend(nested)
            else:
                pieces.append(r_character(item))
        return tuple(pieces)
    return (r_character(value),)


def encode_one(text: str, quote: str) -> str:
    """One element of R encodeString, with a quote character."""

    out: list[str] = []
    for char in text:
        code = ord(char)
        if char in ("\\", quote):
            out.append("\\" + char)
        elif code in _NAMED_ESCAPES:
            out.append(_NAMED_ESCAPES[code])
        elif code < 32 or code == 127:
            out.append(f"\\{code:03o}")
        else:
            out.append(char)
    return quote + "".join(out) + quote


def display_width(text: str) -> int:
    """Width for ASCII text, where R's nchar(type='width') equals the length."""

    return len(text)


def rewrite_names(expression: str, env: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Replace dotted data names so Python does not read them as attributes."""

    keys = [key for key in env if isinstance(key, str) and _IDENT.fullmatch(key)]
    keys.sort(key=len, reverse=True)
    if not keys:
        return expression, {}
    pattern = "|".join(re.escape(key) for key in keys)
    matcher = re.compile(rf"(?<![A-Za-z0-9_\.])(?:{pattern})(?![A-Za-z0-9_\.])")
    extra: dict[str, Any] = {}

    def replace(match: re.Match[str]) -> str:
        slot = f"__glue_{len(extra)}"
        extra[slot] = env[match.group(0)]
        return slot

    return matcher.sub(replace, expression), extra
