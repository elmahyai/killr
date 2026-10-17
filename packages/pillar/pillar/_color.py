"""Crayon-style wrappers pillar builds in .onLoad from cli::make_ansi_style.

The open and close codes are fixed for 16 and 256 colors. The live color
count chooses which pair to apply. One color or fewer pastes the text.
"""

from __future__ import annotations

from typing import Any

from cli.num_ansi_colors import num_ansi_colors
from cli.styles import make_ansi_style

from pillar._text import is_na, paste_atom


def _pair(spec: str, **kwargs: Any) -> tuple[dict, dict]:
    low = make_ansi_style(spec, colors=16, **kwargs)._styles[0]
    high = make_ansi_style(spec, colors=256, **kwargs)._styles[0]
    return low, high


def _painter(spec: str, **kwargs: Any):
    low, high = _pair(spec, **kwargs)

    def paint(value: Any) -> Any:
        count = num_ansi_colors()

        def one(item: Any) -> str:
            text = paste_atom(item)
            if count <= 1:
                return text
            style = high if count >= 256 else low
            return style["open"] + text + style["close"]

        if isinstance(value, str) or is_na(value):
            return one(value)
        return [one(item) for item in value]

    return paint


red = _painter("red")
yellow = _painter("yellow")
bold = _painter("bold")
italic = _painter("italic")
underline = _painter("underline")
# grDevices::grey(0.6) and grey(0.8). grey=True picks the grey ramp.
grey_0_6 = _painter("#999999", grey=True)
grey_0_8 = _painter("#CCCCCC", grey=True)
