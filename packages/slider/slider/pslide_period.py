"""Parallel slide along period groups for a list of vectors."""

from __future__ import annotations

import numpy as np

from datetime import date

from slider.block import (
    _check_index_cannot_be_na,
    _check_index_incompatible_type,
    _check_index_must_be_ascending,
    _index_values,
    _vec_size,
)
from warp import Date, POSIXct, POSIXlt
from warp.time import _EPOCH
from slider.engine import as_vector, hop_index_apply, recycle
from slider.errors import SliderError
from slider.slide_period import (
    _after_for_arithmetic,
    _before_for_arithmetic,
    _check_complete,
    _unique_preserve_order,
    compute_from,
    compute_to,
)
from slider.windows import _as_int
from warp import warp_distance


def _item_as_list(group) -> list:
    if isinstance(group, Date):
        out = []
        for day in group.days:
            if day is None:
                out.append(None)
            else:
                out.append(date.fromordinal(_EPOCH + int(day)))
        return out
    if isinstance(group, (POSIXct, POSIXlt)):
        raise SliderError("`.l` POSIXt vectors are not supported yet.")
    return as_vector(group)


def _prepare_items(items) -> list:
    if isinstance(items, (str, bytes)):
        raise SliderError("`.l` must be a list of vectors.")
    if isinstance(items, dict):
        raise SliderError("`.l` must be a list of vectors.")
    groups = list(items)
    if not groups:
        raise SliderError("`.l` must be a list of vectors.")
    vectors = recycle([_item_as_list(group) for group in groups])
    return vectors


def pslide_period(
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
    """Slide ``f`` over parallel vectors using period groups from ``warp_distance`` on ``i``."""
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
        kind="list",
        atomic=False,
        simplify=False,
    )

    if not complete:
        return out

    front = [None] * size_front
    back = [None] * size_back
    return front + out + back
