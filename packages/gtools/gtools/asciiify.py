"""Convert characters to ASCII escape codes (gtools 3.9.5 ``ASCIIfy``)."""

from __future__ import annotations

import warnings
from collections.abc import Sequence

_BYTES_CHOICES = ("1", "2")


def _match_arg(value: object, choices: tuple[str, ...]) -> str:
    text = str(value)
    if text in choices:
        return text
    hits = [choice for choice in choices if choice.startswith(text)]
    shown = ", ".join(f'"{choice}"' for choice in choices)
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise ValueError(f"'{text}' should be one of {shown}")
    raise ValueError(f"'{text}' matches more than one of {shown}")


def _format_c_width4(hex_text: str) -> str:
    return hex_text.rjust(4).replace(" ", "0")


def _raw_as_character(byte: int) -> str:
    return f"{byte:02x}"


def _format_hexmode(codepoint: int, width: int | None = None) -> str:
    text = format(codepoint, "x")
    if width is None:
        return text
    return text.rjust(width, "0")


def _convert_char(char: str, bytes_mode: str, fallback: str) -> str:
    raw = char.encode("utf-8")
    length = len(raw)
    if length == 1 and raw[0] <= 127:
        return char
    if length == 1 and bytes_mode == "1":
        return "\\x" + _raw_as_character(raw[0])
    if length == 1 and bytes_mode == "2":
        hex_text = _raw_as_character(raw[0])
        return "\\u" + _format_c_width4(hex_text)
    codepoint = ord(char)
    if length == 2 and bytes_mode == "1":
        if codepoint <= 255:
            return "\\x" + _format_hexmode(codepoint)
        warnings.warn(f"{char} could not be converted to 1 byte", stacklevel=4)
        return fallback
    if length == 2 and bytes_mode == "2":
        return "\\u" + _format_hexmode(codepoint, width=4)
    warnings.warn(f"{char} could not be converted to {bytes_mode} byte", stacklevel=4)
    return fallback


def _asciiify_one(text: str, bytes_mode: str, fallback: str) -> str:
    parts = [_convert_char(char, bytes_mode, fallback) for char in text]
    return "".join(parts)


def ASCIIfy(x, bytes=2, fallback="?"):
    """Replace non-ASCII characters with ``\\x00`` or ``\\u0000`` escape codes."""
    bytes_mode = _match_arg(bytes, _BYTES_CHOICES)
    if isinstance(x, str):
        items = [x]
    elif isinstance(x, Sequence):
        items = [str(item) for item in x]
    else:
        items = [str(x)]

    if len(items) > 1:
        return [_asciiify_one(item, bytes_mode, fallback) for item in items]
    return _asciiify_one(items[0], bytes_mode, fallback)
