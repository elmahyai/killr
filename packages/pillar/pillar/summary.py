"""Short descriptions of a vector: dimensions, type, size, and a table line."""

from __future__ import annotations

from typing import Any

from cli.symbol import symbol

from pillar._options import get_option
from pillar._vec import (
    NULL,
    DataFrame,
    Environment,
    Factor,
    _dim,
    vec_is,
    vec_ptype_abbr,
    vec_size,
)


class ShortStr(str):
    """A summary string that also carries the compact form."""

    short: str

    def __new__(cls, text: str, short: str) -> ShortStr:
        obj = str.__new__(cls, text)
        obj.short = short
        return obj


class NamedChar(str):
    """A length-one character vector with one name."""

    name: str

    def __new__(cls, text: str, name: str) -> NamedChar:
        obj = str.__new__(cls, text)
        obj.name = name
        return obj


def _vector(value: Any) -> bool:
    # A complex scalar is a length-one complex vector. vec_is rejects it.
    return vec_is(value) or isinstance(value, complex)


def _label(value: Any) -> str | None:
    pillar = getattr(value, "pillar", None)
    if not isinstance(pillar, dict) or "label" not in pillar:
        return None
    label = pillar["label"]
    if label is None:
        return None
    return str(label)


def _thousands_mark() -> str:
    if get_option("OutDec") == ",":
        return "."
    return ","


def _group_digits(value: int, mark: str) -> str:
    sign = "-" if value < 0 else ""
    digits = str(abs(value))
    pieces: list[str] = []
    while digits:
        pieces.append(digits[-3:])
        digits = digits[:-3]
    return sign + mark.join(reversed(pieces))


def _format_extent(value: Any, mark: str) -> str:
    if isinstance(value, bool) or not isinstance(value, int):
        return "??"
    return _group_digits(value, mark)


def _is_array(value: Any) -> bool:
    if isinstance(value, DataFrame):
        return False
    dims = _dim(value)
    return dims is not None and len(dims) > 0


def dim_desc(x: Any) -> str:
    """Format dimensions, or the length when the object has none."""

    dims = _dim(x)
    if dims is None:
        dims = (vec_size(x),)
    mark = _thousands_mark()
    parts = [_format_extent(item, mark) for item in dims]
    return (" " + symbol["times"] + " ").join(parts)


def type_sum(x: Any) -> str:
    """Brief type name. An unordered factor stays ``fct``, with no shape."""

    if isinstance(x, Factor) and not x.ordered:
        return "fct"
    label = _label(x)
    if label is not None:
        return label
    if _vector(x):
        return vec_ptype_abbr(x, suffix_shape=True)
    if isinstance(x, Environment):
        return "env"
    if callable(x) and not isinstance(x, type):
        return "fn"
    if x is NULL:
        return "NULL"
    return type(x).__name__


def size_sum(x: Any) -> str:
    """Size in brackets. An empty string when ``x`` is not a vector."""

    if not _vector(x):
        return ""
    return "[" + dim_desc(x) + "]"


def obj_sum(x: Any) -> str:
    """Type and size for a vector. Other objects are ``type_sum`` alone."""

    if not _vector(x):
        return type_sum(x)
    abbr = vec_ptype_abbr(x, suffix_shape=False)
    text = abbr + " " + size_sum(x)
    if _is_array(x):
        short = abbr + "[" + symbol["ellipsis"] + "]"
    else:
        short = abbr
    return ShortStr(text, short)


def tbl_sum(x: Any) -> NamedChar:
    """Named description. The default name is ``Description``."""

    return NamedChar(str(obj_sum(x)), "Description")
