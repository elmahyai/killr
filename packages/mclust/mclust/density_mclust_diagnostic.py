"""densityMclust.diagnostic: the CDF and QQ diagnostics of a one-dimensional densityMclust fit.

The drawing is logged the way proof/plot_mclust_record.R logs it: the empirical
CDF knots and heights (``E``), the window (``W``), the estimated CDF line
(``P``), the rug (``R``), the QQ points (``P`` and ``U``) and the QQ line
(``L``). Matplotlib draws the figure when an axes is given. The legend is layout,
so it is not logged. The values come from the object's fields only.
"""

from __future__ import annotations

import warnings
from typing import Any, Sequence

import numpy as np

from .cdf_mclust import cdfMclust
from .plot_log import PlotLog
from .quantile_mclust import quantileMclust

__all__ = ["densityMclust_diagnostic"]


def _field(obj: Any, name: str) -> Any:
    return obj[name] if isinstance(obj, dict) else getattr(obj, name)


def _ppoints(n: int) -> np.ndarray:
    """R's ppoints(n): (1:n - a) / (n + 1 - 2a) with a = 3/8 for n <= 10, else 1/2."""
    a = 3.0 / 8.0 if n <= 10 else 0.5
    return (np.arange(1, n + 1, dtype=float) - a) / (n + 1 - 2 * a)


def _match(choice: Sequence[str], allowed: Sequence[str]) -> list[str]:
    values = [choice] if isinstance(choice, str) else list(choice)
    bad = [v for v in values if v not in allowed]
    if bad:
        raise ValueError(f"'arg' should be one of {', '.join(map(repr, allowed))}")
    return [name for name in allowed if name in values]


def densityMclust_diagnostic(
    object: Any,
    type: Sequence[str] | str = ("cdf", "qq"),
    col: Sequence[str] = ("black", "black"),
    lwd: Sequence[float] = (2, 1),
    lty: Sequence[int] = (1, 1),
    legend: bool = True,
    grid: bool = True,
    *,
    ax: Any = None,
    log: PlotLog | None = None,
) -> None:
    """Draw the CDF and/or QQ diagnostic of a one-dimensional densityMclust fit.

    Returns None, as R's invisible(). For a multivariate fit R warns and draws
    nothing; this does the same.
    """
    del legend, grid, lwd, lty
    if log is None:
        log = PlotLog()
    d = int(np.asarray(_field(object, "d")).ravel()[0])
    if d > 1:
        warnings.warn("only available for one-dimensional data", stacklevel=2)
        return None

    kinds = _match(type, ("cdf", "qq"))
    data = np.asarray(_field(object, "data"), dtype=float).ravel()
    n = data.size
    sorted_data = np.sort(data)

    if "cdf" in kinds:
        cdf = cdfMclust(object, data=data, ngrid=min(n * 10, 1000))
        knots = np.unique(sorted_data)
        heights = np.searchsorted(sorted_data, knots, side="right") / n
        log.log.append(("E", [knots, heights]))
        log.window(ax, _stepfun_xlim(knots), (0.0, 1.0), xaxs="r", yaxs="r")
        if ax is not None:
            ax.step(knots, heights, where="post", color="black", linewidth=1)
        log.lines(ax, cdf["x"], cdf["y"], col=col[0], type="l")
        if ax is not None:
            ax.plot(data, np.zeros(n), linestyle="none", marker="|", color="black")
        log.log.append(("R", [data]))

    if "qq" in kinds:
        q = np.asarray(quantileMclust(object, p=_ppoints(n)), dtype=float).ravel()
        log.window(ax, _range(q), _range(sorted_data), xaxs="r", yaxs="r")
        log.points(ax, q, sorted_data, pch=1, col="black")
        q_y = np.quantile(sorted_data, [0.25, 0.75])
        q_x = np.asarray(quantileMclust(object, p=[0.25, 0.75]), dtype=float).ravel()
        b = (q_y[1] - q_y[0]) / (q_x[1] - q_x[0])
        a = q_y[0] - b * q_x[0]
        log.log.append(("L", [[a], [b]]))
        if ax is not None:
            ax.axline((0.0, a), slope=b, color=col[1], linestyle="--")
    return None


def _stepfun_xlim(knots: np.ndarray) -> tuple[float, float]:
    """plot.stepfun's default xlim: the knot range widened by max(8% of it, median gap)."""
    lo, hi = float(knots.min()), float(knots.max())
    if knots.size > 1:
        dr = max(0.08 * (hi - lo), float(np.median(np.diff(knots))))
    else:
        dr = abs(float(knots[0])) / 16.0
    return lo - dr, hi + dr


def _range(v: Any) -> tuple[float, float]:
    arr = np.asarray(v, dtype=float)
    return float(arr.min()), float(arr.max())
