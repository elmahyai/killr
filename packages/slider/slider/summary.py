"""Rolling summaries through the segment tree."""

from __future__ import annotations

import math

import numpy as np

from slider.engine import as_vector
from slider.errors import SliderError
from slider.index import complete_ranges, dense_ranks, plan_from_before
from slider.tree import (
    NA_LGL,
    all_tree,
    any_tree,
    max_tree,
    mean_tree,
    min_tree,
    prod_tree,
    sum_tree,
)
from slider.windows import iter_opts, validate_bool, windows

try:
    import slider_kernels as _kernels
except ImportError:  # the crate is optional; the pure-NumPy tree is the fallback
    _kernels = None


def _no_dots(args) -> None:
    if args:
        raise SliderError("`...` must be empty.")


def _doubles(x) -> np.ndarray:
    values = as_vector(x)
    out = np.empty(len(values), dtype=np.float64)
    for i, value in enumerate(values):
        if value is None:
            out[i] = np.nan
        elif isinstance(value, bool):
            out[i] = float(value)
        elif isinstance(value, (int, float)):
            out[i] = float(value) if not (isinstance(value, float) and math.isnan(value)) else np.nan
        else:
            raise SliderError("`x` must be numeric.")
    return out


def _logicals(x) -> list[int]:
    values = as_vector(x)
    out = []
    for value in values:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            out.append(NA_LGL)
        elif value is True or value == 1:
            out.append(1)
        elif value is False or value == 0:
            out.append(0)
        else:
            raise SliderError("`x` must be logical.")
    return out


def _slide_numeric(x, before, after, step, complete, na_rm, kind, tree_of, args):
    _no_dots(args)
    na_rm = validate_bool(na_rm, "na_rm", dot=False)
    values = _doubles(x)
    opts = iter_opts(before, after, step, complete, len(values), dot=False)
    if _kernels is not None:
        native = _kernels.slide_dbl(
            kind,
            values,
            opts.before,
            opts.before_unbounded,
            opts.after,
            opts.after_unbounded,
            opts.iter_step,
            opts.complete,
            na_rm,
        )
        return native.tolist()
    tree = tree_of(values, na_rm)
    out = [math.nan] * len(values)
    for index, start, stop in windows(opts):
        if start is None:
            begin, end = 0, 0
        else:
            begin, end = start, stop + 1
        out[index] = tree.aggregate(begin, end)
    return out


def _slide_logical(x, before, after, step, complete, na_rm, kind, tree_of, args):
    _no_dots(args)
    na_rm = validate_bool(na_rm, "na_rm", dot=False)
    values = _logicals(x)
    opts = iter_opts(before, after, step, complete, len(values), dot=False)
    if _kernels is not None:
        native = _kernels.slide_lgl(
            kind,
            np.array(values, dtype=np.int32),
            opts.before,
            opts.before_unbounded,
            opts.after,
            opts.after_unbounded,
            opts.iter_step,
            opts.complete,
            na_rm,
        )
        return [None if value == NA_LGL else bool(value) for value in native.tolist()]
    tree = tree_of(values, na_rm)
    out = [None] * len(values)
    for index, start, stop in windows(opts):
        if start is None:
            begin, end = 0, 0
        else:
            begin, end = start, stop + 1
        out[index] = tree.aggregate(begin, end)
    return out


def slide_sum(x, *args, before=0, after=0, step=1, complete=False, na_rm=False):
    return _slide_numeric(x, before, after, step, complete, na_rm, "sum", sum_tree, args)


def slide_prod(x, *args, before=0, after=0, step=1, complete=False, na_rm=False):
    return _slide_numeric(x, before, after, step, complete, na_rm, "prod", prod_tree, args)


def slide_mean(x, *args, before=0, after=0, step=1, complete=False, na_rm=False):
    return _slide_numeric(x, before, after, step, complete, na_rm, "mean", mean_tree, args)


def slide_min(x, *args, before=0, after=0, step=1, complete=False, na_rm=False):
    return _slide_numeric(x, before, after, step, complete, na_rm, "min", min_tree, args)


def slide_max(x, *args, before=0, after=0, step=1, complete=False, na_rm=False):
    return _slide_numeric(x, before, after, step, complete, na_rm, "max", max_tree, args)


def slide_all(x, *args, before=0, after=0, step=1, complete=False, na_rm=False):
    return _slide_logical(x, before, after, step, complete, na_rm, "all", all_tree, args)


