"""Theoretical Lorenz curves from CRAN ineq 0.2-13.

The formulas follow ``Lc.exp``, ``Lc.lognorm``, ``Lc.pareto``, ``Lc.singh``,
``Lc.dagum``, and ``theorLc`` in ``R/Lc.R``. Normal probabilities use
``math.erf``. The regularized incomplete beta is the continued fraction
for R's lower-tail ``pbeta`` on the arguments these curves pass.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

_CHOICES = ("Singh-Maddala", "Dagum", "lognorm", "Pareto", "exponential")

_LOGNORM_DEFAULT = "inadmissible parameter. default parameter=1 is used."
_PARETO_DEFAULT = "inadmissible parameter. default parameter=2 is used."
_TWO_DEFAULT = "inadmissible parameter. default parameter=c(2,2) is used."

# Peter Acklam's rational approximation for the standard normal quantile.
# Two Halley steps against math.erf bring it inside the comparison tolerance.
_ACKLAM_A = (
    -3.969683028665376e01,
    2.209460984245205e02,
    -2.759285104469687e02,
    1.383577518672690e02,
    -3.066479806614716e01,
    2.506628277459239e00,
)
_ACKLAM_B = (
    -5.447609879822406e01,
    1.615858368580409e02,
    -1.556989798598866e02,
    6.680131188771972e01,
    -1.328068155288572e01,
)
_ACKLAM_C = (
    -7.784894002430293e-03,
    -3.223964580411365e-01,
    -2.400758277161838e00,
    -2.549732539343734e00,
    4.374664141464968e00,
    2.938163982698783e00,
)
_ACKLAM_D = (
    7.784695709041462e-03,
    3.224671290700398e-01,
    2.445134137142996e00,
    3.754408661907416e00,
)
_ACKLAM_LOW = 0.02425
_ACKLAM_HIGH = 1.0 - _ACKLAM_LOW

_SQRT2 = math.sqrt(2.0)
_INV_SQRT_2PI = 1.0 / math.sqrt(2.0 * math.pi)


def _match_arg(type):
    """R ``match.arg`` on the ``theorLc`` distribution names.

    A unique prefix is enough. Matching is case-sensitive. ``None`` selects
    the first name, as R's ``NULL`` does.
    """
    if type is None:
        return _CHOICES[0]
    if not isinstance(type, str):
        raise ValueError("type must be a character string")
    if type == "":
        matches = []
    else:
        matches = [choice for choice in _CHOICES if choice.startswith(type)]
    if len(matches) == 1:
        return matches[0]
    listed = ", ".join(f'"{choice}"' for choice in _CHOICES)
    if not matches:
        raise ValueError(f"type should be one of {listed}")
    raise ValueError("there is more than one match in match.arg")


def _as_float_vector(parameter):
    array = np.asarray(parameter, dtype=np.float64).reshape(-1)
    return array


def _param(parameter, index):
    array = _as_float_vector(parameter)
    if index >= array.size:
        return math.nan
    return float(array[index])


def _pnorm_scalar(z):
    if math.isnan(z):
        return math.nan
    return 0.5 * (1.0 + math.erf(z / _SQRT2))


def _acklam(p):
    if p < _ACKLAM_LOW:
        q = math.sqrt(-2.0 * math.log(p))
        return (
            (((((_ACKLAM_C[0] * q + _ACKLAM_C[1]) * q + _ACKLAM_C[2]) * q + _ACKLAM_C[3]) * q + _ACKLAM_C[4]) * q + _ACKLAM_C[5])
            / ((((_ACKLAM_D[0] * q + _ACKLAM_D[1]) * q + _ACKLAM_D[2]) * q + _ACKLAM_D[3]) * q + 1.0)
        )
    if p > _ACKLAM_HIGH:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(
            (((((_ACKLAM_C[0] * q + _ACKLAM_C[1]) * q + _ACKLAM_C[2]) * q + _ACKLAM_C[3]) * q + _ACKLAM_C[4]) * q + _ACKLAM_C[5])
            / ((((_ACKLAM_D[0] * q + _ACKLAM_D[1]) * q + _ACKLAM_D[2]) * q + _ACKLAM_D[3]) * q + 1.0)
        )
    q = p - 0.5
    r = q * q
    return (
        (((((_ACKLAM_A[0] * r + _ACKLAM_A[1]) * r + _ACKLAM_A[2]) * r + _ACKLAM_A[3]) * r + _ACKLAM_A[4]) * r + _ACKLAM_A[5])
        * q
        / (((((_ACKLAM_B[0] * r + _ACKLAM_B[1]) * r + _ACKLAM_B[2]) * r + _ACKLAM_B[3]) * r + _ACKLAM_B[4]) * r + 1.0)
    )


def _refine_quantile(z, p):
    for _ in range(4):
        cdf = _pnorm_scalar(z)
        err = cdf - p
        if err == 0.0:
            return z
        pdf = math.exp(-0.5 * z * z) * _INV_SQRT_2PI
        if pdf == 0.0 or not math.isfinite(pdf):
            return z
        denom = pdf + 0.5 * z * err
        if denom == 0.0 or not math.isfinite(denom):
            return z
        step = err / denom
        if not math.isfinite(step):
            return z
        z = z - step
        if abs(step) <= 1e-15 * (1.0 + abs(z)):
            return z
    return z


def _qnorm_scalar(p):
    if math.isnan(p):
        return math.nan
    if p == 0.0:
        return -math.inf
    if p == 1.0:
        return math.inf
    if p < 0.0 or p > 1.0:
        return math.nan
    # Acklam is already within 1e-8. Halley, using erf, is stable only
    # while the guess is not far into the tail; a large step means the
    # tail probability cancelled and the rational value should stand.
    z0 = _acklam(p)
    if abs(z0) > 6.0:
        return z0
    z = _refine_quantile(z0, p)
    if abs(z - z0) > 1e-7:
        return z0
    return z


def _betacf(a, b, x):
    """Lentz continued fraction for the incomplete-beta tail factor."""
    max_iter = 300
    eps = 1e-15
    tiny = 1e-300
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _pbeta_scalar(x, a, b):
    """Regularized incomplete beta, lower tail, for positive shapes."""
    if math.isnan(x) or math.isnan(a) or math.isnan(b):
        return math.nan
    if a <= 0.0 or b <= 0.0:
        return math.nan
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_bt = (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log(1.0 - x)
    )
    if log_bt < -745.0:
        bt = 0.0
    else:
        bt = math.exp(log_bt)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def _map_values(values, function):
    array = np.asarray(values, dtype=np.float64)
    flat = np.ascontiguousarray(array).reshape(-1)
    out = np.empty(flat.size, dtype=np.float64)
    for i in range(flat.size):
        out[i] = function(float(flat[i]))
    return out.reshape(array.shape)


def _pbeta(x, a, b):
    aa = float(a)
    bb = float(b)
    return _map_values(x, lambda value: _pbeta_scalar(value, aa, bb))


def _warn_default(message):
    warnings.warn(message, UserWarning, stacklevel=3)


def lc_exp(p):
    """Lorenz curve of the exponential distribution.

    ``p`` may be a scalar or an array. The result is a NumPy array of the
    same shape. The share 1 is undefined, as in R.
    """
    values = np.asarray(p, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        elc = 1.0 / (1.0 - values)
        elc = (1.0 - values) * np.log(elc)
        elc = values - elc
    return np.asarray(elc, dtype=np.float64)


def lc_lognorm(p, parameter=1):
    """Lorenz curve of the lognormal distribution.

    For shares other than 0 and 1 the ordinate is ``pnorm(qnorm(p) - sigma)``.
    A non-positive sigma warns and is replaced by 1.
    """
    sigma = _param(parameter, 0)
    if not sigma > 0.0:
        _warn_default(_LOGNORM_DEFAULT)
        sigma = 1.0
    values = np.asarray(p, dtype=np.float64)
    out = np.array(values, dtype=np.float64, copy=True)
    mask = (values != 0.0) & (values != 1.0)
    if np.any(mask):
        interior = np.ascontiguousarray(values[mask]).reshape(-1)
        adjusted = np.empty(interior.size, dtype=np.float64)
        for i in range(interior.size):
            adjusted[i] = _pnorm_scalar(_qnorm_scalar(float(interior[i])) - sigma)
        out[mask] = adjusted
    return out


def lc_pareto(p, parameter=2):
    """Lorenz curve of the Pareto distribution.

    When ``parameter > 1``, ``k = (parameter - 1) / parameter``. Otherwise
    the call warns and uses ``k = 0.5``. The ordinate is ``1 - (1 - p) ** k``.
    """
    alpha = _param(parameter, 0)
    if alpha > 1.0:
        k = (alpha - 1.0) / alpha
    else:
        _warn_default(_PARETO_DEFAULT)
        k = 0.5
    values = np.asarray(p, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        ordinate = 1.0 - np.power(1.0 - values, k)
    return np.asarray(ordinate, dtype=np.float64)


def _singh_exponents(parameter):
    first = _param(parameter, 0)
    second = _param(parameter, 1)
    if (not math.isnan(second)) and first > 0.0 and first < 2.0 + second:
        return first - 1.0, 1.0 / (second + 1.0)
    _warn_default(_TWO_DEFAULT)
    return 1.0, 1.0 / 3.0


def lc_singh(p, parameter=(2, 2)):
    """Lorenz curve of the Singh-Maddala distribution.

    Admissible parameters use R's transformation and lower-tail ``pbeta``.
    Anything else warns and uses the exponents from ``c(2, 2)``.
    """
    b, d = _singh_exponents(parameter)
    values = np.asarray(p, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        x = 1.0 - np.power(1.0 - values, b)
    return _pbeta(x, 1.0 + d, b - d)


def _dagum_exponents(parameter):
    first = _param(parameter, 0)
    second = _param(parameter, 1)
    if (not math.isnan(second)) and first > 1.0:
        return 1.0 / first, second
    _warn_default(_TWO_DEFAULT)
    return 0.5, 2.0


def lc_dagum(p, parameter=(2, 2)):
    """Lorenz curve of the Dagum distribution.

    Admissible parameters use R's transformation and lower-tail ``pbeta``.
    Anything else warns and uses the exponents from ``c(2, 2)``.
    """
    a, b = _dagum_exponents(parameter)
    values = np.asarray(p, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        x = np.power(values, b)
    return _pbeta(x, a + 1.0 / b, 1.0 - a)


def theorLc(type="Singh-Maddala", parameter=0):
    """Return a Lorenz curve with the distribution and parameters fixed.

    ``type`` follows R ``match.arg`` on Singh-Maddala, Dagum, lognorm,
    Pareto, and exponential. A unique prefix is enough. The exponential
    curve ignores ``parameter``.
    """
    kind = _match_arg(type)
    fixed = tuple(float(value) for value in _as_float_vector(parameter))

    if kind == "Singh-Maddala":
        def curve(p):
            return lc_singh(p, parameter=fixed)

    elif kind == "Dagum":
        def curve(p):
            return lc_dagum(p, parameter=fixed)

    elif kind == "lognorm":
        def curve(p):
            return lc_lognorm(p, parameter=fixed)

    elif kind == "Pareto":
        def curve(p):
            return lc_pareto(p, parameter=fixed)

    else:
        def curve(p):
            return lc_exp(p)

    return curve
