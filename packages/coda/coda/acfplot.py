"""Autocorrelation plots for MCMC output.

Translated from coda 0.19-4.1 ``acfplot`` in ``R/trellisplots.R``.
Matplotlib draws the figure; lattice is replaced per project routing.
"""

from __future__ import annotations

import warnings

import matplotlib.pyplot as plt
import numpy as np

from coda.as_mcmc import is_mcmc
from coda.as_mcmc_list import _varnames_mcmc, is_mcmc_list


def acfplot(
    x,
    data=None,
    *,
    outer=None,
    groups=None,
    start=1,
    thin=1,
    lag_max=None,
    xlab="Lag",
    ylab="Autocorrelation",
    main=None,
    draw=True,
    **kwargs,
):
    """Plot autocorrelations for an ``Mcmc`` or ``McmcList`` object."""
    del data, kwargs
    if is_mcmc(x):
        if outer is not None:
            warnings.warn("specification of outer ignored", stacklevel=2)
        result = _acfplot_mcmc(
            x,
            start=start,
            thin=thin,
            lag_max=lag_max,
            xlab=xlab,
            ylab=ylab,
            main=main,
        )
    elif is_mcmc_list(x):
        result = _acfplot_mcmc_list(
            x,
            outer=False if outer is None else outer,
            groups=not outer if groups is None else groups,
            start=start,
            thin=thin,
            lag_max=lag_max,
            xlab=xlab,
            ylab=ylab,
            main=main,
        )
    else:
        raise TypeError("acfplot expects an mcmc or mcmc.list object")

    if draw:
        _draw(result)
    return result


def _acfplot_mcmc(chain, *, start, thin, lag_max, xlab, ylab, main):
    subset = _thinned_indices(chain, start=start, thin=thin)
    matrix = _matrix_mcmc(chain)[subset, :]
    varnames = _varnames_mcmc(chain, allow_null=False)
    series = _acf_columns(matrix, lag_max=lag_max, labels=varnames)
    panels = []
    for item in series:
        panels.append(
            {
                "name": item["name"],
                "ylim": _ylim_from_series([item], grouped=False),
                "series": [item],
            }
        )
    title = main if main is not None else getattr(chain, "title", None)
    return {
        "kind": "mcmc",
        "xlab": xlab,
        "ylab": ylab,
        "main": title,
        "panels": panels,
        "plot_type": "h",
    }


def _acfplot_mcmc_list(obj, *, outer, groups, start, thin, lag_max, xlab, ylab, main):
    if groups and outer:
        warnings.warn("'groups=TRUE' ignored when 'outer=TRUE'", stacklevel=3)
        groups = False

    subset = _thinned_indices(obj.chains[0], start=start, thin=thin)
    varnames = _varnames_mcmc(obj.chains[0], allow_null=False)

    if groups or outer:
        per_chain = []
        for chain in obj.chains:
            matrix = _matrix_mcmc(chain)[subset, :]
            per_chain.append(_acf_columns(matrix, lag_max=lag_max, labels=varnames))
        panels = []
        for var_index, name in enumerate(varnames):
            chain_series = []
            for run, chain_acf in enumerate(per_chain, start=1):
                item = chain_acf[var_index]
                chain_series.append(
                    {
                        "name": name,
                        "run": run,
                        "lag": item["lag"],
                        "acf": item["acf"],
                    }
                )
            ylim = _ylim_from_series(chain_series, grouped=True)
            panels.append({"name": name, "ylim": ylim, "series": chain_series})
        plot_type = "b" if groups else "h"
    else:
        stacked = np.vstack([_matrix_mcmc(chain)[subset, :] for chain in obj.chains])
        series = _acf_columns(stacked, lag_max=lag_max, labels=varnames)
        panels = []
        for item in series:
            panels.append(
                {
                    "name": item["name"],
                    "ylim": _ylim_from_series([item], grouped=False),
                    "series": [item],
                }
            )
        plot_type = "h"

    title = main if main is not None else getattr(obj, "title", None)
    return {
        "kind": "mcmc.list",
        "outer": outer,
        "groups": groups,
        "xlab": xlab,
        "ylab": ylab,
        "main": title,
        "panels": panels,
        "plot_type": plot_type,
    }


