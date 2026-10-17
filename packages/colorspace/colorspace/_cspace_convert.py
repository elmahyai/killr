"""Internal colorspace 2.1-4 color conversions (C port for desaturate)."""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np

from colorspace.hex2rgb import HexRGB, hex2RGB
from colorspace.hls import HLSColor
from colorspace.hsv import HSVColor
from colorspace.lab import LABColor
from colorspace.luv import LUVColor
from colorspace.rgb import RGBColor
from colorspace.xyz import XYZColor

_XN, _YN, _ZN = 95.047, 100.0, 108.883
_KAPPA = 24389.0 / 27.0
_EPSILON = 216.0 / 24389.0
_GAMMA = 2.4
_HEX_DIG = "0123456789ABCDEF"
_COLOR_SPACES = frozenset(
    {"RGB", "sRGB", "XYZ", "HSV", "HLS", "LAB", "LUV", "polarLUV", "polarLAB"}
)
_DEFAULT_PALETTE = (
    "black",
    "#DF536B",
    "#61D04F",
    "#2297E6",
    "#28E2E5",
    "#CD0BBC",
    "#F5C710",
    "gray62",
)


class PolarLUVColor:
    __slots__ = ("space", "coords", "names", "columns")

    def __init__(self, coords, names):
        self.space = "polarLUV"
        self.coords = np.asarray(coords, dtype=np.float64)
        self.names = names
        self.columns = ("L", "C", "H")


def is_color_object(value) -> bool:
    space = getattr(value, "space", None)
    return space in _COLOR_SPACES and hasattr(value, "coords")


def _ftrans(channel: float) -> float:
    if channel > 0.03928:
        return math.pow((channel + 0.055) / 1.055, _GAMMA)
    return channel / 12.92


def _gtrans(channel: float) -> float:
    if channel > 0.00304:
        return 1.055 * math.pow(channel, 1.0 / _GAMMA) - 0.055
    return 12.92 * channel


def _rgb_to_xyz(r: float, g: float, b: float) -> tuple[float, float, float]:
    x = _YN * (0.412453 * r + 0.357580 * g + 0.180423 * b)
    y = _YN * (0.212671 * r + 0.715160 * g + 0.072169 * b)
    z = _YN * (0.019334 * r + 0.119193 * g + 0.950227 * b)
    return x, y, z


def _xyz_to_rgb(x: float, y: float, z: float) -> tuple[float, float, float]:
    r = (3.240479 * x - 1.537150 * y - 0.498535 * z) / _YN
    g = (-0.969256 * x + 1.875992 * y + 0.041556 * z) / _YN
    b = (0.055648 * x - 0.204043 * y + 1.057311 * z) / _YN
    return r, g, b


def _srgb_to_xyz(r: float, g: float, b: float) -> tuple[float, float, float]:
    return _rgb_to_xyz(_ftrans(r), _ftrans(g), _ftrans(b))


def _xyz_to_srgb(x: float, y: float, z: float) -> tuple[float, float, float]:
    r, g, b = _xyz_to_rgb(x, y, z)
    return _gtrans(r), _gtrans(g), _gtrans(b)


def _f_lab(t: float) -> float:
    return math.pow(t, 1.0 / 3.0) if t > _EPSILON else (_KAPPA / 116.0) * t + 16.0 / 116.0


def _xyz_to_lab(x: float, y: float, z: float) -> tuple[float, float, float]:
    xr, yr, zr = x / _XN, y / _YN, z / _ZN
    l_val = 116.0 * math.pow(yr, 1.0 / 3.0) - 16.0 if yr > _EPSILON else _KAPPA * yr
    xt, yt, zt = _f_lab(xr), _f_lab(yr), _f_lab(zr)
    return l_val, 500.0 * (xt - yt), 200.0 * (yt - zt)


def _lab_to_xyz(l_val: float, a_val: float, b_val: float) -> tuple[float, float, float]:
    if l_val <= 0:
        y = 0.0
    elif l_val <= 8.0:
        y = l_val * _YN / _KAPPA
    elif l_val <= 100:
        y = _YN * math.pow((l_val + 16) / 116, 3)
    else:
        y = _YN

    if y <= _EPSILON * _YN:
        fy = (_KAPPA / 116.0) * y / _YN + 16.0 / 116.0
    else:
        fy = math.pow(y / _YN, 1.0 / 3.0)

    fx = fy + a_val / 500.0
    if math.pow(fx, 3) <= _EPSILON:
        x = _XN * (fx - 16.0 / 116.0) / (_KAPPA / 116.0)
    else:
        x = _XN * math.pow(fx, 3)

    fz = fy - b_val / 200.0
    if math.pow(fz, 3) <= _EPSILON:
        z = _ZN * (fz - 16.0 / 116.0) / (_KAPPA / 116.0)
    else:
        z = _ZN * math.pow(fz, 3)
    return x, y, z


