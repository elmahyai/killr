"""Slide ``f`` over ``x`` and ``y`` using period groups; each window yields one integer."""

from __future__ import annotations

from slider.block import _vec_assert
from slider.engine import as_vector, recycle
from slider.period_typed import period_constrained


def slide_period2_int(
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
    """Slide ``f`` over ``x`` and ``y`` using period groups; each window yields one integer."""
    _vec_assert(x)
    _vec_assert(y)
    vectors = recycle([as_vector(x), as_vector(y)])
    return period_constrained(
        vectors, i, period, f, args, "int",
        every=every, origin=origin, before=before, after=after, complete=complete,
    )

