"""One-sample, two-sample, and paired bootstraps.

Each one calls ``boot.boot``. The returned object is that bootstrap with
``student`` set and class ``simpleboot``. Indices from ``boot`` are 1-based.
"""

import math

import numpy as np
from matplotlib import pyplot as plt

from boot import boot


def _fun_name(fun):
    if isinstance(fun, str):
        return fun
    return getattr(fun, "__name__", "")


def r_mean(x):
    values = np.asarray(x, dtype=float).reshape(-1)
    if values.size == 0:
        return math.nan
    return float(np.sum(values) / values.size)


def r_var(x):
    values = np.asarray(x, dtype=float).reshape(-1)
    n = int(values.size)
    if n < 2:
        return math.nan
    center = float(np.sum(values) / n)
    return float(np.sum((values - center) ** 2) / (n - 1))


def r_quantile(x, probs):
    """R ``quantile`` type 7."""
    values = np.sort(np.asarray(x, dtype=float).reshape(-1))
    n = int(values.size)
    levels = np.atleast_1d(np.asarray(probs, dtype=float))
    if n == 0:
        return np.full(levels.shape, np.nan)
    if np.any((levels < 0) | (levels > 1)):
        raise ValueError("probabilities outside [0,1]")
    fuzz = 4.0 * np.finfo(float).eps
    out = np.empty(levels.size, dtype=float)
    for i, level in enumerate(levels.reshape(-1)):
        h = 1.0 + (n - 1) * float(level)
        j = int(math.floor(h + fuzz))
        g = h - j
        if abs(g) < fuzz:
            g = 0.0
        if j < 1:
            j = 1
        if j > n:
            j = n
        if g == 0.0:
            out[i] = values[j - 1]
        else:
            upper = j if j < n else n - 1
            out[i] = (1.0 - g) * values[j - 1] + g * values[upper]
    if levels.shape == ():
        return float(out[0])
    return out.reshape(levels.shape)


def r_median(x):
    return float(np.asarray(r_quantile(x, 0.5), dtype=float).reshape(-1)[0])


def r_cor(x, y):
    left = np.asarray(x, dtype=float).reshape(-1)
    right = np.asarray(y, dtype=float).reshape(-1)
    left = left - np.sum(left) / left.size
    right = right - np.sum(right) / right.size
    denom = math.sqrt(float(np.sum(left * left) * np.sum(right * right)))
    if denom == 0.0:
        return math.nan
    return float(np.sum(left * right) / denom)


_NAMED = {
    "mean": r_mean,
    "median": r_median,
    "var": r_var,
    "quantile": r_quantile,
    "cor": r_cor,
}


def _resolve(fun):
    if isinstance(fun, str):
        if fun not in _NAMED:
            raise ValueError(f"could not find function {fun}")
        return _NAMED[fun]
    if fun in (np.mean, np.median):
        return r_mean if fun is np.mean else r_median
    return fun


def _as_vector(value):
    if np.isscalar(value):
        return np.asarray([value], dtype=float)
    return np.asarray(value, dtype=float).reshape(-1)


def _positions(idx):
    return np.asarray(idx, dtype=int).reshape(-1)


def _mark(result, student):
    result.student = bool(student)
    result.classes = ("simpleboot",)
    return result


def one_boot(data, fun, R, student=False, M=None, weights=None, **extra):
    """Bootstrap a statistic of one sample.

    ``student=True`` nests another ``one_boot`` of size ``M`` and appends
    the sample variance of those replicates. A call that bootstraps
    ``quantile`` must pass a single ``probs`` value.
    """
    name = _fun_name(fun)
    if name == "quantile":
        if "probs" not in extra:
            raise ValueError("'probs' argument must be specified")
        if np.size(extra["probs"]) > 1:
            raise ValueError("can only bootstrap a single quantile")
    func = _resolve(fun)
    series = np.asarray(data, dtype=float).reshape(-1)

    def statistic(x, idx):
        chosen = np.asarray(x, dtype=float).reshape(-1)[_positions(idx) - 1]
        fval = _as_vector(func(chosen, **extra))
        if student:
            nested = one_boot(chosen, fun, R=M, student=False, M=None, weights=None, **extra)
            fval = np.concatenate([fval, [r_var(np.asarray(nested.t, dtype=float))]])
        return fval

    result = boot(series, statistic, R=R, weights=weights)
    return _mark(result, student)


