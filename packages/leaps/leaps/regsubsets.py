"""Translation of ``leaps::regsubsets`` for exhaustive searches."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .leaps import LeapsResult, leaps


@dataclass
class RegsubsetsResult:
    """Subset models and the summary statistics returned by R."""

    which: np.ndarray
    rss: np.ndarray
    rsq: np.ndarray
    adjr2: np.ndarray
    cp: np.ndarray
    bic: np.ndarray
    outmat: np.ndarray
    nvmax: int
    nbest: int
    nobs: int
    nullrss: float
    method: str
    labels: tuple[str, ...]
    search: LeapsResult

    def __getitem__(self, key: str):
        return getattr(self, key)


def regsubsets(
    x,
    y,
    *,
    nbest: int = 1,
    nvmax: int = 8,
    method: str = "exhaustive",
    weights=None,
    intercept: bool = True,
    **kwargs,
) -> RegsubsetsResult:
    """Find the best exhaustive regression subsets.

    ``nvmax`` counts predictors and does not count the intercept, matching
    R.  Formula interfaces and rank-deficient designs are not supported.
    """
    if kwargs:
        names = ", ".join(sorted(kwargs))
        raise TypeError(f"unused arguments: {names}")
    search = leaps(
        x,
        y,
        weights,
        nbest=nbest,
        nvmax=nvmax,
        method=method,
        intercept=intercept,
    )
    n, p = search.nobs, search.npredictors
    ncoef = p + int(intercept)
    labels = tuple(
        (["(Intercept)"] if intercept else []) + [f"x{i + 1}" for i in range(p)]
    )
    which = search.which
    # R's matrices are indexed by subset size and rank; the intercept-only
    # row is retained in the first row when an intercept is requested.
    rss = np.full((search.nvmax, search.nbest), np.nan)
    for size in range(1, search.nvmax + 1):
        for rank in range(search.nbest):
            value = float(search.ress[size - 1, rank])
            if value < 1e35:
                rss[size - 1, rank] = value

    size_for_row = np.repeat(np.arange(1, search.nvmax + 1), search.nbest)
    rsq = 1.0 - rss / search.nullrss if search.nullrss else np.full_like(rss, np.nan)
    adjr2 = np.full_like(rss, np.nan)
    cp = np.full_like(rss, np.nan)
    bic = np.full_like(rss, np.nan)
    for size in range(1, search.nvmax + 1):
        df = size
        valid = np.isfinite(rss[size - 1])
        if n > df:
            adjr2[size - 1, valid] = 1.0 - (1.0 - rsq[size - 1, valid]) * (n - 1) / (n - df)
        if n > 0:
            bic[size - 1, valid] = n * np.log(rss[size - 1, valid] / n) + df * np.log(n)
        # Mallows Cp uses the full-model residual variance in R.
        cp[size - 1, valid] = rss[size - 1, valid] / max(1, n - ncoef) - (n - 2 * df)

    outmat = np.full(which.shape, "", dtype="<U1")
    outmat[which] = "+"
    return RegsubsetsResult(
        which=which,
        rss=rss,
        rsq=rsq,
        adjr2=adjr2,
        cp=cp,
        bic=bic,
        outmat=outmat,
        nvmax=search.nvmax,
        nbest=search.nbest,
        nobs=n,
        nullrss=search.nullrss,
        method=method,
        labels=labels,
        search=search,
    )
