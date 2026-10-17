"""splitpb logic used by pblapply (exported separately as splitpb)."""

from __future__ import annotations

import math
from collections import defaultdict


def splitpb(nx: int, ncl: int, nout: int | None = None) -> list[list[int]]:
    """Split 1..nx into groups the way pbapply::splitpb does."""
    nx = int(nx)
    ncl = int(ncl)
    if ncl == 0:
        return []
    if nout is None:
        k = 1
    else:
        nout = int(nout)
        if nout < 1:
            raise ValueError("nout must be > 0")
        k = max(1, math.ceil(math.ceil(nx / ncl) / nout))
    stride = ncl * k
    groups: dict[int, list[int]] = defaultdict(list)
    for index in range(1, nx + 1):
        group = 1 + (index - 1) // stride
        groups[group].append(index)
    return [groups[key] for key in sorted(groups)]
