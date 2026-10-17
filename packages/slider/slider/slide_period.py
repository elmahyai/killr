"""Slide along windows defined by warp period groups."""

from __future__ import annotations

import numpy as np

from slider.block import (
    _check_index_cannot_be_na,
    _check_index_incompatible_type,
    _check_index_must_be_ascending,
    _index_values,
    _vec_assert,
    _vec_size,
)
from slider.engine import hop_index_apply
from slider.errors import SliderError
from slider.windows import _as_int, _missing
from warp import warp_distance


def _unique_preserve_order(values: list) -> list:
    seen: set = set()
    out: list = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _check_complete(value) -> bool:
    if _missing(value):
        raise SliderError("`.complete` can't be missing.")
    if isinstance(value, bool):
        return value
    raise SliderError("`.complete` must be logical.")


def compute_from(starts: list, first: float, n: int, before_unbounded: bool) -> int:
    if before_unbounded:
        return 1
    from_ = 1
    for i in range(n):
        if first > starts[i]:
            from_ += 1
        else:
            break
    return from_


def compute_to(stops: list, last: float, n: int, after_unbounded: bool) -> int:
    if after_unbounded:
        return n
    to = n
    for i in range(n - 1, -1, -1):
        if last < stops[i]:
            to -= 1
        else:
            break
    return to


def _before_for_arithmetic(before, before_unbounded: bool):
    if before_unbounded:
        return float("inf")
    return before


def _after_for_arithmetic(after, after_unbounded: bool):
    if after_unbounded:
        return float("inf")
    return after


def slide_period(
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
    """Slide ``f`` over ``x`` using period groups from ``warp_distance`` on ``i``."""
    _vec_assert(x)

    _check_index_incompatible_type(i, "i")
    _check_index_cannot_be_na(i, "i")
    _check_index_must_be_ascending(i, "i")

    x_size = _vec_size(x)
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
        [x],
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
