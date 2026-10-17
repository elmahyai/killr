"""Pairwise string similarity matrices (stringdist ``stringsimmatrix``)."""

from __future__ import annotations

from stringdist.stringdist import _match_arg
from stringdist.stringdistmatrix import Dist, stringdistmatrix
from stringdist.stringsim import _normalize_dist, _q_scalar

__all__ = ["stringsimmatrix"]


def _rep_whole(values, times):
    if times == 0:
        return []
    return list(values) * times


def _rep_each(values, each):
    if each == 0:
        return []
    out = []
    for item in values:
        out.extend([item] * each)
    return out


def _dist_to_matrix(dist):
    if not isinstance(dist, Dist):
        return dist
    n = dist.size
    matrix = [[0.0 if i == j else None for j in range(n)] for i in range(n)]
    index = 0
    for j in range(n):
        for i in range(j + 1, n):
            value = dist[index]
            matrix[i][j] = value
            matrix[j][i] = value
            index += 1
    return matrix


def _column_major_flat(matrix):
    if not matrix:
        return []
    nrow = len(matrix)
    ncol = len(matrix[0]) if matrix else 0
    out = []
    for j in range(ncol):
        for i in range(nrow):
            out.append(matrix[i][j])
    return out


def _flat_to_matrix(values, nrow, ncol):
    matrix = [[None] * ncol for _ in range(nrow)]
    index = 0
    for j in range(ncol):
        for i in range(nrow):
            matrix[i][j] = values[index]
            index += 1
    return matrix


def _normalize_dist_matrix(dist, a, b, method, use_bytes, q=1):
    flat = _column_major_flat(dist)
    normalized = _normalize_dist(flat, a, b, method=method, use_bytes=use_bytes, q=q)
    nrow = len(dist)
    ncol = len(dist[0]) if dist else 0
    return _flat_to_matrix(normalized, nrow, ncol)


def stringsimmatrix(a, b=None, method=None, useBytes=False, q=1, **kwargs):
    """Similarity matrix with rows from ``a`` and columns from ``b``.

    With only ``a``, returns a square matrix (diagonal 1). With both arguments,
    returns a rectangular matrix. Distances come from ``stringdistmatrix`` and
    are scaled like R ``normalize_dist`` in ``stringsim.R``.
    """
    method = _match_arg(method)
    q_val = _q_scalar(q)
    if b is None:
        dist = stringdistmatrix(a, method=method, useBytes=useBytes, q=q, **kwargs)
        if isinstance(dist, Dist):
            dist = _dist_to_matrix(dist)
        if not dist:
            return dist
        n = len(dist)
        a_items = _rep_whole(a, n)
        b_items = _rep_each(a, n)
    else:
        dist = stringdistmatrix(
            a, b, method=method, useBytes=useBytes, q=q, **kwargs
        )
        if not dist:
            return dist
        nrow = len(dist)
        ncol = len(dist[0])
        a_items = _rep_whole(a, ncol)
        b_items = _rep_each(b, nrow)
    return _normalize_dist_matrix(
        dist, a_items, b_items, method=method, use_bytes=useBytes, q=q_val
    )
