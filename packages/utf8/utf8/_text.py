"""Display width and C-style escapes used by utf8."""

from __future__ import annotations

import bisect
import unicodedata

from utf8._charwidth import CHARWIDTH

NA = object()

_CONTROLS = {
    7: "\\a",
    8: "\\b",
    9: "\\t",
    10: "\\n",
    11: "\\v",
    12: "\\f",
    13: "\\r",
}

_SINGLE_QUOTES = {
    "\u055a": "'",
    "\u2018": "'",
    "\u2019": "'",
    "\u201b": "'",
    "\uff07": "'",
}

_STARTS = [row[0] for row in CHARWIDTH]


def char_prop(code: int) -> int:
    """utf8lite character class. 0 means control, unassigned, or other."""

    index = bisect.bisect_right(_STARTS, code) - 1
    if index < 0:
        return 0
    start, end, prop = CHARWIDTH[index]
    if code <= end:
        return prop
    return 0


def is_missing(value: object) -> bool:
    return value is NA or value is None


def unit_width(char: str) -> int | None:
    """Printed width of one character. None means the character is not printable."""

    prop = char_prop(ord(char))
    if prop in {1, 2}:
        return 0
    if prop in {3, 4}:
        return 1
    if prop in {5, 6}:
        return 2
    return None


def display_width(text: str) -> int | None:
    total = 0
    for char in text:
        width = unit_width(char)
        if width is None:
            return None
        total += width
    return total


def _style(token: str, escapes: str | None, *, only_first: bool = False) -> str:
    if not escapes:
        return token
    if only_first and len(token) > 1:
        return f"\033[{escapes}m{token[0]}\033[0m{token[1:]}"
    return f"\033[{escapes}m{token}\033[0m"


def escape_char(char: str, *, utf8: bool, quote: bool, escapes: str | None) -> str:
    code = ord(char)
    if quote and char == '"':
        return _style('\\"', escapes)
    if code in _CONTROLS:
        return _style(_CONTROLS[code], escapes)
    if code < 32 or code == 127:
        return _style(f"\\u{code:04x}", escapes)
    if not utf8 and code > 127:
        if code <= 0xFFFF:
            return _style(f"\\u{code:04x}", escapes)
        return _style(f"\\U{code:08x}", escapes)
    if char == "\\":
        return _style("\\\\", escapes, only_first=True)
    return char


def escape_text(
    text: str,
    *,
    utf8: bool = True,
    quote: bool = False,
    escapes: str | None = None,
    display: bool = False,
) -> str:
    if display:
        text = "".join(char for char in text if not _ignorable(char))
    body = "".join(escape_char(char, utf8=utf8, quote=quote, escapes=escapes) for char in text)
    if quote:
        return f'"{body}"'
    return body


def escape_bytes(raw: bytes, *, quote: bool = False, escapes: str | None = None) -> str:
    parts: list[str] = []
    for byte in raw:
        if byte in _CONTROLS:
            parts.append(_style(_CONTROLS[byte], escapes))
        elif byte < 32 or byte >= 127:
            parts.append(_style(f"\\x{byte:02x}", escapes))
        elif byte >= 128:
            parts.append(_style(f"\\x{byte:02x}", escapes))
        elif byte == ord("\\"):
            parts.append(_style("\\\\", escapes, only_first=True))
        elif quote and byte == ord('"'):
            parts.append(_style('\\"', escapes))
        else:
            parts.append(chr(byte))
    body = "".join(parts)
    if quote:
        return f'"{body}"'
    return body


def _ignorable(char: str) -> bool:
    return char_prop(ord(char)) == 1


def normalize_text(
    text: str,
    *,
    map_case: bool = False,
    map_compat: bool = False,
    map_quote: bool = False,
    remove_ignorable: bool = False,
) -> str:
    if map_compat:
        mapped = unicodedata.normalize("NFKC", text)
        if map_case:
            mapped = "".join(char.lower() if "A" <= char <= "Z" else char for char in mapped)
    elif map_case:
        mapped = unicodedata.normalize("NFC", text.casefold())
    else:
        mapped = unicodedata.normalize("NFC", text)
    if map_quote:
        mapped = "".join(_SINGLE_QUOTES.get(char, char) for char in mapped)
    if remove_ignorable:
        mapped = "".join(char for char in mapped if not _ignorable(char))
    return mapped


def justify(text: str, width: int | None, how: str, *, trim: bool = False) -> str:
    if trim or how == "none" or width is None or width <= 0:
        return text
    current = display_width(text)
    if current is None or current >= width:
        return text
    pad = width - current
    if how == "right":
        return (" " * pad) + text
    if how == "centre":
        left = pad // 2
        return (" " * left) + text + (" " * (pad - left))
    return text + (" " * pad)


def truncate(text: str, chars: int | None, how: str, ellipsis: str = "\u2026") -> str:
    if chars is None:
        return text
    width = display_width(text)
    if width is None or width <= chars:
        return text
    if how == "right":
        kept = _take_suffix(text, chars)
        return ellipsis + kept
    kept = _take_prefix(text, chars)
    return kept + ellipsis


def _take_prefix(text: str, limit: int) -> str:
    kept: list[str] = []
    used = 0
    for char in text:
        width = unit_width(char) or 0
        if used + width > limit:
            break
        kept.append(char)
        used += width
    return "".join(kept)


def _take_suffix(text: str, limit: int) -> str:
    kept: list[str] = []
    used = 0
    for char in reversed(text):
        width = unit_width(char) or 0
        if used + width > limit:
            break
        kept.append(char)
        used += width
    return "".join(reversed(kept))
