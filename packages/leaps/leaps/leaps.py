"""Python entry point for the exhaustive ``leaps`` search."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class LeapsResult:
    """The low-level search result and the R wrapper's bookkeeping."""

    ress: np.ndarray
    lopt: np.ndarray
    rss: np.ndarray
    nvmax: int
    nbest: int
    nobs: int
    npredictors: int
    intercept: bool
    x: np.ndarray
    y: np.ndarray
    weights: np.ndarray
    nullrss: float

    @property
    def which(self) -> np.ndarray:
        """Boolean selected-variable matrix, including the intercept."""
        rows: list[np.ndarray] = []
        nvar = self.x.shape[1]
        for size in range(1, self.nvmax + 1):
            lo = size * (size - 1) // 2
            hi = lo + size
            for rank in range(self.nbest):
                if self.ress[size - 1, rank] >= 1e35:
                    continue
                selected = np.zeros(nvar, dtype=bool)
                for position in self.lopt[lo:hi, rank]:
                    position = int(position)
                    if 1 <= position <= nvar:
                        selected[position - 1] = True
                rows.append(selected)
        return np.asarray(rows, dtype=bool)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ress": self.ress,
            "lopt": self.lopt,
            "rss": self.rss,
            "which": self.which,
            "nvmax": self.nvmax,
            "nbest": self.nbest,
            "nobs": self.nobs,
            "nullrss": self.nullrss,
        }


def _kernel():
    # maturin installs the extension as leaps.leaps; keeping this import lazy
    # lets the pure Python package be imported before the optional extension.
    try:
        from leaps.leaps import exhaustive
    except ImportError as exc:  # pragma: no cover - installation error
        raise ImportError("the leaps Rust extension is not installed") from exc
    return exhaustive


def leaps(
    x,
    y,
    wt=None,
    *,
    nbest: int = 1,
    nvmax: int = 8,
    method: str = "exhaustive",
    intercept: bool = True,
    **kwargs,
) -> LeapsResult:
    """Run exhaustive subset regression, matching ``leaps::leaps`` setup.

    ``nvmax`` counts predictors, as in R; the Rust kernel additionally
    receives the intercept row when ``intercept=True``.
    """
    if kwargs:
        names = ", ".join(sorted(kwargs))
        raise TypeError(f"unused arguments: {names}")
    if method != "exhaustive":
        raise NotImplementedError(
            "only method='exhaustive' is translated"
        )
    if not isinstance(nbest, (int, np.integer)) or nbest < 1:
        raise ValueError("nbest must be a positive integer")
    if not isinstance(nvmax, (int, np.integer)) or nvmax < 1:
        raise ValueError("nvmax must be a positive integer")

    predictors = np.asarray(x, dtype=float)
    if predictors.ndim != 2:
        raise ValueError("x must be a two-dimensional numeric array")
    response = np.asarray(y, dtype=float).reshape(-1)
    if predictors.shape[0] != response.size:
        raise ValueError("x and y have incompatible lengths")
    n, p = predictors.shape
    if n == 0 or p == 0:
        raise ValueError("x must have at least one row and one predictor")
    weights = np.ones(n, dtype=float) if wt is None else np.asarray(wt, dtype=float).reshape(-1)
    if weights.size != n:
        raise ValueError("wt and y have incompatible lengths")
    if np.any(weights < 0) or not np.all(np.isfinite(weights)):
        raise ValueError("wt must contain finite non-negative values")

    nvmax_eff = min(int(nvmax), p)
    if intercept:
        design = np.column_stack((np.ones(n), predictors))
        first = 2
        kernel_nvmax = nvmax_eff + 1
    else:
        design = predictors
        first = 1
        kernel_nvmax = nvmax_eff

    ress, lopt, rss = _kernel()(
        np.ascontiguousarray(design),
        np.ascontiguousarray(response),
        np.ascontiguousarray(weights),
        first,
        kernel_nvmax,
        int(nbest),
    )
    weighted_mean = np.average(response, weights=weights)
    nullrss = float(np.sum(weights * (response - weighted_mean) ** 2))
    return LeapsResult(
        ress=np.asarray(ress),
        lopt=np.asarray(lopt),
        rss=np.asarray(rss),
        nvmax=kernel_nvmax,
        nbest=int(nbest),
        nobs=n,
        npredictors=p,
        intercept=intercept,
        x=np.asarray(design),
        y=response,
        weights=weights,
        nullrss=nullrss,
    )
