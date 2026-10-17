"""Gower distance wrapper."""

from __future__ import annotations

from typing import Any

import gower_kernel

from ._common import prepare


def gower_dist(
    x: Any,
    y: Any | None = None,
    pair_x: Any | None = None,
    pair_y: Any | None = None,
    eps: float = 1e-8,
    weights: Any | None = None,
    nthread: int = 1,
):
    """Compute Gower distances, recycling the shorter input as R does."""
    xc, yc, ranges, pair, factors, weights, eps = prepare(
        x, y, pair_x, pair_y, eps, weights
    )
    return gower_kernel.gower_dist(
        xc, yc, ranges, pair, factors, eps, weights, int(nthread)
    )
