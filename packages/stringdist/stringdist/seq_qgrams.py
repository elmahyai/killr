"""Q-gram count tables for integer sequences (stringdist ``seq_qgrams``)."""

from __future__ import annotations

import math

from stringdist.seq_dist import _to_int, _vec_to_int
from stringdist.stringdist import _is_num

__all__ = ["seq_qgrams"]

_NA_INTEGER = -2147483648


class SeqQgramsMatrix:
    """Matrix of q-gram profiles with q-gram columns and per-vector counts."""

    __slots__ = ("data", "colnames")

    def __init__(self, data, colnames=None):
        self.data = data
        self.colnames = colnames


class _QNode:
    __slots__ = ("qgram", "counts", "left", "right")

    def __init__(self, qgram, counts, left, right):
        self.qgram = qgram
        self.counts = counts
        self.left = left
        self.right = right


def _uint(code):
    if code is None:
        code = _NA_INTEGER
    return int(code) & 0xFFFFFFFF


def _compare_qgram(left, right):
    for left_code, right_code in zip(left, right):
        left_u = _uint(left_code)
        right_u = _uint(right_code)
        if left_u > right_u:
            return 1
        if left_u < right_u:
            return -1
    return 0


def _push(node, qgram, q, iloc, nloc):
    if node is None:
        counts = [0.0] * nloc
        counts[iloc] += 1.0
        return _QNode(tuple(qgram), counts, None, None)
    cond = _compare_qgram(qgram, node.qgram)
    if cond == 1:
        node.left = _push(node.left, qgram, q, iloc, nloc)
    elif cond == -1:
        node.right = _push(node.right, qgram, q, iloc, nloc)
    else:
        node.counts[iloc] += 1.0
    return node


def _push_string(node, codes, q, iloc, nloc):
    limit = len(codes) - q + 1
    for index in range(limit):
        node = _push(node, codes[index : index + q], q, iloc, nloc)
    return node


def _collect(node, q, nloc, qgrams_out, counts_out):
    if node is None:
        return
    qgrams_out.append(list(node.qgram))
    counts_out.append(list(node.counts))
    _collect(node.left, q, nloc, qgrams_out, counts_out)
    _collect(node.right, q, nloc, qgrams_out, counts_out)


def _setnames(items, names):
    generic = [f"V{index + 1}" for index in range(len(items))]
    if names is None:
        return generic, items
    resolved = list(names)
    for index, name in enumerate(resolved):
        if name is None or name == "":
            resolved[index] = generic[index]
    return resolved, items


def _as_integer_inner(value):
    if value is None:
        return [None]
    if isinstance(value, float) and math.isnan(value):
        return [None]
    if isinstance(value, bool):
        raise TypeError("argument must be coercible to integer")
    if _is_num(value):
        return [_to_int(value)]
    try:
        import numpy as np

        if isinstance(value, np.ndarray):
            if value.ndim == 0:
                return [_to_int(value.item())]
            if value.ndim == 1:
                return _vec_to_int(value.tolist())
            raise TypeError("argument must be coercible to integer")
    except ImportError:
        pass
    if isinstance(value, (list, tuple)):
        return _vec_to_int(value)
    raise TypeError("argument must be coercible to integer")


def _build_qtree(encoded, q):
    nloc = len(encoded)
    root = None
    for iloc, strlist in enumerate(encoded):
        for codes in strlist:
            nchar = len(codes)
            if nchar == 0:
                continue
            if codes[0] is None:
                continue
            if q > nchar:
                continue
            if q == 0 and nchar > 0:
                continue
            root = _push_string(root, codes, q, iloc, nloc)
    return root, nloc


def _qgram_cell(code):
    if code is None:
        return None
    return float(int(code))


def seq_qgrams(*args, _list=None, q=1):
    """Return q-gram profiles for one or more integer sequences."""
    if not _is_num(q):
        raise ValueError("q must be a numeric value")
    if isinstance(q, float) and not math.isfinite(q):
        raise ValueError("q must be a numeric value")
    q = int(q)
    if q < 0:
        raise ValueError("q must be a nonnegative integer")

    if _list is not None and len(_list) == 0:
        _list = None

    pieces = list(args)
    arg_names = [None] * len(pieces)
    if _list is not None:
        if isinstance(_list, (list, tuple)):
            pieces.extend(_list)
            arg_names.extend([None] * len(_list))
        else:
            pieces.append(_list)
            arg_names.append(None)

    if not pieces:
        return SeqQgramsMatrix([], None)

    encoded = [[_as_integer_inner(item)] for item in pieces]
    rownames, encoded = _setnames(encoded, arg_names)

    root, nloc = _build_qtree(encoded, q)
    qgram_rows = []
    flat_counts = []
    _collect(root, q, nloc, qgram_rows, flat_counts)

    colnames = [f"q{index + 1}" for index in range(q)]
    colnames.extend(f"n.{name}" for name in rownames)

    nqgrams = len(qgram_rows)
    if nqgrams == 0:
        return SeqQgramsMatrix([], colnames)

    data = []
    for row_index in range(nqgrams):
        row = [_qgram_cell(value) for value in qgram_rows[row_index]]
        row.extend(float(flat_counts[row_index][loc]) for loc in range(nloc))
        data.append(row)

    return SeqQgramsMatrix(data, colnames)
