"""Small numeric helpers from CRAN boot 1.3-32, R/bootfuns.q.

logit and inv.logit are the installed wrappers of qlogis and plogis.
var.linear and k3.linear group strata with tapply when FUN is omitted,
which returns group codes rather than applying a summary.
"""

from __future__ import annotations

import warnings

import numpy as np

__all__ = [
    "corr",
    "cum3",
    "freq_array",
    "inv_logit",
    "k3_linear",
    "logit",
    "var_linear",
]


def corr(d, w=None) -> float:
    """Weighted correlation of the first two columns of d.

    The denominator is sum(w) on the weight vector as supplied. Products
    recycle the shorter argument the way R does, so a length-1 weight does
    not cancel out of the means.
    """
    data = np.asarray(d, dtype=np.float64)
    if data.ndim != 2:
        raise ValueError("incorrect number of dimensions")
    if data.shape[1] < 2:
        raise ValueError("subscript out of bounds")
    x = data[:, 0]
    y = data[:, 1]
    if w is None:
        n = x.size
        weights = np.full(n, 1.0 / n) if n else np.empty(0, dtype=np.float64)
    else:
        weights = np.ravel(np.asarray(w, dtype=np.float64), order="F")
    if x.size == 0 or weights.size == 0:
        return float("nan")
    scale = float(np.sum(weights))
    m1 = _sum_product(x, weights) / scale
    m2 = _sum_product(y, weights) / scale
    with np.errstate(divide="ignore", invalid="ignore"):
        cov = _sum_product(x * y, weights) / scale - m1 * m2
        v1 = _sum_product(x * x, weights) / scale - m1 * m1
        v2 = _sum_product(y * y, weights) / scale - m2 * m2
        return float(cov / np.sqrt(v1 * v2))


def freq_array(i_array) -> np.ndarray:
    """Bootstrap frequency matrix from an R by n index matrix.

    Each row is tabulate(..., nbins = n). Positive values are truncated
    toward zero and counted when that integer is in 1..n. A one-column
    matrix comes back as one row, matching apply before the transpose.
    An empty input comes back as a 1 by 0 integer matrix.
    """
    indices = np.asarray(i_array)
    if indices.ndim != 2:
        raise ValueError("dim(X) must have a positive length")
    replicates, n = indices.shape
    if replicates == 0 or n == 0:
        return np.zeros((1, 0), dtype=np.int32)
    values = np.asarray(indices, dtype=np.float64)
    if np.isinf(values).any():
        warnings.warn(
            "NAs introduced by coercion to integer range",
            RuntimeWarning,
            stacklevel=2,
        )
    with np.errstate(invalid="ignore"):
        truncated = np.trunc(values)
    ok = np.isfinite(truncated) & (truncated >= 1) & (truncated <= n)
    counts = np.zeros((replicates, n), dtype=np.int32)
    row = np.repeat(np.arange(replicates, dtype=np.intp), n)
    chosen = ok.ravel()
    np.add.at(
        counts,
        (row[chosen], truncated.ravel()[chosen].astype(np.intp) - 1),
        np.int32(1),
    )
    if n == 1:
        return np.ascontiguousarray(counts.reshape(1, replicates))
    return counts


def var_linear(L, strata=None) -> float:
    """Variance estimate sum_s sum(L_i^2) / n_s^2 from influence values."""
    return _linear_power(L, strata, 2)


def k3_linear(L, strata=None) -> float:
    """Skewness estimate sum_s sum(L_i^3) / n_s^3 from influence values."""
    return _linear_power(L, strata, 3)


def cum3(a, b=None, c=None, unbiased: bool = True) -> float:
    """Third-order product moment, with the unbiased multiplier by default.

    b and c default to a. Means are taken on each vector before the product
    is recycled to the longest length.
    """
    flag = _as_flag(unbiased)
    left = _as_vector(a)
    mid = left if b is None else _as_vector(b)
    right = left if c is None else _as_vector(c)
    n = left.size
    if n == 0:
        return float("nan") if not flag else 0.0
    total = _recycled_product_sum(
        (left - np.mean(left), mid - np.mean(mid), right - np.mean(right))
    )
    if flag:
        if n < 3:
            return float("nan")
        multiplier = n / ((n - 1.0) * (n - 2.0))
    else:
        multiplier = 1.0 / n
    with np.errstate(invalid="ignore", divide="ignore"):
        return float(multiplier * total)


def logit(p):
    """Logit log(p) - log1p(-p), the same values as R qlogis.

    Values outside [0, 1] become NaN and produce the warning R emits.
    0 and 1 are -inf and inf. A scalar returns a float; an array keeps its shape.
    """
    scalar = np.ndim(p) == 0
    proportions = np.asarray(p, dtype=np.float64)
    invalid = np.isfinite(proportions) & ((proportions < 0.0) | (proportions > 1.0))
    if np.any(invalid):
        warnings.warn("NaNs produced", RuntimeWarning, stacklevel=2)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.log(proportions) - np.log1p(-proportions)
    out = np.where(invalid, np.nan, out)
    if scalar:
        return float(out)
    return out


