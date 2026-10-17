"""vec_recycle_common and list_unchop from vctrs 0.7.3."""

from __future__ import annotations


class RecycleError(Exception):
    pass


def _as_vec(value):
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def vec_recycle_common(*args, size=None):
    vectors = [_as_vec(arg) for arg in args]
    lengths = [len(item) for item in vectors]
    if size is None:
        positive = [item for item in lengths if item > 1]
        size = max(positive) if positive else max(lengths) if lengths else 0
    out = []
    for item, length in zip(vectors, lengths):
        if length == size:
            out.append(item)
        elif length == 1:
            out.append(item * size)
        elif length == 0:
            out.append([])
        else:
            raise RecycleError(f"Can't recycle input of size {length} to size {size}.")
    return out


def vec_size(x):
    if x is None:
        return 0
    if isinstance(x, (list, tuple, str, bytes)):
        if isinstance(x, str):
            return 1
        return len(x)
    return 1


def vec_slice(x, index):
    values = list(x)
    return [values[i - 1] for i in index]


def list_sizes(x):
    return [vec_size(item) for item in x]


def list_unchop(x, indices=None):
    pieces = [_as_vec(item) for item in x]
    if indices is None:
        out = []
        for piece in pieces:
            out.extend(piece)
        return out
    if len(indices) != len(pieces):
        raise RecycleError("indices must have the same size as x")
    size = 0
    for index in indices:
        if index:
            size = max(size, max(index))
    out = [None] * size
    for piece, index in zip(pieces, indices):
        if len(piece) == 1 and len(index) != 1:
            piece = piece * len(index)
        if len(piece) != len(index):
            raise RecycleError("index size must match the value size")
        for value, at in zip(piece, index):
            out[at - 1] = value
    return out
