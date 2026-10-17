"""Poverty measures translated from CRAN ineq 0.2-13."""

from __future__ import annotations

import math

import numpy as np

from ineq.measures import Gini

__all__ = ["Foster", "SST", "Sen", "Watts", "pov"]

# Order matches pov(). match.arg uses the first name when type is NULL.
# A partial match counts only when it is unique; an ambiguous prefix is
# rejected, as in R pmatch.
_TYPE_CHOICES = ("Watts", "Sen", "SST", "Foster")


def Watts(x, k, na_rm: bool = True) -> float:
    """Watts poverty index.

    Sum of ``log(k / income)`` over incomes strictly below ``k``, divided
    by the length of the whole sample.
    """
    values, poor, line, early = _screen(x, k, na_rm)
    if early is not None:
        return early
    with np.errstate(divide="ignore", invalid="ignore"):
        total = np.sum(np.log(line / poor), dtype=np.float64)
    return float(total / values.size)


def Sen(x, k, na_rm: bool = True) -> float:
    """Sen poverty index.

    ``H * (I + (1 - I) * G)``, where ``G`` is :func:`Gini` on the incomes
    strictly below ``k``.
    """
    values, poor, line, early = _screen(x, k, na_rm)
    if early is not None:
        return early
    headcount = poor.size / values.size
    with np.errstate(divide="ignore", invalid="ignore"):
        shortfall = float(np.sum((line - poor) / line, dtype=np.float64) / poor.size)
    gini = Gini(poor)
    return float(headcount * (shortfall + (1.0 - shortfall) * gini))


def SST(x, k, na_rm: bool = True) -> float:
    """Sen-Shorrocks-Thon poverty index.

    Incomes strictly below ``k`` are sorted. The gap in position ``i``
    (counting from 1) is weighted by ``2 * n - 2 * i + 1``. This is the
    weighted sum from the R source; it does not call :func:`Gini`.
    """
    values, poor, line, early = _screen(x, k, na_rm)
    if early is not None:
        return early
    ordered = np.sort(poor)
    n = float(values.size)
    ranks = np.arange(1, ordered.size + 1, dtype=np.float64)
    weights = 2.0 * n - 2.0 * ranks + 1.0
    with np.errstate(divide="ignore", invalid="ignore"):
        # Left-associative, as in `(weights * (k - x2)) / k`.
        total = np.sum((weights * (line - ordered)) / line, dtype=np.float64)
    return float(total / (n * n))


def Foster(x, k, parameter=1, na_rm: bool = True) -> float:
    """Foster / Greer / Thorbecke poverty index.

    ``parameter=None`` uses 1. Parameter 1 is the headcount ratio and
    parameter 2 is the poverty gap ratio. The exponent is ``parameter - 1``.
    """
    values, poor, line, early = _screen(x, k, na_rm)
    if early is not None:
        return early
    if parameter is None:
        parameter = 1
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        gaps = (line - poor) / line
        total = np.sum(gaps ** (parameter - 1), dtype=np.float64)
    return float(total / values.size)


def pov(x, k, parameter=None, type: str | None = "Watts", na_rm: bool = True) -> float:
    """Dispatch to Watts, Sen, SST, or Foster.

    ``type`` follows R ``match.arg``: a unique prefix is enough, and
    ``None`` selects Watts. ``parameter`` is passed through, so
    ``pov(x, k, type="Foster")`` matches ``Foster(x, k)``.
    """
    chosen = _match_arg(type)
    if chosen == "Watts":
        return Watts(x, k, na_rm=na_rm)
    if chosen == "Sen":
        return Sen(x, k, na_rm=na_rm)
    if chosen == "SST":
        return SST(x, k, na_rm=na_rm)
    return Foster(x, k, parameter=parameter, na_rm=na_rm)


def _prepare(x, na_rm: bool) -> np.ndarray | None:
    """Return a 1-d float vector, or None when a missing value must be kept.

    R ``is.na`` is true for both NA and NaN. With ``na_rm`` false, any such
    value makes the measure NaN. Otherwise those values are dropped.
    """
    values = np.asarray(x, dtype=np.float64)
    values = np.atleast_1d(values).reshape(-1)
    missing = np.isnan(values)
    if not na_rm and bool(missing.any()):
        return None
    if bool(missing.any()):
        return values[~missing]
    return values


def _screen(x, k, na_rm: bool):
    """Shared preamble of the four poverty measures.

    Returns ``(sample, poor, line, None)`` when there is something to
    compute. Otherwise the fourth item is the finished result: NaN when
    missing values are kept or the poverty line is missing, and 0 when
    nobody is strictly below the line.
    """
    values = _prepare(x, na_rm)
    if values is None:
        return None, None, None, float("nan")
    line = float(k)
    # R comparisons with NA are NA, so the subset stays the same length
    # and the later sum is NA. An empty sample has nobody below the line.
    if values.size and math.isnan(line):
        return None, None, None, float("nan")
    poor = values[values < line]
    if poor.size < 1:
        return None, None, None, 0.0
    return values, poor, line, None


def _match_arg(arg) -> str:
    """Partial matching used by R ``match.arg`` for ``pov(type=)``."""
    if arg is None:
        return _TYPE_CHOICES[0]
    if not isinstance(arg, str):
        raise ValueError("'arg' must be NULL or a character vector")
    if arg == "":
        _reject_type()
    exact = [choice for choice in _TYPE_CHOICES if choice == arg]
    if exact:
        return exact[0]
    partial = [choice for choice in _TYPE_CHOICES if choice.startswith(arg)]
    if len(partial) == 1:
        return partial[0]
    _reject_type()


def _reject_type() -> None:
    quoted = ", ".join(f"'{choice}'" for choice in _TYPE_CHOICES)
    raise ValueError(f"'arg' should be one of {quoted}")
