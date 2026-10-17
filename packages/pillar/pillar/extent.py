"""Display width, alignment, and pillar ornaments.

``get_extent`` is ``display_extent``. A missing string has width 2.
``match_arg`` rejects None; R's ``match.arg(NULL)`` is the first choice,
so a missing alignment is left.
"""

from __future__ import annotations

import math
from typing import Any

from pillar._color import bold
from pillar._options import get_option
from pillar._text import is_na, match_arg, paste_atom, strrep
from pillar._width import display_extent

_ALIGN = ("left", "right")


def get_extent(x: Any) -> Any:
    """Display width of one string, or of each string in a list."""

    return display_extent(x)


def get_max_extent(x: Any) -> int:
    """Widest display width. An empty vector is 0."""

    extent = get_extent(x)
    if isinstance(extent, int):
        values = [extent]
    else:
        values = list(extent)
    if not values:
        return 0
    return max(0, *values)


def _match_align(align: Any) -> str:
    if is_na(align):
        return "left"
    return match_arg(align, _ALIGN)


def _scalar(value: Any) -> bool:
    return isinstance(value, str) or is_na(value)


def _vector(value: Any) -> list[Any]:
    if _scalar(value):
        return [value]
    return list(value)


def _missing_width(width: Any) -> bool:
    return isinstance(width, float) and math.isnan(width)


def _spare(width: Any, extent: int) -> Any:
    if _missing_width(width):
        return float("nan")
    diff = width - extent
    if isinstance(diff, float) and (math.isnan(diff) or diff < 0):
        if math.isnan(diff):
            return float("nan")
        return 0
    if diff < 0:
        return 0
    return diff


def _pad(space: str, times: Any) -> str:
    """Repeat ``space``. A non-finite count pastes as the letters NA."""

    if isinstance(times, float) and (math.isnan(times) or math.isinf(times)):
        return "NA"
    count = int(times)
    if count <= 0:
        return ""
    return strrep(space, count)


def align(
    x: Any,
    width: Any = None,
    align: Any = "left",
    space: str = " ",
) -> Any:
    """Pad each string to ``width``. Left pads on the right."""

    side = _match_align(align)
    scalar = _scalar(x)
    items = _vector(x)
    if not items:
        return []
    extents = get_extent(items)
    if width is None:
        width = max(extents)
    padded: list[str] = []
    for item, extent in zip(items, extents):
        pad = _pad(space, _spare(width, extent))
        text = paste_atom(item)
        if side == "left":
            padded.append(text + pad)
        else:
            padded.append(pad + text)
    if scalar:
        return padded[0]
    return padded


def _store_width(width: Any) -> int | float:
    if isinstance(width, float) and (math.isnan(width) or math.isinf(width)):
        return float("nan")
    return int(width)


def _header() -> str:
    text = "<pillar_ornament>"
    if get_option("pillar.bold") is True:
        return bold(text)
    return text


class PillarOrnament:
    """Character vector with an alignment and a width."""

    def __init__(self, x: list[Any], align: Any, width: int | float):
        self.x = x
        self.align = align
        self.width = width

    def format(self, width: Any = None, **_ignored: Any) -> list[str]:
        use = self.width if width is None else width
        return align(self.x, width=use, align=self.align)

    def __str__(self) -> str:
        lines = self.format()
        header = _header()
        if not lines:
            return header
        return header + "\n" + "\n".join(lines)


def new_ornament(x: Any, width: Any = None, align: Any = None) -> PillarOrnament:
    """Ornament whose print shows a header and the aligned lines."""

    items = _vector(x)
    if width is None:
        width = get_max_extent(items)
    return PillarOrnament(items, align, _store_width(width))
