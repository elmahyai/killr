"""Escape text the way utf8_encode prepares it for printing."""

from __future__ import annotations

from typing import Any

from utf8._text import display_width, escape_bytes, escape_text, justify
from utf8.output import output_utf8

_JUSTIFY = ("left", "right", "centre", "none")


def _match_justify(value: str) -> str:
    hits = [choice for choice in _JUSTIFY if choice.startswith(value)]
    if len(hits) != 1:
        raise ValueError("'justify' must be one of \"left\", \"right\", \"centre\", \"none\"")
    return hits[0]


def _encode_one(
    value: Any,
    *,
    width: int | None,
    quote: bool,
    how: str,
    escapes: str | None,
    display: bool,
    utf8: bool,
) -> str:
    if isinstance(value, bytes):
        text = escape_bytes(value, quote=quote, escapes=escapes)
    elif isinstance(value, str):
        text = escape_text(value, utf8=utf8, quote=quote, escapes=escapes, display=display)
    else:
        raise TypeError("argument is not a character object")
    if how == "none":
        return text
    return justify(text, width, how)


def utf8_encode(
    x: Any,
    *,
    width: int = 0,
    quote: bool = False,
    justify: str = "left",
    escapes: str | None = None,
    display: bool = False,
    utf8: bool | None = None,
) -> Any:
    """Escape controls, and non-ASCII when ``utf8`` is false. ``bytes`` are escaped per byte."""

    if x is None:
        return None
    if utf8 is None:
        utf8 = output_utf8()
    how = _match_justify(justify)
    field = None if width in (0, None) else width

    def one(value: Any) -> str:
        return _encode_one(
            value,
            width=field,
            quote=quote,
            how=how,
            escapes=escapes,
            display=display,
            utf8=utf8,
        )

    if isinstance(x, (str, bytes)):
        return one(x)
    return [one(item) for item in x]
