"""Approximate grep-style matching from stringdist ``grab``."""

from __future__ import annotations

import math

from stringdist.afind import afind
from stringdist.stringdist import _is_num

__all__ = ["grab"]


def _stopifnot_grab(max_dist, pattern):
    if not _is_num(max_dist):
        raise ValueError("is.numeric(maxDist) is not TRUE")
    if max_dist < 0:
        raise ValueError("maxDist >= 0 is not TRUE")
    if pattern is None:
        plen = 0
    elif isinstance(pattern, str):
        plen = 1
    else:
        try:
            plen = len(pattern)
        except TypeError:
            plen = 1
    if plen != 1:
        raise ValueError("length(pattern) == 1 is not TRUE")


def grab(
    x,
    pattern,
    maxDist=float("inf"),
    value=False,
    window=None,
    method=None,
    useBytes=False,
    weight=(1.0, 1.0, 1.0, 1.0),
    q=1,
    p=0,
    bt=0,
    nthread=1,
):
    """Return indices or matched substrings where afind distance is at most ``maxDist``."""
    _stopifnot_grab(maxDist, pattern)
    result = afind(
        x,
        pattern,
        window=window,
        value=value,
        method=method,
        useBytes=useBytes,
        weight=weight,
        q=q,
        p=p,
        bt=bt,
        nthread=nthread,
    )
    distances = result["distance"]
    nrow = len(distances)
    if not value:
        out = []
        for i in range(nrow):
            dist = distances[i][0]
            if dist is None or (isinstance(dist, float) and math.isnan(dist)):
                continue
            if dist <= maxDist:
                out.append(i + 1)
        return out
    matches = result["match"]
    out = []
    for i in range(nrow):
        dist = distances[i][0]
        if dist is None or (isinstance(dist, float) and math.isnan(dist)):
            continue
        if dist <= maxDist:
            out.append(matches[i][0])
    return out
