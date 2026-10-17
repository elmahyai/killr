"""Complex gamma and the incomplete gamma functions."""

from __future__ import annotations

import math
import warnings

import numpy as np

from pracma._util import PracmaError
from pracma.special_common import is_complex_value, is_numeric_value, length_of

_G = 607.0 / 128.0
_CC = np.array(
    [
        0.99999999999999709182,
        57.156235665862923517,
        -59.597960355475491248,
        14.136097974741747174,
        -0.49191381609762019978,
        0.33994649984811888699e-4,
        0.46523628927048575665e-4,
        -0.98374475304879564677e-4,
        0.15808870322491248884e-3,
        -0.21026444172410488319e-3,
        0.21743961811521264320e-3,
        -0.16431810653676389022e-3,
        0.84418223983852743293e-4,
        -0.26190838401581408670e-4,
        0.36899182659531622704e-5,
    ]
)
_SQ2PI = 2.5066282746310005024157652848110


def _gamma_real(value):
    number = float(value)
    if number <= 0.0 and number == math.floor(number):
        return math.nan
    return math.gamma(number)


def gammaz(z):
    if not is_numeric_value(z) and not is_complex_value(z):
        raise PracmaError("Argument 'z' must be a numeric or complex vector.")
    was_real = not is_complex_value(z)
    original = np.ravel(
        np.asarray(z, dtype=np.float64 if was_real else np.complex128),
        order="F",
    )
    zz = np.array(original, copy=True)
    work = np.array(original, copy=True)
    negative = np.real(work) < 0
    if np.any(negative):
        work = np.array(work, copy=True)
        work[negative] = -work[negative]
    work = work - 1
    zh = work + 0.5
    zgh = zh + _G
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        zp = zgh ** (zh * 0.5)
        ss = np.zeros(work.shape, dtype=work.dtype)
        for k in range(len(_CC) - 1, 0, -1):
            ss = ss + _CC[k] / (work + k)
        f = (_SQ2PI * (_CC[0] + ss)) * ((zp * np.exp(-zgh)) * zp)
        exact = (work == 0) | (work == 1)
        f = np.array(f, copy=True)
        f[exact] = 1.0
        if np.any(negative):
            f[negative] = -np.pi / (zz[negative] * f[negative] * np.sin(np.pi * zz[negative]))
        poles = (np.round(zz) == zz) & (np.imag(np.asarray(zz, dtype=np.complex128)) == 0) & (np.real(zz) <= 0)
        if np.any(poles):
            f = np.array(f, dtype=np.result_type(f, np.float64), copy=True)
            f[poles] = np.inf
    if was_real:
        return np.real(f).astype(float)
    return f


def _upper_gamma(x, a):
    """Upper incomplete gamma, the same quantity as gamma(a) * pgamma(x, a, lower=FALSE)."""
    log_pref = -x + a * math.log(x)
    if x < a + 1.0:
        term = 1.0 / a
        total = term
        for k in range(1, 10000):
            term *= x / (a + k)
            total += term
            if abs(term) < abs(total) * 1e-16:
                break
        lower = math.exp(log_pref) * total
        return _gamma_real(a) - lower
    tiny = 1e-30
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 10000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return math.exp(log_pref) * h


def gammainc(x, a):
    if not is_numeric_value(a) or not is_numeric_value(x):
        raise PracmaError("All arguments must be real numbers.")
    if length_of(a) > 1 or length_of(x) > 1:
        raise PracmaError("Arguments must be of length 1; function is not vectorized.")
    a = float(np.asarray(a).reshape(-1)[0])
    x = float(np.asarray(x).reshape(-1)[0])
    if a < 0:
        raise PracmaError("Argument 'a' must be real and nonnegative.")
    if x == 0 and a == 0:
        return np.array([0.0, np.inf, 0.0])
    if x == 0:
        return np.array([0.0, _gamma_real(a), 0.0])
    if x > 0:
        xam = -x + a * math.log(x)
    else:
        xam = -x + a * cmath_log(x)
    if abs(xam) > 700.0 or abs(a) > 170.0:
        warnings.warn("Arguments 'x' and/or 'a' are too large.", RuntimeWarning)
        return np.array([np.nan])
    gin = 0.0
    gim = 0.0
    gip = 0.0
    if x == 0.0:
        ga = _gamma_real(a)
        gim = ga
        gip = 0.0
    elif x <= 1.0 + a:
        s = 1.0 / a
        r = s
        for k in range(1, 61):
            r = r * x / (a + k)
            s = s + r
            if abs(r / s) < 1e-15:
                break
        gin = cmath_exp(xam) * s
        ga = _gamma_real(a)
        gip = gin / ga
        gim = ga - gin
    else:
        t0 = 0.0
        for k in range(60, 0, -1):
            t0 = (k - a) / (1.0 + k / (x + t0))
        gim = cmath_exp(xam) / (x + t0)
        ga = _gamma_real(a)
        gin = ga - gim
        gip = 1.0 - gim / ga
    return np.array([np.real(gin), np.real(gim), np.real(gip)], dtype=float)


def cmath_log(x):
    return complex(np.log(complex(x)))


def cmath_exp(x):
    return np.exp(x)


def incgam(x, a):
    if not is_numeric_value(a) or not is_numeric_value(x):
        raise PracmaError("All arguments must be real numbers.")
    if length_of(a) > 1 or length_of(x) > 1:
        raise PracmaError("Arguments must be of length 1; function is not vectorized.")
    a = float(np.asarray(a).reshape(-1)[0])
    x = float(np.asarray(x).reshape(-1)[0])
    if x > 0:
        if a > 0:
            return np.array([_upper_gamma(x, a)])
        if a == 0:
            from pracma.special_expint import expint_E1

            return np.atleast_1d(np.asarray(expint_E1(x), dtype=float))
        if a < 0 and a >= -1:
            return np.array([-1.0 * x**a * math.exp(-x) / a + float(incgam(x, a + 1)[0]) / a])
        raise PracmaError("Not yet implemented: use recursion -- see help")
    if x == 0:
        return np.array([_gamma_real(a)])
    raise PracmaError("Not implemented: Result for 'x<0' will be complex.")
