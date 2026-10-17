"""makeRaw from digest 0.6.39.

Turns a string, a raw vector, a hex digest, or numbers into bytes.
hmac calls ``make_raw_digest`` on a character hash. ``makeRaw`` on a
plain ``str`` stays ``charToRaw``.
"""

from __future__ import annotations

import math
import warnings
from collections.abc import Iterable

# Installed charToRaw and as.raw messages, including the newline charToRaw uses.
_CHAR_LEN_WARN = (
    "argument should be a character vector of length 1\n"
    "all but the first element will be ignored"
)
_RAW_WARN = "out-of-range values treated as 0 in coercion to raw"
_HEX_ERROR = "'x' cannot be coerced to class \"hexmode\""
# seq(1, nchar(""), 2) in makeRaw.digest.
_EMPTY_HEX = "wrong sign in 'by' argument"

_HEX_SPACE = " \t\n\r\v\f"


class DigestHex:
    """A character hash. ``makeRaw`` parses the hex; a plain ``str`` does not."""

    def __init__(self, text: str) -> None:
        self.text = text

    def __repr__(self) -> str:
        return f"DigestHex({self.text!r})"


def _strtoi_hex(text: str) -> int | None:
    """R's ``strtoi(text, 16L)``. ``None`` is ``NA``."""
    index = 0
    size = len(text)
    while index < size and text[index] in _HEX_SPACE:
        index += 1
    if index >= size:
        return None
    sign = 1
    if text[index] == "+":
        index += 1
    elif text[index] == "-":
        sign = -1
        index += 1
    if index + 1 < size and text[index] == "0" and text[index + 1] in "xX":
        index += 2
    value = 0
    digits = 0
    while index < size:
        char = text[index]
        if "0" <= char <= "9":
            digit = ord(char) - 48
        elif "a" <= char <= "f":
            digit = ord(char) - 87
        elif "A" <= char <= "F":
            digit = ord(char) - 55
        else:
            break
        digits += 1
        value = value * 16 + digit
        if value > 0x80000000:
            return None
        index += 1
    if digits == 0 or index != size:
        return None
    value *= sign
    if value < -0x80000000 or value > 0x7FFFFFFF:
        return None
    return value


def _one_raw(value: object) -> tuple[int, bool]:
    """One ``as.raw`` element. The flag is the out-of-range warning."""
    if isinstance(value, bool):
        return int(value), False
    if isinstance(value, int):
        if value < 0 or value > 255:
            return 0, True
        return value, False
    if isinstance(value, float):
        # Truncate toward zero. (-1, 256) stays in range, so -0.1 is 0
        # with no warning and 255.9 is 255. -1 and 256 warn and become 0.
        if not math.isfinite(value) or value <= -1.0 or value >= 256.0:
            return 0, True
        return int(value), False
    raise TypeError("cannot coerce to raw")


def _as_raw(values: Iterable[object]) -> bytes:
    out = bytearray()
    warned = False
    for value in values:
        byte, bad = _one_raw(value)
        out.append(byte)
        warned = warned or bad
    if warned:
        warnings.warn(_RAW_WARN, UserWarning, stacklevel=3)
    return bytes(out)


def _char_to_raw(text: str) -> bytes:
    """Bytes of a UTF-8 string. ASCII code points are those byte values."""
    return text.encode("utf-8")


def make_raw_digest(text: str) -> bytes:
    """``makeRaw.digest``: hex pairs, then ``as.hexmode``, then ``as.raw``.

    The last pair is one character when the length is odd. An empty string
    is the ``seq(1, 0, 2)`` error.
    """
    if isinstance(text, DigestHex):
        text = text.text
    if not isinstance(text, str):
        raise TypeError("make_raw_digest expects a hex string")
    if len(text) == 0:
        raise ValueError(_EMPTY_HEX)
    parsed: list[int] = []
    for start in range(0, len(text), 2):
        value = _strtoi_hex(text[start : start + 2])
        if value is None or value < 0:
            raise ValueError(_HEX_ERROR)
        parsed.append(value)
    return _as_raw(parsed)


def makeRaw(object: object) -> bytes:
    """Convert ``object`` to bytes the way digest's ``makeRaw`` does.

    ``bytes`` and ``bytearray`` are returned as bytes. A ``str`` is
    ``charToRaw``. ``DigestHex`` and ``make_raw_digest`` parse hex.
    A list or tuple of numbers, or one number, is ``as.raw``. ``None``
    is ``as.raw(NULL)``.
    """
    if isinstance(object, DigestHex):
        return make_raw_digest(object.text)
    if isinstance(object, bytearray):
        return bytes(object)
    if isinstance(object, bytes):
        return object
    if isinstance(object, str):
        return _char_to_raw(object)
    if isinstance(object, (list, tuple)):
        if len(object) == 0:
            return b""
        if all(isinstance(item, str) for item in object):
            if len(object) > 1:
                warnings.warn(_CHAR_LEN_WARN, UserWarning, stacklevel=2)
            return _char_to_raw(object[0])
        return _as_raw(object)
    if isinstance(object, (bool, int, float)):
        return _as_raw((object,))
    if object is None:
        return b""
    raise TypeError("cannot coerce to raw")
