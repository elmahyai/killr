"""Lighten colors in HCL, HLS, or combined space (colorspace 2.1-4)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

from colorspace._cspace_convert import (
    as_polar_luv,
    as_srgb_coords,
    col2rgb_matrix,
    hex_from_srgb,
    is_color_object,
)
from colorspace.desaturate import _PrismaticColors, _is_na, _parse_input
from colorspace.hex2rgb import HexRGB, hex2RGB
from colorspace.max_chroma import max_chroma
from colorspace.rgb import RGBColor


def lighten(col, amount=0.1, method="relative", space="HCL", fixup=True):
    """Algorithmically lighten colors (see ``darken`` for the inverse)."""
    if method not in ("relative", "absolute"):
        raise ValueError('method must be "relative" or "absolute"')
    if space not in ("HCL", "HLS", "combined"):
        raise ValueError('space must be "HCL", "HLS", or "combined"')

    col_rep, amount_arr, names, prismatic = _recycle_inputs(col, amount)
    col_orig_texts, col_obj, alpha_suffixes, na_indices, parsed_prismatic = _lighten_input(
        col_rep
    )
    prismatic = prismatic or parsed_prismatic

    zero_mask = amount_arr == 0
    working = _apply_lighten(col_obj, amount_arr, method, space)

    hexes = hex_from_srgb(as_srgb_coords(working), fixup=fixup)
    if alpha_suffixes is not None:
        hexes = [
            (None if value is None else value + suffix)
            for value, suffix in zip(hexes, alpha_suffixes, strict=True)
        ]
    for index in na_indices:
        hexes[index] = None

    for index in np.flatnonzero(zero_mask):
        hexes[int(index)] = col_orig_texts[int(index)]

    if names is not None:
        # names preserved on output vector in R; Python returns list
        pass
    if prismatic or parsed_prismatic:
        out = _PrismaticColors(hexes)
        if names is not None:
            out.names = names
        return out
    if names is not None:
        named = _NamedHexList(hexes)
        named.names = names
        return named
    return hexes


class _NamedHexList(list):
    pass


def _length_col(col) -> int:
    if isinstance(col, str):
        return 1
    if is_color_object(col):
        return col.coords.shape[0]
    if isinstance(col, Mapping):
        return len(col)
    if isinstance(col, Sequence) and not isinstance(col, (str, bytes)):
        return len(col)
    return 1


def _rep_len_amount(values: np.ndarray, n: int) -> np.ndarray:
    if values.size == 0:
        return np.zeros(n, dtype=np.float64)
    if values.size == 1:
        return np.full(n, values[0], dtype=np.float64)
    if values.size < n:
        reps = int(np.ceil(n / values.size))
        return np.tile(values, reps)[:n]
    if values.size > n:
        return values[:n]
    return values


def _rep_len_col(col, n: int):
    if isinstance(col, Mapping):
        if n == len(col):
            return col
        items = list(col.items())
        if len(items) == 1:
            return dict(items * n)
        reps = int(np.ceil(n / len(items)))
        expanded = dict((items * reps)[:n])
        return expanded
    if isinstance(col, str) or is_color_object(col) or not isinstance(col, Sequence):
        if n == 1:
            return col
        if isinstance(col, str):
            return [col] * n
        if is_color_object(col):
            coords = np.repeat(col.coords, n, axis=0)
            return type(col)(col.space, coords, col.names)
        return [col] * n
    if len(col) == n:
        return col
    if len(col) == 1:
        return list(col) * n
    if len(col) < n:
        reps = int(np.ceil(n / len(col)))
        expanded = (list(col) * reps)[:n]
        return expanded
    return list(col)[:n]


def _recycle_inputs(col, amount):
    amount_arr = np.asarray(amount, dtype=np.float64).ravel()
    n = max(_length_col(col), amount_arr.size if amount_arr.size else 1)
    col_rep = _rep_len_col(col, n)
    amount_arr = _rep_len_amount(amount_arr, n)

    names = None
    prismatic = False
    if isinstance(col, Sequence) and not isinstance(col, (str, bytes)):
        prismatic = getattr(col, "__class__", type(col)).__name__ == "PrismaticColors"
        names = getattr(col, "names", None)
    if isinstance(col_rep, list):
        prismatic = prismatic or getattr(col, "__class__", type(col)).__name__ == "PrismaticColors"
    return col_rep, amount_arr, names, prismatic


def _lighten_input(col):
    input_type, _target, col_obj, alpha_suffixes, na_indices, _transpose, parsed_prismatic = (
        _parse_input(col)
    )
    col_orig_texts = _col_orig_texts(col, input_type, col_obj, alpha_suffixes, na_indices)
    return col_orig_texts, col_obj, alpha_suffixes, na_indices, parsed_prismatic


def _col_orig_texts(col, input_type, col_obj, alpha_suffixes, na_indices):
    if input_type == "hex":
        if isinstance(col, dict):
            texts = [("" if _is_na(v) else str(v)) for v in col.values()]
        elif isinstance(col, Sequence) and not isinstance(col, (str, bytes)):
            texts = [("" if _is_na(v) else str(v)) for v in col]
        else:
            texts = [str(col)]
        out = []
        for text in texts:
            if not text or _is_na(text):
                out.append(None)
            else:
                out.append(text)
        return out

    if is_color_object(col):
        rgb = (as_srgb_coords(col_obj) * 255).astype(np.int64)
        texts = []
        for row in rgb:
            texts.append(f"#{row[0]:02X}{row[1]:02X}{row[2]:02X}")
        return texts

    rgb = col2rgb_matrix(col if isinstance(col, Sequence) and not isinstance(col, str) else [col])
    texts = []
    for row in rgb:
        r, g, b, a = int(row[0]), int(row[1]), int(row[2]), int(row[3])
        text = f"#{r:02X}{g:02X}{b:02X}"
        if a != 255:
            text += f"{a:02X}"
        texts.append(text)
    return texts


def _apply_lighten(col_obj, amount_arr, method, space):
    if space == "HLS":
        return _lighten_hls(col_obj, amount_arr, method)
    if space == "HCL":
        return _lighten_hcl(col_obj, amount_arr, method)
    return _lighten_combined(col_obj, amount_arr, method)


def _adjust_l(values, amount_arr, method, scale):
    """Adjust luminance on 0..scale scale (100 for HCL, 1 for HLS)."""
    l_old = values.copy()
    if method == "relative":
        pos = amount_arr >= 0
        out = np.empty_like(l_old)
        if scale == 100:
            out[pos] = 100 - (100 - l_old[pos]) * (1 - amount_arr[pos])
            out[~pos] = l_old[~pos] * (1 + amount_arr[~pos])
        else:
            out[pos] = 1 - (1 - l_old[pos]) * (1 - amount_arr[pos])
            out[~pos] = l_old[~pos] * (1 + amount_arr[~pos])
    else:
        if scale == 100:
            out = l_old + amount_arr * 100
        else:
            out = l_old + amount_arr
    return np.minimum(scale, np.maximum(0, out))


def _clamp_chroma(polar: np.ndarray) -> None:
    h = polar[:, 2]
    l_val = polar[:, 0]
    c_max = max_chroma(h, l_val, floor=True)
    polar[:, 1] = np.minimum(c_max, np.maximum(0, polar[:, 1]))


def _lighten_hcl(col_obj, amount_arr, method):
    polar = as_polar_luv(col_obj)
    coords = polar.coords.copy()
    coords[:, 0] = np.minimum(100, np.maximum(0, coords[:, 0]))
    l_old = coords[:, 0].copy()
    coords[:, 0] = _adjust_l(l_old, amount_arr, method, 100)
    _clamp_chroma(coords)
    polar.coords = coords
    return polar


def _srgb_rows_to_hls(coords: np.ndarray) -> np.ndarray:
    rows = [_rgb_to_hls(float(r), float(g), float(b)) for r, g, b in coords]
    return np.array(rows, dtype=np.float64)


def _hls_rows_to_srgb(coords: np.ndarray) -> np.ndarray:
    rows = [_hls_to_rgb(float(h), float(l_val), float(s)) for h, l_val, s in coords]
    return np.array(rows, dtype=np.float64)


def _rgb_to_hls(r: float, g: float, b: float) -> tuple[float, float, float]:
    min_c = min(r, g, b)
    max_c = max(r, g, b)
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
        h_val = h_val * 60.0
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


def _lighten_hls(col_obj, amount_arr, method):
    srgb = as_srgb_coords(col_obj)
    hls = _srgb_rows_to_hls(srgb)
    hls[:, 1] = _adjust_l(hls[:, 1], amount_arr, method, 1)
    out = _hls_rows_to_srgb(hls)
    return HexRGB("sRGB", out, col_obj.names)


def _lighten_combined(col_obj, amount_arr, method):
    srgb = as_srgb_coords(col_obj)
    hls = _srgb_rows_to_hls(srgb)
    hls[:, 1] = _adjust_l(hls[:, 1], amount_arr, method, 1)
    hls_rgb = _hls_rows_to_srgb(hls)
    col_hls_hcl = as_polar_luv(RGBColor(hls_rgb, None))

    polar = as_polar_luv(col_obj)
    coords = polar.coords.copy()
    coords[:, 0] = np.minimum(100, np.maximum(0, coords[:, 0]))
    l_old = coords[:, 0].copy()
    coords[:, 0] = _adjust_l(l_old, amount_arr, method, 100)
    coords[:, 0] = np.minimum(100, np.maximum(0, coords[:, 0]))
    coords[:, 1] = col_hls_hcl.coords[:, 1]
    _clamp_chroma(coords)
    polar.coords = coords
    return polar
