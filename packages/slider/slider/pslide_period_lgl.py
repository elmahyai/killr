"""Slide ``f`` over parallel vectors; each window yields one logical."""

from __future__ import annotations

from slider.period_typed import period_constrained
from slider.pslide_period import _prepare_items


def pslide_period_lgl(
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
    """Slide ``f`` over parallel vectors; each window yields one logical."""
    vectors = _prepare_items(items)
    return period_constrained(
        vectors, i, period, f, args, "lgl",
        every=every, origin=origin, before=before, after=after, complete=complete,
    )

