"""Logical approximate grep-style matching from stringdist ``grabl``."""

from __future__ import annotations

import math

from stringdist.afind import afind
from stringdist.stringdist import _is_num

__all__ = ["grabl"]


def _stopifnot_grabl(max_dist, pattern):
    if not _is_num(max_dist):
        raise ValueError("is.numeric(maxDist) is not TRUE")
    if max_dist < 0:
        raise ValueError("maxDist >= 0 is not TRUE")
    # An R NA pattern has length 1, so None counts as one pattern here.
    if pattern is None or isinstance(pattern, str):
        plen = 1
    else:
        try:
            plen = len(pattern)
        except TypeError:
            plen = 1
    if plen != 1:
        raise ValueError("length(pattern) == 1 is not TRUE")


def grabl(
    x,
    pattern,
    maxDist=float("inf"),
    window=None,
    method=None,
    useBytes=False,
    weight=(1.0, 1.0, 1.0, 1.0),
    q=1,
    p=0,
    bt=0,
    nthread=1,
):
    """Return one flag per element of ``x``: True when afind distance is at most ``maxDist``.

    An NA distance gives None, as R gives NA.
    """
    _stopifnot_grabl(maxDist, pattern)
    result = afind(
        x,
        pattern,
        window=window,
        value=False,
        method=method,
        useBytes=useBytes,
        weight=weight,
        q=q,
        p=p,
        bt=bt,
        nthread=nthread,
    )
    out = []
    for row in result["distance"]:
        dist = row[0]
        if dist is None or (isinstance(dist, float) and math.isnan(dist)):
            out.append(None)
        else:
            out.append(dist <= maxDist)
    return out
