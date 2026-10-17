"""Pairwise similarities between integer sequences (stringdist ``seq_sim``)."""

from __future__ import annotations

import math

import numpy as np

from stringdist.seq_dist import _match_seq_method, seq_dist
from stringdist.stringdist import _is_num

__all__ = ["seq_sim"]


def _lengths_list(value):
    """Per-sequence lengths for ``a`` / ``b`` (R ``lengths.list``)."""
    if _is_num(value):
        return [1]
    if isinstance(value, np.ndarray) and value.ndim == 1:
        return [int(value.size)]
    if isinstance(value, (list, tuple)):
        if not value:
            return []
        if all(_is_num(item) for item in value):
            return [len(value)]
        out = []
        for item in value:
            if item is None or (isinstance(item, float) and math.isnan(item)):
                out.append(1)
            elif _is_num(item):
                out.append(1)
            elif isinstance(item, (list, tuple)):
                out.append(len(item))
            elif isinstance(item, np.ndarray):
                out.append(int(item.size))
            else:
                raise TypeError(
                    "no applicable method for 'lengths' applied to an object of class "
                    f"'{type(item).__name__}'"
                )
        return out
    raise TypeError(
        "no applicable method for 'lengths' applied to an object of class "
        f"'{type(value).__name__}'"
    )


def _recycle(values, size):
    if not values:
        return []
    return [values[index % len(values)] for index in range(size)]


def _normalize_dist(dist, a, b, method, q=1):
    lens_a = _lengths_list(a)
    lens_b = _lengths_list(b)
    size = max(len(lens_a), len(lens_b))
    ra = _recycle(lens_a, size)
    rb = _recycle(lens_b, size)

    dist_arr = np.empty(size, dtype=float)
    missing = np.zeros(size, dtype=bool)
    for index, item in enumerate(dist):
        if item is None:
            missing[index] = True
            dist_arr[index] = math.nan
        elif isinstance(item, float) and math.isnan(item):
            missing[index] = True
            dist_arr[index] = math.nan
        else:
            dist_arr[index] = float(item)

    if method == "hamming":
        base = rb if len(lens_b) > len(lens_a) else ra
        max_dist = np.asarray(base, dtype=float)
        max_dist[max_dist == 0] = 1.0
        sim = 1.0 - dist_arr / max_dist
    elif method == "lcs":
        max_dist = np.asarray(ra, dtype=float) + np.asarray(rb, dtype=float)
        max_dist[max_dist == 0] = 1.0
        sim = 1.0 - dist_arr / max_dist
    elif method in ("lv", "osa", "dl"):
        max_dist = np.maximum(np.asarray(ra, dtype=float), np.asarray(rb, dtype=float))
        max_dist[max_dist == 0] = 1.0
        sim = 1.0 - dist_arr / max_dist
    elif method == "qgram":
        max_dist = np.asarray(ra, dtype=float) + np.asarray(rb, dtype=float) - 2 * q + 2
        max_dist[max_dist < 0] = 1.0
        sim = 1.0 - dist_arr / max_dist
    elif method in ("cosine", "jaccard", "jw"):
        sim = 1.0 - dist_arr
    else:
        raise ValueError(f"unsupported method {method!r}")

    sim[sim < 0] = 0.0
    sim[missing] = math.nan

    out = []
    for item in sim:
        if math.isnan(item):
            out.append(None)
        else:
            out.append(float(item))
    return out


def seq_sim(a, b, method=None, q=1, **kwargs):
    """Similarities between integer sequences in ``a`` and ``b``.

    Distances come from ``seq_dist``; each value is turned into a score in
    ``[0, 1]`` the same way as R ``normalize_dist`` in ``stringsim.R``.
    """
    method = _match_seq_method(method)
    q_size = int(q[0]) if isinstance(q, (list, tuple)) else int(q)
    dist = seq_dist(a, b, method=method, q=q, **kwargs)
    return _normalize_dist(dist, a, b, method=method, q=q_size)
