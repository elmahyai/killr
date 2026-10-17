"""Imputation, column scaling, and an HSV palette."""

from __future__ import annotations

import colorsys
import math


def _missing(value):
    return value is None or (isinstance(value, float) and math.isnan(value))


def _median(values):
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2


def impute(x, what="median"):
    if what not in ("median", "mean"):
        raise ValueError("what must be median or mean")
    columns = list(zip(*x))
    filled = []
    for column in columns:
        present = [float(value) for value in column if not _missing(value)]
        if what == "median":
            replacement = _median(present)
        else:
            replacement = sum(present) / len(present)
        filled.append([replacement if _missing(value) else float(value) for value in column])
    return [list(row) for row in zip(*filled)]


def _mean(values):
    return sum(values) / len(values)


def _sd(values):
    mean = _mean(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def scale_data_frame(frame, center=True, scale=True):
    """Scale numeric and logical columns. Logical values are 1 and 0."""
    names = list(frame)
    columns = {}
    centers = {}
    scales = {}
    for name in names:
        values = list(frame[name])
        if not values:
            columns[name] = values
            continue
        numeric = all(
            isinstance(value, (int, float, bool)) and not _missing(value) for value in values
        )
        if not numeric:
            columns[name] = values
            continue
        numbers = [float(value) for value in values]
        if center is True:
            shift = _mean(numbers)
        elif center is False:
            shift = 0.0
        else:
            shift = float(center)
        shifted = [value - shift for value in numbers]
        if scale is True:
            factor = _sd(numbers)
        elif scale is False:
            factor = 1.0
        else:
            factor = float(scale)
        columns[name] = [value / factor for value in shifted]
        if center is not False:
            centers[name] = shift
        if scale is not False:
            scales[name] = factor
    return {"columns": columns, "center": centers, "scale": scales}


def hsv_palette(h=2 / 3, start=0.7, end=0.2, v=1):
    """Return a function of n. R's argument `from` is `start` here."""

    def palette(n):
        if n == 1:
            saturations = [start]
        else:
            step = (end - start) / (n - 1)
            saturations = [start + step * i for i in range(n)]
        colors = []
        for saturation in saturations:
            red, green, blue = colorsys.hsv_to_rgb(h, saturation, v)
            colors.append(f"#{round(red * 255):02X}{round(green * 255):02X}{round(blue * 255):02X}")
        return colors

    return palette
