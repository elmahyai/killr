"""Slide two vectors along period groups with double results."""

from __future__ import annotations

import math

from slider.engine import _scalar, _size
from slider.errors import SliderError
from slider.slide_period2 import slide_period2


def slide_period2_dbl(
    x,
    y,
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
    """Slide ``f`` over ``x`` and ``y``; each period window yields one double."""
    def constrained(a, b):
        value = f(a, b, *args)
        if _size(value) != 1:
            raise SliderError(
                f"The result of `.f` must have size 1, not {_size(value)}."
            )
        return _scalar(value, "dbl")

    out = slide_period2(
        x,
        y,
        i,
        period,
        constrained,
        every=every,
        origin=origin,
        before=before,
        after=after,
        complete=complete,
    )

    result = []
    for value in out:
        if value is None:
            result.append(math.nan)
        else:
            result.append(_scalar(value, "dbl"))
    return result
