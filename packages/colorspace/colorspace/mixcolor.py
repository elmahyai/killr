"""Convex combination of two colors (colorspace 2.1-4 ``mixcolor``)."""

from __future__ import annotations

import math
import warnings

import numpy as np

from colorspace._cspace_convert import (
    PolarLUVColor,
    as_polar_luv,
    coerce_color,
    is_color_object,
)
from colorspace.hex2rgb import HexRGB
from colorspace.hls import HLS
from colorspace.hsv import HSV
from colorspace.lab import LAB
from colorspace.luv import LUV
from colorspace.rgb import RGB
from colorspace.xyz import XYZ

_POLAR_WARN_SPACES = frozenset({"polarLUV", "polarLAB", "HSV", "HLS"})


class PolarLABColor:
    __slots__ = ("space", "coords", "names", "columns")

    def __init__(self, coords, names):
        self.space = "polarLAB"
        self.coords = np.asarray(coords, dtype=np.float64)
        self.names = names
        self.columns = ("L", "C", "H")


def mixcolor(alpha, color1, color2, where=None):
    """Mix ``color1`` and ``color2`` with weight ``alpha`` in space ``where``."""
    if not is_color_object(color1) or not is_color_object(color2):
        raise TypeError("color1 and color2 must be colorspace color objects")
    if where is None:
        where = color1.space
    if where in _POLAR_WARN_SPACES:
        warnings.warn(
            f"convex combination of colors in polar coordinates ({where}) may not be appropriate",
            stacklevel=2,
        )

    alpha_arr = np.asarray(alpha, dtype=np.float64).ravel()
    c1 = _as_coords(color1, where)
    c2 = _as_coords(color2, where)
    na = alpha_arr.size if alpha_arr.size else 1
    n1 = c1.shape[0]
    n2 = c2.shape[0]
    n = max(na, n1, n2)
    if na < n:
        alpha_arr = np.resize(alpha_arr, n)
    if n1 < n:
        c1 = c1[np.resize(np.arange(n1), n)]
    if n2 < n:
        c2 = c2[np.resize(np.arange(n2), n)]

    mixed = (1.0 - alpha_arr[:, None]) * c1 + alpha_arr[:, None] * c2
    return _make_color(where, mixed, None)


def _coords_matrix(color) -> np.ndarray:
    coords = np.asarray(color.coords, dtype=np.float64)
    if coords.ndim != 2 or coords.shape[1] != 3:
        raise ValueError("invalid color matrix")
    return coords


def _as_coords(color, where: str) -> np.ndarray:
    if color.space == where:
        return _coords_matrix(color).copy()
    space = color.space
    if where in ("RGB", "sRGB", "XYZ", "LAB", "LUV", "polarLUV"):
        if space in ("HSV", "HLS"):
            raise ValueError("Ambiguous conversion")
        return _coords_matrix(coerce_color(as_polar_luv(color), where))
    if where == "HSV":
        return _coords_to_hsv(_coords_matrix(color), space)
    if where == "HLS":
        return _coords_to_hls(_coords_matrix(color), space)
    if where == "polarLAB":
        return _coords_to_polar_lab(color)
    raise ValueError(f"unimplemented colour space ({where})")


def _make_color(where: str, coords: np.ndarray, names):
    coords = np.asarray(coords, dtype=np.float64)
    if where == "RGB":
        return RGB(coords, names=names)
    if where == "sRGB":
        return HexRGB("sRGB", coords, names)
    if where == "XYZ":
        return XYZ(coords, names=names)
    if where == "LAB":
        return LAB(coords, names=names)
    if where == "LUV":
        return LUV(coords, names=names)
    if where == "HSV":
        return HSV(coords, names=names)
    if where == "HLS":
        return HLS(coords, names=names)
    if where == "polarLUV":
        return PolarLUVColor(coords, names)
    if where == "polarLAB":
        return PolarLABColor(coords, names)
    raise ValueError(f"unimplemented colour space ({where})")


def _coords_to_polar_lab(color) -> np.ndarray:
    space = color.space
    if space == "polarLAB":
        return _coords_matrix(color).copy()
    if space in ("HSV", "HLS"):
        raise ValueError("Ambiguous conversion")
    if space == "LAB":
        lab = _coords_matrix(color)
    else:
        lab = _coords_matrix(coerce_color(as_polar_luv(color), "LAB"))
    rows = [_lab_to_polar_lab(*lab[i]) for i in range(lab.shape[0])]
    return np.array(rows, dtype=np.float64)


