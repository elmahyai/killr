"""Display width of text, after the same escaping utf8_encode uses."""

from __future__ import annotations

from typing import Any

from utf8._text import NA, display_width, escape_bytes, escape_text
from utf8.output import output_utf8


def _width_one(value: Any, *, encode: bool, quote: bool, utf8: bool) -> int | None:
    if value is NA:
        return None
    if isinstance(value, bytes):
        if not encode and not utf8:
            return None
        text = escape_bytes(value, quote=quote) if encode else None
        if text is None:
            return None
        return display_width(text)
    if not isinstance(value, str):
        raise TypeError("argument is not a character object")
    if encode:
        text = escape_text(value, utf8=utf8, quote=quote)
        width = display_width(text)
    else:
        if not utf8 and any(ord(char) > 127 for char in value):
            return None
        width = display_width(value)
    return width


def utf8_width(
    x: Any,
    *,
    encode: bool = True,
    quote: bool = False,
    utf8: bool | None = None,
) -> Any:
    """Printed width. With ``encode``, controls count as their backslash escapes."""

    if x is None:
        return None
    if utf8 is None:
        utf8 = output_utf8()

    def one(value: Any) -> int | None:
        return _width_one(value, encode=encode, quote=quote, utf8=utf8)

    if isinstance(x, (str, bytes)) or value_is_scalar(x):
        return one(x)
    return [one(item) for item in x]


def value_is_scalar(value: Any) -> bool:
    return value is NA
