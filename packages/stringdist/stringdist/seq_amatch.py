"""Approximate sequence matching from stringdist ``seq_amatch``."""

from __future__ import annotations

from stringdist.seq_ain import _seq_amatch

__all__ = ["seq_amatch"]


def seq_amatch(
    x,
    table,
    nomatch=None,
    matchNA=True,
    method=None,
    weight=(1.0, 1.0, 1.0, 1.0),
    maxDist=0.1,
    q=1,
    p=0,
    bt=0,
    nthread=1,
):
    """1-based index of the closest table sequence within ``maxDist``."""
    return _seq_amatch(
        x,
        table,
        nomatch=nomatch,
        matchNA=matchNA,
        method=method,
        weight=weight,
        maxDist=maxDist,
        q=q,
        p=p,
        bt=bt,
        nthread=nthread,
    )
