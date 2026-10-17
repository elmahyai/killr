"""Slide ``f`` over ``x`` using period groups; each window yields one integer."""

from __future__ import annotations

from slider.block import _vec_assert
from slider.engine import as_vector
from slider.period_typed import period_constrained


def slide_period_int(
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
    """Slide ``f`` over ``x`` using period groups; each window yields one integer."""
    _vec_assert(x)
    return period_constrained(
        [as_vector(x)], i, period, f, args, "int",
        every=every, origin=origin, before=before, after=after, complete=complete,
    )

