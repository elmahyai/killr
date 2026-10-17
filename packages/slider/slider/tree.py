"""Segment tree with fanout 16, matching slider's range summaries.

Sums and products accumulate in NumPy long double, which is the 80-bit
long double on this platform. Means divide that sum by the count. An
empty range keeps the reset state: 0 for a sum, NaN for a mean, +Inf
for a min, and -Inf for a max.
"""

from __future__ import annotations

import math

import numpy as np

FANOUT = 16
POWER = 4
NA_LGL = -2147483648


def _level(source, aggregate, begin: int, end: int, state):
    parent_begin = begin >> POWER
    parent_end = end >> POWER
    if parent_begin == parent_end:
        aggregate(source, begin, end, state)
        return True, begin, end
    group_begin = parent_begin * FANOUT
    group_end = parent_end * FANOUT
    if begin != group_begin:
        aggregate(source, begin, group_begin + FANOUT, state)
        parent_begin += 1
    if end != group_end:
        aggregate(source, group_end, end, state)
    return False, parent_begin, parent_end


class SegmentTree:
    def __init__(self, leaves, init_node, agg_leaves, agg_nodes, reset, finalize):
        self.leaves = leaves
        self.init_node = init_node
        self.agg_leaves = agg_leaves
        self.agg_nodes = agg_nodes
        self.reset = reset
        self.finalize = finalize
        self.levels: list[list] = []
        self._build()

    def _build(self) -> None:
        n = len(self.leaves)
        if n <= 1:
            return
        level = []
        for begin in range(0, n, FANOUT):
            node = self.init_node()
            self.agg_leaves(self.leaves, begin, min(n, begin + FANOUT), node)
            level.append(node)
        self.levels.append(level)
        source = level
        while len(source) > 1:
            nxt = []
            for begin in range(0, len(source), FANOUT):
                node = self.init_node()
                self.agg_nodes(source, begin, min(len(source), begin + FANOUT), node)
                nxt.append(node)
            self.levels.append(nxt)
            source = nxt

    def aggregate(self, begin: int, end: int):
        state = self.reset()
        done, begin, end = _level(self.leaves, self.agg_leaves, begin, end, state)
        if done:
            return self.finalize(state)
        for level in self.levels:
            done, begin, end = _level(level, self.agg_nodes, begin, end, state)
            if done:
                break
        return self.finalize(state)


def _isnan(value) -> bool:
    try:
        return math.isnan(value)
    except TypeError:
        return False


def _sum_tree(values: np.ndarray, na_rm: bool) -> SegmentTree:
    def init():
        return [np.longdouble(0)]

    def reset():
        return [np.longdouble(0)]

    def finalize(state):
        value = state[0]
        limit = np.longdouble(np.finfo(np.float64).max)
        if value > limit:
            return math.inf
        if value < -limit:
            return -math.inf
        return float(value)

    def keep_leaves(source, begin, end, dest):
        if _isnan(dest[0]):
            return
        for i in range(begin, end):
            elt = source[i]
            if _isnan(elt):
                dest[0] = np.longdouble(elt)
                return
            dest[0] += elt

    def keep_nodes(source, begin, end, dest):
        if _isnan(dest[0]):
            return
        for i in range(begin, end):
            elt = source[i][0]
            if _isnan(elt):
                dest[0] = elt
                return
            dest[0] += elt

    def drop_leaves(source, begin, end, dest):
        for i in range(begin, end):
            elt = source[i]
            if not _isnan(elt):
                dest[0] += elt

    def drop_nodes(source, begin, end, dest):
        for i in range(begin, end):
            dest[0] += source[i][0]

    if na_rm:
        return SegmentTree(values, init, drop_leaves, drop_nodes, reset, finalize)
    return SegmentTree(values, init, keep_leaves, keep_nodes, reset, finalize)


def _prod_tree(values: np.ndarray, na_rm: bool) -> SegmentTree:
    def init():
        return [np.longdouble(1)]

    def reset():
        return [np.longdouble(1)]

    def finalize(state):
        value = state[0]
        limit = np.longdouble(np.finfo(np.float64).max)
        if value > limit:
            return math.inf
        if value < -limit:
            return -math.inf
        return float(value)

    def keep_leaves(source, begin, end, dest):
        if _isnan(dest[0]):
            return
        for i in range(begin, end):
            elt = source[i]
            if _isnan(elt):
                dest[0] = np.longdouble(elt)
                return
            dest[0] *= elt

    def keep_nodes(source, begin, end, dest):
        if _isnan(dest[0]):
            return
        for i in range(begin, end):
            elt = source[i][0]
            if _isnan(elt):
                dest[0] = elt
                return
            dest[0] *= elt

    def drop_leaves(source, begin, end, dest):
        for i in range(begin, end):
            elt = source[i]
            if not _isnan(elt):
                dest[0] *= elt

    def drop_nodes(source, begin, end, dest):
        for i in range(begin, end):
            dest[0] *= source[i][0]

    if na_rm:
        return SegmentTree(values, init, drop_leaves, drop_nodes, reset, finalize)
    return SegmentTree(values, init, keep_leaves, keep_nodes, reset, finalize)


