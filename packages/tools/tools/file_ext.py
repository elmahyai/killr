"""tools::file_ext from R 4.5.0.

The extension is the trailing run of locale alphanumeric characters after a
dot. pathlib and str.isalnum() disagree with that class, so the character
test is libc iswalnum, which is the class R's [[:alnum:]] uses.
"""

from __future__ import annotations

import ctypes
import math
from typing import Any

_libc = ctypes.CDLL(None)
_libc.iswalnum.argtypes = [ctypes.c_uint32]
_libc.iswalnum.restype = ctypes.c_int


class NA:
    """R's NA_character_, kept distinct from an empty extension."""

    def __repr__(self) -> str:
        return "NA"


NA_character_ = NA()


def _is_alnum(char: str) -> bool:
    return bool(_libc.iswalnum(ord(char)))


def _as_character(value: Any) -> str | NA:
    if value is None or isinstance(value, NA):
        return NA_character_
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Inf" if value > 0 else "-Inf"
        if value == math.trunc(value) and abs(value) < 2**53:
            return str(int(value))
        return str(value)
    return str(value)


def _one(text: str | NA) -> str | NA:
    if isinstance(text, NA):
        return NA_character_
    end = len(text)
    start = end
    while start > 0 and _is_alnum(text[start - 1]):
        start -= 1
    if start < end and start > 0 and text[start - 1] == ".":
        return text[start:]
    return ""


def file_ext(x: Any) -> Any:
    """Extension after the last dot, or "" when it is not alphanumeric.

    NULL and an empty character vector return an empty list, which is R's
    logical(0). A single string returns a string. NA stays NA.
    """
    if x is None or x == []:
        return []
    if isinstance(x, (str, bool, int, float, NA)):
        return _one(_as_character(x))
    return [_one(_as_character(item)) for item in x]
