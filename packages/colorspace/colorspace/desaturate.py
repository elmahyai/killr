"""Desaturate colors by chroma removal in HCL space (colorspace 2.1-4)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

from colorspace._cspace_convert import (
    as_polar_luv,
    as_srgb_coords,
    coerce_color,
    col2rgb_matrix,
    hex_from_srgb,
    is_color_object,
    srgb_from_gamma_matrix,
)
from colorspace.hex2rgb import HexRGB, hex2RGB


def desaturate(col, amount=1, **kwargs):
    """Reduce chroma of colors in HCL (polar LUV) space."""
    if "severity" in kwargs and kwargs["severity"] is not None:
        amount = kwargs["severity"]

    input_type, target_space, col_obj, alpha_suffixes, na_indices, transpose, prismatic = (
        _parse_input(col)
    )

    polar = as_polar_luv(col_obj)
    coords = polar.coords
    coords[:, 1] = (1 - amount) * coords[:, 1]
    extreme = (coords[:, 0] <= 0) | (coords[:, 0] >= 100)
    coords[extreme, 1:3] = 0

    if input_type == "colorspace":
        return coerce_color(polar, target_space)

    if input_type == "matrix":
        rgb = as_srgb_coords(polar) * 255
        return rgb.T if transpose else rgb

    hexes = hex_from_srgb(as_srgb_coords(polar), fixup=False)
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


class _PrismaticColors(list):
    __name__ = "colors"


def _is_na(value) -> bool:
    return value is None or (isinstance(value, float) and np.isnan(value))


def _parse_input(col):
    if is_color_object(col):
        return "colorspace", col.space, col, None, [], True, False

    if isinstance(col, np.ndarray) and col.ndim == 2:
        return _parse_rgb_matrix(col)

    if isinstance(col, str):
        if col.startswith("#") and len(col) in (7, 9):
            return _parse_hex_vector([col])
        return _parse_other_vector([col])

    if isinstance(col, Mapping):
        values = list(col.values())
        if values and all(
            isinstance(item, str) and item.startswith("#") and len(item) in (7, 9)
            for item in values
            if not _is_na(item)
        ):
            color = hex2RGB({key: value[:7] for key, value in col.items()})
            alpha = ["" if _is_na(value) else value[7:9] for value in values]
            na_idx = [index for index, value in enumerate(values) if _is_na(value)]
            return "hex", None, color, alpha, na_idx, True, False
        raise ValueError("invalid color input")

    if isinstance(col, Sequence) and not isinstance(col, (str, bytes)):
        if not col:
            return _parse_other_vector([])
        if all(isinstance(item, str) for item in col):
            if all(
                (not _is_na(item))
                and item.startswith("#")
                and len(item) in (7, 9)
                for item in col
            ):
                prismatic = getattr(col, "__class__", type(col)).__name__ == "PrismaticColors"
                return _parse_hex_vector(col, prismatic=prismatic)
        return _parse_other_vector(list(col))

    return _parse_other_vector([col])


def _parse_hex_vector(col, prismatic=False):
    na_idx = [index for index, value in enumerate(col) if _is_na(value)]
    texts = ["" if _is_na(value) else value[:7] for value in col]
    color = hex2RGB(texts)
    alpha = ["" if _is_na(value) else value[7:9] for value in col]
    return "hex", None, color, alpha, na_idx, True, prismatic


def _parse_other_vector(col):
    na_idx = [index for index, value in enumerate(col) if _is_na(value)]
    rgb = col2rgb_matrix(col)
    alpha = []
    for _, _, _, a_val in rgb:
        alpha.append("" if int(a_val) == 255 else format(int(a_val), "02X"))
    color = srgb_from_gamma_matrix(rgb[:, :3])
    return "hex", None, color, alpha, na_idx, True, False


def _parse_rgb_matrix(col):
    matrix = np.asarray(col, dtype=np.float64)
    transpose = True
    if matrix.shape[0] != 3 and matrix.shape[1] == 3:
        transpose = False
        matrix = matrix.T
    if matrix.shape[0] != 3:
        raise ValueError("matrix must have 3 rows named R, G, and B")
    coords = (matrix[:3, :].T / 255.0).astype(np.float64)
    color = HexRGB("sRGB", coords, None)
    return "matrix", None, color, None, [], transpose, False
