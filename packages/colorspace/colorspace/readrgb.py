"""Read gcolorsel-style RGB triplets from a file (colorspace 2.1-4)."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from colorspace._cspace_convert import _ftrans, as_polar_luv, coerce_color
from colorspace.rgb import RGBColor
from colorspace.hls import HLSColor
from colorspace.hsv import HSVColor
from colorspace.mixcolor import _rgb_to_hls, _rgb_to_hsv
from colorspace.rgb import RGB


def _as_class(color, class_name: str = "RGB"):
    target = class_name if class_name else "RGB"
    if getattr(color, "space", None) == target:
        return color
    if target == "RGB" and color.space == "sRGB":
        rows = [
            (_ftrans(float(r)), _ftrans(float(g)), _ftrans(float(b)))
            for r, g, b in color.coords
        ]
        return RGBColor(np.asarray(rows, dtype=np.float64), color.names)
    polar = as_polar_luv(color)
    if target == "polarLUV":
        return polar
    if target in ("HSV", "HLS"):
        if color.space in ("RGB", "sRGB"):
            channels = color.coords
        else:
            channels = coerce_color(polar, "sRGB").coords
        rows = []
        for r, g, b in channels:
            if target == "HSV":
                rows.append(_rgb_to_hsv(float(r), float(g), float(b)))
            else:
                rows.append(_rgb_to_hls(float(r), float(g), float(b)))
        cls = HSVColor if target == "HSV" else HLSColor
        return cls(np.asarray(rows, dtype=np.float64), color.names)
    return coerce_color(polar, target)


def _scan_rgb_file(path: str | Path) -> tuple[list[int], list[int], list[int]]:
    text = Path(path).read_text(encoding="utf-8")
    tokens = re.findall(r"\S+", text)
    reds: list[int] = []
    greens: list[int] = []
    blues: list[int] = []
    index = 0
    while index + 3 < len(tokens):
        reds.append(int(tokens[index]))
        greens.append(int(tokens[index + 1]))
        blues.append(int(tokens[index + 2]))
        index += 4
    return reds, greens, blues


def readRGB(file, class_: str = "RGB"):
    """Read integer RGB lines from ``file`` and return a color object."""
    reds, greens, blues = _scan_rgb_file(file)
    if not reds:
        return _as_class(RGB(), class_)
    color = RGB(
        R=[value / 255.0 for value in reds],
        G=[value / 255.0 for value in greens],
        B=[value / 255.0 for value in blues],
    )
    return _as_class(color, class_)
