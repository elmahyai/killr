"""Simulate deuteranomaly color vision deficiency (colorspace 2.1-4)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from colorspace._cspace_convert import (
    _ftrans,
    _gtrans,
    as_polar_luv,
    as_srgb_coords,
    coerce_color,
    hex_from_srgb,
)
from colorspace.desaturate import _PrismaticColors, _parse_input
from colorspace.hex2rgb import HexRGB
from colorspace.rgb import RGBColor


def deutan(col, severity=1, linear=True):
    """Simulate deuteranomaly by severity in ``[0, 1]`` (default dichromacy)."""
    transform = _interpolate_cvd_transform(_deutanomaly_cvd(), float(severity))
    return _simulate_cvd(col, transform, linear=linear)


@lru_cache(maxsize=1)
def _deutanomaly_cvd() -> list[np.ndarray]:
    path = Path(__file__).resolve().parent / "deutanomaly_cvd.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [np.asarray(row, dtype=np.float64).reshape(3, 3) for row in raw]


def _interpolate_cvd_transform(cvd: list[np.ndarray], severity: float) -> np.ndarray:
    if severity <= 0:
        return cvd[0]
    if severity >= 1:
        return cvd[10]
    s = 10.0 * severity
    i1 = int(np.floor(s))
    i2 = int(np.ceil(s))
    if i1 == i2:
        return cvd[i1]
    return (i2 - s) * cvd[i1] + (s - i1) * cvd[i2]


def _srgb_to_linear_rgb(values: np.ndarray) -> np.ndarray:
    x = np.asarray(values, dtype=np.float64)
    out = np.empty_like(x)
    for idx, channel in np.ndenumerate(x):
        out[idx] = _ftrans(channel / 255.0) * 255.0
    return out


def _linear_rgb_to_srgb(values: np.ndarray) -> np.ndarray:
    y = np.asarray(values, dtype=np.float64)
    out = np.empty_like(y)
    for idx, channel in np.ndenumerate(y):
        out[idx] = _gtrans(channel / 255.0) * 255.0
    return out


def _rgb_working_matrix(col_obj, *, linear: bool) -> np.ndarray:
    if linear:
        if col_obj.space == "RGB":
            return col_obj.coords.T * 255.0
        if col_obj.space == "sRGB":
            rows = [
                [_ftrans(float(r)), _ftrans(float(g)), _ftrans(float(b))]
                for r, g, b in col_obj.coords
            ]
            return np.asarray(rows, dtype=np.float64).T * 255.0
        return coerce_color(as_polar_luv(col_obj), "RGB").coords.T * 255.0
    return as_srgb_coords(col_obj).T * 255.0


def _color_from_working_rgb(rgb, col_obj, target_space: str, *, linear: bool):
    coords = (rgb / 255.0).T
    if linear:
        if target_space == "RGB":
            return RGBColor(coords, col_obj.names)
        if target_space == "sRGB":
            srgb = np.array(
                [[_gtrans(r), _gtrans(g), _gtrans(b)] for r, g, b in coords],
                dtype=np.float64,
            )
            return HexRGB("sRGB", srgb, col_obj.names)
        return coerce_color(as_polar_luv(RGBColor(coords, col_obj.names)), target_space)
    if target_space == "sRGB":
        return HexRGB("sRGB", coords, col_obj.names)
    return coerce_color(as_polar_luv(HexRGB("sRGB", coords, col_obj.names)), target_space)


def _matrix_output_transpose(col) -> bool:
    matrix = np.asarray(col, dtype=np.float64)
    return matrix.ndim == 2 and matrix.shape[0] != 3 and matrix.shape[1] == 3


def _simulate_cvd(col, cvd_transform: np.ndarray, *, linear: bool = True):
    matrix_transpose = _matrix_output_transpose(col) if isinstance(col, np.ndarray) else False
    input_type, target_space, col_obj, alpha_suffixes, na_indices, _transpose, prismatic = (
        _parse_input(col)
    )

    if input_type == "colorspace":
        rgb = _rgb_working_matrix(col_obj, linear=linear)
    else:
        rgb = col_obj.coords.T * 255.0

    if linear and input_type in ("hex", "other"):
        rgb = _srgb_to_linear_rgb(rgb)

    rgb = cvd_transform @ rgb
    rgb = np.clip(rgb, 0.0, 255.0)

    if linear and input_type in ("hex", "other"):
        rgb = _linear_rgb_to_srgb(rgb)

    if input_type == "colorspace":
        return _color_from_working_rgb(rgb, col_obj, target_space, linear=linear)

    if input_type == "matrix":
        return rgb.T if matrix_transpose else rgb

    srgb = np.clip(np.round(rgb) / 255.0, 0.0, 1.0).T
    hexes = hex_from_srgb(srgb, fixup=False)
    if alpha_suffixes is not None:
        hexes = [
            (None if value is None else value + suffix)
            for value, suffix in zip(hexes, alpha_suffixes, strict=True)
        ]
    for index in na_indices:
        hexes[index] = None
    if prismatic:
        return _PrismaticColors(hexes)
    return hexes
