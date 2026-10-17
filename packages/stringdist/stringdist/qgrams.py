"""Q-gram count tables from stringdist ``qgrams``."""

from __future__ import annotations

import math
import numbers

__all__ = ["qgrams"]


class QgramsMatrix:
    """Matrix of q-gram counts with optional row and column names."""

    __slots__ = ("data", "rownames", "colnames")

    def __init__(self, data, rownames=None, colnames=None):
        self.data = data
        self.rownames = rownames
        self.colnames = colnames


def _is_num(value):
    return isinstance(value, numbers.Real) and not isinstance(value, bool)


def _as_character(value):
    if isinstance(value, str):
        return [value]
    if value is None:
        return []
    if _is_num(value):
        if isinstance(value, float) and value.is_integer():
            return [str(int(value))]
        return [str(value)]
    if isinstance(value, bool):
        return ["TRUE" if value else "FALSE"]
    try:
        items = list(value)
    except TypeError:
        return [str(value)]
    out = []
    for item in items:
        if item is None:
            out.append(None)
        elif isinstance(item, str):
            out.append(item)
        elif isinstance(item, bool):
            out.append("TRUE" if item else "FALSE")
        elif _is_num(item):
            if isinstance(item, float) and item.is_integer():
                out.append(str(int(item)))
            else:
                out.append(str(item))
        else:
            out.append(str(item))
    return out


def _setnames(items, names):
    generic = [f"V{index + 1}" for index in range(len(items))]
    if names is None:
        return generic, items
    resolved = list(names)
    for index, name in enumerate(resolved):
        if name is None or name == "":
            resolved[index] = generic[index]
    return resolved, items


def _char2int(strings):
    blocks = []
    for text in strings:
        if text is None:
            blocks.append([None])
        else:
            blocks.append([ord(ch) for ch in text])
    return blocks


def _compare(left, right):
    for a, b in zip(left, right):
        if a > b:
            return 1
        if a < b:
            return -1
    return 0


class _QNode:
    __slots__ = ("qgram", "counts", "left", "right")

    def __init__(self, qgram, counts, left, right):
        self.qgram = qgram
        self.counts = counts
        self.left = left
        self.right = right


def _push(node, qgram, q, iloc, nloc):
    if node is None:
        counts = [0.0] * nloc
        counts[iloc] += 1.0
        return _QNode(tuple(qgram), counts, None, None)
    cond = _compare(qgram, node.qgram)
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


def _count_nodes(node):
    if node is None:
        return 0
    return 1 + _count_nodes(node.left) + _count_nodes(node.right)


def _collect(node, q, nloc, qgrams_out, counts_out):
    if node is None:
        return
    qgrams_out.append(list(node.qgram))
    counts_out.append(list(node.counts))
    _collect(node.left, q, nloc, qgrams_out, counts_out)
    _collect(node.right, q, nloc, qgrams_out, counts_out)


def _format_colnames(qgram_rows, q, use_bytes):
    names = []
    for row in qgram_rows:
        if use_bytes:
            names.append("|".join(format(value & 0xFF, "02x") for value in row))
        else:
            names.append("".join(chr(value) for value in row))
    return names


def qgrams(*args, _list=None, q=1, useBytes=False, useNames=None):
    """Return a table of q-gram counts for one or more character vectors."""
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
    if _list is not None:
        if isinstance(_list, (list, tuple)):
            pieces.extend(_list)
        else:
            pieces.append(_list)

    if not pieces:
        return QgramsMatrix([], None, None)

    coerced = [_as_character(item) for item in pieces]
    rownames, coerced = _setnames(coerced, None)

    if q == 0:
        counts = [sum(text == "" for text in strings) for strings in coerced]
        return QgramsMatrix([[float(value)] for value in counts], rownames, None)

    encoded = [_char2int(strings) for strings in coerced]
    nloc = len(encoded)
    root = None
    for iloc, blocks in enumerate(encoded):
        for codes in blocks:
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

    qgram_rows = []
    flat_counts = []
    _collect(root, q, nloc, qgram_rows, flat_counts)

    nqgrams = len(qgram_rows)
    if nqgrams == 0:
        return QgramsMatrix([[] for _ in range(nloc)], rownames, None)

    data = [[0.0] * nqgrams for _ in range(nloc)]
    for col, counts in enumerate(flat_counts):
        for row, value in enumerate(counts):
            data[row][col] = float(value)

    colnames = None
    if useNames is None:
        useNames = not useBytes
    if useNames:
        colnames = _format_colnames(qgram_rows, q, useBytes)

    return QgramsMatrix(data, rownames, colnames)
