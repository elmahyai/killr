"""Fold-change from gtools 3.9.5.

``num / denom`` when ``num >= denom``, otherwise ``-denom / num``, with R
recycling and array rules.
"""

from __future__ import annotations

import warnings

import numpy as np

from gtools.logit import (
    _Atom,
    _binary,
    _cast,
    _divide,
    _higher,
    _materialize,
    _prepare,
)

_NA_INT = np.int32(-(2**31))
_NA_REAL_BITS = np.array([0x7FF00000000007A2], dtype=np.uint64)
_NA_REAL = _NA_REAL_BITS.view(np.float64)[0]
_NA_LOGICAL = np.int8(2)
_OVERFLOW = "NAs produced by integer overflow"
_COMPLEX_COMPARE = "invalid comparison with complex values"


def foldchange(num, denom):
    """Fold-change of ``num`` relative to ``denom``."""
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        left = _prepare(num)
        right = _prepare(denom)
        if left.kind == "complex" or right.kind == "complex":
            raise ValueError(_COMPLEX_COMPARE)
        test = _binary(left, right, _greater_equal)
        positive = _binary(left, right, _divide)
        negative = _binary(_unary_minus(right), left, _divide)
        return _materialize(_ifelse(test, positive, negative))


def _greater_equal(left, right, left_kind, right_kind):
    kind = _higher(left_kind, right_kind)
    if kind == "complex":
        raise ValueError(_COMPLEX_COMPARE)
    if kind == "integer":
        first = np.asarray(left, dtype=np.int64)
        second = np.asarray(right, dtype=np.int64)
        missing = (first == np.int64(-2147483648)) | (second == np.int64(-2147483648))
        out = np.empty(first.shape, dtype=np.int8)
        keep = ~missing
        out[keep] = np.int8(first[keep] >= second[keep])
        out[~keep] = _NA_LOGICAL
        return out, "logical", None
    first = _cast(left, left_kind, "double")
    second = _cast(right, right_kind, "double")
    missing = _is_na_real(first) | _is_na_real(second)
    out = np.empty(first.shape, dtype=np.int8)
    keep = ~missing
    out[keep] = np.int8(first[keep] >= second[keep])
    out[~keep] = _NA_LOGICAL
    return out, "logical", None


def _unary_minus(atom):
    if atom.kind == "integer":
        raw = np.asarray(atom.values, dtype=np.int64)
        missing = raw == np.int64(-2147483648)
        negated = -raw
        overflow = (~missing) & (
            (negated <= np.int64(-2147483648)) | (negated > np.int64(2147483647))
        )
        out = np.empty(raw.shape, dtype=np.int32)
        keep = ~missing & ~overflow
        out[keep] = negated[keep].astype(np.int32)
        out[~keep] = _NA_INT
        flagged = _OVERFLOW if np.any(overflow) else None
        if flagged:
            warnings.warn(flagged, RuntimeWarning, stacklevel=3)
        return _Atom(out, atom.shape, "integer")
    if atom.kind == "complex":
        values = -np.asarray(atom.values, dtype=np.complex128)
        return _Atom(values, atom.shape, "complex")
    values = -np.asarray(_cast(atom.values, atom.kind, "double"), dtype=np.float64)
    return _Atom(values, atom.shape, "double")


def _ifelse(test, yes, no):
    length = int(test.values.size)
    if length == 0:
        return _Atom(np.array([], dtype=np.float64), test.shape, "double")
    t = np.asarray(test.values, dtype=np.int8)
    y = np.asarray(_promote_division(yes), dtype=np.float64)
    n = np.asarray(_promote_division(no), dtype=np.float64)
    out = np.empty(length, dtype=np.float64)
    missing = t == _NA_LOGICAL
    choose_yes = (~missing) & (t != 0)
    choose_no = (~missing) & (t == 0)
    out[choose_yes] = y[choose_yes]
    out[choose_no] = n[choose_no]
    out[missing] = _NA_REAL
    return _Atom(out, test.shape, "double")


def _promote_division(atom):
    if atom.kind == "integer":
        return _cast(atom.values, "integer", "double")
    if atom.kind == "double":
        return atom.values
    return _cast(atom.values, atom.kind, "double")


def _is_na_real(values):
    array = np.asarray(values, dtype=np.float64)
    missing = np.isnan(array)
    if array.size:
        bits = array.view(np.uint64)
        missing |= bits == np.uint64(0x7FF00000000007A2)
    return missing