def _lab_to_polar_lab(l_val: float, a_val: float, b_val: float) -> tuple[float, float, float]:
    h_val = math.degrees(math.atan2(b_val, a_val))
    while h_val > 360:
        h_val -= 360
    while h_val < 0:
        h_val += 360
    return l_val, math.hypot(a_val, b_val), h_val


def _max3(a: float, b: float, c: float) -> float:
    return max(a, b, c)


def _min3(a: float, b: float, c: float) -> float:
    return min(a, b, c)


def _rgb_to_hsv(r: float, g: float, b: float) -> tuple[float, float, float]:
    x_val = _min3(r, g, b)
    y_val = _max3(r, g, b)
    if y_val != x_val:
        if r == x_val:
            f_val = g - b
            i_val = 3
        elif g == x_val:
            f_val = b - r
            i_val = 5
        else:
            f_val = r - g
            i_val = 1
        h_val = 60.0 * (i_val - f_val / (y_val - x_val))
        s_val = (y_val - x_val) / y_val
        v_val = y_val
    else:
        h_val = 0.0
        s_val = 0.0
        v_val = y_val
    return h_val, s_val, v_val


def _hsv_to_rgb(h: float, s: float, v: float) -> tuple[float, float, float]:
    if math.isnan(h):
        return v, v, v
    h_scaled = h / 60.0
    i_val = math.floor(h_scaled)
    f_val = h_scaled - i_val
    if not (int(i_val) & 1):
        f_val = 1.0 - f_val
    m_val = v * (1.0 - s)
    n_val = v * (1.0 - s * f_val)
    i_mod = int(i_val) % 6
    if i_mod in (0, 6):
        return v, n_val, m_val
    if i_mod == 1:
        return n_val, v, m_val
    if i_mod == 2:
        return m_val, v, n_val
    if i_mod == 3:
        return m_val, n_val, v
    if i_mod == 4:
        return n_val, m_val, v
    return v, m_val, n_val


def _rgb_to_hls(r: float, g: float, b: float) -> tuple[float, float, float]:
    min_c = _min3(r, g, b)
    max_c = _max3(r, g, b)
    l_val = (max_c + min_c) / 2.0
    if max_c != min_c:
        if l_val < 0.5:
            s_val = (max_c - min_c) / (max_c + min_c)
        else:
            s_val = (max_c - min_c) / (2.0 - max_c - min_c)
        if r == max_c:
            h_val = (g - b) / (max_c - min_c)
        elif g == max_c:
            h_val = 2.0 + (b - r) / (max_c - min_c)
        else:
            h_val = 4.0 + (r - g) / (max_c - min_c)
        h_val *= 60.0
        if h_val < 0:
            h_val += 360.0
        if h_val > 360:
            h_val -= 360.0
    else:
        s_val = 0.0
        h_val = 0.0
    return h_val, l_val, s_val


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


def _hls_to_rgb(h: float, l_val: float, s: float) -> tuple[float, float, float]:
    if l_val <= 0.5:
        p2 = l_val * (1.0 + s)
    else:
        p2 = l_val + s - (l_val * s)
    p1 = 2.0 * l_val - p2
    if s == 0:
        return l_val, l_val, l_val
    return _qtrans(p1, p2, h + 120), _qtrans(p1, p2, h), _qtrans(p1, p2, h - 120)


def _coords_to_hsv(coords: np.ndarray, space: str) -> np.ndarray:
    rows = []
    for row in coords:
        r, g, b = float(row[0]), float(row[1]), float(row[2])
        if space == "HSV":
            rows.append((r, g, b))
        elif space == "HLS":
            rgb = _hls_to_rgb(r, g, b)
            rows.append(_rgb_to_hsv(*rgb))
        elif space in ("RGB", "sRGB"):
            rows.append(_rgb_to_hsv(r, g, b))
        else:
            raise ValueError("Ambiguous conversion")
    return np.array(rows, dtype=np.float64)


def _coords_to_hls(coords: np.ndarray, space: str) -> np.ndarray:
    rows = []
    for row in coords:
        r, g, b = float(row[0]), float(row[1]), float(row[2])
        if space == "HLS":
            rows.append((r, g, b))
        elif space == "HSV":
            rgb = _hsv_to_rgb(r, g, b)
            rows.append(_rgb_to_hls(*rgb))
        elif space == "RGB":
            rows.append(_rgb_to_hls(r, g, b))
        elif space == "sRGB":
            rows.append(_rgb_to_hls(r, g, b))
        else:
            raise ValueError("Ambiguous conversion")
    return np.array(rows, dtype=np.float64)
