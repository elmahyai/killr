"""Gamma quantile, matching R stats::qgamma with scale = 1."""

import math

from survival.norm import qnorm

_MACHEP = 2.2204460492503131e-16


def _pgamma_raw(x, shape):
    if x <= 0.0:
        return 0.0
    ax = shape * math.log(x) - x - math.lgamma(shape)
    if ax < -709.0:
        return 1.0 if x > shape else 0.0
    if x <= 1.0 or x <= shape:
        sum_ = term = 1.0 / shape
        for n in range(1, 1000):
            term *= x / (shape + n)
            sum_ += term
            if term < sum_ * _MACHEP:
                break
        return math.exp(ax) * sum_
    sum_ = term = 1.0
    for n in range(1, 1000):
        term *= (shape - n) / x
        sum_ += term
        if abs(term) < abs(sum_) * _MACHEP:
            break
    return 1.0 - math.exp(ax) / x * sum_


def _dgamma_raw(x, shape):
    if x <= 0.0:
        return 0.0
    return math.exp((shape - 1.0) * math.log(x) - x - math.lgamma(shape))


def qgamma(p, shape, scale=1.0):
    """Lower-tail gamma quantile (R qgamma with rate = 1/scale)."""
    if math.isnan(p) or math.isnan(shape) or math.isnan(scale):
        return math.nan
    if shape <= 0.0 or scale <= 0.0:
        return math.nan
    if p <= 0.0:
        return 0.0 if p == 0.0 else math.nan
    if p >= 1.0:
        return math.inf if p == 1.0 else math.nan
    return _solve_qgamma(p, shape) * scale


def _initial_qgamma(p, shape):
    t = shape - 1.0 / 3.0
    if t <= 0.0:
        return max(1e-300, shape * 1e-6)
    c = 1.0 / (3.0 * math.sqrt(t))
    x = t * (1.0 - c * (qnorm(p) + c * (2.0 / 3.0))) ** 3
    if x <= 0.0:
        return max(1e-300, shape * 1e-6)
    return x


def _solve_qgamma(p, shape):
    lo = 0.0
    hi = max(shape + 10.0 * math.sqrt(shape), 1.0)
    while _pgamma_raw(hi, shape) < p:
        hi *= 2.0
        if hi > 1e300:
            break

    x = _initial_qgamma(p, shape)
    if x <= lo or x >= hi or abs(_pgamma_raw(x, shape) - p) > 0.25:
        x = (lo + hi) / 2.0

    for _ in range(32):
        cdf = _pgamma_raw(x, shape)
        err = cdf - p
        if abs(err) < 1e-14 * max(1.0, p):
            return x
        pdf = _dgamma_raw(x, shape)
        if pdf > 0.0:
            trial = x - err / pdf
            if lo < trial < hi:
                x = trial
                continue
        x = (lo + hi) / 2.0
        cdf = _pgamma_raw(x, shape)
        if cdf < p:
            lo = x
        else:
            hi = x
    return x
