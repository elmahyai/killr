"""Unicode escape and unescape from stringi.

Escapes follow ``stri_escape.cpp``: lowercase ``\\uXXXX`` and ``\\UXXXXXXXX``.
Unescape follows ICU ``UnicodeString::unescape`` / ``u_unescapeAt``.
"""

from __future__ import annotations

import warnings

from stringi._na import NA, is_na
from stringi.utils import _as_character

_SPECIAL = {
    0x07: "\\a",
    0x08: "\\b",
    0x09: "\\t",
    0x0A: "\\n",
    0x0B: "\\v",
    0x0C: "\\f",
    0x0D: "\\r",
    0x22: '\\"',
    0x27: "\\'",
    0x5C: "\\\\",
}

# ICU UNESCAPE_MAP. Quotes and the backslash are not in the table; they
# fall through to the generic "drop the backslash" rule.
_UNESCAPE_MAP = {
    0x61: 0x07,  # a
    0x62: 0x08,  # b
    0x65: 0x1B,  # e
    0x66: 0x0C,  # f
    0x6E: 0x0A,  # n
    0x72: 0x0D,  # r
    0x74: 0x09,  # t
    0x76: 0x0B,  # v
}

_CONVERSION_ERROR = (
    "Character conversion: Unmappable input sequence / Invalid character. "
    "(U_INVALID_CHAR_FOUND)"
)


def _escape_code_point(code):
    if code <= 127:
        special = _SPECIAL.get(code)
        if special is not None:
            return special
        if 32 <= code <= 126:
            return chr(code)
        return f"\\u{code:04x}"
    if code <= 0xFFFF:
        return f"\\u{code:04x}"
    return f"\\U{code:08x}"


def stri_escape_unicode(str):
    """Escape non-printable and non-ASCII characters.

    Printable ASCII stays as itself, except bell, backspace, tab, newline,
    vertical tab, form feed, carriage return, quote, apostrophe, and
    backslash. Other code points at or below U+FFFF use ``\\u`` and four
    lowercase hex digits. Higher code points use ``\\U`` and eight.
    """
    out = []
    for value in _as_character(str):
        if is_na(value):
            out.append(NA)
        else:
            out.append("".join(_escape_code_point(ord(ch)) for ch in value))
    return out


def _is_lead(code):
    return 0xD800 <= code <= 0xDBFF


def _is_trail(code):
    return 0xDC00 <= code <= 0xDFFF


def _supplementary(lead, trail):
    return ((lead - 0xD800) << 10) + (trail - 0xDC00) + 0x10000


def _digit16(code):
    if 48 <= code <= 57:
        return code - 48
    if 65 <= code <= 70:
        return code - 55
    if 97 <= code <= 102:
        return code - 87
    return -1


def _digit8(code):
    if 48 <= code <= 55:
        return code - 48
    return -1


def _utf16_units(text):
    units = []
    for ch in text:
        code = ord(ch)
        if code <= 0xFFFF:
            units.append(code)
        else:
            code -= 0x10000
            units.append(0xD800 + (code >> 10))
            units.append(0xDC00 + (code & 0x3FF))
    return units


def _append_units(out, units):
    index = 0
    limit = len(units)
    while index < limit:
        unit = units[index]
        index += 1
        if _is_lead(unit) and index < limit and _is_trail(units[index]):
            out.append(_supplementary(unit, units[index]))
            index += 1
        else:
            out.append(unit)


def _unescape_at(units, offset, limit):
    """Parse one escape starting at ``offset``. Return ``(code, new_offset)``.

    ``None`` means the sequence is ill-formed. ``limit`` is an exclusive end,
    which the surrogate lookahead uses to cap a recursive parse.
    """
    start = offset
    if offset < 0 or offset >= limit:
        return None, start
    code = units[offset]
    offset += 1
    result = 0
    count = 0
    min_digits = 0
    max_digits = 0
    bits = 4
    braces = False

    if code == 0x75:  # u
        min_digits = max_digits = 4
    elif code == 0x55:  # U
        min_digits = max_digits = 8
    elif code == 0x78:  # x
        min_digits = 1
        if offset < limit and units[offset] == 0x7B:  # {
            offset += 1
            braces = True
            max_digits = 8
        else:
            max_digits = 2
    else:
        digit = _digit8(code)
        if digit >= 0:
            min_digits = 1
            max_digits = 3
            count = 1
            bits = 3
            result = digit

    if min_digits != 0:
        while offset < limit and count < max_digits:
            code = units[offset]
            digit = _digit8(code) if bits == 3 else _digit16(code)
            if digit < 0:
                break
            result = (result << bits) | digit
            offset += 1
            count += 1
        if count < min_digits:
            return None, start
        # Eight hex digits inside \x{} leave `code` on the last digit, so the
        # brace test fails. Fewer digits stop on '}' and succeed.
        if braces:
            if code != 0x7D:
                return None, start
            offset += 1
        if result < 0 or result >= 0x110000:
            return None, start
        if offset < limit and _is_lead(result):
            ahead = offset + 1
            nxt = units[offset]
            if nxt == 0x5C and ahead < limit:
                tail = ahead + 11
                if tail > limit:
                    tail = limit
                nxt, ahead = _unescape_at(units, ahead, tail)
                if nxt is None:
                    nxt = -1
            if _is_trail(nxt):
                offset = ahead
                result = _supplementary(result, nxt)
        return result, offset

    mapped = _UNESCAPE_MAP.get(code)
    if mapped is not None:
        return mapped, offset
    if code == 0x63 and offset < limit:  # \cX
        code = units[offset]
        offset += 1
        if _is_lead(code) and offset < limit:
            trail = units[offset]
            if _is_trail(trail):
                offset += 1
                code = _supplementary(code, trail)
        return 0x1F & code, offset
    if _is_lead(code) and offset < limit:
        trail = units[offset]
        if _is_trail(trail):
            offset += 1
            return _supplementary(code, trail), offset
    return code, offset


def _unescape_units(units):
    out = []
    index = 0
    prev = 0
    limit = len(units)
    while True:
        if index == limit:
            _append_units(out, units[prev:limit])
            return out
        if units[index] == 0x5C:
            _append_units(out, units[prev:index])
            index += 1
            code, index = _unescape_at(units, index, limit)
            if code is None:
                return None
            out.append(code)
            prev = index
        else:
            index += 1


def _finish(codes):
    if any(_is_lead(code) or _is_trail(code) for code in codes):
        raise ValueError(_CONVERSION_ERROR)
    if any(code == 0 for code in codes):
        shown = "".join(chr(code) for code in codes)
        raise ValueError(f"embedded nul in string: '{shown}'")
    return "".join(chr(code) for code in codes)


def stri_unescape_unicode(str):
    """Unescape ICU sequences. An ill-formed sequence warns and returns NA.

    A decoded U+0000 raises ``embedded nul in string``. A lone surrogate
    raises the ICU unmappable-character error. An empty string stays empty.
    """
    out = []
    for value in _as_character(str):
        if is_na(value):
            out.append(NA)
            continue
        if value == "":
            out.append("")
            continue
        codes = _unescape_units(_utf16_units(value))
        if codes is None:
            warnings.warn(
                "invalid escape sequence detected; setting NA",
                stacklevel=2,
            )
            out.append(NA)
            continue
        out.append(_finish(codes))
    return out
