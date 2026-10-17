"""Inequality measures translated from CRAN ineq 0.2-13."""

from __future__ import annotations

import numpy as np

__all__ = [
    "Atkinson",
    "Gini",
    "Kolm",
    "RS",
    "Theil",
    "entropy",
    "ineq",
    "var_coeff",
]

# Order matches the default of ineq(). match.arg uses the first name when
# type is NULL, and a unique prefix otherwise.
_TYPE_CHOICES = (
    "Gini",
    "RS",
    "Atkinson",
    "Theil",
    "Kolm",
    "var",
    "square.var",
    "entropy",
)


def Gini(x, corr: bool = False, na_rm: bool = True) -> float:
    """Gini coefficient.

    Sorted values are weighted by ranks 1..n. ``corr=True`` divides by
    ``n - 1`` instead of ``n``.
    """
    values = _prepare(x, na_rm)
    if values is None:
        return float("nan")
    n = values.size
    ordered = np.sort(values)
    ranks = np.arange(1, n + 1, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        score = 2 * np.sum(ordered * ranks) / np.sum(ordered) - (n + 1)
        divisor = (n - 1) if corr else n
        return float(score / divisor)


def RS(x, na_rm: bool = True) -> float:
    """Ricci-Schutz coefficient (Pietra's measure)."""
    values = _prepare(x, na_rm)
    if values is None:
        return float("nan")
    center = _mean(values)
    with np.errstate(divide="ignore", invalid="ignore"):
        return float(_mean(np.abs(values - center)) / (2 * center))


def Atkinson(x, parameter: float | None = 0.5, na_rm: bool = True) -> float:
    """Atkinson's inequality measure. ``parameter=None`` uses 0.5."""
    values = _prepare(x, na_rm)
    if values is None:
        return float("nan")
    if parameter is None:
        parameter = 0.5
    center = _mean(values)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        if parameter == 1:
            return float(1 - (np.exp(_mean(np.log(values))) / center))
        powered = (values / center) ** (1 - parameter)
        return float(1 - _mean(powered) ** (1 / (1 - parameter)))


def Theil(x, parameter: float | None = 0, na_rm: bool = True) -> float:
    """Theil's entropy measure, or his second measure when parameter is not 0.

    ``parameter=None`` uses 0. Parameter 0 drops exact zeros before the log.
    """
    values = _prepare(x, na_rm)
    if values is None:
        return float("nan")
    if parameter is None:
        parameter = 0
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        if parameter == 0:
            values = values[values != 0]
            center = _mean(values)
            logged = np.sum(values * np.log(values / center))
            return float(logged / np.sum(values))
        ratio = np.exp(_mean(np.log(values))) / _mean(values)
        return float(-np.log(ratio))


def Kolm(x, parameter: float | None = 1, na_rm: bool = True) -> float:
    """Kolm's inequality measure. ``parameter=None`` uses 1."""
    values = _prepare(x, na_rm)
    if values is None:
        return float("nan")
    if parameter is None:
        parameter = 1
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        scaled = np.exp(parameter * (_mean(values) - values))
        return float(np.log(_mean(scaled)) / parameter)


def var_coeff(x, square: bool = False, na_rm: bool = True) -> float:
    """Coefficient of variation.

    ``var`` is the sample variance. The ratio uses the population standard
    deviation, ``sqrt((n - 1) * var(x) / n) / mean(x)``. ``square=True``
    returns that ratio squared.
    """
    values = _prepare(x, na_rm)
    if values is None:
        return float("nan")
    n = values.size
    center = _mean(values)
    with np.errstate(divide="ignore", invalid="ignore"):
        if n < 2:
            result = float("nan")
        else:
            variance = np.sum((values - center) ** 2) / (n - 1)
            result = float(np.sqrt((n - 1) * variance / n) / center)
    if square:
        result = float(result**2)
    return result


def entropy(x, parameter: float | None = 0.5, na_rm: bool = True) -> float:
    """Generalized entropy. ``parameter=None`` uses 0.5.

    Parameter 0 calls :func:`Theil` with parameter 1. Parameter 1 calls
    :func:`Theil` with parameter 0.
    """
    values = _prepare(x, na_rm)
    if values is None:
        return float("nan")
    if parameter is None:
        parameter = 0.5
    if parameter == 0:
        return Theil(values, parameter=1)
    if parameter == 1:
        return Theil(values, parameter=0)
    k = parameter
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        powered = (values / _mean(values)) ** k
        return float(_mean(powered - 1) / (k * (k - 1)))


def ineq(x, parameter=None, type: str | None = "Gini", na_rm: bool = True) -> float:
    """Dispatch to one inequality measure.

    ``type`` follows R ``match.arg``: a unique prefix is enough. ``parameter``
    is passed through, so ``None`` selects the default inside Atkinson, Theil,
    Kolm, and entropy.
    """
    chosen = _match_arg(type)
    if chosen == "Gini":
        return Gini(x, na_rm=na_rm)
    if chosen == "RS":
        return RS(x, na_rm=na_rm)
    if chosen == "Atkinson":
        return Atkinson(x, parameter=parameter, na_rm=na_rm)
    if chosen == "Theil":
        return Theil(x, parameter=parameter, na_rm=na_rm)
    if chosen == "Kolm":
        return Kolm(x, parameter=parameter, na_rm=na_rm)
    if chosen == "var":
        return var_coeff(x, na_rm=na_rm)
    if chosen == "square.var":
        return var_coeff(x, square=True, na_rm=na_rm)
    return entropy(x, parameter=parameter, na_rm=na_rm)


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


def _mean(values: np.ndarray) -> float:
    """Arithmetic mean. An empty vector is NaN, as in R."""
    if values.size == 0:
        return float("nan")
    return float(np.sum(values, dtype=np.float64) / values.size)


def _match_arg(arg) -> str:
    """Partial matching used by R ``match.arg`` for ``ineq(type=)``."""
    if arg is None:
        return _TYPE_CHOICES[0]
    if not isinstance(arg, str):
        raise ValueError("'arg' must be NULL or a character vector")
    exact = [choice for choice in _TYPE_CHOICES if choice == arg]
    if len(exact) == 1:
        return exact[0]
    # An empty string is not a prefix in R's pmatch, even though
    # str.startswith("") is true for every choice.
    if arg == "":
        partial: list[str] = []
    else:
        partial = [choice for choice in _TYPE_CHOICES if choice.startswith(arg)]
    if len(partial) == 1:
        return partial[0]
    if len(partial) == 0:
        quoted = ", ".join(f"'{choice}'" for choice in _TYPE_CHOICES)
        raise ValueError(f"'arg' should be one of {quoted}")
    raise ValueError("there is more than one match in 'match.arg'")
