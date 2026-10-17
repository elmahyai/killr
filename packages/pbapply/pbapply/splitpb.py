"""Split indices the way pbapply's splitpb does."""

from __future__ import annotations

import math


def splitpb(nx: int, ncl: int, nout: int | None = None) -> list[list[int]]:
    """Return 1-based index groups for progress-bar chunks."""
    if ncl == 0:
        return []
    indices = list(range(1, nx + 1))
    if nout is None:
        k = 1
    else:
        if nout < 1:
            raise ValueError("nout must be > 0")
        k = max(1, math.ceil(math.ceil(nx / ncl) / nout))
    chunk = int(ncl * k)
    groups: dict[int, list[int]] = {}
    for idx in indices:
        g = 1 + (idx - 1) // chunk
        groups.setdefault(g, []).append(idx)
    return [groups[key] for key in sorted(groups)]
