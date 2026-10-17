"""Mean and standard error of the mean."""

from __future__ import annotations

import math

import numpy as np

__all__ = ["mean_se"]


class _Missing:
    def __repr__(self):
        return "NA"

    def __str__(self):
        return "NA"


NA = _Missing()


class _MeanSe:
    """One row with the mean and the lower and upper standard-error bounds."""

    def __init__(self, y, ymin, ymax):
        self.y = y
        self.ymin = ymin
        self.ymax = ymax

    def __iter__(self):
        yield self.y
        yield self.ymin
        yield self.ymax

    def __repr__(self):
        return f"y={_show(self.y)} ymin={_show(self.ymin)} ymax={_show(self.ymax)}"

    def __str__(self):
        return self.__repr__()


def mean_se(x, mult=1):
    """Mean and ``mult`` times the standard error, after omitting missing values.

    The standard error uses the sample variance, divided by the number of
    values that remain. Fewer than two values leaves ``ymin`` and ``ymax``
    missing. The result has ``y``, ``ymin``, and ``ymax``.
    """
    if x is None:
        raise ValueError("'x' is NULL")
    factor = _scalar_mult(mult)
    values = [value for value in _as_floats(x) if not _is_missing(value)]
    n = len(values)
    if n == 0:
        center = math.nan
        variance = NA
    elif n == 1:
        center = float(values[0])
        variance = NA
    else:
        center = _mean(values)
        variance = _sample_variance(values)
    error = _mul(factor, _sqrt(_div(variance, n)))
    return _MeanSe(center, _sub(center, error), _add(center, error))


def _show(value):
    if value is NA:
        return "NA"
    if isinstance(value, float) and math.isnan(value):
        return "NaN"
    if isinstance(value, float) and math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    return format(value, ".16g")


def _as_floats(x):
    if isinstance(x, np.ndarray) and x.ndim == 0:
        return [_one_float(x.item())]
    if isinstance(x, (str, bytes)):
        return [_one_float(x)]
    if isinstance(x, (list, tuple, np.ndarray)):
        return [_one_float(value) for value in x]
    if isinstance(x, (int, float, np.integer, np.floating, np.bool_, bool)):
        return [_one_float(x)]
    try:
        iterator = iter(x)
    except TypeError:
        return [_one_float(x)]
    return [_one_float(value) for value in iterator]


def _one_float(value):
    if value is None or value is NA:
        return math.nan
    if isinstance(value, (bool, np.bool_)):
        return float(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return math.nan
    raise TypeError(f"cannot coerce {type(value).__name__} to numeric")


def _is_missing(value):
    return isinstance(value, float) and math.isnan(value)


def _scalar_mult(mult):
    if isinstance(mult, np.ndarray) and mult.ndim == 0:
        return _one_number(mult.item())
    if isinstance(mult, (list, tuple, np.ndarray)):
        values = list(mult)
        if len(values) != 1:
            raise ValueError(
                f"Can't recycle `ymin` (size {len(values)}) to size 1."
            )
        return _one_number(values[0])
    return _one_number(mult)


def _one_number(value):
    if value is None or value is NA:
        return NA
    number = _one_float(value)
    if _is_missing(number):
        return math.nan
    return number


def _mean(values):
    # The sum is long double, matching stats::mean, then stored as double.
    with np.errstate(invalid="ignore", divide="ignore"):
        total = np.longdouble(0)
        for value in values:
            total += np.longdouble(value)
        return float(total / np.longdouble(len(values)))


def _sample_variance(values):
    # Two-pass sample variance in long double, matching stats::var.
    n = len(values)
    with np.errstate(invalid="ignore", divide="ignore"):
        center = np.longdouble(0)
        for value in values:
            center += np.longdouble(value)
        center /= np.longdouble(n)
        total = np.longdouble(0)
        for value in values:
            delta = np.longdouble(value) - center
            total += delta * delta
        return float(total / np.longdouble(n - 1))


def _div(left, right):
    if isinstance(left, float) and math.isnan(left):
        return math.nan
    if left is NA:
        return NA
    return left / right


def _sqrt(value):
    if value is NA:
        return NA
    return math.sqrt(value)


def _mul(left, right):
    if isinstance(left, float) and math.isnan(left):
        return math.nan
    if left is NA or right is NA:
        return NA
    if isinstance(right, float) and math.isnan(right):
        return math.nan
    return left * right


def _sub(left, right):
    if isinstance(left, float) and math.isnan(left):
        return math.nan
    if left is NA or right is NA:
        return NA
    if isinstance(right, float) and math.isnan(right):
        return math.nan
    return left - right


def _add(left, right):
    if isinstance(left, float) and math.isnan(left):
        return math.nan
    if left is NA or right is NA:
        return NA
    if isinstance(right, float) and math.isnan(right):
        return math.nan
    return left + right
