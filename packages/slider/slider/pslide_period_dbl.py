"""Parallel period slide with double results."""

from __future__ import annotations

import math

import numpy as np

from slider.engine import hop_index_apply
from slider.pslide_period import _prepare_items
from slider.slide_period import (
    _after_for_arithmetic,
    _before_for_arithmetic,
    _check_complete,
    _unique_preserve_order,
    compute_from,
    compute_to,
)
from slider.block import (
    _check_index_cannot_be_na,
    _check_index_incompatible_type,
    _check_index_must_be_ascending,
    _index_values,
)
from slider.errors import SliderError
from slider.windows import _as_int
from warp import warp_distance


def pslide_period_dbl(
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
    """Slide ``f`` over parallel vectors; each window yields one double."""
    vectors = _prepare_items(items)

    _check_index_incompatible_type(i, "i")
    _check_index_cannot_be_na(i, "i")
    _check_index_must_be_ascending(i, "i")

    x_size = len(vectors[0])
    i_size = len(_index_values(i))
    if x_size != i_size:
        raise SliderError(f"`i` must have size {x_size}, not {i_size}.")

    before_val, before_unbounded = _as_int(before, "before", dot=True)
    after_val, after_unbounded = _as_int(after, "after", dot=True)
    complete = _check_complete(complete)

    groups = np.asarray(warp_distance(i, period, every=every, origin=origin)).tolist()
    unique = _unique_preserve_order(groups)

    before_num = _before_for_arithmetic(before_val, before_unbounded)
    after_num = _after_for_arithmetic(after_val, after_unbounded)
    starts = [value - before_num for value in unique]
    stops = [value + after_num for value in unique]

    size_front = 0
    size_back = 0

    if complete and unique:
        first = unique[0]
        last = unique[-1]
        n_unique = len(unique)
        from_ = compute_from(starts, first, n_unique, before_unbounded)
        to_ = compute_to(stops, last, n_unique, after_unbounded)
        size_front = from_ - 1
        size_back = n_unique - to_
        if from_ != 1 or to_ != n_unique:
            starts = starts[from_ - 1 : to_]
            stops = stops[from_ - 1 : to_]

    out = hop_index_apply(
        vectors,
        groups,
        starts,
        stops,
        f,
        args,
        kind="dbl",
        atomic=True,
        simplify=False,
    )

    if not complete:
        return out

    front = [math.nan] * size_front
    back = [math.nan] * size_back
    return front + out + back
