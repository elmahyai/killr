"""Coerce text to UTF-8 and test that it is valid UTF-8."""

from __future__ import annotations

from typing import Any

from utf8._text import normalize_text


def _one_utf8(value: Any, normalize: bool) -> str:
    if isinstance(value, bytes):
        text = value.decode("utf-8")
    elif isinstance(value, str):
        text = value
    else:
        raise TypeError("argument is not a character object")
    if normalize:
        return normalize_text(text)
    return text


def as_utf8(x: Any, normalize: bool = False) -> Any:
    """Convert text to Unicode. ``normalize`` composes it to NFC.

    A Python string is already Unicode. ``bytes`` are decoded as UTF-8 and
    rejected when that decoding fails. R's declared encodings are not a
    separate mark on a Python string.
    """

    if x is None:
        return None
    if isinstance(x, (str, bytes)):
        return _one_utf8(x, normalize)
    return [_one_utf8(item, normalize) for item in x]


def _valid_one(value: Any) -> bool:
    if isinstance(value, str):
        return True
    if isinstance(value, bytes):
        try:
            value.decode("utf-8")
        except UnicodeDecodeError:
            return False
        return True
    raise TypeError("argument is not a character object")


def utf8_valid(x: Any) -> Any:
    """Whether each element is valid UTF-8. A string is valid. ``bytes`` must decode."""

    if isinstance(x, (str, bytes)):
        return _valid_one(x)
    return [_valid_one(item) for item in x]
