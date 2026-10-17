"""probplot: a probability plot against a quantile function (e1071 ``probplot``).

The chart is drawn with Matplotlib. The line through the two quartiles is the
fit that R stores as ``int`` and ``slope``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from statistics import NormalDist
from typing import Any

import numpy as np


def _ppoints(n: int) -> np.ndarray:
    """R ppoints(n): (i - a) / (n + 1 - 2a), with a = 3/8 for n <= 10 and 1/2 otherwise."""
    a = 3.0 / 8.0 if n <= 10 else 0.5
    i = np.arange(1, n + 1, dtype=float)
    return (i - a) / (n + 1.0 - 2.0 * a)


def qnorm(p: Any, mean: float = 0.0, sd: float = 1.0) -> np.ndarray:
    """Normal quantile, as R qnorm. The inverse is the AS 241 algorithm in the standard library."""
    dist = NormalDist(mean, sd)
    return np.array([dist.inv_cdf(float(v)) for v in np.atleast_1d(np.asarray(p, dtype=float))])


def probplot(
    x: Sequence[float],
    qdist: Callable[..., Any] | None = None,
    probs: Sequence[float] | None = None,
    line: bool = True,
    xlab: str | None = None,
    ylab: str = "Probability in %",
    **dots: Any,
):
    """Draw the probability plot and return the fitted line and the quantile function."""
    import matplotlib.pyplot as plt

    qfun_base = qnorm if qdist is None else qdist
    values = np.sort(np.asarray(x, dtype=float))
    xlab = "x" if xlab is None else xlab

    def qfun(p: Any) -> np.ndarray:
        return np.asarray(qfun_base(p, **dots), dtype=float)

    y = qfun(_ppoints(len(values)))

    if probs is None:
        probs = [0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]
        if len(values) >= 1000:
            probs = [0.001] + probs + [0.999]
    probs = np.asarray(probs, dtype=float)
    qprobs = qfun(probs)

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.set_xlim(values.min(), values.max())
    ax.set_ylim(min(y.min(), qprobs.min()), max(y.max(), qprobs.max()))
    ax.set_xlabel(xlab)
    ax.set_ylabel(ylab)
    for level in qprobs:
        ax.axhline(level, color="grey")
    ax.set_yticks(qprobs, labels=[f"{100 * p:g}" for p in probs])
    ax.scatter(values, y, color="black", s=12)
    ax.text(1.0, -0.22, f"Quantile: {getattr(qdist, '__name__', 'qnorm')}", transform=ax.transAxes,
            ha="right", va="top")

    xl = np.quantile(values, [0.25, 0.75])
    yl = qfun(np.array([0.25, 0.75]))
    slope = (yl[1] - yl[0]) / (xl[1] - xl[0])
    intercept = yl[0] - slope * xl[0]
    if line:
        grid = np.array([values.min(), values.max()])
        ax.plot(grid, intercept + slope * grid, color="red")

    return {
        "qdist": qfun,
        "int": float(intercept),
        "slope": float(slope),
        "class": "probplot",
        "figure": fig,
    }