def slide_any(x, *args, before=0, after=0, step=1, complete=False, na_rm=False):
    return _slide_logical(x, before, after, step, complete, na_rm, "any", any_tree, args)


def _index_plan(index, size, before, after, complete):
    index_values = as_vector(index)
    if len(index_values) != size:
        raise SliderError(f"`i` must have size {size}, not {len(index_values)}.")
    return plan_from_before(index_values, before, after, complete)


def _index_native(plan):
    """The ranked arguments the kernel expects, or `None` when it can't be used.

    R ranks `i`, `starts`, and `stops` together (`compute_combined_ranks`), so
    the C compares dense ranks rather than the original values. A non-numeric
    index (a date, say) has no dense rank here and falls back to Python.
    """
    if _kernels is None:
        return None
    try:
        return dense_ranks(plan.keys, plan.starts, plan.stops)
    except TypeError:
        return None


def _index_numeric(x, index, before, after, complete, na_rm, kind, tree_of, args):
    _no_dots(args)
    na_rm = validate_bool(na_rm, "na_rm", dot=False)
    complete = validate_bool(complete, "complete", dot=False)
    values = _doubles(x)
    plan = _index_plan(index, len(values), before, after, complete)
    native = _index_native(plan)
    if native is not None:
        keys, starts, stops = native
        return _kernels.slide_index_dbl(
            kind,
            values,
            np.array(keys, dtype=np.int32),
            np.array(plan.times, dtype=np.int32),
            None if starts is None else np.array(starts, dtype=np.int32),
            None if stops is None else np.array(stops, dtype=np.int32),
            complete,
            na_rm,
        ).tolist()
    tree = tree_of(values, na_rm)
    out = [math.nan] * len(values)
    for pos, start, stop in complete_ranges(plan):
        if start is None:
            begin, end = 0, 0
        else:
            begin, end = start, stop + 1
        result = tree.aggregate(begin, end)
        element = plan.peer_starts[pos]
        for _ in range(plan.times[pos]):
            out[element] = result
            element += 1
    return out


def _index_logical(x, index, before, after, complete, na_rm, kind, tree_of, args):
    _no_dots(args)
    na_rm = validate_bool(na_rm, "na_rm", dot=False)
    complete = validate_bool(complete, "complete", dot=False)
    values = _logicals(x)
    plan = _index_plan(index, len(values), before, after, complete)
    native = _index_native(plan)
    if native is not None:
        keys, starts, stops = native
        native_out = _kernels.slide_index_lgl(
            kind,
            np.array(values, dtype=np.int32),
            np.array(keys, dtype=np.int32),
            np.array(plan.times, dtype=np.int32),
            None if starts is None else np.array(starts, dtype=np.int32),
            None if stops is None else np.array(stops, dtype=np.int32),
            complete,
            na_rm,
        )
        return [None if value == NA_LGL else bool(value) for value in native_out.tolist()]
    tree = tree_of(values, na_rm)
    out = [None] * len(values)
    for pos, start, stop in complete_ranges(plan):
        if start is None:
            begin, end = 0, 0
        else:
            begin, end = start, stop + 1
        result = tree.aggregate(begin, end)
        element = plan.peer_starts[pos]
        for _ in range(plan.times[pos]):
            out[element] = result
            element += 1
    return out


def slide_index_sum(x, i, *args, before=0, after=0, complete=False, na_rm=False):
    return _index_numeric(x, i, before, after, complete, na_rm, "sum", sum_tree, args)


def slide_index_prod(x, i, *args, before=0, after=0, complete=False, na_rm=False):
    return _index_numeric(x, i, before, after, complete, na_rm, "prod", prod_tree, args)


def slide_index_mean(x, i, *args, before=0, after=0, complete=False, na_rm=False):
    return _index_numeric(x, i, before, after, complete, na_rm, "mean", mean_tree, args)


def slide_index_min(x, i, *args, before=0, after=0, complete=False, na_rm=False):
    return _index_numeric(x, i, before, after, complete, na_rm, "min", min_tree, args)


def slide_index_max(x, i, *args, before=0, after=0, complete=False, na_rm=False):
    return _index_numeric(x, i, before, after, complete, na_rm, "max", max_tree, args)


def slide_index_all(x, i, *args, before=0, after=0, complete=False, na_rm=False):
    return _index_logical(x, i, before, after, complete, na_rm, "all", all_tree, args)


def slide_index_any(x, i, *args, before=0, after=0, complete=False, na_rm=False):
    return _index_logical(x, i, before, after, complete, na_rm, "any", any_tree, args)
