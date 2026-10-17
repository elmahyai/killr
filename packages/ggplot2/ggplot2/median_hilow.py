"""Median and high-low sample quantiles.

``median_hilow`` follows Hmisc's ``smedian.hilow``: the median and the
quantiles at ``(1 - conf.int) / 2`` and ``(1 + conf.int) / 2``, using R's
type-7 ``quantile``. The three results are named ``y``, ``ymin``, and ``ymax``.
"""

from __future__ import annotations

import math

import numpy as np

__all__ = ["median_hilow"]


class _Missing:
    def __repr__(self):
        return "NA"

    def __str__(self):
        return "NA"


NA = _Missing()

_NAME_MAP = (
    ("Median", "y"),
    ("Mean", "y"),
    ("Lower", "ymin"),
    ("Upper", "ymax"),
)
_LABELS = ("Median", "Lower", "Upper")


class _MedianHilow:
    """One row of the median and the lower and upper quantiles."""

    def __init__(self, columns):
        self._columns = list(columns)
        first = {}
        for name, value in self._columns:
            if name not in first:
                first[name] = value
        self.y = first.get("y", NA)
        self.ymin = first.get("ymin", NA)
        self.ymax = first.get("ymax", NA)

    def __iter__(self):
        for _name, value in self._columns:
            yield value

    def __repr__(self):
        return " ".join(f"{name}={_show(value)}" for name, value in self._columns)

    def __str__(self):
        return self.__repr__()


def median_hilow(x, conf_int=0.95, na_rm=True):
    """Median and the high-low quantiles, after the requested missing-value rule.

    ``conf_int`` is R's ``conf.int``. With the default ``0.95`` the bounds
    are the 0.025 and 0.975 sample quantiles. ``na_rm`` drops missing values
    before the quantiles are taken. An empty sample leaves each result missing.
    """
    # c(.5, (1 - conf.int) / 2, (1 + conf.int) / 2) concatenates the three pieces.
    levels = [] if conf_int is None else _as_floats(conf_int)
    probabilities = [
        0.5,
        *[(1.0 - level) / 2.0 for level in levels],
        *[(1.0 + level) / 2.0 for level in levels],
    ]
    quantiles = _quantile_type7(_sample(x), probabilities, na_rm)
    names = _assign_names(quantiles)
    columns = _rename(names, quantiles)
    return _MedianHilow(columns)


def _sample(x):
    if x is None:
        return []
    return _as_floats(x)


def _assign_names(quantiles):
    if len(quantiles) < len(_LABELS):
        raise ValueError(
            f"'names' attribute [{len(_LABELS)}] must be the same length as the vector [{len(quantiles)}]"
        )
    names = [None] * len(quantiles)
    for index, label in enumerate(_LABELS):
        names[index] = label
    return names


def _rename(names, quantiles):
    """Rename the first Median, Mean, Lower, and Upper, as ggplot2's rename does."""
    positions = {}
    for index, name in enumerate(names):
        if name is not None and name not in positions:
            positions[name] = index
    renamed = list(names)
    for old, new in _NAME_MAP:
        index = positions.get(old)
        if index is not None:
            renamed[index] = new
    columns = []
    for name, value in zip(renamed, quantiles):
        columns.append(("" if name is None else name, value))
    return columns


def _quantile_type7(values, probs, na_rm):
    """R 4.5 ``stats::quantile`` type 7, with fuzz 0."""
    eps = 100.0 * float(np.finfo(float).eps)
    ok = []
    for prob in probs:
        missing = _is_missing(prob)
        ok.append(not missing)
        if not missing and (prob < -eps or prob > 1.0 + eps):
            raise ValueError("'probs' outside [0,1]")
    clamped = []
    for prob, present in zip(probs, ok):
        if not present:
            clamped.append(math.nan)
        elif prob < 0.0:
            clamped.append(0.0)
        elif prob > 1.0:
            clamped.append(1.0)
        else:
            clamped.append(float(prob))

    if _as_flag(na_rm):
        data = [value for value in values if not _is_missing(value)]
    else:
        if any(_is_missing(value) for value in values):
            raise ValueError("missing values and NaN's not allowed if 'na.rm' is FALSE")
        data = list(values)

    count = len(clamped)
    if count == 0:
        return []
    size = len(data)
    if size == 0:
        return [NA for _present in ok]

    ordered = sorted(data)
    span = max(size - 1, 0)
    index = []
    lo = []
    hi = []
    for prob, present in zip(clamped, ok):
        if not present:
            index.append(math.nan)
            lo.append(None)
            hi.append(None)
            continue
        position = 1.0 + span * prob
        index.append(position)
        lo.append(math.floor(position))
        hi.append(math.ceil(position))

    result = []
    for position, present in zip(lo, ok):
        if not present:
            result.append(NA)
        else:
            result.append(ordered[position - 1])

    for i, present in enumerate(ok):
        if not present:
            continue
        right = ordered[hi[i] - 1]
        # An exact index, or two equal order statistics, keeps the lower one.
        if index[i] > lo[i] and right != result[i]:
            weight = index[i] - lo[i]
            result[i] = (1.0 - weight) * result[i] + weight * right
    return result


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
    return value is NA or (isinstance(value, float) and math.isnan(value))


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