def _xyz_to_uv(x: float, y: float, z: float) -> tuple[float, float]:
    total = x + y + z
    if total == 0:
        return 0.0, 0.0
    xv, yv = x / total, y / total
    return 2 * xv / (6 * yv - xv + 1.5), 4.5 * yv / (6 * yv - xv + 1.5)


def _xyz_to_luv(x: float, y: float, z: float) -> tuple[float, float, float]:
    u, v = _xyz_to_uv(x, y, z)
    u_n, v_n = _xyz_to_uv(_XN, _YN, _ZN)
    y_ratio = y / _YN
    l_val = 116 * math.pow(y_ratio, 1.0 / 3.0) - 16 if y_ratio > _EPSILON else _KAPPA * y_ratio
    return l_val, 13 * l_val * (u - u_n), 13 * l_val * (v - v_n)


def _luv_to_xyz(l_val: float, u_val: float, v_val: float) -> tuple[float, float, float]:
    if l_val <= 0 and u_val == 0 and v_val == 0:
        return 0.0, 0.0, 0.0
    y = _YN * (math.pow((l_val + 16) / 116, 3) if l_val > 8 else l_val / _KAPPA)
    u_n, v_n = _xyz_to_uv(_XN, _YN, _ZN)
    if l_val == 0:
        u, v = u_n, v_n
    else:
        u = u_val / (13 * l_val) + u_n
        v = v_val / (13 * l_val) + v_n
    x = 9.0 * y * u / (4 * v)
    z = -x / 3 - 5 * y + 3 * y / v
    return x, y, z


def _luv_to_polar(l_val: float, u_val: float, v_val: float) -> tuple[float, float, float]:
    h = math.degrees(math.atan2(v_val, u_val))
    while h > 360:
        h -= 360
    while h < 0:
        h += 360
    return l_val, math.hypot(u_val, v_val), h


def _polar_to_luv(l_val: float, c_val: float, h_val: float) -> tuple[float, float, float]:
    rad = math.radians(h_val)
    return l_val, c_val * math.cos(rad), c_val * math.sin(rad)


def _coords_matrix(color) -> np.ndarray:
    coords = np.asarray(color.coords, dtype=np.float64)
    if coords.ndim != 2 or coords.shape[1] != 3:
        raise ValueError("invalid color matrix")
    return coords


def _row_to_polar_luv(space: str, row: np.ndarray) -> tuple[float, float, float]:
    r, g, b = float(row[0]), float(row[1]), float(row[2])
    if space == "polarLUV":
        return r, g, b
    if space == "LUV":
        return _luv_to_polar(r, g, b)
    if space == "LAB":
        x, y, z = _lab_to_xyz(r, g, b)
        return _luv_to_polar(*_xyz_to_luv(x, y, z))
    if space == "XYZ":
        return _luv_to_polar(*_xyz_to_luv(r, g, b))
    if space == "RGB":
        return _luv_to_polar(*_xyz_to_luv(*_rgb_to_xyz(r, g, b)))
    if space == "sRGB":
        return _luv_to_polar(*_xyz_to_luv(*_srgb_to_xyz(r, g, b)))
    if space in ("HSV", "HLS"):
        raise ValueError("Ambiguous conversion")
    raise ValueError(f"unimplemented colour space ({space})")


def _row_from_polar_luv(target: str, row: np.ndarray) -> tuple[float, float, float]:
    l_val, c_val, h_val = float(row[0]), float(row[1]), float(row[2])
    if target == "polarLUV":
        return l_val, c_val, h_val
    l_u, u, v = _polar_to_luv(l_val, c_val, h_val)
    if target == "LUV":
        return l_u, u, v
    x, y, z = _luv_to_xyz(l_u, u, v)
    if target == "XYZ":
        return x, y, z
    if target == "LAB":
        return _xyz_to_lab(x, y, z)
    if target == "RGB":
        return _xyz_to_rgb(x, y, z)
    if target == "sRGB":
        return _xyz_to_srgb(x, y, z)
    if target in ("HSV", "HLS"):
        raise ValueError("Ambiguous conversion")
    raise ValueError(f"unimplemented colour space ({target})")


def as_polar_luv(color):
    if color.space == "polarLUV":
        return PolarLUVColor(_coords_matrix(color).copy(), color.names)
    coords = _coords_matrix(color)
    rows = [_row_to_polar_luv(color.space, coords[i]) for i in range(coords.shape[0])]
    return PolarLUVColor(np.array(rows, dtype=np.float64), color.names)


