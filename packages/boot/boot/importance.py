"""Importance sampling weights, moments, tail probabilities, and quantiles.

These functions take the numeric fields of an R ``boot`` object. R rebuilds
the resample frequencies with ``boot.array``. This module reads that matrix
from ``frequency`` on the object, copied from one R call, and does not redraw
the resamples.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

_MISSING = object()
_DEFAULT_ALPHA = np.array([0.01, 0.025, 0.05, 0.95, 0.975, 0.99], dtype=np.float64)

__all__ = ["imp_moments", "imp_prob", "imp_quantile", "imp_weights"]


def imp_weights(boot_out: Any, def_: bool = True, q: Any = None) -> np.ndarray:
    """Importance weights that reweight replicates drawn under ``p`` to ``q``.

    ``def_`` is ``def`` in R. A single resampling distribution forces
    ``def_`` to false. ``q`` of ``None`` is the uniform distribution.
    """
    replicates = _as_counts(_field(boot_out, "R"))
    if replicates.size == 1:
        def_ = False
    frequency = np.asarray(_field(boot_out, "frequency"), dtype=np.float64)
    if frequency.ndim != 2:
        raise ValueError("frequency must be the resample matrix from boot.array")
    n = frequency.shape[1]
    strata = _group_strata(_field(boot_out, "strata"))
    if strata.shape[0] != n:
        raise ValueError("strata must have one value per observation")
    if q is None:
        target = np.ones(n, dtype=np.float64)
    else:
        target = np.asarray(q, dtype=np.float64).reshape(-1)
    if target.shape[0] != n:
        raise ValueError("q must have one value per observation")
    if np.any(target == 0):
        raise ValueError("0 elements not allowed in 'q'")
    if frequency.shape[0] != int(replicates.sum()):
        raise ValueError("frequency must have sum(R) rows")
    sampling = np.asarray(_field(boot_out, "weights"), dtype=np.float64)
    if replicates.size == 1 and _weights_match(sampling, target):
        return np.ones(int(replicates[0]), dtype=np.float64)
    target = _normalize(target, strata)
    log_target = frequency @ np.log(target)
    sampling = _as_weight_matrix(sampling, n)
    sampling = _normalize_rows(sampling, strata)
    n_dist = replicates.size
    if sampling.shape[0] != n_dist:
        raise ValueError("weights must have one row per value of R")
    log_sampling = np.empty((int(replicates.sum()), n_dist), dtype=np.float64)
    for i in range(n_dist):
        positive = np.flatnonzero(sampling[i] > 0)
        log_sampling[:, i] = frequency[:, positive] @ np.log(sampling[i, positive])
    if def_:
        mixture = np.exp(log_sampling - log_target[:, None]) @ replicates
        weights = 1.0 / (mixture / replicates.sum())
    else:
        column = np.repeat(np.arange(n_dist), replicates)
        weights = np.exp(log_target - log_sampling[np.arange(log_sampling.shape[0]), column])
    return np.asarray(weights, dtype=np.float64).reshape(-1)


def imp_moments(
    boot_out: Any = None,
    index: Any = 1,
    t: Any = None,
    w: Any = None,
    def_: bool = True,
    q: Any = None,
) -> dict[str, np.ndarray]:
    """Raw, ratio, and regression estimates of the mean and variance of ``t``."""
    if t is None:
        t = _MISSING
    values, weights = _replicates_and_weights(boot_out, index, t, None, w, def_, q)
    if not _const(weights):
        y = values * weights
        mean_raw = _mean(y)
        mean_ratio = _sum(y) / _sum(weights)
        mean_reg = _mean(y) - _slope(weights, y) * (_mean(weights) - 1.0)
        var_raw = _mean(weights * (values - mean_raw) ** 2)
        var_ratio = _sum(weights / _sum(weights) * (values - mean_ratio) ** 2)
        x = weights * (values - mean_reg) ** 2
        var_reg = _mean(x) - _slope(weights, x) * (_mean(weights) - 1.0)
    else:
        mean_raw = mean_ratio = mean_reg = _mean(values)
        var_raw = var_ratio = var_reg = _var(values)
    return {
        "raw": np.array([mean_raw, var_raw], dtype=np.float64),
        "rat": np.array([mean_ratio, var_ratio], dtype=np.float64),
        "reg": np.array([mean_reg, var_reg], dtype=np.float64),
    }


def imp_quantile(
    boot_out: Any = None,
    alpha: Any = None,
    index: Any = 1,
    t: Any = None,
    w: Any = None,
    def_: bool = True,
    q: Any = None,
) -> dict[str, np.ndarray]:
    """Raw, ratio, and regression estimates of the ``alpha`` quantiles of ``t``."""
    if t is None:
        t = _MISSING
    values, weights = _replicates_and_weights(boot_out, index, t, None, w, def_, q)
    if alpha is None:
        levels = _DEFAULT_ALPHA.copy()
    else:
        levels = np.asarray(alpha, dtype=np.float64).reshape(-1)
    order = np.argsort(values, kind="stable")
    ordered = values[order]
    ordered_w = weights[order]
    cumulative = np.cumsum(ordered_w)
    cumulative_ratio = cumulative / _mean(ordered_w)
    cumulative_reg = np.cumsum(_imp_reg(ordered_w))
    # The installed function subscripts the sorted weights by the reversed
    # order index. The upper raw quantile follows that, and an empty max is -Inf.
    mirror_w = ordered_w[order[::-1]]
    mirror_t = -ordered[::-1]
    cumulative_mirror = np.cumsum(mirror_w)
    count = ordered.shape[0]
    raw = np.empty(levels.shape[0], dtype=np.float64)
    ratio = np.empty(levels.shape[0], dtype=np.float64)
    regression = np.empty(levels.shape[0], dtype=np.float64)
    for i, level in enumerate(levels):
        if level <= 0.5:
            raw[i] = _r_max(ordered[cumulative <= (count + 1) * level])
        else:
            raw[i] = -_r_max(mirror_t[cumulative_mirror <= (count + 1) * (1.0 - level)])
        ratio[i] = _r_max(ordered[cumulative_ratio <= (count + 1) * level])
        regression[i] = _r_max(ordered[cumulative_reg <= (count + 1) * level])
    return {"alpha": levels, "raw": raw, "rat": ratio, "reg": regression}


def imp_prob(
    boot_out: Any = None,
    index: Any = 1,
    t0: Any = None,
    t: Any = None,
    w: Any = None,
    def_: bool = True,
    q: Any = None,
) -> dict[str, np.ndarray]:
    """Raw, ratio, and regression estimates of the tail probability P(t <= t0)."""
    if t is None:
        t = _MISSING
    if t0 is None:
        t0 = _MISSING
    values, weights = _replicates_and_weights(boot_out, index, t, t0, w, def_, q)
    thresholds = _thresholds(boot_out, index, t, t0)
    order = np.argsort(values, kind="stable")
    ordered = values[order]
    ordered_w = weights[order]
    total = _sum(ordered_w)
    cumulative = np.cumsum(ordered_w) / total
    regression_w = _imp_reg(ordered_w)
    cumulative_reg = np.cumsum(regression_w) / _sum(regression_w)
    count = ordered.shape[0]
    raw = np.empty(thresholds.shape[0], dtype=np.float64)
    ratio = np.empty(thresholds.shape[0], dtype=np.float64)
    regression = np.empty(thresholds.shape[0], dtype=np.float64)
    for i, point in enumerate(thresholds):
        at_most = ordered <= point
        raw[i] = _sum(ordered_w[at_most]) / count
        if raw[i] > 1.0:
            raw[i] = 1.0
        if np.any(at_most):
            ratio[i] = _r_max(cumulative[at_most])
            regression[i] = _r_max(cumulative_reg[at_most])
        else:
            ratio[i] = 0.0
            regression[i] = 0.0
    return {"t0": thresholds, "raw": raw, "rat": ratio, "reg": regression}


def _replicates_and_weights(boot_out, index, t, t0, w, def_, q):
    values = _statistic(boot_out, index, t, t0)
    if w is None:
        if boot_out is None:
            raise ValueError("either 'boot.out' or 'w' must be specified.")
        weights = imp_weights(boot_out, def_=def_, q=q)
    else:
        weights = np.asarray(w, dtype=np.float64).reshape(-1)
    if weights.shape[0] != values.shape[0]:
        raise ValueError("t and w must have the same length")
    finite = np.isfinite(values)
    return values[finite], weights[finite]


def _statistic(boot_out, index, t, t0):
    columns = np.atleast_1d(np.asarray(index))
    t_missing = t is _MISSING
    t0_missing = t0 is _MISSING
    if t_missing and (boot_out is None or _field(boot_out, "t", default=None) is None):
        raise ValueError("bootstrap replicates must be supplied")
    if columns.size > 1 and (t_missing or t0_missing):
        warnings.warn("only first element of 'index' used", stacklevel=3)
        columns = columns[:1]
    if not t_missing:
        if _is_missing_value(t):
            if boot_out is None:
                raise ValueError("bootstrap replicates must be supplied")
            return _column(_field(boot_out, "t"), columns[0])
        return np.asarray(t, dtype=np.float64).reshape(-1)
    return _column(_field(boot_out, "t"), columns[0])


def _thresholds(boot_out, index, t, t0):
    columns = np.atleast_1d(np.asarray(index))
    if columns.size > 1 and (t is _MISSING or t0 is _MISSING):
        columns = columns[:1]
    if t0 is not _MISSING and not _is_missing_value(t0):
        return np.asarray(t0, dtype=np.float64).reshape(-1)
    if boot_out is None:
        raise ValueError("bootstrap replicates must be supplied")
    observed = np.asarray(_field(boot_out, "t0"), dtype=np.float64).reshape(-1)
    position = int(columns[0]) - 1
    return np.array([observed[position]], dtype=np.float64)


def _imp_reg(weights: np.ndarray) -> np.ndarray:
    count = weights.shape[0]
    if _const(weights):
        return weights
    center = _mean(weights)
    second = (count - 1) / count * _var(weights)
    slope = (1.0 - center) / second
    return weights * (1.0 + slope * (weights - center))


def _group_strata(strata) -> np.ndarray:
    """Integer codes from ``tapply(strata, as.numeric(strata))`` with ``FUN`` null."""
    values = np.asarray(strata)
    if values.dtype.kind not in "biufc":
        raise ValueError("strata must be numeric")
    numeric = np.asarray(values, dtype=np.float64).reshape(-1)
    _levels, inverse = np.unique(numeric, return_inverse=True)
    return inverse.astype(np.int64) + 1


def _normalize(weights: np.ndarray, strata: np.ndarray) -> np.ndarray:
    scaled = np.array(weights, dtype=np.float64, copy=True)
    for code in np.unique(strata):
        group = strata == code
        scaled[group] = scaled[group] / np.sum(scaled[group])
    return scaled


def _normalize_rows(weights: np.ndarray, strata: np.ndarray) -> np.ndarray:
    scaled = np.array(weights, dtype=np.float64, copy=True)
    for row in range(scaled.shape[0]):
        scaled[row] = _normalize(scaled[row], strata)
    return scaled


def _as_weight_matrix(weights: np.ndarray, n: int) -> np.ndarray:
    if weights.ndim == 1:
        return weights.reshape(1, n)
    if weights.ndim == 2:
        return weights
    raise ValueError("weights must be a vector or a matrix")


def _weights_match(sampling: np.ndarray, target: np.ndarray) -> bool:
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.abs(sampling - target) / sampling
    if np.any(np.isnan(ratio)):
        raise ValueError("missing value where TRUE/FALSE needed")
    return bool(np.all(ratio < 1e-10))


def _const(weights: np.ndarray, eps: float = 1e-8) -> bool:
    if weights.size == 0:
        return True
    center = _mean(weights)
    return bool(np.all(np.abs(weights - center) < eps))


def _column(t, index) -> np.ndarray:
    values = np.asarray(t, dtype=np.float64)
    if values.ndim == 1:
        return values.reshape(-1)
    position = int(index) - 1
    return np.array(values[:, position], dtype=np.float64, copy=True)


def _r_max(values: np.ndarray) -> float:
    if values.size == 0:
        warnings.warn(
            "no non-missing arguments to max; returning -Inf",
            stacklevel=2,
        )
        return -np.inf
    return float(np.max(values))


def _is_missing_value(value) -> bool:
    if value is None:
        return True
    array = np.asarray(value, dtype=np.float64)
    if array.size == 0:
        return True
    return array.size == 1 and bool(np.isnan(array.reshape(-1)[0]))


def _slope(x: np.ndarray, y: np.ndarray) -> float:
    """Slope of ``lm(y ~ x)``, the second coefficient."""
    design = np.column_stack([np.ones(x.shape[0]), np.asarray(x, dtype=np.float64)])
    coef, _residuals, rank, _singular = np.linalg.lstsq(design, y, rcond=None)
    if rank < 2:
        return np.nan
    return float(coef[1])


def _mean(values: np.ndarray) -> float:
    return _sum(values) / values.shape[0]


def _sum(values: np.ndarray) -> float:
    return float(np.sum(values, dtype=np.float64))


def _var(values: np.ndarray) -> float:
    """R ``var``: the sample variance, divided by n - 1."""
    count = values.shape[0]
    if count < 2:
        return np.nan
    center = _mean(values)
    return _sum((values - center) ** 2) / (count - 1)


def _as_counts(replicates) -> np.ndarray:
    return np.atleast_1d(np.asarray(replicates, dtype=np.int64)).reshape(-1)


def _field(obj: Any, name: str, default: Any = ...):
    if isinstance(obj, dict):
        if name in obj:
            return obj[name]
        if default is ...:
            raise KeyError(name)
        return default
    if hasattr(obj, name):
        return getattr(obj, name)
    if default is ...:
        raise AttributeError(name)
    return default
