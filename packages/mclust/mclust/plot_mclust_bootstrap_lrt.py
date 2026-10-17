"""Translation of ``plot.mclustBootstrapLRT`` (mclust 6.1.3)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Sequence

import numpy as np

from ._plot_common import extendrange, hist_density, pretty

__all__ = ["plot_mclustBootstrapLRT"]


def _get(x: Any, name: str) -> Any:
    if isinstance(x, Mapping):
        return x[name]
    return getattr(x, name)


def _scott_breaks(values: np.ndarray) -> np.ndarray:
    """Return R's ``hist(..., breaks = "Scott")`` breaks."""
    n = values.size
    width = 3.5 * float(np.std(values, ddof=1)) * n ** (-1.0 / 3.0)
    if not np.isfinite(width) or width <= 0:
        return np.asarray(pretty(values, n=1), dtype=float)
    nclass = max(1, int(np.ceil((float(np.max(values)) - float(np.min(values))) / width)))
    return np.asarray(pretty(values, n=nclass), dtype=float)


def plot_data(
    x: Any,
    G: int | Sequence[int] = 1,
    breaks: str | Sequence[float] = "Scott",
) -> dict[str, Any]:
    """Compute the histogram and axis data used by the R method."""
    groups = np.asarray(_get(x, "G"), dtype=float).ravel()
    requested = np.asarray(G, dtype=float).ravel()
    if requested.size == 0 or not np.any(groups == requested[0]):
        raise ValueError(f"bootstrap LRT not available for G = {requested[0] if requested.size else G}")
    g = int(requested[0])
    boot = np.asarray(_get(x, "boot"), dtype=float)
    values = boot[:, g - 1] if boot.ndim > 1 else boot
    values = np.asarray(values, dtype=float).ravel()
    if isinstance(breaks, str):
        if breaks != "Scott":
            raise NotImplementedError("only R's breaks = 'Scott' is translated")
        edges = _scott_breaks(values)
    else:
        edges = np.asarray(breaks, dtype=float).ravel()
    hist = hist_density(values, edges)
    obs = float(np.asarray(_get(x, "obs"), dtype=float).ravel()[g - 1])
    raw_range = np.asarray(
        [*edges, *values, obs], dtype=float
    )
    xlim = tuple(float(v) for v in extendrange(raw_range, f=0.05))
    return {
        "G": g,
        "values": values,
        "breaks": hist["breaks"],
        "density": hist["density"],
        "obs": obs,
        "xlim": xlim,
        "ylim": (0.0, float(np.max(hist["density"]))),
    }


def plot_mclustBootstrapLRT(
    x: Any,
    G: int | Sequence[int] = 1,
    hist_col: str = "grey",
    hist_border: str = "lightgrey",
    breaks: str | Sequence[float] = "Scott",
    col: str = "forestgreen",
    lwd: float = 2,
    lty: int = 3,
    main: str | None = None,
    ax: Any = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Plot one bootstrap LRT distribution and its observed statistic.

    The returned mapping contains the numeric drawing data, which is useful
    for comparing the translation with R independently of rendered pixels.
    """
    if kwargs:
        raise NotImplementedError("plot parameters are not translated: " + ", ".join(sorted(kwargs)))
    d = plot_data(x, G=G, breaks=breaks)
    if ax is None:
        import matplotlib.pyplot as plt
        ax = plt.gca()
    ax.stairs(d["density"], d["breaks"], fill=True, color=hist_col, edgecolor=hist_border)
    ax.axvline(d["obs"], color=col, linewidth=lwd, linestyle=":")
    ax.set_xlim(*d["xlim"])
    ax.set_xlabel("LRTS")
    if main is None:
        model = _get(x, "modelName")
        main = f"Bootstrap LRT for model {model} with {d['G']} vs {d['G'] + 1} components"
    ax.set_title(main)
    return d
