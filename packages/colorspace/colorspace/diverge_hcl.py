"""Diverging HCL palettes alias path via ``hcl_palettes`` (colorspace 2.1-4)."""

from __future__ import annotations

import math
import warnings

import numpy as np

from colorspace.diverging_hcl import (
    _MISSING,
    _append_alpha,
    _as_pals_dict,
    _seqhcl,
)
from colorspace.hcl_palettes import add_hcl_pal, hcl_palette_parameters


def diverge_hcl(
    n,
    h=_MISSING,
    c=_MISSING,
    l=_MISSING,
    power=_MISSING,
    gamma=None,
    fixup=_MISSING,
    alpha=_MISSING,
    palette=None,
    rev=False,
    register="",
    h1=_MISSING,
    h2=_MISSING,
    c1=_MISSING,
    l1=_MISSING,
    l2=_MISSING,
    p1=_MISSING,
    p2=_MISSING,
    cmax=_MISSING,
    **hex_kwargs,
):
    """Build a diverging HCL palette (R ``diverge_hcl``)."""
    if gamma is not None:
        warnings.warn("'gamma' is deprecated and has no effect", stacklevel=2)

    n_int = int(n)
    if n_int < 1:
        return []

    h_is_character = isinstance(h, str)
    if h_is_character:
        palette = h

    if palette is not None:
        raw = hcl_palette_parameters("Diverging", palette)
        pals = {k: raw[k] for k in raw}
    else:
        h_use = (260.0, 0.0) if h is _MISSING or h_is_character else h
        c_use = 80.0 if c is _MISSING else c
        l_use = (30.0, 90.0) if l is _MISSING else l
        power_use = 1.5 if power is _MISSING else power
        fixup_use = True if fixup is _MISSING else fixup

        h_arr = np.ravel(np.asarray(h_use, dtype=np.float64))
        c_arr = np.ravel(np.asarray(c_use, dtype=np.float64))
        l_arr = np.ravel(np.asarray(l_use, dtype=np.float64))
        power_arr = np.ravel(np.asarray(power_use, dtype=np.float64))
        cmax_init = float(c_arr[1]) if c_arr.size > 1 else float("nan")
        power_p2 = float(power_arr[1]) if power_arr.size > 1 else float("nan")
        pals = _as_pals_dict(
            {
                "h1": float(h_arr[0]) if h_arr.size else float("nan"),
                "h2": float(h_arr[1]) if h_arr.size > 1 else float(h_arr[0]),
                "c1": float(c_arr[0]),
                "c2": float("nan"),
                "l1": float(l_arr[0]) if l_arr.size else float("nan"),
                "l2": float(l_arr[1]) if l_arr.size > 1 else float(l_arr[0]),
                "p1": float(power_arr[0]),
                "p2": power_p2,
                "cmax": cmax_init,
                "fixup": fixup_use,
            }
        )

    if h is not _MISSING and not h_is_character:
        h_arr = np.ravel(np.asarray(h, dtype=np.float64))
        if h_arr.size >= 1:
            pals["h1"] = float(h_arr[0])
        if h_arr.size >= 2:
            pals["h2"] = float(h_arr[1])
    if c is not _MISSING:
        c_arr = np.ravel(np.asarray(c, dtype=np.float64))
        if c_arr.size >= 1:
            pals["c1"] = float(c_arr[0])
        if c_arr.size > 1:
            pals["cmax"] = float(c_arr[1])
    if l is not _MISSING:
        l_arr = np.ravel(np.asarray(l, dtype=np.float64))
        if l_arr.size >= 1:
            pals["l1"] = float(l_arr[0])
        if l_arr.size >= 2:
            pals["l2"] = float(l_arr[1])
    if power is not _MISSING:
        power_arr = np.ravel(np.asarray(power, dtype=np.float64))
        if power_arr.size >= 1:
            pals["p1"] = float(power_arr[0])
        if power_arr.size >= 2:
            pals["p2"] = float(power_arr[1])
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
    if l2 is not _MISSING:
        pals["l2"] = float(l2)
    if p1 is not _MISSING:
        pals["p1"] = float(p1)
    if p2 is not _MISSING:
        pals["p2"] = float(p2)
    if cmax is not _MISSING:
        pals["cmax"] = float(cmax)
    pals["c2"] = float("nan")

    if isinstance(register, str) and register:
        add_hcl_pal(palette=register, type="Diverging", parameters=dict(pals))

    p2_val = pals["p2"]
    if isinstance(p2_val, float) and math.isnan(p2_val):
        pals["p2"] = pals["p1"]

    n2 = math.ceil(n_int / 2)
    if n_int == 1:
        rval_i = np.array([0.0], dtype=np.float64)
    else:
        step = -2.0 / (n_int - 1)
        rval_i = np.maximum(0.0, 1.0 + step * np.arange(n2, dtype=np.float64))

    fixup_val = bool(pals["fixup"])
    cmax_val = float(pals["cmax"]) if isinstance(pals["cmax"], (int, float)) else float("nan")
    left = _seqhcl(
        rval_i,
        float(pals["h1"]),
        float(pals["h1"]),
        float(pals["c1"]),
        0.0,
        float(pals["l1"]),
        float(pals["l2"]),
        float(pals["p1"]),
        float(pals["p2"]),
        cmax_val,
        fixup_val,
    )
    right = list(
        reversed(
            _seqhcl(
                rval_i,
                float(pals["h2"]),
                float(pals["h2"]),
                float(pals["c1"]),
                0.0,
                float(pals["l1"]),
                float(pals["l2"]),
                float(pals["p1"]),
                float(pals["p2"]),
                cmax_val,
                fixup_val,
            )
        )
    )
    rval = left + right
    if math.floor(n_int / 2) < n2:
        del rval[n2 - 1]

    if alpha is not _MISSING:
        rval = _append_alpha(rval, alpha)

    if rev:
        rval.reverse()
    return rval
