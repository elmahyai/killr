"""Top-n Gower match wrapper."""

from __future__ import annotations

from typing import Any

import gower_kernel

from ._common import prepare


def gower_topn(
    x: Any,
    y: Any | None = None,
    n: int = 5,
    pair_x: Any | None = None,
    pair_y: Any | None = None,
    eps: float = 1e-8,
    weights: Any | None = None,
    nthread: int = 1,
):
    """Return ``(index, distance)`` for each record's n nearest y records."""
    if int(n) < 0:
        raise ValueError("n must be non-negative")
    xc, yc, ranges, pair, factors, weights, eps = prepare(
        x, y, pair_x, pair_y, eps, weights
    )
    # gower 1.0.2's top-n wrapper compares character fields against "" by
    # overwriting its temporary record; the Rust kernel intentionally retains
    # that behavior without mutating the caller's object.
    return gower_kernel.gower_topn(
        xc, yc, ranges, pair, factors, int(n), eps, weights, int(nthread)
    )
