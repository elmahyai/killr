"""Pairwise string similarities (stringdist ``stringsim``)."""

from __future__ import annotations

import math

import numpy as np

from stringdist.stringdist import _as_character, _match_arg, stringdist

__all__ = ["stringsim"]


def _nchar(text, use_bytes):
    if text is None:
        return 0
    if use_bytes:
        return len(text.encode("utf-8"))
    return len(text)


def _lengths_char(value, use_bytes):
    warn = [False]
    items = _as_character(value, warn)
    return [_nchar(item, use_bytes) for item in items]


def _recycle(values, size):
    if not values:
        return []
    return [values[index % len(values)] for index in range(size)]


def _normalize_dist(dist, a, b, method, use_bytes, q=1):
    lens_a = _lengths_char(a, use_bytes)
    lens_b = _lengths_char(b, use_bytes)
    size = max(len(lens_a), len(lens_b))
    ra = _recycle(lens_a, size)
    rb = _recycle(lens_b, size)

    dist_arr = np.empty(size, dtype=float)
    missing = np.zeros(size, dtype=bool)
    for index, item in enumerate(dist):
        if item is None:
            missing[index] = True
            dist_arr[index] = math.nan
        elif item == float("inf") or item == float("-inf"):
            dist_arr[index] = float(item)
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
    elif method in ("cosine", "jaccard", "jw", "soundex"):
        sim = 1.0 - dist_arr
    else:
        raise ValueError(f"unsupported method {method!r}")

    sim[sim < 0] = 0.0
    sim[missing] = math.nan

    out = []
    for index, item in enumerate(sim):
        if missing[index]:
            out.append(None)
        elif math.isnan(item):
            out.append(float("nan"))
        else:
            out.append(float(item))
    return out


def _q_scalar(q):
    if isinstance(q, (list, tuple)):
        return float(q[0])
    return float(q)


def stringsim(a, b, method=None, useBytes=False, q=1, **kwargs):
    """Similarities between strings in ``a`` and ``b``.

    Distances come from ``stringdist``; each value is turned into a score in
    ``[0, 1]`` the same way as R ``normalize_dist`` in ``stringsim.R``.
    """
    method = _match_arg(method)
    dist = stringdist(a, b, method=method, useBytes=useBytes, q=q, **kwargs)
    return _normalize_dist(dist, a, b, method=method, use_bytes=useBytes, q=_q_scalar(q))
