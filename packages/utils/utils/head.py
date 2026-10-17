"""head() and tail() from utils 4.5.0."""

from __future__ import annotations


class UtilsError(Exception):
    """An error raised with R's stop message."""


class RMatrix:
    """A column-major matrix. ``data`` is filled down each column."""

    def __init__(self, data, nrow: int, ncol: int, dimnames=None) -> None:
        self.data = list(data)
        self.nrow = int(nrow)
        self.ncol = int(ncol)
        self.dimnames = dimnames

    def dim(self) -> tuple[int, int]:
        return (self.nrow, self.ncol)

    def column(self, index: int) -> list:
        start = index * self.nrow
        return self.data[start : start + self.nrow]


def checkHT(n, dim) -> None:
    """``.checkHT``: reject an empty, non-numeric, or over-long ``n``."""
    values = _as_n(n)
    length = len(values)
    if length == 0 or all(_missing(item) for item in values):
        raise UtilsError(
            "invalid 'n' - must contain at least one non-missing element, got none."
        )
    if any(not isinstance(item, (int, float)) or isinstance(item, bool) for item in values if item is not None):
        raise UtilsError("invalid 'n' - must be numeric, possibly NA.")
    if dim is None and length > 1:
        raise UtilsError(
            f"invalid 'n' - must have length one when dim(x) is NULL, got {length}"
        )
    if dim is not None and length > len(dim):
        raise UtilsError(
            "invalid 'n' - length(n) must be <= length(dim(x)), "
            f"got {length} > {len(dim)}"
        )


def head(x, n=6):
    """The first ``n`` elements, or the first rows of a matrix."""
    if isinstance(x, RMatrix):
        return head_matrix(x, n)
    checkHT(n, None)
    values = list(x)
    count = _one_count(n, len(values))
    return values[:count]


def head_matrix(x: RMatrix, n=6) -> RMatrix:
    """The leading slice of a matrix. A missing margin is kept whole."""
    return _slice_matrix(x, n, from_end=False)


def tail(x, n=6, keepnums: bool | None = None):
    """The last ``n`` elements, or the last rows of a matrix."""
    if isinstance(x, RMatrix):
        return tail_matrix(x, n, keepnums=True if keepnums is None else keepnums)
    checkHT(n, None)
    values = list(x)
    count = _one_count(n, len(values))
    if count == 0:
        return []
    return values[-count:]


def tail_matrix(x: RMatrix, n=6, keepnums: bool = True) -> RMatrix:
    """The trailing slice of a matrix. ``keepnums`` labels the kept margins."""
    return _slice_matrix(x, n, from_end=True, keepnums=keepnums)


def _slice_matrix(x: RMatrix, n, from_end: bool, keepnums: bool = False) -> RMatrix:
    dims = x.dim()
    checkHT(n, dims)
    counts = _as_n(n)
    row_index = _margin(dims[0], counts[0] if counts else None, from_end)
    if len(counts) > 1:
        col_index = _margin(dims[1], counts[1], from_end)
    else:
        col_index = list(range(dims[1]))
    data = []
    for column in col_index:
        rows = x.column(column)
        data.extend(rows[row] for row in row_index)
    dimnames = None
    if from_end and keepnums and len(dims) > 1:
        labels = [None, None]
        for index, count in enumerate(counts):
            if _missing(count) or index > 1:
                continue
            if index == 0:
                width = len(f"[{dims[0]},]")
                labels[0] = [f"[{row + 1},]".rjust(width) for row in row_index]
            else:
                labels[1] = [f"[,{column + 1}]" for column in col_index]
        if any(item is not None for item in labels):
            dimnames = labels
    return RMatrix(data, len(row_index), len(col_index), dimnames)


def _margin(size: int, count, from_end: bool) -> list[int]:
    if count is None or _missing(count):
        return list(range(size))
    number = int(count)
    if number < 0:
        length = max(size + number, 0)
    else:
        length = min(number, size)
    if from_end:
        start = size - length
        return list(range(start, size))
    return list(range(length))


def _one_count(n, size: int) -> int:
    values = _as_n(n)
    if len(values) != 1:
        raise UtilsError(
            f"invalid 'n' - must have length one when dim(x) is NULL, got {len(values)}"
        )
    number = values[0]
    if _missing(number):
        raise UtilsError("invalid 'n' - must be numeric, possibly NA.")
    number = int(number)
    if number < 0:
        return max(size + number, 0)
    return min(number, size)


def _as_n(n) -> list:
    if isinstance(n, (list, tuple)):
        return list(n)
    return [n]


def _missing(value) -> bool:
    return value is None or (isinstance(value, float) and value != value)
