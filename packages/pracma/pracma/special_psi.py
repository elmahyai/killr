"""Polygamma function."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.special_common import is_complex_value, is_numeric_value
from pracma.special_gamma import _CC, _G

_MISSING = object()
_ROOTS = np.array(
    [
        -4.1614709798720630 - 0.14578107125196249j,
        -4.1614709798720630 + 0.14578107125196249j,
        -4.3851935502539474 - 0.19149326909941256j,
        -4.3851935502539474 + 0.19149326909941256j,
        -4.0914355423005926,
        -5.0205261882982271,
        -5.9957952053472399,
        -7.0024851819328395,
        -7.9981186370233868,
        -9.0013449037361806,
        -9.9992157162305535,
        -11.0003314815563886,
        -11.9999115102434217,
        -13.0000110489923175587,
    ],
    dtype=np.complex128,
)


def _sign_pow(n):
    return -1.0 if int(n) % 2 else 1.0


def _digamma(z):
    values = np.asarray(z, dtype=np.complex128)
    numerator = np.zeros(values.shape, dtype=np.complex128)
    denominator = np.zeros(values.shape, dtype=np.complex128)
    for index in range(len(_CC) - 1, 0, -1):
        step = 1.0 / (values + index - 1)
        term = _CC[index] * step
        denominator = denominator + term
        numerator = numerator - term * step
    denominator = denominator + _CC[0]
    gg = values + _G - 0.5
    return np.log(gg) + (numerator / denominator - _G / gg)


def _polygamma_right(z, order):
    values = np.asarray(z, dtype=np.complex128)
    total = np.zeros(values.shape, dtype=np.complex128)
    for index in range(len(_ROOTS) - 1, -1, -1):
        total = total + (
            1.0 / (values - _ROOTS[index]) ** (order + 1)
            - 1.0 / (values + index) ** (order + 1)
        )
    total = _sign_pow(order) * math.gamma(order + 1) * total
    zgh = values + (_G - 0.5)
    total = _sign_pow(order + 1) * (
        math.gamma(order) * zgh ** (-order) + _G * math.gamma(order + 1) * zgh ** (-(order + 1))
    ) + total
    return total


def psi(k, z=_MISSING):
    if z is _MISSING:
        z = k
        k = 0
    if not is_numeric_value(z) and not is_complex_value(z):
        raise PracmaError("is.numeric(z) || is.complex(z) is not TRUE")
    order_values = np.asarray(k)
    if order_values.size > 1 or float(np.real(order_values.reshape(-1)[0])) < 0:
        raise PracmaError("Argument 'k': Invalid Polygamma order, or 'k' not a scalar.")
    order = math.floor(float(np.real(order_values.reshape(-1)[0])))
    was_real = not is_complex_value(z)
    shape = np.shape(np.asarray(z))
    original = np.ravel(np.asarray(z, dtype=np.float64 if was_real else np.complex128), order="F")
    work = np.array(original, dtype=np.complex128, copy=True)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        if order == 0:
            reflect = np.real(work) < 0.5
            if np.any(reflect):
                work = np.array(work, copy=True)
                work[reflect] = 1.0 - work[reflect]
            values = _digamma(work)
            if np.any(reflect):
                values = np.array(values, copy=True)
                values[reflect] = values[reflect] - np.pi / np.tan(np.pi * original[reflect])
            if original.size > 1:
                raise PracmaError(
                    f"'length = {original.size}' in coercion to 'logical(1)'"
                )
            item = original.reshape(-1)[0] if original.size else 0
            if original.size == 1 and np.round(item) == item and np.real(item) <= 0 and np.imag(item) == 0:
                values = np.array([np.inf], dtype=np.complex128)
        elif order > 0:
            negative = np.real(original) < 0
            positive = ~negative
            values = np.zeros(original.shape, dtype=np.complex128)
            if np.any(negative):
                values[negative] = _shift_negative(original[negative], order)
            if np.any(positive):
                values[positive] = _polygamma_right(original[positive], order)
        else:
            raise PracmaError("Argument 'k': Invalid Polygamma order.")
    if was_real:
        values = np.real(values).astype(float)
    if len(shape) >= 2:
        return np.reshape(values, shape, order="F")
    return values


def _shift_negative(zneg, order):
    shift = 500
    moved = psi(order, np.asarray(zneg) + shift)
    total = np.zeros(np.shape(zneg), dtype=np.complex128)
    base = np.asarray(zneg, dtype=np.complex128)
    for step in range(shift - 1, -1, -1):
        total = total + (base + step) ** (-(order + 1))
    total = -_sign_pow(order) * math.gamma(order + 1) * total
    return np.asarray(moved, dtype=np.complex128) + total
