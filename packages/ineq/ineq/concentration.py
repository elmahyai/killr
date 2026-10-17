"""Concentration measures from the R package ineq."""

from __future__ import annotations

import numpy as np

_CONC_TYPES = ("Herfindahl", "Rosenbluth")


def Herfindahl(x, parameter=1, na_rm=True) -> float:
    """Herfindahl concentration coefficient.

    Shares are the values divided by their sum. With parameter ``m`` the
    coefficient is the sum of the shares raised to ``m + 1``, then raised
    to ``1 / m``. ``parameter=None`` uses ``m = 1``, as in R. Missing
    values are dropped when ``na_rm`` is true. If ``na_rm`` is false and
    any value is missing, the result is NaN.
    """
    values = _numeric_values(x, na_rm)
    if values is None:
        return float("nan")
    m = np.float64(1.0 if parameter is None else parameter)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        shares = values / np.sum(values, dtype=np.float64)
        total = np.sum(shares ** (m + np.float64(1.0)), dtype=np.float64)
        result = total ** (np.float64(1.0) / m)
    return float(result)


def Rosenbluth(x, na_rm=True) -> float:
    """Rosenbluth concentration coefficient.

    Values are sorted ascending and weighted by ``n, n - 1, ..., 1``, so
    the largest value receives weight 1. The coefficient is
    ``1 / (2 * sum(weight * share) - 1)``. Missing values are dropped
    when ``na_rm`` is true. If ``na_rm`` is false and any value is
    missing, the result is NaN.
    """
    values = _numeric_values(x, na_rm)
    if values is None:
        return float("nan")
    ordered = np.sort(values)
    weights = np.arange(ordered.size, 0, -1, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        total = np.sum(ordered, dtype=np.float64)
        weighted = np.sum((weights * ordered) / total, dtype=np.float64)
        result = np.float64(1.0) / (np.float64(2.0) * weighted - np.float64(1.0))
    return float(result)


def conc(x, parameter=None, type="Herfindahl", na_rm=True) -> float:
    """Concentration of ``x`` by the Herfindahl or Rosenbluth coefficient.

    ``type`` follows R ``match.arg``: a unique prefix is enough, and
    ``None`` selects Herfindahl. ``parameter`` is passed through to
    Herfindahl, so ``conc(x)`` matches ``Herfindahl(x)``. Rosenbluth
    does not use ``parameter``.
    """
    chosen = _match_type(type)
    if chosen == "Herfindahl":
        return Herfindahl(x, parameter=parameter, na_rm=na_rm)
    return Rosenbluth(x, na_rm=na_rm)


def _numeric_values(x, na_rm: bool):
    values = np.asarray(x, dtype=np.float64)
    if values.ndim == 0:
        values = values.reshape(1)
    else:
        values = np.ravel(values)
    missing = np.isnan(values)
    if not na_rm and bool(np.any(missing)):
        return None
    if na_rm and bool(np.any(missing)):
        return values[~missing]
    return values


def _match_type(type) -> str:
    if type is None:
        return _CONC_TYPES[0]
    if not isinstance(type, str):
        raise ValueError("'type' must be NULL or a character vector")
    matches = [name for name in _CONC_TYPES if name.startswith(type)]
    if len(matches) == 1:
        return matches[0]
    raise ValueError("'type' should be one of \"Herfindahl\", \"Rosenbluth\"")
