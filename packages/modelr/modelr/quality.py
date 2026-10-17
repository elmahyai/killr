"""Summaries of a fitted model on a data frame."""

from __future__ import annotations

import math

from modelr.design import residuals, response
from modelr.frame import is_na
from modelr.quantile import quantile


def mse(model, data):
    values = [value * value for value in residuals(model, data) if not is_na(value)]
    return sum(values) / len(values)


def rmse(model, data):
    return math.sqrt(mse(model, data))


def mae(model, data):
    values = [abs(value) for value in residuals(model, data) if not is_na(value)]
    return sum(values) / len(values)


def rsquare(model, data):
    gaps = residuals(model, data)
    observed = response(model, data)
    return 1 - _var(gaps) / _var(observed)


def qae(model, data, probs=None):
    if probs is None:
        probs = [0.05, 0.25, 0.5, 0.75, 0.95]
    absolute = [abs(value) if not is_na(value) else float("nan") for value in residuals(model, data)]
    return quantile(absolute, probs, type=7, na_rm=True)


def mape(model, data):
    gaps = residuals(model, data)
    observed = response(model, data)
    ratios = []
    for gap, actual in zip(gaps, observed):
        if is_na(gap) or is_na(actual):
            continue
        ratios.append(abs(gap / actual))
    return sum(ratios) / len(ratios)


def rsae(model, data):
    gaps = residuals(model, data)
    observed = response(model, data)
    numerator = 0.0
    denominator = 0.0
    for gap, actual in zip(gaps, observed):
        if is_na(gap) or is_na(actual):
            continue
        numerator += abs(gap)
        denominator += abs(actual)
    return numerator / denominator


def _var(values):
    """R's sample variance. Fewer than two values is NaN."""
    kept = [float(value) for value in values if not is_na(value)]
    n = len(kept)
    if n < 2:
        return float("nan")
    center = sum(kept) / n
    return sum((value - center) ** 2 for value in kept) / (n - 1)
