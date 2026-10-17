"""Rolling summaries through the segment tree."""

from __future__ import annotations

import math

import numpy as np

from slider.engine import as_vector
from slider.errors import SliderError
from slider.index import complete_ranges, plan_from_before
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


def _slide_numeric(x, before, after, step, complete, na_rm, tree_of, args):
    _no_dots(args)
    na_rm = validate_bool(na_rm, "na_rm", dot=False)
    values = _doubles(x)
    opts = iter_opts(before, after, step, complete, len(values), dot=False)
    tree = tree_of(values, na_rm)
    out = [math.nan] * len(values)
    for index, start, stop in windows(opts):
        if start is None:
            begin, end = 0, 0
        else:
            begin, end = start, stop + 1
        out[index] = tree.aggregate(begin, end)
    return out


def _slide_logical(x, before, after, step, complete, na_rm, tree_of, args):
    _no_dots(args)
    na_rm = validate_bool(na_rm, "na_rm", dot=False)
    values = _logicals(x)
    opts = iter_opts(before, after, step, complete, len(values), dot=False)
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
    return _slide_numeric(x, before, after, step, complete, na_rm, sum_tree, args)


def slide_prod(x, *args, before=0, after=0, step=1, complete=False, na_rm=False):
    return _slide_numeric(x, before, after, step, complete, na_rm, prod_tree, args)


def slide_mean(x, *args, before=0, after=0, step=1, complete=False, na_rm=False):
    return _slide_numeric(x, before, after, step, complete, na_rm, mean_tree, args)


def slide_min(x, *args, before=0, after=0, step=1, complete=False, na_rm=False):
    return _slide_numeric(x, before, after, step, complete, na_rm, min_tree, args)


def slide_max(x, *args, before=0, after=0, step=1, complete=False, na_rm=False):
    return _slide_numeric(x, before, after, step, complete, na_rm, max_tree, args)


def slide_all(x, *args, before=0, after=0, step=1, complete=False, na_rm=False):
    return _slide_logical(x, before, after, step, complete, na_rm, all_tree, args)


def slide_any(x, *args, before=0, after=0, step=1, complete=False, na_rm=False):
    return _slide_logical(x, before, after, step, complete, na_rm, any_tree, args)


def _index_numeric(x, index, before, after, complete, na_rm, tree_of, args):
    _no_dots(args)
    na_rm = validate_bool(na_rm, "na_rm", dot=False)
    complete = validate_bool(complete, "complete", dot=False)
    values = _doubles(x)
    index_values = as_vector(index)
    if len(index_values) != len(values):
        raise SliderError(f"`i` must have size {len(values)}, not {len(index_values)}.")
    plan = plan_from_before(index_values, before, after, complete)
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


def _index_logical(x, index, before, after, complete, na_rm, tree_of, args):
    _no_dots(args)
    na_rm = validate_bool(na_rm, "na_rm", dot=False)
    complete = validate_bool(complete, "complete", dot=False)
    values = _logicals(x)
    index_values = as_vector(index)
    if len(index_values) != len(values):
        raise SliderError(f"`i` must have size {len(values)}, not {len(index_values)}.")
    plan = plan_from_before(index_values, before, after, complete)
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
    return _index_numeric(x, i, before, after, complete, na_rm, sum_tree, args)


def slide_index_prod(x, i, *args, before=0, after=0, complete=False, na_rm=False):
    return _index_numeric(x, i, before, after, complete, na_rm, prod_tree, args)


def slide_index_mean(x, i, *args, before=0, after=0, complete=False, na_rm=False):
    return _index_numeric(x, i, before, after, complete, na_rm, mean_tree, args)


def slide_index_min(x, i, *args, before=0, after=0, complete=False, na_rm=False):
    return _index_numeric(x, i, before, after, complete, na_rm, min_tree, args)


def slide_index_max(x, i, *args, before=0, after=0, complete=False, na_rm=False):
    return _index_numeric(x, i, before, after, complete, na_rm, max_tree, args)


def slide_index_all(x, i, *args, before=0, after=0, complete=False, na_rm=False):
    return _index_logical(x, i, before, after, complete, na_rm, all_tree, args)


def slide_index_any(x, i, *args, before=0, after=0, complete=False, na_rm=False):
    return _index_logical(x, i, before, after, complete, na_rm, any_tree, args)
