"""Smallest non-zero gap in a numeric vector.

A NumPy integer array is an integer vector and resolves to 1. A list or a
floating array is numeric, the same split as ``c(2, 10)`` and ``c(2L, 10L)``.
"""

from __future__ import annotations

import math
import sys
import warnings

import numpy as np

__all__ = ["resolution"]

_TOLERANCE = math.sqrt(sys.float_info.epsilon)
_ZERO_RANGE_TOL = 1000.0 * sys.float_info.epsilon


def resolution(x, zero=True, discrete=False):
    """Smallest gap between adjacent values that exceeds ``sqrt(.Machine$double.eps)``.

    An integer vector, or a vector whose range is constant within the
    relative tolerance used by scales' ``zero_range``, returns 1. With
    ``zero`` true, 0 is included in the gaps. ``discrete`` returns 1 only
    for a vector marked ``mapped_discrete``.
    """
    if _is_integer_vector(x):
        return 1.0
    values = _as_floats(x)
    constant = _zero_range(_range_drop_missing(values))
    if constant is None:
        raise ValueError("missing value where TRUE/FALSE needed")
    if constant:
        return 1.0
    if discrete and _is_mapped_discrete(x):
        return 1.0

    numeric = _unique(values)
    if zero:
        numeric = _unique([0.0, *numeric])
    ordered = sorted(value for value in numeric if not _is_missing(value))
    gaps = [ordered[i + 1] - ordered[i] for i in range(len(ordered) - 1)]
    if all(gap < _TOLERANCE for gap in gaps):
        return 1.0
    kept = [gap for gap in gaps if gap > _TOLERANCE]
    if not kept:
        warnings.warn(
            "no non-missing arguments to min; returning Inf",
            RuntimeWarning,
            stacklevel=2,
        )
        return math.inf
    return float(min(kept))


def _is_integer_vector(x):
    if isinstance(x, np.ndarray) and x.dtype.kind in "iu":
        return True
    return isinstance(x, np.integer) and not isinstance(x, bool)


def _is_mapped_discrete(x):
    if type(x).__name__ == "mapped_discrete":
        return True
    classes = getattr(x, "classes", ())
    if isinstance(classes, str):
        return classes == "mapped_discrete"
    return "mapped_discrete" in tuple(classes)


def _as_floats(x):
    if x is None:
        return []
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
    if value is None:
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


def _range_drop_missing(values):
    present = [value for value in values if not _is_missing(value)]
    if not present:
        warnings.warn(
            "no non-missing arguments to min; returning Inf",
            RuntimeWarning,
            stacklevel=3,
        )
        warnings.warn(
            "no non-missing arguments to max; returning -Inf",
            RuntimeWarning,
            stacklevel=3,
        )
        return (math.inf, -math.inf)
    return (min(present), max(present))


def _zero_range(pair):
    """Relative constant-range test, the same rule as scales' ``zero_range``."""
    left, right = pair
    if _is_missing(left) or _is_missing(right):
        return None
    if left == right:
        return True
    if math.isinf(left) or math.isinf(right):
        return False
    scale = min(abs(left), abs(right))
    if scale == 0.0:
        return False
    return abs((left - right) / scale) < _ZERO_RANGE_TOL


def _unique(values):
    kept = []
    for value in values:
        if any(value == previous for previous in kept):
            continue
        kept.append(value)
    return kept