def two_boot(sample1, sample2, fun, R, student=False, M=None, weights=None, **extra):
    """Bootstrap the difference of a statistic on two samples.

    The samples are stacked and resampled with ``boot``'s ``strata``
    argument, one stratum per sample.
    """
    name = _fun_name(fun)
    if name == "quantile":
        if "probs" not in extra:
            raise ValueError("'probs' argument must be specified")
        if np.size(extra["probs"]) > 1:
            raise ValueError("can only bootstrap a single quantile")
    func = _resolve(fun)
    left = np.asarray(sample1, dtype=float).reshape(-1)
    right = np.asarray(sample2, dtype=float).reshape(-1)
    ind = np.concatenate([np.ones(left.size, dtype=int), np.full(right.size, 2, dtype=int)])
    pooled = np.concatenate([left, right])
    if weights is not None:
        weights = np.concatenate([np.asarray(part, dtype=float).reshape(-1) for part in weights]) if isinstance(weights, (list, tuple)) else np.asarray(weights, dtype=float).reshape(-1)

    def statistic(x, idx):
        positions = _positions(idx)
        drawn = np.asarray(x, dtype=float).reshape(-1)
        d1 = drawn[positions[ind == 1] - 1]
        d2 = drawn[positions[ind == 2] - 1]
        fval = _as_vector(func(d1, **extra) - func(d2, **extra))
        if student:
            nested = two_boot(d1, d2, fun, R=M, student=False, M=None, weights=None, **extra)
            fval = np.concatenate([fval, [r_var(np.asarray(nested.t, dtype=float))]])
        return fval

    result = boot(pooled, statistic, R=R, weights=weights, strata=ind)
    return _mark(result, student)


def pairs_boot(x, y=None, fun=None, R=None, student=False, M=None, weights=None, **extra):
    """Bootstrap a statistic of paired observations.

    ``y is None`` means ``x`` is a two-column matrix and ``fun`` takes that
    matrix. Otherwise ``fun`` is called as ``fun(x, y)``.
    """
    if fun is None or R is None:
        raise TypeError("pairs_boot requires FUN and R")
    if student and M is None:
        raise ValueError("need to specify 'M' for studentized bootstrap")
    func = _resolve(fun)
    y_missing = y is None
    if y_missing:
        data = np.asarray(x, dtype=float)
        if data.ndim != 2:
            raise ValueError("'x' must be a matrix or a data frame")
    else:
        left = np.asarray(x, dtype=float).reshape(-1)
        right = np.asarray(y, dtype=float).reshape(-1)
        if left.size != right.size:
            raise ValueError("length of 'x' must equal length of 'y'")
        data = np.column_stack([left, right])

    def statistic(rows, idx):
        chosen = np.asarray(rows, dtype=float)[_positions(idx) - 1]
        if y_missing:
            fval = _as_vector(func(chosen, **extra))
        else:
            fval = _as_vector(func(chosen[:, 0], chosen[:, 1], **extra))
        if student:
            nested = pairs_boot(
                chosen[:, 0],
                chosen[:, 1],
                fun,
                M,
                student=False,
                M=None,
                weights=None,
                **extra,
            )
            fval = np.concatenate([fval, [r_var(np.asarray(nested.t, dtype=float))]])
        return fval

    result = boot(data, statistic, R=R, weights=weights)
    return _mark(result, student)


def _is_simple(obj):
    return getattr(obj, "classes", ()) == ("simpleboot",) or (
        isinstance(getattr(obj, "classes", ()), tuple) and "simpleboot" in obj.classes and "lm.simpleboot" not in obj.classes and "loess.simpleboot" not in getattr(obj, "classes", ())
    )


def perc(boot_out, p=(0.025, 0.975)):
    """Percentile intervals of a ``simpleboot`` or ``lm.simpleboot`` object."""
    classes = getattr(boot_out, "classes", ())
    if "lm.simpleboot" in classes:
        from simpleboot.linear import perc_lm

        return perc_lm(boot_out, p)
    if "simpleboot" not in classes:
        raise ValueError("only use this function on 'simpleboot' objects")
    levels = np.atleast_1d(np.asarray(p, dtype=float))
    if np.any(levels < 0) or np.any(levels > 1):
        raise ValueError("probabilities in 'p' must be between 0 and 1")
    replicates = np.asarray(boot_out.t, dtype=float)
    if getattr(boot_out, "student", False):
        replicates = replicates[:, :1]
    columns = []
    for column in range(replicates.shape[1]):
        columns.append(np.asarray(r_quantile(replicates[:, column], levels), dtype=float).reshape(-1))
    stacked = np.column_stack(columns)
    return np.squeeze(stacked)


def hist_simpleboot(x, do_rug=False, xlab="Bootstrap samples", main="", ax=None, **kwargs):
    """Histogram of the first bootstrap replicate, with the original estimate marked."""
    replicates = np.asarray(x.t, dtype=float)[:, 0]
    t0 = np.asarray(x.t0, dtype=float).reshape(-1)
    created = ax is None
    if created:
        _, ax = plt.subplots()
    ax.hist(replicates, **kwargs)
    if do_rug:
        ax.plot(replicates, np.full(replicates.shape, ax.get_ylim()[0]), "|", color="0.2")
    ax.axvline(float(t0[0]), color="C3", linestyle=":")
    ax.set_xlabel(xlab)
    ax.set_title(main)
    return None
