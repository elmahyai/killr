"""list2DF and asplit."""

from __future__ import annotations

import math

from backports._values import BackportError, length_of

__all__ = ["Array", "DataFrame", "asplit", "list2DF"]


class DataFrame:
    def __init__(self, columns, nrow):
        self.columns = columns
        self.nrow = nrow
        self.names = list(columns)

    def __repr__(self) -> str:
        if not self.columns:
            return f"data.frame({self.nrow} rows)"
        headers = list(self.columns)
        rows = []
        for index in range(self.nrow):
            rows.append(" ".join(str(self.columns[name][index]) for name in headers))
        body = "\n".join(f"{i + 1} {row}" for i, row in enumerate(rows))
        return "  " + " ".join(headers) + "\n" + body


def list2DF(x=None, nrow=0):
    if x is None:
        x = {}
    if not isinstance(x, dict) and not isinstance(x, list):
        raise BackportError("is.list(x) is not TRUE")
    if isinstance(x, list):
        x = {str(index): value for index, value in enumerate(x)}
    if nrow is not None and nrow < 0:
        raise BackportError("nrow >= 0 is not TRUE")
    if len(x):
        sizes = {length_of(value) if not isinstance(value, (list, tuple)) else len(value) for value in x.values()}
        if len(sizes) > 1:
            raise BackportError("all variables should have the same length")
        nrow = sizes.pop()
        columns = {}
        for name, value in x.items():
            if isinstance(value, (list, tuple)):
                columns[str(name)] = list(value)
            else:
                columns[str(name)] = [value]
    else:
        if nrow is None:
            nrow = 0
        columns = {}
    return DataFrame(columns, int(nrow))


class Array:
    """A column-major array. data is flat, dim is the R dimension vector."""

    def __init__(self, data, dim, dimnames=None):
        self.data = list(data)
        self.dim = [int(item) for item in dim]
        self.dimnames = dimnames

    def __repr__(self) -> str:
        return f"array({self.data}, dim={self.dim})"


def asplit(x, MARGIN):
    if not isinstance(x, Array) or not x.dim:
        raise BackportError("dim(x) must have a positive length")
    dim = list(x.dim)
    rank = len(dim)
    margin = _margin_index(x, MARGIN, rank)
    call_axes = [axis for axis in range(rank) if axis not in margin]
    ans_axes = list(margin)
    d_call = [dim[axis] for axis in call_axes]
    d_ans = [dim[axis] for axis in ans_axes]
    permuted = _aperm(x, call_axes + ans_axes)
    d2 = math.prod(d_ans) if d_ans else 1
    call_size = math.prod(d_call) if d_call else 1
    pieces = []
    for index in range(d2):
        start = index * call_size
        pieces.append(Array(permuted.data[start : start + call_size], d_call or [1]))
    if len(d_ans) == 1 and d_ans[0] == len(pieces):
        return pieces
    return pieces


def _margin_index(x, margin, rank):
    if isinstance(margin, str):
        margin = [margin]
    if isinstance(margin, (list, tuple)) and margin and isinstance(margin[0], str):
        names = []
        if x.dimnames and isinstance(x.dimnames, dict):
            names = list(x.dimnames.get("names") or [])
        if not names:
            raise BackportError("'x' must have named dimnames")
        found = []
        for item in margin:
            if item not in names:
                raise BackportError("not all elements of 'MARGIN' are names of dimensions")
            found.append(names.index(item))
        return found
    if isinstance(margin, (list, tuple)):
        return [int(item) - 1 for item in margin]
    return [int(margin) - 1]


def _aperm(array: Array, order):
    """order is 0-based old axes in the new axis order."""
    old = array.dim
    new_dim = [old[axis] for axis in order]
    total = math.prod(old) if old else 0
    out = [None] * total
    for flat in range(total):
        coords = _unravel(flat, old)
        new_coords = [coords[axis] for axis in order]
        out[_ravel(new_coords, new_dim)] = array.data[flat]
    return Array(out, new_dim, array.dimnames)


def _unravel(flat, dim):
    coords = []
    for size in dim:
        coords.append(flat % size)
        flat //= size
    return coords


def _ravel(coords, dim):
    flat = 0
    stride = 1
    for coord, size in zip(coords, dim):
        flat += coord * stride
        stride *= size
    return flat
