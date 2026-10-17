"""Approximate ``%in%`` from stringdist ``ain``."""

from __future__ import annotations

from stringdist._amatch import amatch

__all__ = ["ain"]


def ain(
    x,
    table,
    matchNA=True,
    method=None,
    useBytes=False,
    weight=(1.0, 1.0, 1.0, 1.0),
    maxDist=0.1,
    q=1,
    p=0,
    bt=0,
    nthread=1,
):
    """Whether each element of ``x`` has an approximate match in ``table``."""
    positions = amatch(
        x,
        table,
        nomatch=0,
        matchNA=matchNA,
        method=method,
        useBytes=useBytes,
        weight=weight,
        maxDist=maxDist,
        q=q,
        p=p,
        bt=bt,
        nthread=nthread,
    )
    out = []
    for pos in positions:
        if pos is None:
            out.append(None)
        else:
            out.append(pos > 0)
    return out
