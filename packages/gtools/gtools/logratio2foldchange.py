"""Log-ratio to fold-change from gtools 3.9.5.

``base^logratio``, then ``-1 / value`` when that power is below one, otherwise
the power itself, with R recycling and array rules.
"""

from __future__ import annotations

import numpy as np

from gtools.foldchange import _ifelse, _unary_minus
from gtools.logit import (
    _ONE,
    _binary,
    _cast,
    _divide,
    _higher,
    _materialize,
    _prepare,
)

_NA_LOGICAL = np.int8(2)
_COMPLEX_COMPARE = "invalid comparison with complex values"


def logratio2foldchange(logratio, base=2):
    """Fold-change from log-ratio values with exponential ``base``."""
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        ratios = _prepare(logratio)
        bases = _prepare(base)
        powered = _binary(bases, ratios, _power)
        below_one = _binary(powered, _ONE, _less_than)
        reciprocal = _binary(_unary_minus(_ONE), powered, _divide)
        return _materialize(_ifelse(below_one, reciprocal, powered))


def _power(left, right, left_kind, right_kind):
    kind = _higher(left_kind, right_kind)
    if kind == "complex":
        base = _cast(left, left_kind, "complex")
        exponent = _cast(right, right_kind, "complex")
        return np.power(base, exponent), "complex", None
    base = _cast(left, left_kind, "double")
    exponent = _cast(right, right_kind, "double")
    return np.power(base, exponent), "double", None


def _less_than(left, right, left_kind, right_kind):
    kind = _higher(left_kind, right_kind)
    if kind == "complex":
        raise ValueError(_COMPLEX_COMPARE)
    if kind == "integer":
        first = np.asarray(left, dtype=np.int64)
        second = np.asarray(right, dtype=np.int64)
        missing = (first == np.int64(-2147483648)) | (second == np.int64(-2147483648))
        out = np.empty(first.shape, dtype=np.int8)
        keep = ~missing
        out[keep] = np.int8(first[keep] < second[keep])
        out[~keep] = _NA_LOGICAL
        return out, "logical", None
    first = _cast(left, left_kind, "double")
    second = _cast(right, right_kind, "double")
    missing = _is_na_real(first) | _is_na_real(second)
    out = np.empty(first.shape, dtype=np.int8)
    keep = ~missing
    out[keep] = np.int8(first[keep] < second[keep])
    out[~keep] = _NA_LOGICAL
    return out, "logical", None


def _is_na_real(values):
    array = np.asarray(values, dtype=np.float64)
    missing = np.isnan(array)
    if array.size:
        bits = array.view(np.uint64)
        missing |= bits == np.uint64(0x7FF00000000007A2)
    return missing
