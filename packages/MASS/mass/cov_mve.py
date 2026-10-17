"""Minimum volume ellipsoid estimate (MASS cov.mve compatibility wrapper)."""

from __future__ import annotations

from typing import Any

from mass.cov_rob import CovRob, cov_rob


def cov_mve(
    x,
    cor: bool = False,
    quantile_used: int | None = None,
    nsamp: int | str = "best",
    seed: Any = None,
) -> CovRob:
    """Resistant multivariate location and scatter via the MVE method."""
    return cov_rob(
        x,
        cor=cor,
        quantile_used=quantile_used,
        method="mve",
        nsamp=nsamp,
        seed=seed,
    )
