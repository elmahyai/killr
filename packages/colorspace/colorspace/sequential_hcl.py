"""Sequential HCL color palettes (colorspace 2.1-4)."""

from __future__ import annotations

import json
import math
import re
import warnings
from functools import lru_cache
from pathlib import Path
import numpy as np

from colorspace.diverging_hcl import (
    _VARS_PAL,
    _append_alpha,
    _as_pals_dict,
    _seqhcl,
)

_MISSING = object()
_CUSTOM_SEQUENTIAL_PALS: dict[str, dict[str, float | bool | None]] = {}


@lru_cache(maxsize=1)
def _builtin_sequential_pals() -> dict[str, dict[str, float | bool | None]]:
    path = Path(__file__).resolve().parent / "sequential_hcl_palettes.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, float | bool | None]] = {}
    for name, row in raw.items():
        parsed: dict[str, float | bool | None] = {}
        for key in _VARS_PAL:
            value = row.get(key)
            if key == "fixup":
                parsed[key] = bool(value) if value is not None else True
            elif value is None:
                parsed[key] = float("nan")
            else:
                parsed[key] = float(value)
        out[name] = parsed
    return out


def _normalize_palette_name(name: str) -> str:
    return re.sub(r"[-_,() \.]", "", name.lower())


def _lookup_sequential_palette(palette: str) -> dict[str, float | bool | None]:
    pals = {**_builtin_sequential_pals(), **_CUSTOM_SEQUENTIAL_PALS}
    norm = {_normalize_palette_name(k): k for k in pals}
    key = _normalize_palette_name(palette)
    if key in norm:
        return dict(pals[norm[key]])
    matches = [n for n in norm if n.startswith(key)]
    if not matches:
        names = ", ".join(sorted(pals))
        raise ValueError(f"Named 'palette' should be one of: {names}")
    return dict(pals[norm[matches[0]]])


def _expand_c_vector(c) -> np.ndarray:
    c_arr = np.ravel(np.asarray(c, dtype=np.float64))
    if c_arr.size == 3:
        c_arr = np.array([c_arr[0], c_arr[2], c_arr[1]], dtype=np.float64)
    return c_arr


def _c1_c2_cmax(c_arr: np.ndarray) -> tuple[float, float, float]:
    if c_arr.size < 2:
        c_work = np.array([float(c_arr[0]), 0.0], dtype=np.float64)
    else:
        c_work = np.resize(c_arr, 2).astype(np.float64, copy=False)
    cmax = float(c_arr[2]) if c_arr.size >= 3 else float("nan")
    return float(c_work[0]), float(c_work[1]), cmax


def sequential_hcl(
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
    c2=_MISSING,
    l1=_MISSING,
    l2=_MISSING,
    p1=_MISSING,
    p2=_MISSING,
    cmax=_MISSING,
    c_=_MISSING,
    **_,
):
    """Build a sequential HCL palette and return hex color strings."""
    if gamma is not None:
        warnings.warn("'gamma' is deprecated and has no effect", stacklevel=2)

    n_int = int(n)
    if n_int < 1:
        return []

    if c_ is not _MISSING:
        c = c_

    c_arg = 80.0 if c is _MISSING else c
    c_arr = _expand_c_vector(c_arg)

    h_is_character = isinstance(h, str)
    if h_is_character:
        palette = h

    if palette is not None:
        pals = _lookup_sequential_palette(palette)
    else:
        h_use = 260.0 if h is _MISSING or h_is_character else h
        l_use = (30.0, 90.0) if l is _MISSING else l
        power_use = 1.5 if power is _MISSING else power
        fixup_use = True if fixup is _MISSING else fixup

        h_arr = np.ravel(np.asarray(h_use, dtype=np.float64))
        if h_arr.size < 2:
            h_pair = (float(h_arr[0]), float("nan"))
        else:
            h_pair = (float(h_arr[0]), float(h_arr[1]))

        c1_init, c2_init, cmax_init = _c1_c2_cmax(c_arr)
        l_arr = np.ravel(np.asarray(l_use, dtype=np.float64))
        power_arr = np.ravel(np.asarray(power_use, dtype=np.float64))
        power_p2 = float(power_arr[1]) if power_arr.size > 1 else float("nan")

        pals = _as_pals_dict(
            {
                "h1": h_pair[0],
                "h2": h_pair[1],
                "c1": c1_init,
                "c2": c2_init,
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
    if c is not _MISSING or c_ is not _MISSING:
        c1_val, c2_val, cmax_val = _c1_c2_cmax(c_arr)
        pals["c1"] = c1_val
        pals["c2"] = c2_val
        if not math.isnan(cmax_val):
            pals["cmax"] = cmax_val
    if l is not _MISSING:
        l_arr = np.ravel(np.asarray(l, dtype=np.float64))
        l_arr = np.resize(l_arr, 2)
        pals["l1"] = float(l_arr[0])
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
    if c2 is not _MISSING:
        pals["c2"] = float(c2)
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

    h2_val = pals["h2"]
    h1_val = pals["h1"]
    if (
        isinstance(h2_val, (int, float))
        and not math.isnan(float(h2_val))
        and isinstance(h1_val, (int, float))
        and float(h1_val) == float(h2_val)
    ):
        pals["h2"] = float("nan")

    if isinstance(register, str) and register:
        _CUSTOM_SEQUENTIAL_PALS[register] = dict(pals)

    if isinstance(pals["h2"], float) and math.isnan(pals["h2"]):
        pals["h2"] = float(pals["h1"])
    if isinstance(pals["c2"], float) and math.isnan(pals["c2"]):
        pals["c2"] = 0.0
    p2_val = pals["p2"]
    if isinstance(p2_val, float) and math.isnan(p2_val):
        pals["p2"] = pals["p1"]

    i = np.linspace(1.0, 0.0, n_int, dtype=np.float64)
    fixup_val = bool(pals["fixup"])
    cmax_val = (
        float(pals["cmax"])
        if isinstance(pals["cmax"], (int, float)) and not math.isnan(float(pals["cmax"]))
        else float("nan")
    )
    rval = _seqhcl(
        i,
        float(pals["h1"]),
        float(pals["h2"]),
        float(pals["c1"]),
        float(pals["c2"]),
        float(pals["l1"]),
        float(pals["l2"]),
        float(pals["p1"]),
        float(pals["p2"]),
        cmax_val,
        fixup_val,
    )

    if alpha is not _MISSING:
        rval = _append_alpha(rval, alpha)

    if rev:
        rval.reverse()
    return rval
