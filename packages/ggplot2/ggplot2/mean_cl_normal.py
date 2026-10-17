"""Mean and normal confidence limits.

``mean_cl_normal`` follows Hmisc's ``smean.cl.normal``. Missing values are
removed when ``na_rm`` is true. The mean and the standard error then come
from ``mean_se``, and the multiplier is the t critical value
``qt((1 + conf.int) / 2, n - 1)`` unless ``mult`` is supplied. Fewer than
two remaining values leaves the limits missing. The result has ``y``,
``ymin``, and ``ymax``.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.stats import t

from .mean_se import NA, _as_floats, _is_missing, mean_se

__all__ = ["mean_cl_normal"]


class _MissingMult:
    pass


_MISSING = _MissingMult()


class _MeanClNormal:
    """One row with the mean and the lower and upper normal limits."""

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


def mean_cl_normal(x, mult=_MISSING, conf_int=0.95, na_rm=True):
    """Mean and t confidence limits, after the requested missing-value rule.

    ``conf_int`` is R's ``conf.int``. With the default ``0.95`` the limits
    are the mean plus or minus ``qt(0.975, n - 1)`` standard errors.
    ``mult``, when supplied, replaces that critical value. ``na_rm`` drops
    missing values before the mean is taken. Fewer than two remaining
    values leaves ``ymin`` and ``ymax`` missing.
    """
    if x is None:
        raise ValueError("'x' is NULL")
    drop = _as_flag(na_rm)
    values = _as_floats(x)
    if drop:
        values = [value for value in values if not _is_missing(value)]
    n = len(values)
    if n < 2:
        # mean() of an empty sample is NaN. One value is that value.
        # The default multiplier is not evaluated on this path.
        center = mean_se(values).y
        return _MeanClNormal(center, NA, NA)
    if mult is _MISSING:
        factor = _qt((1.0 + _level(conf_int)) / 2.0, n - 1)
    else:
        factor = mult
    if any(_is_missing(value) for value in values):
        # sum() of a missing value is missing, so the mean and both limits are.
        missing = math.nan
        return _MeanClNormal(missing, missing, missing)
    row = mean_se(values, factor)
    return _MeanClNormal(row.y, row.ymin, row.ymax)


def _qt(probability, df):
    """Student t quantile, matching ``stats::qt`` for a central interval."""
    if _is_missing(probability) or _is_missing(float(df)):
        return math.nan
    return float(t.ppf(probability, df))


def _level(conf_int):
    if isinstance(conf_int, np.ndarray) and conf_int.shape == ():
        conf_int = conf_int.item()
    if conf_int is None or conf_int is NA:
        return math.nan
    return float(conf_int)


def _show(value):
    if value is NA:
        return "NA"
    if isinstance(value, float) and math.isnan(value):
        return "NaN"
    if isinstance(value, float) and math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    return format(value, ".16g")


def _as_flag(value):
    if isinstance(value, np.ndarray) and value.ndim == 0:
        return _as_flag(value.item())
    if isinstance(value, np.ndarray) or isinstance(value, (list, tuple)):
        items = list(value)
        if len(items) == 0:
            raise ValueError("argument is of length zero")
        if len(items) != 1:
            raise ValueError("the condition has length > 1")
        return _as_flag(items[0])
    if value is None or value is NA:
        raise ValueError("missing value where TRUE/FALSE needed")
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value) != 0
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if math.isnan(number):
            raise ValueError("missing value where TRUE/FALSE needed")
        return number != 0.0
    raise ValueError("missing value where TRUE/FALSE needed")
