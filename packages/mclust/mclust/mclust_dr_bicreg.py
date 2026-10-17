"""Stepwise BIC regression used by GMMDR subset selection (``MclustDRBICreg``).

This is a package-local helper of R's ``mclustdr.R``. It is not an exported
function, so it has no registry entry.

R fits ``lm(y ~ 1)`` and, when ``x`` has columns, ``lm(y ~ 1 + x)``. The matrix
``x`` enters ``step(..., direction = "forward")`` as one term, so the search
has one step: the full regression is kept only when its AIC, with penalty
``k = log(n)``, is strictly below the intercept-only AIC. R's ``step`` stops
on ties (``o[1] == 1`` in ``stats::step``), so the comparison is strict.

``extractAIC.lm`` gives ``n * log(RSS / n) + k * edf`` with
``edf = n - df.residual``. The returned value is the Gaussian BIC-style
score ``-n log(2 pi) - n log(RSS / n) - n - p log(n)`` with
``p = n - df.residual + 1``, as in R.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

__all__ = ["MclustDRBICreg"]

# R's lm() detects rank deficiency with a tolerance of 1e-7.
_RANK_RCOND = 1e-7


def _least_squares(y: np.ndarray, design: np.ndarray) -> tuple[float, int]:
    """Return ``(RSS, rank)`` of the least-squares fit of ``y`` on ``design``."""
    coef, _, rank, _ = np.linalg.lstsq(design, y, rcond=_RANK_RCOND)
    resid = y - design @ coef
    return float(resid @ resid), int(rank)


def MclustDRBICreg(y: Any, x: Any, stepwise: bool = True) -> float:
    """Bayesian-information score of ``y`` regressed on the columns of ``x``.

    ``x`` may be ``None`` or an ``n x 0`` matrix, which gives the intercept-only
    model as in R (``mod <- mod0`` when ``ncol(x) == 0``).
    """
    y = np.asarray(y, dtype=float).reshape(-1)
    n = int(y.size)
    if x is None:
        x = np.zeros((n, 0), dtype=float)
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)

    ones = np.ones((n, 1), dtype=float)
    rss0, rank0 = _least_squares(y, ones)

    if x.shape[1] >= 1:
        rss1, rank1 = _least_squares(y, np.column_stack([ones, x]))
        if stepwise:
            k = math.log(n)
            aic0 = n * math.log(rss0 / n) + k * rank0
            aic1 = n * math.log(rss1 / n) + k * rank1
            use_full = aic1 < aic0
        else:
            use_full = True
        rss, rank = (rss1, rank1) if use_full else (rss0, rank0)
    else:
        rss, rank = rss0, rank0

    # R: p <- n - df.residual + 1, and df.residual = n - rank.
    p = rank + 1
    return float(
        -n * math.log(2.0 * math.pi) - n * math.log(rss / n) - n - p * math.log(n)
    )
