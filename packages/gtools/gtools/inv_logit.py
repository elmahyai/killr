"""Generalized inverse logit from gtools 3.9.5.

``p = exp(x) / (1 + exp(x))``, with ``+Inf`` mapped to ``p = 1``, then
``p * (max - min) + min``. ``min`` and ``max`` follow the same recycling
rules as ``logit``.
"""

from __future__ import annotations

import numpy as np

from gtools.logit import (
    _Atom,
    _ONE,
    _binary,
    _cast,
    _divide,
    _higher,
    _materialize,
    _prepare,
    _recycle,
    _subtract,
)


def inv_logit(x, min=0, max=1):
    """Generalized inverse logit of ``x`` on the interval from ``min`` to ``max``."""
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        left = _prepare(x)
        lower = _prepare(min)
        upper = _prepare(max)
        exponent = _exponential(left)
        denominator = _binary(_ONE, exponent, _add)
        proportion = _binary(exponent, denominator, _divide)
        proportion = _fix_positive_inf(proportion, left)
        span = _binary(upper, lower, _subtract)
        scaled = _binary(proportion, span, _multiply)
        return _materialize(_binary(scaled, lower, _add))


def _exponential(atom):
    if atom.kind == "complex":
        values = np.exp(np.asarray(atom.values, dtype=np.complex128))
        return _Atom(values, atom.shape, "complex")
    values = atom.values if atom.kind == "double" else _cast(atom.values, atom.kind, "double")
    return _Atom(np.exp(np.asarray(values, dtype=np.float64)), atom.shape, "double")


def _add(left, right, left_kind, right_kind):
    kind = _higher(left_kind, right_kind)
    if kind == "double" and left_kind == "double" and right_kind == "double":
        return left + right, "double", None
    return _cast(left, left_kind, kind) + _cast(right, right_kind, kind), kind, None


def _multiply(left, right, left_kind, right_kind):
    kind = _higher(left_kind, right_kind)
    if kind == "integer":
        kind = "double"
    if kind == "double" and left_kind == "double" and right_kind == "double":
        return left * right, "double", None
    return _cast(left, left_kind, kind) * _cast(right, right_kind, kind), kind, None


def _is_na(values, kind):
    if kind == "integer":
        raw = np.asarray(values, dtype=np.int64)
        return raw == np.int64(-2147483648)
    if kind == "complex":
        real = np.real(values)
        imag = np.imag(values)
        return _is_na_real(real) | _is_na_real(imag)
    return _is_na_real(np.asarray(values, dtype=np.float64))


def _is_na_real(values):
    missing = np.isnan(values)
    if values.size:
        bits = np.asarray(values, dtype=np.float64).view(np.uint64)
        missing |= bits == np.uint64(0x7FF00000000007A2)
    return missing


def _fix_positive_inf(proportion, original):
    length = int(proportion.values.size)
    if length == 0:
        return proportion
    x_values = _recycle(original.values, length)
    p_values = np.asarray(proportion.values, dtype=np.float64, copy=True)
    na_p = np.isnan(p_values)
    if p_values.size:
        bits = p_values.view(np.uint64)
        na_p |= bits == np.uint64(0x7FF00000000007A2)
    not_na_x = ~_is_na(x_values, original.kind)
    p_values[na_p & not_na_x] = 1.0
    return _Atom(p_values, proportion.shape, "double")
