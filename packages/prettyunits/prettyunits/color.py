"""Nearest named color in CIE Lab.

`pretty_colour` is the same function as `pretty_color`.
"""

import json
import math
import os

_EPSILON = 216.0 / 24389.0
_KAPPA = 24389.0 / 27.0
_WHITE = (0.95320571254937703, 1.0, 1.08538438164691575)
# Rows are the linear sRGB channels. xyz[j] sums linear[k] * _M[k][j].
_M = (
    (0.41682134188531705, 0.214923504409616606, 0.019538500400874251),
    (0.35657671707797467, 0.713153434155949340, 0.118858905692658334),
    (0.17980765358608541, 0.071923061434434166, 0.946986975553383292),
)
_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


class PrettyColor:
    """Closest color name and the alternate names stored on that row."""

    __slots__ = ("name", "alt")

    def __init__(self, name, alt):
        self.name = name
        self.alt = alt

    def __str__(self):
        if self.name is None:
            return "NA"
        return self.name


def _load_tables():
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, "r_colors.json"), encoding="utf-8") as handle:
        colors = json.load(handle)
    with open(os.path.join(base, "color_reference.json"), encoding="utf-8") as handle:
        reference = json.load(handle)
    labs = tuple((row["L"], row["a"], row["b"]) for row in reference)
    names = tuple(row["name"] for row in reference)
    alts = tuple(tuple(row["name_alt"]) for row in reference)
    return colors, labs, names, alts


_R_COLORS, _LABS, _NAMES, _ALTS = _load_tables()


def _length(color):
    if isinstance(color, (list, tuple)):
        return len(color)
    return 1


def _dogamma(channel):
    if channel < 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def _srgb_to_lab(red, green, blue):
    """R `convertColor(..., from="sRGB", to="Lab", scale.in=256)`."""
    linear = (
        _dogamma(red / 256.0),
        _dogamma(green / 256.0),
        _dogamma(blue / 256.0),
    )
    xyz = [0.0, 0.0, 0.0]
    for column in range(3):
        total = 0.0
        for channel in range(3):
            total += linear[channel] * _M[channel][column]
        xyz[column] = total

    def f(t):
        if t <= _EPSILON:
            return (_KAPPA * t + 16.0) / 116.0
        return t ** (1.0 / 3.0)

    xyzr = (
        f(xyz[0] / _WHITE[0]),
        f(xyz[1] / _WHITE[1]),
        f(xyz[2] / _WHITE[2]),
    )
    lightness = 116.0 * xyzr[1] - 16.0
    a_star = 500.0 * (xyzr[0] - xyzr[1])
    b_star = 200.0 * (xyzr[1] - xyzr[2])
    return lightness, a_star, b_star


def _parse_hex(color):
    body = color[1:]
    size = len(body)
    if size not in (3, 4, 6, 8):
        raise ValueError("invalid RGB specification")
    if any(character not in _HEX_DIGITS for character in body):
        raise ValueError("invalid hex digit in 'color' or 'lty'")
    if size <= 4:
        body = "".join(character * 2 for character in body)
    red = int(body[0:2], 16)
    green = int(body[2:4], 16)
    blue = int(body[4:6], 16)
    return red, green, blue


def _col2rgb(color):
    if color in ("NA", "transparent"):
        return 255, 255, 255
    if color.startswith("#"):
        return _parse_hex(color)
    key = color.replace(" ", "").lower()
    try:
        red, green, blue = _R_COLORS[key]
    except KeyError:
        raise ValueError(f"invalid color name '{color}'") from None
    return red, green, blue


def _nearest(lab):
    lightness, a_star, b_star = lab
    best_index = 0
    best = math.inf
    for index, (ref_l, ref_a, ref_b) in enumerate(_LABS):
        distance = math.sqrt(
            (lightness - ref_l) ** 2 + (a_star - ref_a) ** 2 + (b_star - ref_b) ** 2
        )
        if distance < best:
            best = distance
            best_index = index
    return PrettyColor(_NAMES[best_index], list(_ALTS[best_index]))


def pretty_color(color):
    """Name the nearest color in CIE Lab.

    `color` must have length 1. `None` is a missing color. Any other value
    must be a string that `col2rgb` can read.
    """
    if _length(color) != 1:
        raise ValueError("length(color) == 1 is not TRUE")
    if color is None:
        return PrettyColor(None, None)
    if not isinstance(color, str):
        raise ValueError("is.character(color) is not TRUE")
    return _nearest(_srgb_to_lab(*_col2rgb(color)))


pretty_colour = pretty_color
