"""Parallel period slide with integer results."""

from __future__ import annotations

import math

from slider.engine import _scalar
from slider.pslide_period_dbl import pslide_period_dbl


def pslide_period_int(
    items,
    i,
    period,
    f,
    *args,
    every=1,
    origin=None,
    before=0,
    after=0,
    complete=False,
):
    """Slide ``f`` over parallel vectors; each window yields one integer."""
    def int_f(*slices):
        return _scalar(f(*slices, *args), "int")

    out = pslide_period_dbl(
        items,
        i,
        period,
        int_f,
        *args,
        every=every,
        origin=origin,
        before=before,
        after=after,
        complete=complete,
    )

    result = []
    for value in out:
        if isinstance(value, float) and math.isnan(value):
            result.append(None)
        else:
            result.append(int(value))
    return result
