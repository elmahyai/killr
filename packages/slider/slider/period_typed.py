"""Shared period-window core for the typed and simplified period slides.

Used by the `*_period_<type>`, `*_period2_<type>`, `*_period_vec`, and
`pslide_period_<type>` functions. The index planning matches
`slide_period_common` in slider 0.3.3. The typed path casts each result to the
requested ptype the way `vec_cast` does. The simplified path merges results
the way `list_unchop` does with no ptype.
"""

from __future__ import annotations

import math

import numpy as np

from slider.block import (
    _check_index_cannot_be_na,
    _check_index_incompatible_type,
    _check_index_must_be_ascending,
    _index_values,
)
from slider.engine import _plain, _size, hop_index_apply
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


def period_plan(size, i, period, every, origin, before, after, complete):
    """Return group ids, hop starts and stops, and the front and back padding counts."""
    _check_index_incompatible_type(i, "i")
    _check_index_cannot_be_na(i, "i")
    _check_index_must_be_ascending(i, "i")

    i_size = len(_index_values(i))
    if size != i_size:
        raise SliderError(f"`i` must have size {size}, not {i_size}.")

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

    return groups, starts, stops, size_front, size_back


def _blank(kind: str):
    return math.nan if kind == "dbl" else None


def cast_to(value, kind: str):
    """Cast one result to a ptype, as `vec_cast` does. `None` and NaN are NA."""
    value = _plain(value)
    if value is None:
        return _blank(kind)
    if kind == "dbl":
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        raise SliderError("The result of `.f` must be a number.")
    if isinstance(value, float) and math.isnan(value):
        return None
    if kind == "int":
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        raise SliderError("The result of `.f` must be an integer.")
    if kind == "lgl":
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)
        raise SliderError("The result of `.f` must be logical.")
    if kind == "chr":
        if isinstance(value, str):
            return value
        raise SliderError("The result of `.f` must be a string.")
    raise SliderError(f"Unknown ptype `{kind}`.")


def period_constrained(vectors, i, period, f, args, kind, *, every, origin, before, after, complete):
    """Slide `f` over period windows; each result is cast to the ptype `kind`."""
    groups, starts, stops, size_front, size_back = period_plan(
        len(vectors[0]), i, period, every, origin, before, after, complete
    )

    def constrained(*slices):
        value = f(*slices, *args)
        if _size(value) != 1:
            raise SliderError(
                f"The result of `.f` must have size 1, not {_size(value)}."
            )
        return cast_to(value, kind)

    out = hop_index_apply(
        vectors,
        groups,
        starts,
        stops,
        constrained,
        (),
        kind=kind,
        atomic=True,
        simplify=False,
    )

    if not complete:
        return out

    front = [_blank(kind)] * size_front
    back = [_blank(kind)] * size_back
    return front + out + back


def _kind_of(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "lgl"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "dbl"
    if isinstance(value, str):
        return "chr"
    raise SliderError("The result of `.f` must be an atomic vector of size 1.")


def common_simplify(values: list) -> list:
    """Merge size-1 results to one common atomic type, as `list_unchop` does.

    Missing `None` values carry no type. Their output is the common type's NA.
    """
    kinds: set[str] = set()
    for value in values:
        kind = _kind_of(_plain(value))
        if kind is not None:
            kinds.add(kind)

    if "chr" in kinds and kinds != {"chr"}:
        raise SliderError("Can't combine character and numeric results.")

    if "chr" in kinds:
        kind = "chr"
    elif "dbl" in kinds:
        kind = "dbl"
    elif "int" in kinds:
        kind = "int"
    else:
        kind = "lgl"

    return [cast_to(value, kind) for value in values]


def period_simplified(vectors, i, period, f, args, *, every, origin, before, after, complete):
    """Slide `f` over period windows and simplify the results to one atomic vector."""
    groups, starts, stops, size_front, size_back = period_plan(
        len(vectors[0]), i, period, every, origin, before, after, complete
    )

    out = hop_index_apply(
        vectors,
        groups,
        starts,
        stops,
        f,
        args,
        kind="list",
        atomic=True,
        simplify=False,
    )

    full = [None] * size_front + out + [None] * size_back
    return common_simplify(full)
