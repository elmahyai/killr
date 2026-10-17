"""Slide ``f`` over parallel vectors and simplify the results."""

from __future__ import annotations

from slider.period_typed import period_simplified
from slider.pslide_period import _prepare_items


def pslide_period_vec(
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
    """Slide ``f`` over parallel vectors and simplify the results."""
    vectors = _prepare_items(items)
    return period_simplified(
        vectors, i, period, f, args,
        every=every, origin=origin, before=before, after=after, complete=complete,
    )

