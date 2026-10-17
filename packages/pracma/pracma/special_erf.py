"""Error functions. erf and erfc follow pchisq and pnorm; erfz is the series."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError, as_1d
from pracma.special_common import is_complex_value, is_na, is_numeric_value, length_of

_SQRT2 = math.sqrt(2.0)
_SQRTPI = math.sqrt(math.pi)

# Peter J. Acklam's rational approximation for the inverse normal.
_A = (
    -3.969683028665376e01,
    2.209460984245205e02,
    -2.759285104469687e02,
    1.383577518672690e02,
    -3.066479806614716e01,
    2.506628277459239e00,
)
_B = (
    -5.447609879822406e01,
    1.615858368580409e02,
    -1.556989798598866e02,
    6.680131188771972e01,
    -1.328068155288572e01,
)
_C = (
    -7.784894002430293e-03,
    -3.223964580411365e-01,
    -2.400758277161838e00,
    -2.549732539343734e00,
    4.374664141464968e00,
    2.938163982698783e00,
)
_D = (
    7.784695709041462e-03,
    3.224671290700398e-01,
    2.445134137142996e00,
    3.754408661907416e00,
)


def _pnorm(x):
    return 0.5 * math.erfc(-x / _SQRT2)


def _acklam(p):
    plow = 0.02425
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        return (
            (((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5])
            / ((((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0)
        )
    if p > 1.0 - plow:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(
            (((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5])
            / ((((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0)
        )
    q = p - 0.5
    r = q * q
    return (
        (((((_A[0] * r + _A[1]) * r + _A[2]) * r + _A[3]) * r + _A[4]) * r + _A[5])
        * q
        / (((((_B[0] * r + _B[1]) * r + _B[2]) * r + _B[3]) * r + _B[4]) * r + 1.0)
    )


def _qnorm(p):
    """Inverse of pnorm, refined by Halley's method."""
    if p <= 0.0:
        return -math.inf
    if p >= 1.0:
        return math.inf
    x = _acklam(p)
    for _ in range(3):
        err = _pnorm(x) - p
        if err == 0.0:
            break
        density = math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)
        step = err / density
        x = x - step / (1.0 + x * step / 2.0)
    return x


def erf(x):
    values = as_1d(x)
    return np.array([math.erf(float(item)) for item in values], dtype=float)


def erfc(x):
    values = as_1d(x)
    return np.array([math.erfc(float(item)) for item in values], dtype=float)


def erfcx(x):
    values = as_1d(x)
    with np.errstate(over="ignore"):
        return np.exp(values * values) * erfc(values)


def erfinv(y):
    values = as_1d(y)
    out = np.empty(values.size, dtype=float)
    for index, item in enumerate(values):
        if not np.isfinite(item) or abs(item) > 1.0:
            out[index] = np.nan
        elif item == 0.0:
            out[index] = 0.0
        elif abs(item) == 1.0:
            out[index] = math.copysign(math.inf, item)
        else:
            out[index] = math.copysign(_qnorm((1.0 + abs(item)) / 2.0) / _SQRT2, item)
    return out


def erfcinv(y):
    values = as_1d(y)
    out = np.empty(values.size, dtype=float)
    for index, item in enumerate(values):
        if not np.isfinite(item) or item < 0.0 or item > 2.0:
            out[index] = np.nan
        elif item == 0.0:
            out[index] = math.inf
        elif item == 2.0:
            out[index] = -math.inf
        else:
            out[index] = -_qnorm(item / 2.0) / _SQRT2
    return out


def erfz(z):
    if z is None:
        return None
    if not is_numeric_value(z) and not is_complex_value(z):
        raise PracmaError("Argument 'z' must be a numeric or complex scalar or vector.")
    was_complex = is_complex_value(z)
    dtype = np.complex128 if was_complex else np.float64
    values = np.ravel(np.asarray(z, dtype=dtype), order="F")
    a0 = np.abs(values)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        c0 = np.exp(-values * values)
        z1 = np.where(np.real(values) < 0, -values, values).astype(dtype)
        cer = np.full(values.shape, np.nan, dtype=dtype)
        small = (a0 > 0) & (a0 <= 5.8)
        work = small.copy()
        if np.any(work):
            cs = np.array(z1, copy=True)
            cr = np.array(cs, copy=True)
            for k in range(1, 121):
                active = work
                cr[active] = cr[active] * z1[active] * z1[active] / (k + 0.5)
                cs[active] = cs[active] + cr[active]
                work = work & (np.abs(cr / cs) >= 1e-15)
                if not np.any(work):
                    break
            cer[small] = 2.0 * c0[small] * cs[small] / _SQRTPI
        work = a0 > 5.8
        if np.any(work):
            cl = 1.0 / z1
            cr = np.array(cl, copy=True)
            for k in range(1, 14):
                active = work
                cr[active] = -cr[active] * (k - 0.5) / (z1[active] * z1[active])
                cl[active] = cl[active] + cr[active]
                work = work & (np.abs(cr / cl) >= 1e-15)
                if not np.any(work):
                    break
            outside = ~small
            cer[outside] = 1.0 - c0[outside] * cl[outside] / _SQRTPI
        negative = np.real(values) < 0
        cer[negative] = -cer[negative]
    if not was_complex:
        return np.real(cer).astype(float)
    return cer


def _erfi_one(z):
    if is_na(z):
        return np.nan
    if z == 0:
        return 0.0
    if isinstance(z, (complex, np.complexfloating)):
        return (-1j * np.asarray(erfz(1j * z)).reshape(-1)[0])
    if isinstance(z, (int, float, np.integer, np.floating)):
        return float(np.real(-1j * np.asarray(erfz(1j * complex(float(z)))).reshape(-1)[0]))
    raise PracmaError("Argument 'z' must be a numeric or complex scalar or vector.")


def erfi(z):
    if z is None or length_of(z) == 0:
        return None
    if length_of(z) == 1:
        item = np.asarray(z).reshape(-1)[0]
        return np.array([_erfi_one(item)])
    flat = np.ravel(np.asarray(z), order="F")
    return np.array([_erfi_one(item) for item in flat])