def _draw(result):
    panels = result["panels"]
    nvar = len(panels)
    fig, axes = plt.subplots(nvar, 1, figsize=(4.5, 2.5 * nvar), squeeze=False)
    if result.get("main"):
        fig.suptitle(result["main"])
    plot_type = result.get("plot_type", "h")
    for index, panel in enumerate(panels):
        ax = axes[index, 0]
        y0, y1 = panel["ylim"]
        if not np.isfinite(y0) or not np.isfinite(y1):
            y0, y1 = -1.0, 1.0
        ax.set_ylim(y0, y1)
        ax.axhline(0.0, color="gray", linewidth=0.8, linestyle="dashed", zorder=0)
        for series in panel["series"]:
            lags = np.asarray(series["lag"], dtype=np.float64)
            acf = np.asarray(series["acf"], dtype=np.float64)
            label = None
            if "run" in series:
                label = f"run{series['run']}"
            if plot_type == "h":
                ax.vlines(lags, 0.0, acf, colors="black", linewidth=1.0)
            else:
                ax.plot(lags, acf, marker="o", markersize=3, linewidth=1.0, label=label)
        if plot_type == "b" and len(panel["series"]) > 1:
            ax.legend(loc="best", fontsize="small")
        if index == nvar - 1:
            ax.set_xlabel(result["xlab"])
        ax.set_ylabel(result["ylab"])
        if nvar > 1:
            ax.set_title(panel["name"])
    fig.tight_layout()
    return fig


def proof_values(result):
    """Flatten panel limits and ACF values for checks against R."""
    values = []
    for panel in result["panels"]:
        values.extend(float(x) for x in panel["ylim"])
        for series in panel["series"]:
            values.extend(float(x) for x in series["acf"])
    return values


def _acf_columns(matrix, *, lag_max, labels):
    nvar = matrix.shape[1]
    resolved_lag = _default_lag_max(matrix.shape[0]) if lag_max is None else int(lag_max)
    out = []
    for index in range(nvar):
        acf = _acf_vector(matrix[:, index], resolved_lag)
        out.append(
            {
                "name": labels[index],
                "lag": list(range(len(acf))),
                "acf": [float(value) for value in acf],
            }
        )
    return out


def _acf_vector(series, lag_max):
    series = np.asarray(series, dtype=np.float64).reshape(-1)
    centered = series - series.mean()
    denom = float(centered @ centered)
    nobs = centered.size
    values = np.empty(lag_max + 1, dtype=np.float64)
    if denom == 0.0:
        values.fill(np.nan)
        return values
    for lag in range(lag_max + 1):
        values[lag] = float(centered[lag:] @ centered[: nobs - lag] / denom)
    return values


def _default_lag_max(nobs):
    return int(min(float(nobs) - 1.0, 10.0 * np.log10(float(nobs))))


def _ylim_from_series(series, *, grouped):
    peaks = []
    for item in series:
        tail = np.asarray(item["acf"], dtype=np.float64)[1:]
        if not tail.size:
            continue
        finite = tail[np.isfinite(tail)]
        if finite.size:
            peaks.append(float(np.max(np.abs(finite))))
        else:
            peaks.append(float("-inf"))
    if not peaks:
        peak = 0.0
    elif grouped:
        peak = max(peaks)
    else:
        peak = peaks[0]
    if peak == float("-inf"):
        return [float("inf"), float("-inf")]
    return [-peak, peak]


def _thinned_indices(chain, *, start, thin):
    n = _nrow_mcmc(chain)
    if is_mcmc(chain) and start * thin != 1 and not np.all(np.asarray(chain.mcpar, dtype=np.float64)[[0, 2]] == 1):
        warnings.warn("mcmc object is already thinned", stacklevel=4)
    if start < 1:
        raise ValueError("Invalid start")
    if thin < 1:
        raise ValueError("Invalid thin")
    if start == 1:
        if thin == 1:
            return slice(None)
        pattern = np.zeros(n, dtype=bool)
        pattern[0::thin] = True
        return pattern
    if thin == 1:
        return np.arange(start - 1, n)
    count = int(np.floor(n - start) / thin) + 1
    return start - 1 + thin * np.arange(count)


def _matrix_mcmc(chain):
    data = np.asarray(chain.data, dtype=np.float64)
    if data.ndim == 1:
        return data.reshape(-1, 1)
    return data


def _nrow_mcmc(chain):
    data = np.asarray(chain.data)
    if data.ndim >= 2:
        return int(data.shape[0])
    return int(data.size)
