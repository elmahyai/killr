"""Link densities and their gradients from ordinal 2026.7-26 src/links.c."""

import math

import numpy as np
from scipy.special import gammaln
from scipy.stats import gamma, norm

_SQRT_2PI = math.sqrt(2.0 * math.pi)


def _dnorm(x, give_log=False):
    log_d = -0.5 * x * x - math.log(_SQRT_2PI)
    return log_d if give_log else math.exp(log_d)


def _as_float_list(values):
    array = np.asarray(values, dtype=float).reshape(-1)
    return array


def glogis(x):
    """Gradient of the logistic density."""
    values = _as_float_list(x)
    out = np.empty(values.size)
    for i, value in enumerate(values):
        if not math.isfinite(value):
            out[i] = 0.0 if math.isinf(value) else value
            continue
        sign = value > 0.0
        z = math.exp(-abs(value))
        z = 2.0 * z * z * (1.0 + z) ** -3 - z * (1.0 + z) ** -2
        out[i] = z if sign else -z
    return out


def gnorm(x):
    """Gradient of the standard normal density."""
    values = _as_float_list(x)
    out = np.empty(values.size)
    for i, value in enumerate(values):
        if not math.isfinite(value):
            out[i] = 0.0 if math.isinf(value) else value
            continue
        out[i] = -value * _dnorm(value)
    return out


def gcauchy(x):
    """Gradient of the Cauchy density."""
    values = _as_float_list(x)
    out = np.empty(values.size)
    for i, value in enumerate(values):
        if not math.isfinite(value):
            out[i] = 0.0 if math.isinf(value) else value
            continue
        out[i] = -2.0 * value / math.pi * (1.0 + value * value) ** -2
    return out


def _exp(x):
    """exp that returns inf instead of raising, as the C code does."""
    return math.inf if x > 709.0 else math.exp(x)


def _pgumbel_max(q, location, scale, lower_tail):
    if not math.isfinite(q):
        if math.isnan(q):
            return q
        prob = 1.0 if q > 0 else 0.0
    else:
        z = (q - location) / scale
        prob = math.exp(-_exp(-z))
    return prob if lower_tail else 1.0 - prob


def _pgumbel_min(q, location, scale, lower_tail):
    # The C wrapper is 1 - pgumbel(-q), including the infinite cases.
    return 1.0 - _pgumbel_max(-q, location, scale, lower_tail)


def pgumbel(q, location=0.0, scale=1.0, lower_tail=True, max=True):
    """Gumbel cdf. max=True is the right-skew log-log form."""
    values = _as_float_list(q)
    fn = _pgumbel_max if max else _pgumbel_min
    return np.array([fn(float(value), float(location), float(scale), bool(lower_tail)) for value in values])


def _dgumbel_max(x, location, scale, log):
    if math.isnan(x):
        return x
    if math.isinf(x):
        return 0.0
    z = (x - location) / scale
    log_d = -_exp(-z) - z - math.log(scale)
    return log_d if log else _exp(log_d)


def _dgumbel_min(x, location, scale, log):
    if math.isnan(x):
        return x
    if math.isinf(x):
        return 0.0
    z = (-x - location) / scale
    log_d = -_exp(-z) - z - math.log(scale)
    return log_d if log else _exp(log_d)


def dgumbel(x, location=0.0, scale=1.0, log=False, max=True):
    """Gumbel density."""
    values = _as_float_list(x)
    fn = _dgumbel_max if max else _dgumbel_min
    return np.array([fn(float(value), float(location), float(scale), bool(log)) for value in values])


def _ggumbel_max(x):
    if not math.isfinite(x):
        return 0.0 if math.isinf(x) else x
    z = _exp(-x)
    if math.isinf(z):
        return 0.0
    eq = math.exp(-z)
    return -eq * z + eq * z * z


def ggumbel(x, max=True):
    """Gradient of the unit Gumbel density."""
    values = _as_float_list(x)
    if max:
        return np.array([_ggumbel_max(float(value)) for value in values])
    return np.array([-_ggumbel_max(-float(value)) for value in values])


def qgumbel(p, location=0.0, scale=1.0, lower_tail=True, max=True):
    """Gumbel quantile."""
    values = _as_float_list(p)
    if not lower_tail:
        values = 1.0 - values
    if max:
        return location - scale * np.log(-np.log(values))
    return location + scale * np.log(-np.log(1.0 - values))


def _plgamma_one(eta, lambda_):
    if math.isnan(eta) or math.isnan(lambda_):
        return math.nan
    if math.isinf(eta):
        return 1.0 if eta > 0 else 0.0
    if abs(lambda_) <= 1.0e-6:
        return float(norm.cdf(eta))
    shape = lambda_ ** -2
    v = shape * math.exp(lambda_ * eta)
    if lambda_ < 1.0e-6:
        v = 1.0 - float(gamma.cdf(v, a=shape, scale=1.0))
    if lambda_ > -1.0e-6:
        v = float(gamma.cdf(v, a=shape, scale=1.0))
    if -1.0e-6 <= lambda_ <= 1.0e-6:
        v = float(norm.cdf(eta))
    return v


def plgamma(q, lambda_, lower_tail=True):
    """Log-gamma cdf used as a flexible link."""
    values = _as_float_list(q)
    lam = float(np.asarray(lambda_, dtype=float).reshape(-1)[0])
    out = np.array([_plgamma_one(float(value), lam) for value in values])
    if not lower_tail:
        out = 1.0 - out
    return out


def _dlgamma_one(x, lambda_, give_log):
    if math.isnan(x) or math.isnan(lambda_):
        return math.nan
    if math.isinf(x):
        return 0.0
    if abs(lambda_) < 1.0e-5:
        return _dnorm(x, give_log)
    q2 = lambda_ ** -2
    z = x * lambda_
    log_d = math.log(abs(lambda_)) + q2 * math.log(q2) - gammaln(q2) + q2 * (z - math.exp(z))
    return log_d if give_log else math.exp(log_d)


def dlgamma(x, lambda_, log=False):
    """Log-gamma density."""
    if np.asarray(lambda_).size != 1 or np.asarray(log).size != 1:
        raise ValueError("lambda and log must have length 1")
    values = _as_float_list(x)
    lam = float(lambda_)
    return np.array([_dlgamma_one(float(value), lam, bool(log)) for value in values])


def glgamma(x, lambda_):
    """Gradient of the log-gamma density."""
    if np.asarray(lambda_).size != 1:
        raise ValueError("lambda must have length 1")
    values = _as_float_list(x)
    lam = float(np.asarray(lambda_, dtype=float).reshape(-1)[0])
    out = np.empty(values.size)
    for i, value in enumerate(values):
        value = float(value)
        if math.isnan(value) or math.isnan(lam):
            out[i] = math.nan
            continue
        if math.isinf(value):
            out[i] = 0.0
            continue
        if abs(lam) < 1.0e-5:
            out[i] = -value * _dnorm(value)
            continue
        z = math.exp(lam * value)
        if math.isinf(z) or z == 0.0:
            out[i] = 0.0
            continue
        y = _dlgamma_one(value, lam, False)
        out[i] = 0.0 if y <= 0.0 else y * (1.0 - math.exp(lam * value)) / lam
    return out
