"""Qualitative HCL color palettes (colorspace 2.1-4)."""

from __future__ import annotations

import math
import warnings

import numpy as np

from colorspace._cspace_convert import PolarLUVColor
from colorspace.hex import hex as hex_color
from colorspace.hcl_palettes import add_hcl_pal, hcl_palette_parameters

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


def _default_pals_from_hcl(h, c, l) -> dict[str, float | bool | None]:
    h_arr = np.ravel(np.asarray(h, dtype=np.float64))
    if h_arr.size < 2:
        h_pair = (float(h_arr[0]), float("nan"))
    else:
        h_pair = (float(h_arr[0]), float(h_arr[1]))
    c_arr = np.ravel(np.asarray(c, dtype=np.float64))
    l_arr = np.ravel(np.asarray(l, dtype=np.float64))
    return {
        "h1": h_pair[0],
        "h2": h_pair[1],
        "c1": float(c_arr[0]),
        "c2": float("nan"),
        "l1": float(l_arr[0]),
        "l2": float("nan"),
        "p1": float("nan"),
        "p2": float("nan"),
        "cmax": float("nan"),
        "fixup": True,
    }


def qualitative_hcl(
    n,
    h=_MISSING,
    c=_MISSING,
    l=_MISSING,
    fixup=_MISSING,
    alpha=_MISSING,
    palette=None,
    rev=False,
    register="",
    h1=_MISSING,
    h2=_MISSING,
    c1=_MISSING,
    l1=_MISSING,
    **hex_kwargs,
):
    """Build a qualitative HCL palette and return hex color strings."""
    n_int = int(n)
    if n_int < 1:
        return []

    h_is_character = isinstance(h, str)
    if h_is_character:
        palette = h

    if palette is not None:
        pals = hcl_palette_parameters("Qualitative", palette)
    else:
        if h is _MISSING:
            h_use = np.array([0.0, 360.0 * (n_int - 1) / n_int], dtype=np.float64)
        elif h_is_character:
            h_use = np.array([0.0, 360.0 * (n_int - 1) / n_int], dtype=np.float64)
        else:
            h_use = np.ravel(np.asarray(h, dtype=np.float64))
        c_use = 80.0 if c is _MISSING else c
        l_use = 60.0 if l is _MISSING else l
        pals = _default_pals_from_hcl(h_use, c_use, l_use)

    if h is not _MISSING and not h_is_character:
        h_arr = np.ravel(np.asarray(h, dtype=np.float64))
        if h_arr.size < 2:
            pals["h1"] = float(h_arr[0])
            pals["h2"] = float("nan")
        else:
            pals["h1"] = float(h_arr[0])
            pals["h2"] = float(h_arr[1])
    if c is not _MISSING:
        c_arr = np.ravel(np.asarray(c, dtype=np.float64))
        pals["c1"] = float(c_arr[0])
    if l is not _MISSING:
        l_arr = np.ravel(np.asarray(l, dtype=np.float64))
        pals["l1"] = float(l_arr[0])
    if fixup is not _MISSING:
        pals["fixup"] = bool(fixup)

    if h1 is not _MISSING:
        pals["h1"] = float(h1)
    if h2 is not _MISSING:
        pals["h2"] = float(h2)
    if c1 is not _MISSING:
        pals["c1"] = float(c1)
    if l1 is not _MISSING:
        pals["l1"] = float(l1)

    do_register = isinstance(register, str) and bool(register)
    if do_register:
        add_hcl_pal(palette=register, type="Qualitative", parameters=dict(pals))

    h2_val = pals["h2"]
    if isinstance(h2_val, float) and math.isnan(h2_val):
        pals["h2"] = float(pals["h1"]) + 360.0 * (n_int - 1) / n_int

    h_vals = np.linspace(float(pals["h1"]), float(pals["h2"]), n_int, dtype=np.float64)
    l_vals = np.full(n_int, float(pals["l1"]), dtype=np.float64)
    c_vals = np.full(n_int, float(pals["c1"]), dtype=np.float64)
    polar = PolarLUVColor(np.column_stack([l_vals, c_vals, h_vals]), None)
    rval = hex_color(polar, fixup=bool(pals["fixup"]), **hex_kwargs)

    if alpha is not _MISSING:
        rval = _append_alpha(rval, alpha)

    if rev:
        rval = list(reversed(rval))
    return rval
