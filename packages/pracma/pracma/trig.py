"""Degree trigonometric functions and the one-line reciprocal helpers."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import as_1d

_PI = math.pi


def sind(x):
    return np.sin(_PI * as_1d(x) / 180.0)


def cosd(x):
    return np.cos(_PI * as_1d(x) / 180.0)


def tand(x):
    values = as_1d(x)
    return np.sin(_PI * values / 180.0) / np.cos(_PI * values / 180.0)


def cotd(x):
    return 1.0 / tand(x)


def asind(x):
    return np.arcsin(as_1d(x)) * 180.0 / _PI


def acosd(x):
    return np.arccos(as_1d(x)) * 180.0 / _PI


def atand(x):
    return np.arctan(as_1d(x)) * 180.0 / _PI


def acotd(x):
    return atand(1.0 / as_1d(x))


def atan2d(x1, x2):
    return np.arctan2(as_1d(x1), as_1d(x2)) * 180.0 / _PI


def secd(x):
    return 1.0 / cosd(x)


def cscd(x):
    return 1.0 / sind(x)


def cot(z):
    return 1.0 / np.tan(as_1d(z))


def csc(z):
    return 1.0 / np.sin(as_1d(z))


def sec(z):
    return 1.0 / np.cos(as_1d(z))


def acot(z):
    return np.arctan(1.0 / as_1d(z))


def acsc(z):
    return np.arcsin(1.0 / as_1d(z))


def asec(z):
    return np.arccos(1.0 / as_1d(z))


def asecd(x):
    return asec(x) * 180.0 / _PI


def acscd(x):
    return acsc(x) * 180.0 / _PI


def coth(z):
    return 1.0 / np.tanh(as_1d(z))


def csch(z):
    return 1.0 / np.sinh(as_1d(z))


def sech(z):
    return 1.0 / np.cosh(as_1d(z))


def acoth(z):
    return np.arctanh(1.0 / as_1d(z))


def acsch(z):
    return np.arcsinh(1.0 / as_1d(z))


def asech(z):
    return np.arccosh(1.0 / as_1d(z))
