"""Diverging HSV palette (colorspace 2.1-4)."""

from __future__ import annotations

import warnings

import numpy as np

from colorspace.hex import hex as hex_color
from colorspace.hsv import HSV
from colorspace.mixcolor import _hsv_to_rgb
from colorspace.rgb import RGB

_MISSING = object()


def _append_alpha(hexes: list[str | None], alpha) -> list[str | None]:
    alpha_arr = np.ravel(np.asarray(alpha, dtype=np.float64))
    if alpha_arr.size == 1:
        alpha_arr = np.full(len(hexes), alpha_arr[0], dtype=np.float64)
    elif alpha_arr.size != len(hexes):
        alpha_arr = np.resize(alpha_arr, len(hexes))
    alpha_arr = np.clip(alpha_arr, 0.0, 1.0)
    out: list[str | None] = []
    for value, a in zip(hexes, alpha_arr, strict=True):
        if value is None:
            out.append(None)
            continue
        suffix = format(int(round(a * 255 + 0.0001)), "02X")
        out.append(value + suffix)
    return out


def diverging_hsv(
    n,
    h=(240, 0),
    s=1,
    v=1,
    power=1,
    gamma=None,
    fixup=True,
    alpha=_MISSING,
    **hex_kwargs,
):
    """Diverging HSV palette (HSV counterpart to base ``diverge`` palettes)."""
    if gamma is not None:
        warnings.warn("'gamma' is deprecated and has no effect", stacklevel=2)

    n_int = int(n)
    if n_int < 1:
        return []

    h_arr = np.resize(np.asarray(h, dtype=np.float64), 2)
    s_val = float(np.ravel(np.asarray(s, dtype=np.float64))[0])
    v_val = float(np.ravel(np.asarray(v, dtype=np.float64))[0])
    power_val = float(np.ravel(np.asarray(power, dtype=np.float64))[0])

    rval_s = np.linspace(-s_val, s_val, n_int, dtype=np.float64)
    hues = np.where(rval_s > 0, h_arr[1], h_arr[0])
    sat = np.power(np.abs(rval_s), power_val)

    rgb_rows = [_hsv_to_rgb(float(hh), float(ss), v_val) for hh, ss in zip(hues, sat, strict=True)]
    rgb_obj = RGB(np.asarray(rgb_rows, dtype=np.float64))
    rval = hex_color(rgb_obj, fixup=bool(fixup), **hex_kwargs)

    if alpha is not _MISSING:
        rval = _append_alpha(rval, alpha)
    return rval
