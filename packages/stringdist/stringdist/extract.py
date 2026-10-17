"""Best-match substring extraction from stringdist ``extract``."""

from __future__ import annotations

import math

from stringdist.afind import afind
from stringdist.stringdist import _is_num

__all__ = ["extract"]


def _stopifnot_extract(max_dist, pattern):
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


def extract(
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
    """Return the best afind window per string, or missing when above ``maxDist``."""
    _stopifnot_extract(maxDist, pattern)
    result = afind(
        x,
        pattern,
        window=window,
        value=True,
        method=method,
        useBytes=useBytes,
        weight=weight,
        q=q,
        p=p,
        bt=bt,
        nthread=nthread,
    )
    out = [row[:] for row in result["match"]]
    distances = result["distance"]
    for i, row in enumerate(distances):
        for j, dist in enumerate(row):
            if dist is not None and not math.isnan(dist) and dist > maxDist:
                out[i][j] = None
    return out
