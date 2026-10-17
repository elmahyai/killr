"""Geweke diagnostic plots for MCMC output.

Translated from coda 0.19-4.1 ``geweke.plot`` in ``R/geweke.R``.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg", force=False)
import matplotlib.pyplot as plt
import numpy as np

from coda.as_mcmc_list import as_mcmc_list
from coda.chanames import chanames
from coda.gelman_diag import _window_mcmc_list
from coda.geweke_diag import geweke_diag
from coda.nchain import nchain
from coda.raftery_diag import _qnorm
from coda.nvar import nvar
from coda.plot_mfrow import draw_paginated
from coda.varnames import varnames


def geweke_plot(
    x,
    frac1=0.1,
    frac2=0.5,
    nbins=20,
    pvalue=0.05,
    auto_layout=True,
    ask=None,
    **kwargs,
):
    """Plot Geweke Z-scores over sliding chain windows."""
    del ask
    obj = as_mcmc_list(x)
    chain_start = float(obj.chains[0].start)
    chain_end = float(obj.chains[0].end)
    ystart = np.linspace(chain_start, (chain_start + chain_end) / 2.0, int(nbins))
    n_var = int(nvar(obj))
    n_chains = int(nchain(obj))
    names = varnames(obj, allow_null=False)
    chains = chanames(obj, allow_null=False)
    gcd = np.full((ystart.size, n_var, n_chains), np.nan, dtype=np.float64)
    for index, start in enumerate(ystart):
        windowed = _window_mcmc_list(obj, start=float(start))
        diag = geweke_diag(windowed, frac1=frac1, frac2=frac2)
        for chain_index, item in enumerate(diag):
            gcd[index, :, chain_index] = np.asarray(item.z, dtype=np.float64).reshape(-1)
    climit = float(_qnorm(1.0 - pvalue / 2.0))
    panels = []
    for chain_index in range(n_chains):
        for var_index in range(n_var):
            zscores = gcd[:, var_index, chain_index]
            ylimit = float(max(climit, np.nanmax(np.abs(zscores))))
            if n_chains > 1:
                title = f"{names[var_index]} ({chains[chain_index]})"
            else:
                title = str(names[var_index])
            panels.append(
                {
                    "x": ystart,
                    "y": zscores,
                    "title": title,
                    "xlab": kwargs.get("xlab", "First iteration in segment"),
                    "ylab": kwargs.get("ylab", "Z-score"),
                    "ylim": (-ylimit, ylimit),
                    "climit": climit,
                }
            )
    figures = []
    if auto_layout:
        figures = draw_paginated(panels, n_var, _draw_panel)
    else:
        figure, axes = plt.subplots(len(panels), 1, squeeze=False)
        for axis, panel in zip(axes[:, 0], panels):
            _draw_panel(axis, panel)
        figure.tight_layout()
        figures = [figure]
    return {"start_iter": ystart, "z": gcd, "panels": panels, "figures": figures}


def proof_values(result):
    """Flatten Z-scores, window starts, limits, and titles."""
    values = []
    values.extend(float(item) for item in np.ravel(result["z"], order="F"))
    values.extend(float(item) for item in np.asarray(result["start_iter"], dtype=np.float64))
    for panel in result["panels"]:
        values.extend(float(item) for item in panel["ylim"])
        values.extend(float(item) for item in np.asarray(panel["y"], dtype=np.float64))
        title = panel["title"]
        values.extend(
            [-1.0, float(len(title)), *[float(ord(char)) for char in title]]
        )
    return values


def _draw_panel(axis, panel):
    x = np.asarray(panel["x"], dtype=np.float64)
    y = np.asarray(panel["y"], dtype=np.float64)
    axis.plot(x, y, linestyle="none", marker="x", markersize=5, color="black")
    climit = panel["climit"]
    axis.axhline(climit, color="black", linewidth=0.8, linestyle="dashed")
    axis.axhline(-climit, color="black", linewidth=0.8, linestyle="dashed")
    axis.set_ylim(panel["ylim"])
    axis.set_xlabel(panel["xlab"])
    axis.set_ylabel(panel["ylab"])
    axis.set_title(panel["title"])
