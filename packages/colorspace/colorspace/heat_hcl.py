"""Heat HCL palette (colorspace 2.1-4)."""

from __future__ import annotations

import warnings

from colorspace.sequential_hcl import _MISSING, sequential_hcl


def heat_hcl(
    n,
    h=(0, 90),
    c_=(100, 30),
    l=(50, 90),
    power=(1 / 5, 1),
    gamma=None,
    fixup=True,
    alpha=_MISSING,
    **kwargs,
):
    """Heat palette via sequential HCL (HCL counterpart to base ``heat.colors``)."""
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
