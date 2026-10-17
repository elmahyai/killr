"""Slide ``f`` over ``x`` using period groups; each window yields one character."""

from __future__ import annotations

from slider.block import _vec_assert
from slider.engine import as_vector
from slider.period_typed import period_constrained


def slide_period_chr(
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
    """Slide ``f`` over ``x`` using period groups; each window yields one character."""
    _vec_assert(x)
    return period_constrained(
        [as_vector(x)], i, period, f, args, "chr",
        every=every, origin=origin, before=before, after=after, complete=complete,
    )

