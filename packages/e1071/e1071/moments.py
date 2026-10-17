"""Skewness, kurtosis, and moments."""

from __future__ import annotations

import math


def _values(x, na_rm):
    missing = [value is None or (isinstance(value, float) and math.isnan(value)) for value in x]
    if any(missing):
        if not na_rm:
            return None
        x = [value for value, gone in zip(x, missing) if not gone]
    return [float(value) for value in x]


def skewness(x, na_rm=False, type=3):
    values = _values(x, na_rm)
    if values is None:
        return float("nan")
    if type not in (1, 2, 3):
        raise ValueError("Invalid 'type' argument.")
    n = len(values)
    mean = sum(values) / n
    centered = [value - mean for value in values]
    y = math.sqrt(n) * sum(value ** 3 for value in centered) / (
        sum(value ** 2 for value in centered) ** 1.5
    )
    if type == 2:
        if n < 3:
            raise ValueError("Need at least 3 complete observations.")
        y = y * math.sqrt(n * (n - 1)) / (n - 2)
    elif type == 3:
        y = y * ((1 - 1 / n) ** 1.5)
    return y


def kurtosis(x, na_rm=False, type=3):
    values = _values(x, na_rm)
    if values is None:
        return float("nan")
    if type not in (1, 2, 3):
        raise ValueError("Invalid 'type' argument.")
    n = len(values)
    mean = sum(values) / n
    centered = [value - mean for value in values]
    r = n * sum(value ** 4 for value in centered) / (sum(value ** 2 for value in centered) ** 2)
    if type == 1:
        return r - 3
    if type == 2:
        if n < 4:
            raise ValueError("Need at least 4 complete observations.")
        return ((n + 1) * (r - 3) + 6) * (n - 1) / ((n - 2) * (n - 3))
    return r * (1 - 1 / n) ** 2 - 3


def moment(x, order=1, center=False, absolute=False, na_rm=False):
    values = list(x)
    if na_rm:
        values = [
            value
            for value in values
            if value is not None and not (isinstance(value, float) and math.isnan(value))
        ]
    values = [float(value) for value in values]
    if center:
        mean = sum(values) / len(values)
        values = [value - mean for value in values]
    if absolute:
        values = [abs(value) for value in values]
    return sum(value ** order for value in values) / len(values)
