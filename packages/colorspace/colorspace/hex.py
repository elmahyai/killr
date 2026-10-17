"""Convert color objects to hexadecimal strings (colorspace 2.1-4)."""

from __future__ import annotations

import math
import warnings

import numpy as np

from colorspace._cspace_convert import (
    _coords_matrix,
    _gtrans,
    as_srgb_coords,
    hex_from_srgb,
    is_color_object,
)


def hex(from_, gamma=None, fixup=False):
    """Convert colorspace color objects to ``#RRGGBB`` strings."""
    if gamma is not None:
        warnings.warn(
            "'gamma' is deprecated and has no effect",
            DeprecationWarning,
            stacklevel=2,
        )
    if not is_color_object(from_):
        raise TypeError("invalid class for 'from' argument")
    coords = _as_srgb_coords(from_)
    return hex_from_srgb(coords, fixup=fixup)


def _as_srgb_coords(color) -> np.ndarray:
    """Mirror R ``as(from, \"sRGB\")@coords`` including HSV and HLS."""
    space = color.space
    coords = _coords_matrix(color)
    if space == "sRGB":
        return coords.copy()
    if space == "RGB":
        rows = [
            (_gtrans(float(r)), _gtrans(float(g)), _gtrans(float(b)))
            for r, g, b in coords
        ]
        return np.asarray(rows, dtype=np.float64)
    if space == "HSV":
        rows = [_hsv_to_rgb(float(h), float(s), float(v)) for h, s, v in coords]
        return np.asarray(rows, dtype=np.float64)
    if space == "HLS":
        rows = [_hls_to_rgb(float(h), float(l_val), float(s)) for h, l_val, s in coords]
        return np.asarray(rows, dtype=np.float64)
    return as_srgb_coords(color)


def _hsv_to_rgb(h: float, s: float, v: float) -> tuple[float, float, float]:
    if math.isnan(h):
        return v, v, v
    h = h / 60.0
    i = math.floor(h)
    f = h - i
    if not (int(i) & 1):
        f = 1.0 - f
    m = v * (1.0 - s)
    n = v * (1.0 - s * f)
    i = int(i) % 6
    if i == 0:
        return v, n, m
    if i == 1:
        return n, v, m
    if i == 2:
        return m, v, n
    if i == 3:
        return m, n, v
    if i == 4:
        return n, m, v
    return v, m, n


def _hls_to_rgb(h: float, l_val: float, s: float) -> tuple[float, float, float]:
    if l_val <= 0.5:
        p2 = l_val * (1.0 + s)
    else:
        p2 = l_val + s - (l_val * s)
    p1 = 2.0 * l_val - p2
    if s == 0:
        return l_val, l_val, l_val
    return (
        _qtrans(p1, p2, h + 120),
        _qtrans(p1, p2, h),
        _qtrans(p1, p2, h - 120),
    )


def _qtrans(q1: float, q2: float, hue: float) -> float:
    if hue > 360:
        hue -= 360
    if hue < 0:
        hue += 360
    if hue < 60:
        return q1 + (q2 - q1) * hue / 60.0
    if hue < 180:
        return q2
    if hue < 240:
        return q1 + (q2 - q1) * (240.0 - hue) / 60.0
    return q1
