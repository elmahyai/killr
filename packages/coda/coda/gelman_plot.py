"""Gelman-Rubin shrink-factor plots for MCMC output.

Translated from coda 0.19-4.1 ``gelman.plot`` and ``gelman.preplot`` in ``R/gelman.R``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg", force=False)
import matplotlib.pyplot as plt
import numpy as np

from coda.as_mcmc_list import as_mcmc_list
from coda.gelman_diag import _window_mcmc_list, gelman_diag
from coda.niter import niter
from coda.nvar import nvar
from coda.plot_mfrow import draw_paginated
from coda.varnames import varnames


@dataclass
class GelmanPreplot:
    shrink: np.ndarray
    last_iter: np.ndarray


def gelman_plot(
    x,
    bin_width=10,
    max_bins=50,
    confidence=0.95,
    transform=False,
    autoburnin=True,
    auto_layout=True,
    ask=None,
    col=(1, 2),
    lty=(1, 2),
    xlab="last iteration in chain",
    ylab="shrink factor",
    type="l",
    **kwargs,
):
    """Plot Gelman-Rubin shrink factors along cumulative chain windows."""
    del ask, kwargs
    obj = as_mcmc_list(x)
    pre = gelman_preplot(
        obj,
        bin_width=bin_width,
        max_bins=max_bins,
        confidence=confidence,
        transform=transform,
        autoburnin=autoburnin,
    )
    names = varnames(obj)
    n_var = int(nvar(obj))
    colors = _recycle_colors(col, 2)
    linestyles = _recycle_lty(lty, 2)
    panels = []
    all_na = np.all(np.isnan(pre.shrink[:, :, 0]), axis=0)
    if not np.all(all_na):
        leg = ("median", f"{int(round(50 * (confidence + 1)))}%")
        for var_index in range(n_var):
            if all_na[var_index]:
                continue
            series = pre.shrink[:, var_index, :]
            panels.append(
                {
                    "x": np.asarray(pre.last_iter, dtype=np.float64),
                    "y": np.asarray(series, dtype=np.float64),
                    "title": None if names is None else str(names[var_index]),
                    "xlab": xlab,
                    "ylab": ylab,
                    "colors": colors,
                    "lty": linestyles,
                    "legend": leg,
                    "type": type,
                }
            )
    figures = []
    if panels:
        if auto_layout:
            figures = draw_paginated(panels, n_var, _draw_panel)
        else:
            figure, axes = plt.subplots(len(panels), 1, squeeze=False)
            for axis, panel in zip(axes[:, 0], panels):
                _draw_panel(axis, panel)
            figure.tight_layout()
            figures = [figure]
    return {"preplot": pre, "panels": panels, "figures": figures}


def gelman_preplot(
    x,
    bin_width=10,
    max_bins=50,
    confidence=0.95,
    transform=False,
    autoburnin=True,
):
    """Cumulative Gelman-Rubin diagnostics used by ``gelman_plot``."""
    del bin_width
    obj = as_mcmc_list(x)
    n_bin = min(int(math.floor((niter(obj) - 50) / float(obj.chains[0].thin))), int(max_bins))
    if n_bin < 1:
        raise ValueError("Insufficient iterations to produce Gelman-Rubin plot")
    binw = int(math.floor((niter(obj) - 50) / n_bin))
    thin = float(obj.chains[0].thin)
    start = float(obj.chains[0].start)
    last_iter = np.concatenate(
        [
            start + thin * (50 + binw * np.arange(n_bin, dtype=np.float64)),
            np.array([float(obj.chains[0].end)], dtype=np.float64),
        ]
    )
    n_var = int(nvar(obj))
    shrink = np.full((n_bin + 1, n_var, 2), np.nan, dtype=np.float64)
    xnames = varnames(obj, allow_null=True)
    for index in range(n_bin + 1):
        windowed = _window_mcmc_list(obj, end=float(last_iter[index]))
        diag = gelman_diag(
            windowed,
            confidence=confidence,
            transform=transform,
            autoburnin=autoburnin,
            multivariate=False,
        )
        shrink[index, :, :] = np.asarray(diag.psrf, dtype=np.float64)
    if xnames is not None:
        # dimnames only used for printing in R; keep array shape.
        pass
    all_na = np.all(np.isnan(shrink[:, :, 0]), axis=0)
    if np.any(all_na) and xnames is not None:
        missing = [xnames[index] for index in range(n_var) if all_na[index]]
        if missing:
            print("\n******* Error: *******\n")
            print("Cannot compute Gelman & Rubin's diagnostic for any chain")
            print("segments for variables", " ".join(missing))
            print("This indicates convergence failure\n")
    return GelmanPreplot(shrink=shrink, last_iter=last_iter)


def proof_values(result):
    """Flatten shrink factors, iteration grid, and panel titles."""
    pre = result["preplot"]
    values = []
    values.extend(float(item) for item in np.ravel(pre.shrink, order="F"))
    values.extend(float(item) for item in np.asarray(pre.last_iter, dtype=np.float64))
    for panel in result["panels"]:
        values.extend(float(item) for item in np.ravel(np.asarray(panel["y"], order="F"), order="F"))
        title = panel["title"]
        if title is None:
            values.append(0.0)
        else:
            values.extend(
                [-1.0, float(len(title)), *[float(ord(char)) for char in title]]
            )
    return values


def _draw_panel(axis, panel):
    x = np.asarray(panel["x"], dtype=np.float64)
    y = np.asarray(panel["y"], dtype=np.float64)
    for series_index in range(y.shape[1]):
        axis.plot(
            x,
            y[:, series_index],
            color=panel["colors"][series_index],
            linestyle=panel["lty"][series_index],
            linewidth=1.0,
        )
    axis.axhline(1.0, color="black", linewidth=0.8)
    ymax = float(np.nanmax(np.concatenate(([1.0], np.ravel(y)))))
    xmax = float(np.max(x))
    axis.legend(
        panel["legend"],
        loc="upper right",
        frameon=False,
        fontsize="small",
    )
    axis.set_xlim(float(np.min(x)), xmax)
    axis.set_ylim(0.0, ymax * 1.05 if ymax > 0 else 1.0)
    axis.set_xlabel(panel["xlab"])
    axis.set_ylabel(panel["ylab"])
    if panel["title"]:
        axis.set_title(panel["title"])


def _recycle_colors(values, count):
    palette = {
        1: "black",
        2: "red",
        3: "#00CD00",
        4: "blue",
        5: "cyan",
        6: "magenta",
    }
    items = list(np.atleast_1d(values))
    if not items:
        items = [1, 2]
    out = []
    for index in range(count):
        value = items[index % len(items)]
        if isinstance(value, (int, np.integer)):
            out.append(palette.get(int(value), "black"))
        else:
            out.append(value)
    return out


def _recycle_lty(values, count):
    mapping = {1: "solid", 2: "dashed", 3: "dotted", 4: "dashdot"}
    items = list(np.atleast_1d(values))
    if not items:
        items = [1, 2]
    out = []
    for index in range(count):
        value = items[index % len(items)]
        if isinstance(value, (int, np.integer)):
            out.append(mapping.get(int(value), "solid"))
        else:
            out.append(value)
    return out
