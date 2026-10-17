"""Reverse each string by code point, from stringi."""

from __future__ import annotations

from stringi._na import NA, is_na
from stringi.utils import _as_character


def stri_reverse(str):
    """Reverse the code points of each string. A missing value stays missing."""
    out = []
    for value in _as_character(str):
        if is_na(value):
            out.append(NA)
        else:
            out.append(value[::-1])
    return out
