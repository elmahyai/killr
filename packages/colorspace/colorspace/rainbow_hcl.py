"""Rainbow HCL palette (colorspace 2.1-4)."""

from __future__ import annotations

import warnings

import numpy as np

from colorspace._cspace_convert import PolarLUVColor
from colorspace.hex import hex as hex_color

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


def _qualitative_hcl_for_rainbow(
    n: int,
    *,
    h1: float,
    h2: float,
    c1: float,
    l1: float,
    fixup: bool,
    alpha,
    hex_kwargs,
) -> list[str | None]:
    """Qualitative HCL path used by ``rainbow_hcl`` (manual h/c/l only)."""
    if n < 1:
        return []
    h_vals = np.linspace(h1, h2, n, dtype=np.float64)
    l_vals = np.full(n, l1, dtype=np.float64)
    c_vals = np.full(n, c1, dtype=np.float64)
    polar = PolarLUVColor(np.column_stack([l_vals, c_vals, h_vals]), None)
    rval = hex_color(polar, fixup=fixup, **hex_kwargs)
    return _append_alpha(rval, alpha)


def rainbow_hcl(
    n,
    c=50,
    l=70,
    start=0,
    end=_MISSING,
    gamma=None,
    fixup=True,
    alpha=_MISSING,
    **kwargs,
):
    """Rainbow palette via qualitative HCL (HCL counterpart to base ``rainbow``)."""
    if gamma is not None:
        warnings.warn("'gamma' is deprecated and has no effect", stacklevel=2)

    n_int = int(n)
    if n_int < 1:
        return []

    if end is _MISSING:
        end_val = 360.0 * (n_int - 1) / n_int
    else:
        end_val = float(end)

    alpha_val = 1.0 if alpha is _MISSING else alpha
    h1 = float(start)
    h2 = float(end_val)
    c_arr = np.ravel(np.asarray(c, dtype=np.float64))
    l_arr = np.ravel(np.asarray(l, dtype=np.float64))
    c1 = float(c_arr[0])
    l1 = float(l_arr[0])

    raw = _qualitative_hcl_for_rainbow(
        n_int,
        h1=h1,
        h2=h2,
        c1=c1,
        l1=l1,
        fixup=bool(fixup),
        alpha=alpha_val,
        hex_kwargs=kwargs,
    )
    width = 7 if alpha is _MISSING else 9
    out: list[str | None] = []
    for value in raw:
        if value is None:
            out.append(None)
        else:
            out.append(value[:width])
    return out
