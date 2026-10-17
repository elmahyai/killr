"""Residual plots for a Johansen VECM (``plotres``)."""

from __future__ import annotations

import math
import sys

import numpy as np
from scipy.stats import norm

from urca.johansen import CaJo


class PlotRes:
    """One figure per equation, and the series those figures draw."""

    def __init__(self, values, figures):
        self.values = values
        self.figures = figures


def plotres(x):
    """Plot VAR residuals and the autocorrelation of the concentrated residuals.

    The series in each top panel is ``Z0 - Z1 GAMMA' - ZK PI'``. The
    autocorrelation and partial autocorrelation are the columns of ``R0``.
    """
    if not isinstance(x, CaJo):
        raise ValueError("\nObject is not of class 'ca.jo' \n")
    resids = _var_residuals(x)
    concentrated = np.asarray(x.R0, dtype=float)
    equations = int(x.P)
    pieces = [np.ravel(resids, order="F")]
    figures = []
    for equation in range(equations):
        series = concentrated[:, equation]
        correlation = _acf(series)
        partial = _pacf(series)
        band = float(norm.ppf(0.975) / math.sqrt(series.size))
        acf_limit = _data_limit(np.concatenate([correlation, [-band, band]]))
        pacf_limit = _data_limit(np.concatenate([partial, [-band, band]]))
        pieces.append(correlation)
        pieces.append(partial)
        pieces.append(acf_limit)
        pieces.append(pacf_limit)
        pieces.append(np.array([band]))
        figures.append(
            _draw_equation(
                equation + 1,
                resids[:, equation],
                correlation,
                partial,
                acf_limit,
                pacf_limit,
                band,
            )
        )
        if sys.stdin.isatty() and sys.stdout.isatty():
            print("\nType <Return> to continue: ", end="", flush=True)
            sys.stdin.readline()
    return PlotRes(np.concatenate(pieces), figures)


def _var_residuals(x):
    level = np.asarray(x.Z0, dtype=float)
    lagged = np.asarray(x.Z1, dtype=float)
    levels = np.asarray(x.ZK, dtype=float)
    gamma = np.asarray(x.GAMMA, dtype=float)
    pi = np.asarray(x.PI, dtype=float)
    return level - lagged @ gamma.T - levels @ pi.T


def _lag_max(n_obs):
    if n_obs < 1:
        raise ValueError("'lag.max' must be at least 0")
    return int(min(n_obs - 1, math.floor(10.0 * math.log10(n_obs))))


def _acf(series):
    """``stats::acf`` correlation for one series, including lag 0."""
    values = np.asarray(series, dtype=float).reshape(-1)
    if np.any(np.isnan(values)):
        raise ValueError("missing values in the residual series")
    n_obs = values.size
    lag_max = _lag_max(n_obs)
    centered = values - values.mean()
    denominator = float(centered @ centered)
    out = np.empty(lag_max + 1, dtype=float)
    if denominator == 0.0:
        out.fill(np.nan)
        return out
    for lag in range(lag_max + 1):
        out[lag] = float(centered[lag:] @ centered[: n_obs - lag] / denominator)
    return out


def _pacf(series):
    """``stats::pacf`` for one series, Durbin-Levinson on the autocorrelation."""
    values = np.asarray(series, dtype=float).reshape(-1)
    centered = values - values.mean()
    correlation = _acf(centered)
    lag_max = correlation.size - 1
    if lag_max < 1:
        raise ValueError("'lag.max' must be at least 1")
    partial = np.empty(lag_max, dtype=float)
    coefficients = np.empty(lag_max, dtype=float)
    partial[0] = correlation[1]
    coefficients[0] = correlation[1]
    for order in range(1, lag_max):
        numerator = correlation[order + 1]
        denominator = 1.0
        for index in range(order):
            numerator -= coefficients[index] * correlation[order - index]
            denominator -= coefficients[index] * correlation[index + 1]
        partial[order] = numerator / denominator
        if order + 1 == lag_max:
            break
        previous = coefficients[:order].copy()
        for index in range(order):
            coefficients[index] = previous[index] - partial[order] * previous[order - 1 - index]
        coefficients[order] = partial[order]
    return partial


def _data_limit(values):
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    return np.array([float(np.min(finite)), float(np.max(finite))])


def _padded(limit):
    low, high = float(limit[0]), float(limit[1])
    pad = 0.04 * (high - low) if high != low else (0.04 if low == 0.0 else 0.04 * abs(low))
    return low - pad, high + pad


def _draw_equation(equation, residuals, correlation, partial, acf_limit, pacf_limit, band):
    import matplotlib

    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt

    figure = plt.figure(figsize=(7, 7))
    grid = figure.add_gridspec(2, 2)
    residual_axis = figure.add_subplot(grid[0, :])
    acf_axis = figure.add_subplot(grid[1, 0])
    pacf_axis = figure.add_subplot(grid[1, 1])
    time = np.arange(1, residuals.size + 1, dtype=float)
    residual_axis.plot(time, residuals, color="black", linewidth=1)
    residual_axis.axhline(0.0, color="red", linewidth=1)
    residual_axis.set_xlim(*_padded(np.array([time[0], time[-1]])))
    residual_axis.set_ylim(*_padded(_data_limit(residuals)))
    residual_axis.set_title(f"Residuals of {equation}. VAR regression")
    residual_axis.set_xlabel("")
    residual_axis.set_ylabel("")
    _stem(acf_axis, np.arange(correlation.size, dtype=float), correlation, acf_limit, band)
    acf_axis.set_title("Autocorrelations of Residuals")
    acf_axis.set_xlabel("Lag")
    acf_axis.set_ylabel("ACF")
    _stem(pacf_axis, np.arange(1, partial.size + 1, dtype=float), partial, pacf_limit, band)
    pacf_axis.set_title("Partial Autocorrelations of Residuals")
    pacf_axis.set_xlabel("Lag")
    pacf_axis.set_ylabel("Partial ACF")
    figure.tight_layout()
    return figure


def _stem(axis, lags, values, limit, band):
    axis.vlines(lags, 0.0, values, colors="black", linewidth=1)
    axis.axhline(0.0, color="black", linewidth=1)
    axis.axhline(band, color="blue", linestyle="--", linewidth=1)
    axis.axhline(-band, color="blue", linestyle="--", linewidth=1)
    axis.set_xlim(*_padded(np.array([lags[0], lags[-1]])))
    axis.set_ylim(*_padded(limit))
