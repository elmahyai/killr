"""Autocorrelation plots for MCMC chains.

Translated from coda 0.19-4.1 ``autocorr.plot`` in ``R/output.R``.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg", force=False)
import matplotlib.pyplot as plt
import numpy as np

from coda.acfplot import _acf_vector, _matrix_mcmc
from coda.as_mcmc_list import is_mcmc_list
from coda.chanames import chanames
from coda.mcmc_list import mcmc_list
from coda.nchain import nchain
from coda.nvar import nvar
from coda.plot_mfrow import draw_paginated
from coda.varnames import varnames


def autocorr_plot(x, lag_max=None, auto_layout=True, ask=None, **kwargs):
    """Plot autocorrelations for each chain and variable in ``x``."""
    del ask
    obj = mcmc_list(x) if not is_mcmc_list(x) else x
    panels = []
    names = varnames(obj)
    chains = chanames(obj)
    n_var = int(nvar(obj))
    for chain_index, chain in enumerate(obj.chains):
        matrix = _matrix_mcmc(chain)
        resolved = _resolve_lag_max(matrix.shape[0], n_var, lag_max)
        for var_index in range(n_var):
            acf = _acf_vector(matrix[:, var_index], resolved)
            lags = np.arange(acf.size, dtype=np.float64)
            title = _panel_title(names, chains, chain_index, var_index)
            panels.append(
                {
                    "lag": lags,
                    "acf": acf,
                    "title": title,
                    "xlab": kwargs.get("xlab", "Lag"),
                    "ylab": kwargs.get("ylab", "Autocorrelation"),
                    "ylim": (-1.0, 1.0),
                }
            )
    figures = []
    if auto_layout:
        figures = draw_paginated(panels, n_var, _draw_panel)
    else:
        figure, axes = plt.subplots(
            max(len(panels), 1),
            1,
            figsize=(4.5, 2.5 * max(len(panels), 1)),
            squeeze=False,
        )
        for axis, panel in zip(axes[:, 0], panels):
            _draw_panel(axis, panel)
        figure.tight_layout()
        figures = [figure]
    return {"panels": panels, "figures": figures, "input": obj}


def proof_values(result):
    """Flatten lags, ACF values, y limits, and titles for checks against R."""
    values = []
    for panel in result["panels"]:
        values.extend(float(item) for item in panel["ylim"])
        values.extend(float(item) for item in np.asarray(panel["lag"], dtype=np.float64))
        values.extend(float(item) for item in np.asarray(panel["acf"], dtype=np.float64))
        values.extend(_encode_title(panel["title"]))
    return values


def _resolve_lag_max(nobs, nvar, lag_max):
    if lag_max is not None:
        return int(lag_max)
    if nvar < 1:
        nvar = 1
    candidate = int(np.floor(10.0 * np.log10(float(nobs) / float(nvar))))
    return int(min(candidate, nobs - 1))


def _panel_title(names, chain_names, chain_index, var_index):
    var_name = None if names is None else names[var_index]
    if chain_names is None:
        return "" if var_name is None else str(var_name)
    chain_name = chain_names[chain_index]
    if var_name is None:
        return f":{chain_name}"
    return f"{var_name}:{chain_name}"


def _encode_title(title):
    if not title:
        return [0.0]
    text = str(title)
    return [-1.0, float(len(text)), *[float(ord(char)) for char in text]]


def _draw_panel(axis, panel):
    lags = np.asarray(panel["lag"], dtype=np.float64)
    acf = np.asarray(panel["acf"], dtype=np.float64)
    axis.set_ylim(panel["ylim"])
    axis.vlines(lags, 0.0, acf, colors="black", linewidth=1.0)
    axis.set_xlabel(panel["xlab"])
    axis.set_ylabel(panel["ylab"])
    if panel["title"]:
        axis.set_title(panel["title"])
