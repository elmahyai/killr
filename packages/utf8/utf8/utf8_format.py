"""Format strings to a display width, truncating with an ellipsis."""

from __future__ import annotations

from typing import Any

from utf8._text import display_width, escape_text
from utf8._text import justify as pad_text
from utf8._text import truncate
from utf8.output import output_utf8
from utf8.utf8_encode import _match_justify


def _format_one(
    value: str,
    *,
    chars: int | None,
    how: str,
    quote: bool,
    utf8: bool,
) -> str:
    encoded = escape_text(value, utf8=utf8, quote=False)
    shortened = truncate(encoded, chars, how)
    if quote:
        return f'"{shortened}"'
    return shortened


def utf8_format(
    x: Any,
    *,
    trim: bool = False,
    chars: int | None = None,
    justify: str = "left",
    width: int | None = None,
    na_encode: bool = True,
    quote: bool = False,
    na_print: str | None = None,
    print_gap: int | None = None,
    utf8: bool | None = None,
) -> Any:
    """Truncate to ``chars`` display units and pad to ``width``.

    The argument names follow Python. ``na_encode``, ``na_print``, and
    ``print_gap`` are the R ``na.encode``, ``na.print``, and ``print.gap``.
    """

    del na_encode, na_print, print_gap
    if x is None:
        return None
    if utf8 is None:
        utf8 = output_utf8()
    how = _match_justify(justify)
    scalar = isinstance(x, str)
    items = [x] if scalar else list(x)
    rendered = []
    for value in items:
        if not isinstance(value, str):
            raise TypeError("argument is not a character object")
        rendered.append(_format_one(value, chars=chars, how=how, quote=quote, utf8=utf8))
    if trim or how == "none":
        field = None
    else:
        longest = max((display_width(item) or 0 for item in rendered), default=0)
        field = longest if width in (0, None) else max(width, longest)
    padded = [pad_text(item, field, how, trim=trim) for item in rendered]
    if scalar:
        return padded[0]
    return padded
