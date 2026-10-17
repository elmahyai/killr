"""Hurst exponent estimates."""

from __future__ import annotations

import math

import numpy as np

from pracma.arrays import std
from pracma.num_helpers import lm_slope, polyfit, require_numeric, sample_sd


def _half(nodes):
    nodes = np.asarray(nodes, dtype=int)
    mids = nodes[:-1] + ((np.diff(nodes) + 1) // 2)
    return np.sort(np.concatenate([nodes, mids]))


def _rscalc(values):
    series = np.asarray(values, dtype=float).reshape(-1)
    centered = np.cumsum(series - np.mean(series))
    return (float(np.max(centered) - np.min(centered))) / sample_sd(series)


def _hurstrs(values):
    series = np.asarray(values, dtype=float).reshape(-1)
    abscissa = [float(series.size)]
    ordinate = [_rscalc(series)]
    nodes = np.array([0, series.size // 2, series.size], dtype=int)
    while np.min(np.diff(nodes)) >= 8:
        lengths = []
        ratios = []
        for index in range(1, nodes.size):
            piece = series[nodes[index - 1]:nodes[index]]
            lengths.append(nodes[index] - nodes[index - 1])
            ratios.append(_rscalc(piece))
        abscissa.append(float(np.mean(lengths)))
        ordinate.append(float(np.mean(ratios)))
        nodes = _half(nodes)
    return lm_slope(np.log(abscissa), np.log(ordinate))


def _divisors(n, n0):
    candidates = np.arange(n0, math.floor(n / 2) + 1)
    return candidates[n % candidates == 0]


def hurstexp(x, d=50, display=True):
    require_numeric(x, "x")
    require_numeric(d, "d")
    series = np.asarray(x, dtype=float).reshape(-1)
    dmin = max(2, math.floor(float(np.asarray(d).reshape(-1)[0])))
    count = series.size
    if count % 2 != 0:
        series = np.concatenate([series, [(series[count - 2] + series[count - 1]) / 2.0]])
        count = series.size

    def rssimple(values):
        n = values.size
        cumulative = np.cumsum(values - np.mean(values))
        return math.log((float(np.max(cumulative) - np.min(cumulative))) / sample_sd(values)) / math.log(n)

    def rscalc(n):
        blocks = series.size // int(n)
        y = series.reshape((int(n), blocks), order="F")
        means = np.mean(y, axis=0)
        scales = np.array([float(std(y[:, i])[0]) for i in range(blocks)])
        y = y - means
        y = np.cumsum(y, axis=0)
        span = np.max(y, axis=0) - np.min(y, axis=0)
        return float(np.mean(span / scales))

    length = series.size
    n0 = min(math.floor(0.99 * length), length - 1)
    best = n0
    divisors = _divisors(best, dmin)
    for candidate in range(n0 + 1, length + 1):
        trial = _divisors(candidate, dmin)
        if trial.size > divisors.size:
            best = candidate
            divisors = trial
    series = series[:best]
    widths = divisors.astype(float)
    empirical = np.array([rscalc(int(width)) for width in widths])
    expected = np.zeros(widths.size)
    for index, width in enumerate(widths):
        n = float(width)
        ratio_terms = np.arange(n - 1, 0, -1) / np.arange(1, n)
        ratio = (n - 0.5) / n * float(np.sum(np.sqrt(ratio_terms)))
        if n > 340:
            expected[index] = ratio / math.sqrt(0.5 * math.pi * n)
        else:
            expected[index] = (math.gamma(0.5 * (n - 1)) * ratio) / (math.gamma(0.5 * n) * math.sqrt(math.pi))
    corrected = np.sqrt(0.5 * math.pi * widths)
    hal = float(polyfit(np.log10(widths), np.log10(empirical - expected + corrected), 1)[0])
    he = float(polyfit(np.log10(widths), np.log10(empirical), 1)[0])
    ht = float(polyfit(np.log10(widths), np.log10(expected), 1)[0])
    hs = rssimple(series)
    hrs = _hurstrs(series)
    if display:
        print(f"Simple R/S Hurst estimation:         {hs}")
        print(f"Corrected R over S Hurst exponent:   {hrs}")
        print(f"Empirical Hurst exponent:            {he}")
        print(f"Corrected empirical Hurst exponent:  {hal}")
        print(f"Theoretical Hurst exponent:          {ht}")
    return {"Hs": hs, "Hrs": hrs, "He": he, "Hal": hal, "Ht": ht}
