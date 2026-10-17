"""Diverging HCL color palettes (colorspace 2.1-4)."""

from __future__ import annotations

import json
import math
import re
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from colorspace._cspace_convert import PolarLUVColor, as_srgb_coords, hex_from_srgb

_MISSING = object()
_VARS_PAL = ("h1", "h2", "c1", "c2", "l1", "l2", "p1", "p2", "cmax", "fixup")
_CUSTOM_DIVERGING_PALS: dict[str, dict[str, float | bool | None]] = {}


@lru_cache(maxsize=1)
def _builtin_diverging_pals() -> dict[str, dict[str, float | bool | None]]:
    path = Path(__file__).resolve().parent / "diverging_hcl_palettes.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, float | bool | None]] = {}
    for name, row in raw.items():
        parsed: dict[str, float | bool | None] = {}
        for key in _VARS_PAL:
            value = row[key]
            if key == "fixup":
                parsed[key] = bool(value)
            elif value is None:
                parsed[key] = float("nan")
            else:
                parsed[key] = float(value)
        out[name] = parsed
    return out


def _normalize_palette_name(name: str) -> str:
    return re.sub(r"[-_,() \.]", "", name.lower())


def _lookup_diverging_palette(palette: str) -> dict[str, float | bool | None]:
    pals = {**_builtin_diverging_pals(), **_CUSTOM_DIVERGING_PALS}
    norm = {_normalize_palette_name(k): k for k in pals}
    key = _normalize_palette_name(palette)
    if key in norm:
        return dict(pals[norm[key]])
    matches = [n for n in norm if n.startswith(key)]
    if not matches:
        names = ", ".join(sorted(pals))
        raise ValueError(f"Named 'palette' should be one of: {names}")
    return dict(pals[norm[matches[0]]])


def _as_pals_dict(values: dict[str, Any]) -> dict[str, float | bool | None]:
    out: dict[str, float | bool | None] = {}
    for key in _VARS_PAL:
        value = values.get(key, float("nan"))
        if key == "fixup":
            out[key] = bool(value)
        elif value is None or (isinstance(value, float) and math.isnan(value)):
            out[key] = float("nan")
        else:
            out[key] = float(value)
    return out


def _lintrj(i: np.ndarray, p1: float, p2: float) -> np.ndarray:
    return p2 - (p2 - p1) * i


def _tritrj(i: np.ndarray, j: float, p1: float, p2: float, pm: float) -> np.ndarray:
    return np.where(
        i <= j,
        p2 - (p2 - pm) * i / j,
        pm - (pm - p1) * np.abs((i - j) / (1.0 - j)),
    )


def _j_chroma(cmax: float, c1: float, c2: float) -> float:
    if math.isnan(cmax) or math.isnan(c2):
        return float("nan")
    denom = abs(cmax - c2)
    if denom == 0.0:
        return float("nan")
    j = 1.0 / (1.0 + abs(cmax - c1) / denom)
    if j <= 0.0 or j >= 1.0:
        return float("nan")
    return j


def _seqhcl(
    i: np.ndarray,
    h1: float,
    h2: float,
    c1: float,
    c2: float,
    l1: float,
    l2: float,
    p1: float,
    p2: float,
    cmax: float,
    fixup: bool,
) -> list[str | None]:
    i_arr = np.asarray(i, dtype=np.float64)
    ip1 = np.power(i_arr, p1)
    ip2 = np.power(i_arr, p2)
    l_vals = _lintrj(ip2, l1, l2)
    j = _j_chroma(cmax, c1, c2)
    if math.isnan(j):
        c_vals = _lintrj(ip1, c1, c2)
    else:
        c_vals = _tritrj(ip1, j, c1, c2, cmax)
    h_vals = _lintrj(i_arr, h1, h2)
    polar = PolarLUVColor(np.column_stack([l_vals, c_vals, h_vals]), None)
    return hex_from_srgb(as_srgb_coords(polar), fixup=fixup)


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


def diverging_hcl(
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
    **_,
):
    """Build a diverging HCL palette and return hex color strings."""
    if gamma is not None:
        warnings.warn("'gamma' is deprecated and has no effect", stacklevel=2)

    n_int = int(n)
    if n_int < 1:
        return []

    h_is_character = isinstance(h, str)
    if h_is_character:
        palette = h

    if palette is not None:
        pals = _lookup_diverging_palette(palette)
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
        _CUSTOM_DIVERGING_PALS[register] = dict(pals)

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
    right = list(reversed(_seqhcl(
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
    )))
    rval = left + right
    if math.floor(n_int / 2) < n2:
        del rval[n2 - 1]

    if alpha is not _MISSING:
        rval = _append_alpha(rval, alpha)

    if rev:
        rval.reverse()
    return rval
