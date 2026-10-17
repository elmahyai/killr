"""Myers shortest edit script, the same algorithm cli's C diff uses."""

from __future__ import annotations

from cli.utf8 import utf8_graphemes

_INT_MAX = 2147483647


class _Edit:
    def __init__(self):
        self.op = 0
        self.off = 0
        self.len = 0


class _Snake:
    def __init__(self):
        self.x = self.y = self.u = self.v = 0


def _as_max_dist(max_dist) -> int:
    if max_dist is None or max_dist == float("inf"):
        return _INT_MAX
    return int(max_dist)


def _edit(edits: list[_Edit], op: int, off: int, length: int) -> None:
    if length == 0:
        return
    current = edits[-1]
    if current.op != op:
        if current.op:
            edits.append(_Edit())
            current = edits[-1]
        current.op = op
        current.off = off
        current.len = length
    else:
        current.len += length


def _find_middle_snake(aoff, n, boff, m, cmp, ctx, dmax, ms: _Snake) -> int:
    delta = n - m
    odd = delta & 1
    mid = (n + m) // 2
    mid += odd
    ctx[(1, 0)] = 0
    ctx[(delta - 1, 1)] = n

    def fv(k):
        return ctx.get((k, 0), 0)

    def rv(k):
        return ctx.get((k, 1), 0)

    for d in range(mid + 1):
        if (2 * d - 1) >= dmax:
            return dmax
        for k in range(d, -d - 1, -2):
            if k == -d or (k != d and fv(k - 1) < fv(k + 1)):
                x = fv(k + 1)
            else:
                x = fv(k - 1) + 1
            y = x - k
            ms.x = x
            ms.y = y
            while x < n and y < m and cmp(aoff + x, boff + y) == 0:
                x += 1
                y += 1
            ctx[(k, 0)] = x
            if odd and (delta - (d - 1)) <= k <= (delta + (d - 1)):
                if x >= rv(k):
                    ms.u = x
                    ms.v = y
                    return 2 * d - 1
        for k in range(d, -d - 1, -2):
            kr = (n - m) + k
            if k == d or (k != -d and rv(kr - 1) < rv(kr + 1)):
                x = rv(kr - 1)
            else:
                x = rv(kr + 1) - 1
            y = x - kr
            ms.u = x
            ms.v = y
            while x > 0 and y > 0 and cmp(aoff + (x - 1), boff + (y - 1)) == 0:
                x -= 1
                y -= 1
            ctx[(kr, 1)] = x
            if not odd and -d <= kr <= d:
                if x <= fv(kr):
                    ms.x = x
                    ms.y = y
                    return 2 * d
    raise RuntimeError("could not calculate diff")


def _ses(aoff, n, boff, m, cmp, ctx, dmax, edits) -> int:
    if n == 0:
        _edit(edits, 3, boff, m)
        return m
    if m == 0:
        _edit(edits, 2, aoff, n)
        return n
    ms = _Snake()
    distance = _find_middle_snake(aoff, n, boff, m, cmp, ctx, dmax, ms)
    if distance >= dmax:
        return dmax
    if distance > 1:
        if _ses(aoff, ms.x, boff, ms.y, cmp, ctx, dmax, edits) == -1:
            return -1
        _edit(edits, 1, aoff + ms.x, ms.u - ms.x)
        if _ses(aoff + ms.u, n - ms.u, boff + ms.v, m - ms.v, cmp, ctx, dmax, edits) == -1:
            return -1
    else:
        x = ms.x
        u = ms.u
        if m > n:
            if x == u:
                _edit(edits, 1, aoff, n)
                _edit(edits, 3, boff + (m - 1), 1)
            else:
                _edit(edits, 3, boff, 1)
                _edit(edits, 1, aoff, n)
        else:
            if x == u:
                _edit(edits, 1, aoff, m)
                _edit(edits, 2, aoff + (n - 1), 1)
            else:
                _edit(edits, 2, aoff, 1)
                _edit(edits, 1, aoff + 1, m)
    return distance


def _diff(old, new, dmax: int):
    def cmp(a, b):
        return 0 if old[a] == new[b] else 1

    n = len(old)
    m = len(new)
    edits = [_Edit()]
    ctx = {}
    limit = dmax if dmax else _INT_MAX
    x = y = 0
    while x < n and y < m and cmp(x, y) == 0:
        x += 1
        y += 1
    _edit(edits, 1, 0, x)
    distance = _ses(x, n - x, y, m - y, cmp, ctx, limit, edits)
    rows = edits if edits[0].op else []
    return rows, distance


def _frame(old, new, rows):
    ops = {1: "match", 2: "delete", 3: "insert"}
    operation = [ops[row.op] for row in rows]
    offset = [row.off for row in rows]
    length = [row.len for row in rows]
    old_offset = []
    new_offset = []
    old_at = new_at = 0
    for name, size in zip(operation, length):
        if name != "insert":
            old_at += size
        if name != "delete":
            new_at += size
        old_offset.append(old_at)
        new_offset.append(new_at)
    return {
        "old": list(old),
        "new": list(new),
        "lcs": [
            {
                "operation": operation[i],
                "offset": offset[i],
                "length": length[i],
                "old_offset": old_offset[i],
                "new_offset": new_offset[i],
            }
            for i in range(len(rows))
        ],
    }


def diff_chr(old, new, max_dist=float("inf")):
    """Shortest edit script from one character vector to another."""

    old = list(old)
    new = list(new)
    limit = _as_max_dist(max_dist)
    rows, distance = _diff(old, new, limit)
    if limit != 0 and distance == limit:
        raise RuntimeError("Diff edit distance is larger than the limit.")
    return _frame(old, new, rows)


def diff_str(old, new, max_dist=float("inf")):
    """Shortest edit script of two strings, one grapheme at a time."""

    if old is None or new is None:
        raise ValueError("diff_str does not accept missing strings")
    old_g = utf8_graphemes([old])[0]
    new_g = utf8_graphemes([new])[0]
    return diff_chr(old_g, new_g, max_dist)
