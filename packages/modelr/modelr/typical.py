"""Typical values.

Numbers use the median. Integers use quantile type 1. Characters, factors,
and logicals use the most common value, and a tie returns every winner.
Missing values are dropped before the choice, except that a missing character
or an explicit missing factor level can itself be the most common value.
"""

from __future__ import annotations

from modelr.frame import Factor, is_na
from modelr.quantile import quantile


def typical(x, **_ignored):
    if isinstance(x, Factor):
        if x.ordered:
            return _typical_ordered(x)
        return _typical_factor(x)
    values = list(x)
    if not values:
        return float("nan")
    if all(value is None or isinstance(value, bool) for value in values):
        return _typical_logical(values)
    if all(value is None or isinstance(value, str) for value in values):
        return _typical_character(values)
    if all(value is None or _is_int(value) for value in values):
        return _typical_integer(values)
    return _typical_numeric(values)


def _typical_numeric(values):
    result = quantile(values, [0.5], type=7, na_rm=True)
    return result[0]


def _typical_integer(values):
    result = quantile(values, [0.5], type=1, na_rm=True)
    return result[0]


def _typical_logical(values):
    kept = [value for value in values if value is not None]
    if not kept:
        return float("nan")
    mean = sum(1.0 if value else 0.0 for value in kept) / len(kept)
    return mean >= 0.5


def _typical_character(values):
    counts = {}
    order = []
    for value in values:
        key = None if is_na(value) else value
        if key not in counts:
            counts[key] = 0
            order.append(key)
        counts[key] += 1
    # table() sorts observed strings and puts NA last.
    labels = sorted((key for key in order if key is not None), key=lambda item: item)
    if None in counts:
        labels.append(None)
    best = max(counts.values())
    winners = [label for label in labels if counts[label] == best]
    if len(winners) == 1:
        return winners[0]
    return winners


def _typical_factor(x):
    counts = {level: 0 for level in x.levels}
    extra = 0
    for value in x.values:
        if value is None:
            extra += 1
        elif value in counts:
            counts[value] += 1
    best = max([extra, *counts.values()]) if counts else extra
    winners = [level for level in x.levels if counts.get(level, 0) == best]
    if None not in x.levels and extra == best and extra > 0:
        # A missing value that is not a level is not returned. It only wins
        # when every level count is lower, and then the result is that missing value.
        if not winners:
            winners = [None]
    if len(winners) == 1:
        return winners[0]
    return winners


def _typical_ordered(x):
    codes = []
    for value in x.values:
        if value is None:
            codes.append(None)
        else:
            codes.append(x.levels.index(value) + 1)
    index = quantile(codes, [0.5], type=1, na_rm=True)[0]
    if is_na(index):
        return None
    return x.levels[int(index) - 1]


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)
