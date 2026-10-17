"""Flexible diverging HCL palettes (colorspace 2.1-4)."""

from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from colorspace.diverging_hcl import _append_alpha, _seqhcl

_MISSING = object()
_PAL_KEYS = (
    "h1",
    "h2",
    "h3",
    "c1",
    "c2",
    "c3",
    "l1",
    "l2",
    "l3",
    "p1",
    "p2",
    "p3",
    "p4",
    "cmax1",
    "cmax2",
)


@lru_cache(maxsize=1)
def _builtin_divergingx_pals() -> dict[str, dict[str, float | None]]:
    path = Path(__file__).resolve().parent / "divergingx_hcl_palettes.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, float | None]] = {}
    for name, row in raw.items():
        parsed: dict[str, float | None] = {}
        for key in _PAL_KEYS:
            value = row[key]
            if value is None:
                parsed[key] = float("nan")
            else:
                parsed[key] = float(value)
        out[name] = parsed
    return out


def _normalize_palette_name(name: str) -> str:
    return re.sub(r"[-_,() \.]", "", name.lower())


def _lookup_divergingx_palette(palette: str) -> dict[str, float]:
    pals = _builtin_divergingx_pals()
    norm = {_normalize_palette_name(k): k for k in pals}
    key = _normalize_palette_name(palette)
    if key in norm:
        return dict(pals[norm[key]])  # type: ignore[arg-type]
    matches = [n for n in norm if n.startswith(key)]
    if not matches:
        names = ", ".join(sorted(pals))
        raise ValueError(f"Named 'palette' should be one of: {names}")
    return dict(pals[norm[matches[0]]])  # type: ignore[arg-type]


def _float_or_nan(value: Any) -> float:
    if value is None or value is _MISSING:
        return float("nan")
    if isinstance(value, float) and math.isnan(value):
        return float("nan")
    return float(value)


def _resolve_pals(pals: dict[str, float]) -> dict[str, float]:
    out = dict(pals)
    if any(math.isnan(out[k]) for k in ("h1", "c1", "l1")):
        raise ValueError("first hue/chroma/luminance coordinate must be specified")
    if math.isnan(out["p1"]):
        out["p1"] = 1.0
    if math.isnan(out["c2"]):
        out["c2"] = 0.0
    if math.isnan(out["l2"]):
        out["l2"] = out["l1"]
    if math.isnan(out["p2"]):
        out["p2"] = out["p1"]
    if math.isnan(out["h3"]):
        raise ValueError("third hue coordinate must be specified")
    if math.isnan(out["c3"]):
        out["c3"] = out["c1"]
    if math.isnan(out["l3"]):
        out["l3"] = out["l1"]
    if math.isnan(out["p3"]):
        out["p3"] = out["p1"]
    if math.isnan(out["p4"]):
        out["p4"] = out["p2"]
    return out


def divergingx_hcl(
    n,
    palette: str = "Geyser",
    *,
    fixup: bool = True,
    alpha=_MISSING,
    rev: bool = False,
    h1=_MISSING,
    h2=_MISSING,
    h3=_MISSING,
    c1=_MISSING,
    c2=_MISSING,
    c3=_MISSING,
    l1=_MISSING,
    l2=_MISSING,
    l3=_MISSING,
    p1=_MISSING,
    p2=_MISSING,
    p3=_MISSING,
    p4=_MISSING,
    cmax1=_MISSING,
    cmax2=_MISSING,
    **hex_kwargs,
):
    """Build a flexible diverging HCL palette and return hex color strings."""
    n_int = int(n)
    if n_int < 1:
        return []

    pals = _lookup_divergingx_palette(palette)
    overrides = {
        "h1": h1,
        "h2": h2,
        "h3": h3,
        "c1": c1,
        "c2": c2,
        "c3": c3,
        "l1": l1,
        "l2": l2,
        "l3": l3,
        "p1": p1,
        "p2": p2,
        "p3": p3,
        "p4": p4,
        "cmax1": cmax1,
        "cmax2": cmax2,
    }
    for key, value in overrides.items():
        if value is not _MISSING:
            pals[key] = _float_or_nan(value)

    resolved = _resolve_pals(pals)

    n2 = math.ceil(n_int / 2)
    if n_int == 1:
        rval_i = np.array([0.0], dtype=np.float64)
    else:
        step = -2.0 / (n_int - 1)
        rval_i = np.maximum(0.0, 1.0 + step * np.arange(n2, dtype=np.float64))

    h2_mid = resolved["h1"] if math.isnan(resolved["h2"]) else resolved["h2"]
    h2_right = resolved["h3"] if math.isnan(resolved["h2"]) else resolved["h2"]

    left = _seqhcl(
        rval_i,
        resolved["h1"],
        h2_mid,
        resolved["c1"],
        resolved["c2"],
        resolved["l1"],
        resolved["l2"],
        resolved["p1"],
        resolved["p2"],
        resolved["cmax1"],
        fixup,
    )
    right = list(
        reversed(
            _seqhcl(
                rval_i,
                resolved["h3"],
                h2_right,
                resolved["c3"],
                resolved["c2"],
                resolved["l3"],
                resolved["l2"],
                resolved["p3"],
                resolved["p4"],
                resolved["cmax2"],
                fixup,
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