def coerce_color(color, target_space: str):
    coords = _coords_matrix(color)
    rows = [_row_from_polar_luv(target_space, coords[i]) for i in range(coords.shape[0])]
    out = np.array(rows, dtype=np.float64)
    names = color.names
    if target_space == "RGB":
        return RGBColor(out, names)
    if target_space == "sRGB":
        return HexRGB("sRGB", out, names)
    if target_space == "XYZ":
        return XYZColor(out, names)
    if target_space == "LAB":
        return LABColor(out, names)
    if target_space == "LUV":
        return LUVColor(out, names)
    if target_space == "HSV":
        return HSVColor(out, names)
    if target_space == "HLS":
        return HLSColor(out, names)
    if target_space == "polarLUV":
        return PolarLUVColor(out, names)
    raise ValueError(f"unimplemented colour space ({target_space})")


def as_srgb_coords(color) -> np.ndarray:
    if color.space == "sRGB":
        return _coords_matrix(color).copy()
    if color.space == "polarLUV":
        return coerce_color(color, "sRGB").coords.copy()
    converted = coerce_color(as_polar_luv(color), "sRGB")
    return converted.coords.copy()


def hex_from_srgb(coords: np.ndarray, fixup: bool = False) -> list[str | None]:
    out: list[str | None] = []
    for row in np.asarray(coords, dtype=np.float64):
        r, g, b = float(row[0]), float(row[1]), float(row[2])
        if not (math.isfinite(r) and math.isfinite(g) and math.isfinite(b)):
            out.append(None)
            continue
        ir = int(255 * r + 0.5)
        ig = int(255 * g + 0.5)
        ib = int(255 * b + 0.5)
        fix = 0
        for channel in (ir, ig, ib):
            if channel < 0 or channel > 255:
                fix = 1
        ir = min(255, max(0, ir))
        ig = min(255, max(0, ig))
        ib = min(255, max(0, ib))
        if fix and not fixup:
            out.append(None)
            continue
        out.append(
            "#"
            + _HEX_DIG[(ir // 16) % 16]
            + _HEX_DIG[ir % 16]
            + _HEX_DIG[(ig // 16) % 16]
            + _HEX_DIG[ig % 16]
            + _HEX_DIG[(ib // 16) % 16]
            + _HEX_DIG[ib % 16]
        )
    return out


@lru_cache(maxsize=1)
def _r_colors() -> dict[str, tuple[int, int, int]]:
    path = Path(__file__).resolve().parent / "r_colors.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {name: (int(rgb[0]), int(rgb[1]), int(rgb[2])) for name, rgb in raw.items()}


def _parse_hex_body(body: str) -> tuple[int, int, int]:
    if len(body) in (3, 4):
        body = "".join(ch * 2 for ch in body)
    red = int(body[0:2], 16)
    green = int(body[2:4], 16)
    blue = int(body[4:6], 16)
    return red, green, blue


def _col2rgb_one(color) -> tuple[int, int, int, int]:
    if color is None or (isinstance(color, float) and math.isnan(color)):
        return (0, 0, 0, 0)
    if isinstance(color, (bool, np.bool_)):
        raise ValueError(f"invalid color: {color}")
    if isinstance(color, (int, np.integer)) or (
        isinstance(color, (float, np.floating)) and float(color).is_integer()
    ):
        index = int(color) - 1
        if index < 0 or index >= len(_DEFAULT_PALETTE):
            raise ValueError(f"invalid palette index: {color}")
        color = _DEFAULT_PALETTE[index]
    if not isinstance(color, str):
        raise ValueError(f"invalid color: {color}")
    if color in ("NA", "transparent"):
        return (255, 255, 255, 0)
    if color.startswith("#"):
        body = color[1:]
        if len(body) not in (3, 4, 6, 8):
            raise ValueError("invalid RGB specification")
        red, green, blue = _parse_hex_body(body[:6])
        alpha = 255
        if len(body) == 8:
            alpha = int(body[6:8], 16)
        elif len(body) == 4:
            alpha = int(body[3] * 2, 16)
        return red, green, blue, alpha
    key = color.replace(" ", "").lower()
    red, green, blue = _r_colors()[key]
    return red, green, blue, 255


def col2rgb_matrix(colors) -> np.ndarray:
    rows = [_col2rgb_one(color) for color in colors]
    return np.array(rows, dtype=np.float64)


def srgb_from_gamma_matrix(values: np.ndarray) -> HexRGB:
    coords = np.asarray(values, dtype=np.float64) / 255.0
    return HexRGB("sRGB", coords, None)
