"""Distribution CDF implementations used by the lmom wrappers."""
from __future__ import annotations

import numpy as np
from scipy import optimize, special, stats


def arr(x):
    return np.asarray(x, dtype=float)


def scalarize(x, value):
    value = np.asarray(value, dtype=float)
    return float(value) if np.ndim(x) == 0 else value


def exp_cdf(x, xi, alpha):
    x = arr(x)
    y = np.where(x <= xi, 0.0, -np.expm1(-(x - xi) / alpha))
    return y


def gam_cdf(x, shape, scale):
    return stats.gamma.cdf(arr(x), shape, scale=scale)


def gev_cdf(x, xi, alpha, k):
    x = arr(x)
    z = (x - xi) / alpha
    if abs(k) < 1e-12:
        return np.exp(-np.exp(-z))
    t = 1.0 - k * z
    return np.where(t > 0, np.exp(-np.power(t, 1.0 / k)),
                    np.where(k > 0, 1.0, 0.0))


def glo_cdf(x, xi, alpha, k):
    x = arr(x)
    z = (x - xi) / alpha
    if abs(k) < 1e-12:
        return 1.0 / (1.0 + np.exp(-z))
    t = 1.0 - k * z
    return np.where(t > 0, np.power(1.0 + np.power(t, 1.0 / k), -1.0),
                    np.where(k > 0, 0.0, 1.0))


def gno_cdf(x, xi, alpha, k):
    # GNO quantile: xi + alpha * (1-exp(-k z))/k, z~N(0,1).
    x = arr(x)
    if abs(k) < 1e-12:
        return stats.norm.cdf((x - xi) / alpha)
    q = 1.0 - k * (x - xi) / alpha
    z = -np.log(q) / k
    return np.where(q > 0, stats.norm.cdf(z), np.where(k > 0, 1.0, 0.0))


def gpa_cdf(x, xi, alpha, k):
    x = arr(x)
    y = (x - xi) / alpha
    if abs(k) < 1e-12:
        return np.where(y >= 0, -np.expm1(-y), 0.0)
    t = 1.0 - k * y
    return np.where(y >= 0, np.where(t > 0, 1.0 - np.power(t, 1.0 / k),
                                      1.0 if k > 0 else 0.0), 0.0)


def gum_cdf(x, xi, alpha):
    return np.exp(-np.exp(-(arr(x) - xi) / alpha))


def kap_cdf(x, xi, alpha, k, h):
    x = arr(x)
    out = np.empty_like(x)
    flat = out.flat
    for i, value in enumerate(x.flat):
        def q(u):
            if not 0.0 < u < 1.0:
                return -np.inf if u <= 0 else np.inf
            z = -np.log(u)
            if abs(k) < 1e-12:
                return xi + alpha * (z ** (-h) - 1.0) / h if abs(h) > 1e-12 else xi - alpha * np.log(z)
            return xi + alpha * (1.0 - z ** h) / k
        lo, hi = 1e-14, 1.0 - 1e-14
        if value <= q(lo):
            flat[i] = 0.0
        elif value >= q(hi):
            flat[i] = 1.0
        else:
            flat[i] = optimize.brentq(lambda u: q(u) - value, lo, hi)
    return out


def ln3_cdf(x, xi, alpha, k):
    y = arr(x)
    if abs(k) < 1e-12:
        return stats.norm.cdf(np.log(np.maximum(y - xi, 0.0)) / alpha)
    z = np.log(np.maximum(y - xi, 0.0))
    return gno_cdf(z, 0.0, alpha, k)


def nor_cdf(x, xi, alpha):
    return stats.norm.cdf((arr(x) - xi) / alpha)


def pe3_cdf(x, xi, beta, gamma):
    x = arr(x)
    if abs(gamma) < 1e-12:
        return nor_cdf(x, xi, beta * np.sqrt(np.pi / 2.0))
    shape = 4.0 / (gamma * gamma)
    scale = abs(beta * gamma) / 2.0
    y = (x - xi) / scale
    return np.where(gamma > 0, stats.gamma.cdf(y, shape, scale=1.0),
                    stats.gamma.sf(y, shape, scale=1.0))


def wei_cdf(x, xi, alpha, beta):
    y = (arr(x) - xi) / alpha
    return np.where(y > 0, -np.expm1(-np.power(y, beta)), 0.0)


def wak_cdf(x, xi, a, b, c, d):
    x = arr(x)
    out = np.empty_like(x)
    def q(u):
        return xi + a / (1.0 + b) * (1.0 - u) ** (1.0 + b) + c / (1.0 - d) * (1.0 - (1.0 - u) ** (1.0 - d))
    for i, value in enumerate(x.flat):
        if value <= q(0.0): out.flat[i] = 0.0
        elif value >= q(1.0): out.flat[i] = 1.0
        else: out.flat[i] = optimize.brentq(lambda u: q(u) - value, 0.0, 1.0)
    return out