def _mean_tree(values: np.ndarray, na_rm: bool) -> SegmentTree:
    def init():
        return [np.longdouble(0), 0]

    def reset():
        return [np.longdouble(0), 0]

    def finalize(state):
        return float(state[0] / state[1])

    def keep_leaves(source, begin, end, dest):
        if _isnan(dest[0]):
            return
        for i in range(begin, end):
            elt = source[i]
            if _isnan(elt):
                dest[0] = np.longdouble(elt)
                return
            dest[0] += elt
            dest[1] += 1

    def keep_nodes(source, begin, end, dest):
        if _isnan(dest[0]):
            return
        for i in range(begin, end):
            total = source[i][0]
            if _isnan(total):
                dest[0] = total
                return
            dest[0] += total
            dest[1] += source[i][1]

    def drop_leaves(source, begin, end, dest):
        for i in range(begin, end):
            elt = source[i]
            if not _isnan(elt):
                dest[0] += elt
                dest[1] += 1

    def drop_nodes(source, begin, end, dest):
        for i in range(begin, end):
            dest[0] += source[i][0]
            dest[1] += source[i][1]

    if na_rm:
        return SegmentTree(values, init, drop_leaves, drop_nodes, reset, finalize)
    return SegmentTree(values, init, keep_leaves, keep_nodes, reset, finalize)


def _minmax_tree(values: np.ndarray, na_rm: bool, *, minimum: bool) -> SegmentTree:
    identity = math.inf if minimum else -math.inf

    def init():
        return [identity]

    def reset():
        return [identity]

    def finalize(state):
        return float(state[0])

    def better(elt, current) -> bool:
        return elt < current if minimum else elt > current

    def keep(source, begin, end, dest):
        for i in range(begin, end):
            elt = float(source[i][0] if isinstance(source[i], list) else source[i])
            if _isnan(elt):
                dest[0] = math.nan
                if not na_rm:
                    break
                continue
            if better(elt, dest[0]):
                dest[0] = elt

    def drop(source, begin, end, dest):
        for i in range(begin, end):
            elt = float(source[i][0] if isinstance(source[i], list) else source[i])
            if better(elt, dest[0]):
                dest[0] = elt

    if na_rm:
        return SegmentTree(values, init, drop, drop, reset, finalize)
    return SegmentTree(values, init, keep, keep, reset, finalize)


def _logic_tree(values: list[int], na_rm: bool, *, every: bool) -> SegmentTree:
    def init():
        return [1 if every else 0]

    def reset():
        return [1 if every else 0]

    def finalize(state):
        value = state[0]
        if value == NA_LGL:
            return None
        return bool(value)

    def all_keep(source, begin, end, dest):
        if dest[0] == 0:
            return
        for i in range(begin, end):
            elt = source[i][0] if isinstance(source[i], list) else source[i]
            if elt == 0:
                dest[0] = 0
                return
            if elt == NA_LGL:
                dest[0] = NA_LGL

    def any_keep(source, begin, end, dest):
        if dest[0] == 1:
            return
        for i in range(begin, end):
            elt = source[i][0] if isinstance(source[i], list) else source[i]
            if elt == 0:
                continue
            if elt == NA_LGL:
                dest[0] = NA_LGL
                continue
            dest[0] = 1
            return

    def all_drop(source, begin, end, dest):
        if dest[0] == 0:
            return
        for i in range(begin, end):
            elt = source[i][0] if isinstance(source[i], list) else source[i]
            if elt == 0:
                dest[0] = 0
                return

    def any_drop(source, begin, end, dest):
        if dest[0] == 1:
            return
        for i in range(begin, end):
            elt = source[i][0] if isinstance(source[i], list) else source[i]
            if elt == 1:
                dest[0] = 1
                return

    if every and na_rm:
        return SegmentTree(values, init, all_drop, all_drop, reset, finalize)
    if every:
        return SegmentTree(values, init, all_keep, all_keep, reset, finalize)
    if na_rm:
        return SegmentTree(values, init, any_drop, any_drop, reset, finalize)
    return SegmentTree(values, init, any_keep, any_keep, reset, finalize)


def sum_tree(values: np.ndarray, na_rm: bool) -> SegmentTree:
    return _sum_tree(values, na_rm)


def prod_tree(values: np.ndarray, na_rm: bool) -> SegmentTree:
    return _prod_tree(values, na_rm)


def mean_tree(values: np.ndarray, na_rm: bool) -> SegmentTree:
    return _mean_tree(values, na_rm)


def min_tree(values: np.ndarray, na_rm: bool) -> SegmentTree:
    return _minmax_tree(values, na_rm, minimum=True)


def max_tree(values: np.ndarray, na_rm: bool) -> SegmentTree:
    return _minmax_tree(values, na_rm, minimum=False)


def all_tree(values: list[int], na_rm: bool) -> SegmentTree:
    return _logic_tree(values, na_rm, every=True)


def any_tree(values: list[int], na_rm: bool) -> SegmentTree:
    return _logic_tree(values, na_rm, every=False)
