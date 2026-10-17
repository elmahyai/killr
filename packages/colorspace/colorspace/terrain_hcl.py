"""Terrain HCL palette (colorspace 2.1-4)."""

from __future__ import annotations

import warnings

from colorspace.sequential_hcl import _MISSING, sequential_hcl


def terrain_hcl(
    n,
    h=(130, 0),
    c_=(80, 0),
    l=(60, 95),
    power=(1 / 10, 1),
    gamma=None,
    fixup=True,
    alpha=_MISSING,
    **kwargs,
):
    """Terrain palette via sequential HCL (HCL counterpart to base ``terrain.colors``)."""
    if gamma is not None:
        warnings.warn("'gamma' is deprecated and has no effect", stacklevel=2)

    n_int = int(n)
    if n_int < 1:
        return []

    raw = sequential_hcl(
        n_int,
        h=h,
        c_=c_,
        l=l,
        power=power,
        fixup=fixup,
        alpha=alpha,
        **kwargs,
    )
    width = 7 if alpha is _MISSING else 9
    out: list[str | None] = []
    for value in raw:
        if value is None:
            out.append(None)
        else:
            out.append(value[:width])
    return out
