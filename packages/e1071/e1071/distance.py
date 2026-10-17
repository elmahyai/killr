"""Hamming distance. A matrix is compared row by row."""

from __future__ import annotations


def _vector(x):
    return not isinstance(x[0], (list, tuple))


def hamming_distance(x, y=None):
    if _vector(x) and (y is None or _vector(y)):
        return sum(left != right for left, right in zip(x, y))
    rows = [list(row) for row in x]
    n = len(rows)
    out = [[0 for _ in range(n)] for _ in range(n)]
    for k in range(n - 1):
        for ell in range(k + 1, n):
            out[k][ell] = hamming_distance(rows[k], rows[ell])
            out[ell][k] = out[k][ell]
    return out