def inv_logit(x):
    """Inverse logit 1 / (1 + exp(-x)), the same values as R plogis.

    -inf and inf return 0 and 1. A scalar returns a float; an array keeps its shape.
    """
    scalar = np.ndim(x) == 0
    values = np.asarray(x, dtype=np.float64)
    with np.errstate(over="ignore", invalid="ignore"):
        out = 1.0 / (1.0 + np.exp(-values))
    if scalar:
        return float(out)
    return out


def _as_vector(values) -> np.ndarray:
    return np.ravel(np.asarray(values, dtype=np.float64), order="F")


def _sum_product(left: np.ndarray, right: np.ndarray) -> float:
    """sum(left * right) with R's recycling rule."""
    if left.size == right.size:
        return float(np.sum(left * right))
    if left.size == 0 or right.size == 0:
        return 0.0
    width = max(left.size, right.size)
    if width % left.size != 0 or width % right.size != 0:
        warnings.warn(
            "longer object length is not a multiple of shorter object length",
            RuntimeWarning,
            stacklevel=3,
        )
    if left.size != width:
        left = np.resize(left, width)
    if right.size != width:
        right = np.resize(right, width)
    return float(np.sum(left * right))


def _recycled_product_sum(parts: tuple[np.ndarray, ...]) -> float:
    width = max(part.size for part in parts)
    if width == 0 or any(part.size == 0 for part in parts):
        return 0.0
    total = np.ones(width, dtype=np.float64)
    warned = False
    for part in parts:
        if part.size != width:
            if not warned and width % part.size != 0:
                warnings.warn(
                    "longer object length is not a multiple of shorter object length",
                    RuntimeWarning,
                    stacklevel=3,
                )
                warned = True
            part = np.resize(part, width)
        total *= part
    return float(np.sum(total))


def _linear_power(L, strata, power: int) -> float:
    values = _as_vector(L)
    n = values.size
    if n == 0:
        return 0.0
    if strata is None:
        blocks = (values,)
    else:
        keys = _strata_keys(strata, n)
        if keys is None:
            return float("nan")
        _labels, inverse = np.unique(keys, return_inverse=True)
        blocks = [values[inverse == index] for index in range(inverse.max() + 1)]
    total = 0.0
    for block in blocks:
        m = block.size
        total += float(np.sum(block**power) / (m**power))
    return float(total)


def _strata_keys(strata, n: int):
    """Group labels for strata, or None when any value is missing.

    tapply(seq_len(n), as.numeric(strata)) with FUN omitted renumbers the
    sorted distinct values as 1..S. Missing values make every later
    strata == s comparison NA, and the estimate is NA.
    """
    if isinstance(strata, (str, bytes)):
        labels = np.asarray([strata])
    else:
        labels = np.asarray(strata)
    if labels.ndim == 0:
        labels = np.reshape(labels, (1,))
    labels = np.ravel(labels, order="F")
    if labels.size != n:
        raise ValueError("arguments must have same length")
    kind = labels.dtype.kind
    if kind == "b":
        return labels.astype(np.int64)
    if kind in "iu":
        return labels
    if kind == "f":
        if np.isnan(labels).any():
            return None
        return labels
    if kind in "SU":
        return labels
    if kind == "O":
        items = labels.tolist()
        if any(item is None or (isinstance(item, float) and np.isnan(item)) for item in items):
            return None
        if all(isinstance(item, (int, np.integer)) and not isinstance(item, bool) for item in items):
            return np.asarray(items, dtype=np.int64)
        if all(
            isinstance(item, (int, float, np.integer, np.floating)) and not isinstance(item, bool)
            for item in items
        ):
            return np.asarray(items, dtype=np.float64)
        return np.asarray([str(item) for item in items])
    raise TypeError("strata must be numeric or a factor")


def _as_flag(value) -> bool:
    """R's if() on one logical or numeric value."""
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    flags = np.asarray(value)
    if flags.ndim > 0 and flags.size != 1:
        raise ValueError("the condition has length > 1")
    if flags.size == 0:
        raise ValueError("argument is of length zero")
    item = flags.reshape(-1)[0]
    if isinstance(item, (bool, np.bool_)):
        return bool(item)
    if isinstance(item, (float, np.floating)) and np.isnan(item):
        raise ValueError("missing value where TRUE/FALSE needed")
    if item is None:
        raise ValueError("missing value where TRUE/FALSE needed")
    if isinstance(item, (int, float, np.integer, np.floating)):
        return bool(item)
    raise ValueError("missing value where TRUE/FALSE needed")
