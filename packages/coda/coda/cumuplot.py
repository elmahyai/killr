"""Cumulative quantile plot for MCMC output.

Translated from coda 0.19-4.1 ``cumuplot`` in ``R/cumuplot.R``.
Each panel is the running type-7 sample quantiles. Matplotlib draws the lines.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg", force=False)

import matplotlib.pyplot as plt
import numpy as np

from coda.as_mcmc import as_mcmc, is_mcmc
from coda.as_mcmc_list import is_mcmc_list
from coda.chanames import chanames
from coda.mcmc_list import mcmc_list
from coda.nchain import nchain
from coda.niter import niter
from coda.varnames import varnames

# set.mfrow with one plot per variable. The index is min(Nparms, 13).
_MFROW_ONE = {
    1: (1, 1),
    2: (1, 2),
    3: (2, 2),
    4: (2, 2),
    5: (3, 2),
    6: (3, 2),
    7: (3, 3),
    8: (3, 3),
    9: (3, 3),
    10: (3, 2),
    11: (3, 2),
    12: (3, 2),
    13: (3, 3),
}

_LTY = {
    1: "solid",
    2: "dashed",
    3: "dotted",
    4: "dashdot",
    5: (0, (8, 3)),
    6: (0, (4, 2, 1, 2)),
}

# R palette indexes used when ``col`` is numeric.
_PALETTE = {
    1: "black",
    2: "red",
    3: "#00CD00",
    4: "blue",
    5: "cyan",
    6: "magenta",
    7: "yellow",
    8: "gray",
}


class CumuplotResult:
    """Iterations, one cumulative-quantile panel per chain and variable, and the figures."""

    def __init__(self, iterations, panels, figures):
        self.iterations = np.asarray(iterations, dtype=np.float64)
        self.panels = panels
        self.figures = figures


def cumuplot(
    x,
    probs=(0.025, 0.5, 0.975),
    ylab="",
    lty=(2, 1),
    lwd=(1, 2),
    type="l",
    ask=None,
    auto_layout=True,
    col=1,
    **kwargs,
):
    """Plot running sample quantiles against iteration number.

    ``x`` is an ``Mcmc``, an ``McmcList``, or a numeric vector or matrix that
    ``as.mcmc`` accepts. A single chain is wrapped as a one-element list.
    The page grid follows the variable count, the same rule as ``set.mfrow``
    when each variable has one plot. Chain names are joined to variable names
    with a colon. ``ask`` is accepted and does not prompt.
    """
    del ask
    probabilities = np.asarray(probs, dtype=np.float64).reshape(-1)
    _check_probs(probabilities)

    if auto_layout:
        shape = _mfrow_one(_nvar(x))
    else:
        shape = (1, 1)

    if not is_mcmc_list(x):
        x = mcmc_list(as_mcmc(x))

    iterations = _iterations(x.chains[0])
    names = varnames(x)
    chains = chanames(x)
    panels = []
    for chain_index, chain in enumerate(x.chains):
        matrix = _matrix(chain)
        for var_index in range(matrix.shape[1]):
            series = matrix[:, var_index]
            quantiles = _cumulative_type7(series, probabilities)
            var_name = None if names is None else names[var_index]
            panels.append(
                {
                    "title": _panel_title(var_name, chains, chain_index),
                    "y": quantiles,
                    "iterations": iterations,
                    "ylab": ylab,
                    "xlab": kwargs.get("xlab", "Iterations"),
                    "lty": lty,
                    "lwd": lwd,
                    "type": type,
                    "col": col,
                    "xlim": kwargs.get("xlim"),
                    "ylim": kwargs.get("ylim"),
                }
            )

    figures = _draw_pages(panels, shape)
    return CumuplotResult(iterations, panels, figures)


def proof_values(result):
    """Iteration numbers, then each panel in column-major order."""
    values = [float(item) for item in np.asarray(result.iterations, dtype=np.float64)]
    for panel in result.panels:
        flat = np.ravel(np.asarray(panel["y"], dtype=np.float64), order="F")
        values.extend(float(item) for item in flat)
    return values


def _nvar(x):
    if is_mcmc(x):
        data = np.asarray(x.data)
        if data.ndim >= 2:
            return int(data.shape[1])
        return 1
    if is_mcmc_list(x):
        return _nvar(x.chains[0])
    return None


def _mfrow_one(nparms):
    """Rows and columns from ``set.mfrow`` with one plot per variable.

    ``min(NULL, 13)`` is 13, so a value that is not an MCMC object uses a 3 by 3 page.
    """
    if nparms is None:
        key = 13
    else:
        key = min(int(nparms), 13)
        if key < 1:
            key = 13
    return _MFROW_ONE[key]


def _iterations(chain):
    count = niter(chain)
    start = float(chain.start)
    step = float(chain.thin)
    return start + step * np.arange(count, dtype=np.float64)


def _matrix(chain):
    data = np.asarray(chain.data, dtype=np.float64)
    if data.ndim == 1:
        return data.reshape(-1, 1)
    return data


def _panel_title(var_name, chain_names, chain_index):
    """Match ``paste(var, ifelse(is.null(chanames), "", ":"), chain, sep="")``."""
    if chain_names is None:
        if var_name is None:
            return ""
        return str(var_name)
    chain_name = chain_names[chain_index]
    if var_name is None:
        return f":{chain_name}"
    return f"{var_name}:{chain_name}"


def _check_probs(probs):
    if probs.size == 0:
        return
    if np.isnan(probs).any():
        raise ValueError("missing values and NaN's not allowed if 'na.rm' is FALSE")
    eps = 100 * np.finfo(np.float64).eps
    if np.any((probs < -eps) | (probs > 1.0 + eps)):
        raise ValueError("'probs' outside [0,1]")


def _cumulative_type7(series, probs):
    """Running ``quantile(..., type = 7, names = FALSE)`` on each prefix."""
    values = np.asarray(series, dtype=np.float64).reshape(-1)
    n = values.size
    k = probs.size
    out = np.empty((n, k), dtype=np.float64)
    if n == 0 or k == 0:
        return out.reshape(n, k)
    if np.isnan(values).any():
        raise ValueError("missing values and NaN's not allowed if 'na.rm' is FALSE")

    ordered = np.empty(n, dtype=np.float64)
    for length in range(1, n + 1):
        incoming = values[length - 1]
        if length == 1:
            ordered[0] = incoming
        else:
            pos = int(np.searchsorted(ordered[: length - 1], incoming, side="left"))
            if pos < length - 1:
                ordered[pos + 1 : length] = ordered[pos : length - 1].copy()
            ordered[pos] = incoming
        index = 1.0 + (length - 1) * probs
        lo = np.floor(index)
        left = ordered[lo.astype(np.intp) - 1]
        move = index > lo
        if np.any(move):
            hi = np.ceil(index).astype(np.intp)
            h = index - lo
            right = ordered[hi - 1]
            left = np.where(move, (1.0 - h) * left + h * right, left)
        out[length - 1, :] = left
    return out


def _draw_pages(panels, shape):
    nrows, ncols = shape
    slots = nrows * ncols
    figures = []
    if not panels:
        return figures
    for start in range(0, len(panels), slots):
        chunk = panels[start : start + slots]
        figure, axes = plt.subplots(nrows, ncols, figsize=(7, 5), squeeze=False)
        flat = axes.ravel()
        for axis in flat:
            axis.set_visible(False)
        for axis, panel in zip(flat, chunk):
            axis.set_visible(True)
            _draw_panel(axis, panel)
        figure.subplots_adjust(
            left=0.08, right=0.98, bottom=0.12, top=0.88, wspace=0.35, hspace=0.45
        )
        figures.append(figure)
    return figures


def _draw_panel(axis, panel):
    iterations = np.asarray(panel["iterations"], dtype=np.float64)
    quantiles = np.asarray(panel["y"], dtype=np.float64)
    k = quantiles.shape[1] if quantiles.ndim == 2 else 0
    styles = _recycle(panel["lty"], k)
    widths = _recycle(panel["lwd"], k)
    colors = _recycle(panel["col"], k)
    kinds = _recycle_type(panel["type"], k)
    for column in range(k):
        _draw_series(
            axis,
            iterations,
            quantiles[:, column],
            kind=kinds[column],
            linestyle=_linestyle(styles[column]),
            linewidth=float(widths[column]),
            color=_color(colors[column]),
        )
    axis.set_xlabel(panel["xlab"])
    axis.set_ylabel(panel["ylab"])
    axis.set_title(panel["title"])
    if panel["xlim"] is not None:
        axis.set_xlim(panel["xlim"])
    if panel["ylim"] is not None:
        axis.set_ylim(panel["ylim"])


def _draw_series(axis, x, y, *, kind, linestyle, linewidth, color):
    if kind == "n" or x.size == 0:
        return
    if kind == "p":
        axis.plot(
            x, y, linestyle="none", marker="o", markersize=3,
            color=color, linewidth=linewidth,
        )
        return
    if kind == "h":
        axis.vlines(x, 0.0, y, colors=color, linewidth=linewidth)
        return
    if kind in ("s", "S"):
        axis.step(x, y, where="pre" if kind == "S" else "post", color=color, linewidth=linewidth)
        return
    line = axis.plot(x, y, linestyle=linestyle, linewidth=linewidth, color=color)
    if kind in ("b", "o"):
        axis.plot(
            x, y, linestyle="none", marker="o", markersize=3,
            color=color, linewidth=linewidth,
        )
    del line


def _recycle(values, k):
    if k == 0:
        return []
    array = np.atleast_1d(np.asarray(values, dtype=object))
    if array.size == 1 and not isinstance(values, (list, tuple, np.ndarray)):
        return [values] * k
    if isinstance(values, (int, float, np.integer, np.floating, str)):
        return [values] * k
    flat = list(np.ravel(np.asarray(values, dtype=object)))
    if not flat:
        return [1] * k
    return [flat[index % len(flat)] for index in range(k)]


def _recycle_type(type_spec, k):
    text = str(type_spec)
    if not text:
        text = "l"
    chars = list(text)
    return [chars[index % len(chars)] for index in range(k)]


def _linestyle(value):
    if isinstance(value, str):
        return value
    return _LTY.get(int(value), "solid")


def _color(value):
    if isinstance(value, str):
        return value
    if isinstance(value, (int, np.integer)):
        return _PALETTE.get(int(value), "black")
    return value
