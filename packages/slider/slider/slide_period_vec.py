"""Slide ``f`` over ``x`` using period groups and simplify the results."""

from __future__ import annotations

from slider.block import _vec_assert
from slider.engine import as_vector
from slider.period_typed import period_simplified


def slide_period_vec(
    x,
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
    """Slide ``f`` over ``x`` using period groups and simplify the results."""
    _vec_assert(x)
    return period_simplified(
        [as_vector(x)], i, period, f, args,
        every=every, origin=origin, before=before, after=after, complete=complete,
    )

