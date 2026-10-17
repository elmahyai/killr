"""Adjust alpha transparency of colors (colorspace 2.1-4 adjust_transparency)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

from colorspace._cspace_convert import (
    as_srgb_coords,
    col2rgb_matrix,
    hex_from_srgb,
    is_color_object,
)
from colorspace.desaturate import _PrismaticColors, _is_na


def adjust_transparency(col, alpha=True):
    """Return hex color strings with adjusted alpha transparency."""
    new_alpha = alpha

    names = None
    if isinstance(col, Mapping):
        names = list(col.keys())
        col = list(col.values())

    prismatic = isinstance(col, _PrismaticColors)
    if prismatic:
        col = list(col)

    if is_color_object(col):
        names = names if names is not None else getattr(col, "names", None)
        hexes = hex_from_srgb(as_srgb_coords(col))
        col = [None if value is None else value + "FF" for value in hexes]

    na_idx = _na_indices(col)
    n = _ncolors(col)

    if _is_rgb_matrix(col):
        alpha_parts, col_hex = _alpha_from_matrix(np.asarray(col, dtype=np.float64))
    else:
        col_list = _as_color_list(col)
        if _is_all_hex(col_list):
            alpha_parts, col_hex = _alpha_from_hex(col_list)
        else:
            alpha_parts, col_hex = _alpha_from_col2rgb(col_list)

    alpha_parts, col_hex = _adjust_alpha_parts(alpha_parts, new_alpha, n, col_hex)

    out = [_paste_hex(rgb, alpha_parts[index]) for index, rgb in enumerate(col_hex)]
    for index in na_idx:
        out[index] = None

    if prismatic:
        result = _PrismaticColors(out)
    else:
        result = out

    if names is not None and len(names) == len(result):
        if isinstance(result, _PrismaticColors):
            result.names = names
        else:
            named = _NamedHexList(result)
            named.names = names
            return named
    return result


class _NamedHexList(list):
    pass


def _na_indices(col) -> list[int]:
    if isinstance(col, np.ndarray) and col.ndim == 2:
        return [
            index
            for index in range(col.shape[1])
            if np.any(np.isnan(col[:, index]))
        ]
    if isinstance(col, (str, bytes)) or is_color_object(col):
        return []
    if isinstance(col, Sequence):
        return [index for index, value in enumerate(col) if _is_na(value)]
    return [] if not _is_na(col) else [0]


def _ncolors(col) -> int:
    if isinstance(col, np.ndarray) and col.ndim == 2 and col.shape[0] in (3, 4):
        return col.shape[1]
    if is_color_object(col):
        return col.coords.shape[0]
    if isinstance(col, (str, bytes)):
        return 1
    if isinstance(col, Sequence) and not isinstance(col, (str, bytes)):
        return len(col)
    return 1


def _as_color_list(col):
    if isinstance(col, np.ndarray):
        return col
    if isinstance(col, (str, bytes)):
        return [col]
    if isinstance(col, Sequence):
        return list(col)
    return [col]


def _is_all_hex(col_list) -> bool:
    if len(col_list) == 0:
        return True
    for value in col_list:
        if _is_na(value):
            return False
        if not isinstance(value, str):
            return False
        if not value.startswith("#"):
            return False
        if len(value) not in (7, 9):
            return False
    return True


def _alpha_from_hex(col_list):
    alpha_parts = []
    col_hex = []
    for value in col_list:
        if _is_na(value):
            col_hex.append("#000000")
            alpha_parts.append("")
        else:
            col_hex.append(value[:7])
            alpha_parts.append("" if len(value) == 7 else value[7:9])
    return alpha_parts, col_hex


def _is_rgb_matrix(col) -> bool:
    if not isinstance(col, np.ndarray):
        return False
    if col.ndim != 2:
        return False
    return np.issubdtype(col.dtype, np.number) and col.shape[0] in (3, 4)


def _alpha_from_matrix(matrix: np.ndarray):
    if matrix.shape[0] == 3:
        alpha_parts = ["FF"] * matrix.shape[1]
    else:
        alpha_parts = _convert_transparency(matrix[3, :] / 255.0, mode="character")
    col_hex = _rgb_rows_to_hex(matrix[:3, :])
    return alpha_parts, col_hex


def _alpha_from_col2rgb(col_list):
    rgb = col2rgb_matrix(col_list)
    alpha_parts = _convert_transparency(rgb[:, 3] / 255.0, mode="character")
    channels = rgb[:, :3].T
    col_hex = _rgb_rows_to_hex(channels)
    return alpha_parts, col_hex


def _rgb_rows_to_hex(matrix_3xn: np.ndarray) -> list[str]:
    out: list[str] = []
    for index in range(matrix_3xn.shape[1]):
        red = int(matrix_3xn[0, index])
        green = int(matrix_3xn[1, index])
        blue = int(matrix_3xn[2, index])
        out.append(f"#{red:02X}{green:02X}{blue:02X}")
    return out


def _adjust_alpha_parts(alpha_parts, new_alpha, n, col_hex):
    alpha = list(alpha_parts)
    if new_alpha is None:
        alpha = ["" if part == "FF" else part for part in alpha]
    elif new_alpha is False:
        alpha = [""] * len(alpha)
    elif new_alpha is True:
        alpha = ["FF" if part == "" else part for part in alpha]
    else:
        converted = _convert_transparency(
            _coerce_alpha_argument(new_alpha), mode="character"
        )
        if not isinstance(converted, list):
            converted = [converted]
        if len(converted) != n:
            n = max(n, len(converted))
            if len(col_hex) != n:
                col_hex = _rep_len(col_hex, n)
            if len(alpha) != n:
                alpha = _rep_len(alpha, n)
            converted = _rep_len(converted, n)
        alpha = converted
    return alpha, col_hex


def _rep_len(values, length: int):
    if not values:
        return [""] * length
    if len(values) >= length:
        return list(values[:length])
    reps = (length + len(values) - 1) // len(values)
    expanded = (values * reps)[:length]
    return list(expanded)


def _paste_hex(rgb: str, alpha: str) -> str:
    return rgb + alpha


def _coerce_alpha_argument(x):
    """Match R when ``c(0, 0.5, 1)`` is numeric but Python ``1`` is int."""
    if isinstance(x, (str, bytes)):
        return x
    if isinstance(x, (float, np.floating)):
        return float(x)
    if isinstance(x, np.ndarray):
        if np.issubdtype(x.dtype, np.floating):
            return x
        flat = x.ravel().tolist()
        return _coerce_alpha_argument(flat)
    if isinstance(x, Sequence) and not isinstance(x, (str, bytes)):
        if any(isinstance(item, (float, np.floating)) for item in x):
            return [float(item) for item in x]
        ints = [int(item) for item in x]
        if ints and all(0 <= item <= 255 for item in ints) and any(item > 1 for item in ints):
            return ints
        return [float(item) for item in x]
    if isinstance(x, (int, np.integer)) and not isinstance(x, (bool, np.bool_)):
        value = int(x)
        if value > 1:
            return value
        return float(value)
    return x


def _convert_transparency(x, mode="numeric"):
    if mode not in ("numeric", "integer", "character"):
        raise ValueError("invalid mode")
    if isinstance(x, (str, bytes)):
        return _convert_transparency_one(x, mode)
    if isinstance(x, np.ndarray):
        flat = x.ravel()
        return [_convert_transparency_one(item, mode) for item in flat]
    if isinstance(x, Sequence) and not isinstance(x, (str, bytes)):
        return [_convert_transparency_one(item, mode) for item in x]
    return _convert_transparency_one(x, mode)


def _convert_transparency_one(x, mode: str):
    if isinstance(x, str):
        upper = x.upper()
        try:
            value = int(upper, 16)
        except ValueError as exc:
            raise ValueError(
                "invalid character specification of alpha transparency, "
                "must be in 00, 01, ..., FF"
            ) from exc
        if value < 0 or value > 255:
            raise ValueError(
                "invalid character specification of alpha transparency, "
                "must be in 00, 01, ..., FF"
            )
        if mode == "integer":
            return value
        if mode == "numeric":
            return value / 255.0
        return f"{value:02X}"
    if isinstance(x, (bool, np.bool_)):
        raise TypeError("invalid transparency value")
    if isinstance(x, (int, np.integer)):
        value = int(x)
        if value < 0 or value > 255:
            raise ValueError(
                "invalid integer specification of alpha transparency, "
                "must be in 0L, 1L, ..., 255L"
            )
        if mode == "numeric":
            return value / 255.0
        if mode == "character":
            return f"{value:02X}"
        return value
    value = float(x)
    if not (value >= 0 and value <= 1):
        raise ValueError(
            "invalid numeric specification of alpha transparency, must be in [0, 1]"
        )
    scaled = int(round(value * 255 + 0.0001))
    if mode == "integer":
        return scaled
    if mode == "character":
        return f"{scaled:02X}"
    return value
