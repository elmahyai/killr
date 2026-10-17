"""Cross-correlation matrix plot for MCMC output.

Translated from coda 0.19-4.1 ``crosscorr.plot`` in ``R/output.R``.
"""

from __future__ import annotations

import colorsys

import matplotlib

matplotlib.use("Agg", force=False)
import matplotlib.pyplot as plt
import numpy as np

from coda.as_mcmc import is_mcmc
from coda.as_mcmc_list import is_mcmc_list
from coda.crosscorr import crosscorr
from coda.nvar import nvar
from coda.varnames import varnames


def crosscorr_plot(x, col=None, **kwargs):
    """Heatmap-style plot of ``crosscorr`` values."""
    if not (is_mcmc(x) or is_mcmc_list(x)):
        raise TypeError("crosscorr.plot expects an mcmc or mcmc.list object")
    n_var = int(nvar(x))
    palette = _topo_colors(10 if col is None else len(np.atleast_1d(col)))
    if col is not None:
        palette = [_color(item, palette) for item in np.atleast_1d(col)]
    pcorr = np.asarray(crosscorr(x), dtype=np.float64)
    dens = _dens_indices(pcorr, len(palette))
    labels = _abbreviate_labels(varnames(x, allow_null=False))
    figure, axis = plt.subplots(figsize=(6, 6))
    axis.set_xlim(0, n_var)
    axis.set_ylim(0, n_var)
    axis.set_aspect("equal")
    axis.set_xlabel(kwargs.get("xlab", ""))
    axis.set_ylabel(kwargs.get("ylab", ""))
    axis.set_xticks(np.arange(n_var) + 0.5)
    axis.set_yticks(np.arange(n_var) + 0.5)
    axis.set_xticklabels(labels)
    axis.set_yticklabels(list(reversed(labels)))
    for cl in range(1, n_var + 1):
        for rw in range(1, n_var - cl + 2):
            row = n_var - cl
            col_index = rw - 1
            color_index = dens[row, col_index]
            if color_index is None or np.isnan(color_index):
                continue
            xs = [rw - 1, rw, rw, rw - 1, rw - 1]
            ys = [cl - 1, cl - 1, cl, cl, cl - 1]
            axis.fill(xs, ys, color=palette[int(color_index) - 1], linewidth=0)
    _draw_legend(axis, n_var, palette)
    figure.tight_layout()
    return {
        "pcorr": pcorr,
        "dens": dens,
        "labels": labels,
        "palette": palette,
        "figure": figure,
    }


def proof_values(result):
    """Correlation matrix, color bins, and abbreviated axis labels."""
    values = []
    values.extend(float(item) for item in np.ravel(result["pcorr"], order="F"))
    for row in result["dens"]:
        for item in row:
            if item is None or (isinstance(item, float) and np.isnan(item)):
                values.append(0.0)
            else:
                values.append(float(item))
    for label in result["labels"]:
        values.extend(_encode_title(label))
    return values


def _dens_indices(pcorr, ncolors):
    out = np.empty(pcorr.shape, dtype=object)
    for row in range(pcorr.shape[0]):
        for col in range(pcorr.shape[1]):
            value = pcorr[row, col]
            if np.isnan(value):
                out[row, col] = np.nan
            else:
                index = int(((value + 1.0) * ncolors) // 2) + int(value < 1.0) + int(value < -1.0)
                out[row, col] = index
    return out


def _topo_colors(n):
    hues = np.linspace(0.2, 0.6, n)
    saturation = np.linspace(0.6, 0.0, n)
    return [colorsys.hsv_to_rgb(float(h), float(s), 1.0) for h, s in zip(hues, saturation)]


def _color(value, palette):
    if isinstance(value, (int, np.integer)):
        index = int(value)
        if index <= 0:
            return "#00000000"
        return palette[(index - 1) % len(palette)]
    return value


def _abbreviate_labels(names):
    return [_abbreviate(name, 7) for name in names]


def _abbreviate(text, minlength):
    text = str(text)
    if len(text) <= minlength:
        return text
    if minlength <= 1:
        return text[:1]
    return text[: minlength - 1] + "."


def _draw_legend(axis, n_var, palette):
    ncolors = len(palette)
    yval = np.linspace(n_var / 2.0, float(n_var), ncolors + 1)
    ydelta = n_var / (2.0 * (ncolors + 1))
    x_left = n_var - ydelta
    for index, color in enumerate(palette):
        ys = [yval[index], yval[index + 1], yval[index + 1], yval[index], yval[index]]
        xs = [x_left, x_left, n_var, n_var, x_left]
        axis.fill(xs, ys, color=color, linewidth=0)
    axis.text(x_left, n_var, "1", ha="right", va="top")
    axis.text(x_left, 0.5 * n_var, "-1", ha="right", va="bottom")
    axis.text(x_left, 0.75 * n_var, "0", ha="right", va="center")


def _encode_title(title):
    text = str(title)
    if not text:
        return [0.0]
    return [-1.0, float(len(text)), *[float(ord(char)) for char in text]]
