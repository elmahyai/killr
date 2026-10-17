"""first() and last() defaults from xts 0.14.3."""

from __future__ import annotations


def first(x, n: int = 1, keep: bool = False):
    """The first ``n`` rows or elements. A negative ``n`` drops that many from the front."""
    if type(x).__name__ == "Xts":
        from xts.calc import first_last_xts

        return first_last_xts(x, n, keep, from_end=False)
    return _take(x, n, keep, from_end=False)


def last(x, n: int = 1, keep: bool = False):
    """The last ``n`` rows or elements. A negative ``n`` drops that many from the end."""
    if type(x).__name__ == "Xts":
        from xts.calc import first_last_xts

        return first_last_xts(x, n, keep, from_end=True)
    return _take(x, n, keep, from_end=True)


def _take(x, n: int, keep: bool, from_end: bool):
    if len(x) == 0:
        return x
    rows = _rows(x)
    if rows is None:
        values = list(x)
        chosen = _index(len(values), n, from_end)
        out = [values[index] for index in chosen]
        if keep:
            return _Kept(out, _kept(values, n, from_end))
        return out
    chosen = _index(len(rows), n, from_end)
    out = [rows[index] for index in chosen]
    if keep:
        return _Kept(out, _kept(rows, n, from_end))
    return out


class _Kept(list):
    """A slice that also carries the ``keep`` attribute."""

    def __init__(self, values, kept) -> None:
        super().__init__(values)
        self.keep = kept


def _rows(x):
    if not x or not isinstance(x[0], (list, tuple)):
        return None
    return [list(row) for row in x]


def _index(size: int, n: int, from_end: bool) -> list[int]:
    if n > 0:
        count = min(n, size)
        if from_end:
            start = size - count
            return list(range(start, size))
        return list(range(count))
    if n < 0:
        if from_end:
            return list(range(max(size + n, 0)))
        count = max(size - (-n), 0)
        start = size - count
        return list(range(start, size))
    return []


def _kept(values, n: int, from_end: bool):
    size = len(values)
    if n > 0:
        if from_end:
            start = max(size + (-n), 0)
            return values[start:]
        start = max(-(-n) + 1, 1) - 1
        return values[start:]
    if n < 0:
        if from_end:
            return values[: (-n)]
        return values[: max(size + (-n), 0)]
    return values[:0]
