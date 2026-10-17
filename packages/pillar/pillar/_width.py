"""Display width after ANSI sequences are removed.

cli::utf8_nchar is not translated yet. Widths come from the utf8 table.
A control or unassigned character has width 0, which matches nchar(type = "width")
for the characters pillar formats. A missing string has width 2 because
nchar(NA) is the width of the letters NA.
"""

from __future__ import annotations

import re
from typing import Any

from utf8._text import unit_width

from pillar._text import is_na

_CSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_OSC = re.compile(r"\x1b\][^\x07]*(?:\x07|\x1b\\)")


def ansi_strip(value: Any) -> Any:
    if is_na(value):
        return None
    if isinstance(value, str):
        return _OSC.sub("", _CSI.sub("", value))
    return [ansi_strip(item) for item in value]


def _width_one(text: str) -> int:
    total = 0
    for char in text:
        width = unit_width(char)
        total += 0 if width is None else width
    return total


def display_extent(value: Any) -> Any:
    """Width of one string, or of each string in a list."""

    def one(item: Any) -> int:
        if is_na(item):
            return 2
        if not isinstance(item, str):
            raise TypeError("get_extent expects a string")
        return _width_one(ansi_strip(item))

    if isinstance(value, str) or is_na(value):
        return one(value)
    return [one(item) for item in value]
