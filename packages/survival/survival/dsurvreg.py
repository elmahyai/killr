"""Density for survreg-supported distributions (survival::dsurvreg)."""

from __future__ import annotations

import math
from typing import Any, Callable

import numpy as np

_SQRT2PI = math.sqrt(2.0 * math.pi)


def _recycle(*arrays: np.ndarray) -> tuple[int, list[np.ndarray]]:
    lengths = [int(np.size(arr)) for arr in arrays]
    nn = max(lengths)
    out: list[np.ndarray] = []
    for arr, length in zip(arrays, lengths):
        flat = np.asarray(arr, dtype=float).reshape(-1)
        if nn > 1 and length == 1:
            flat = np.full(nn, flat[0], dtype=float)
        elif length != nn:
            flat = np.resize(flat, nn)
        out.append(flat)
    return nn, out


def _log_trans(y: np.ndarray) -> np.ndarray:
    return np.log(y)


def _dlog_trans(y: np.ndarray) -> np.ndarray:
    return 1.0 / y


def _pnorm(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    inv_sqrt2 = 1.0 / math.sqrt(2.0)
    return np.vectorize(lambda z: 0.5 * math.erfc(-z * inv_sqrt2))(x)


def _dnorm(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    return np.exp(-0.5 * x * x) / _SQRT2PI


def _density_extreme(x: np.ndarray, _parms: Any) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    w = np.exp(x)
    ww = np.exp(-w)
    return np.column_stack((1.0 - ww, ww, w * ww, (1.0 - w), w * (w - 3.0) + 1.0))


def _density_logistic(x: np.ndarray, _parms: Any) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    w = np.exp(x)
    denom = (1.0 + w) ** 2
    return np.column_stack(
        (
            w / (1.0 + w),
            1.0 / (1.0 + w),
            w / denom,
            (1.0 - w) / (1.0 + w),
            (w * (w - 4.0) + 1.0) / denom,
        )
    )


def _density_gaussian(x: np.ndarray, _parms: Any) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    return np.column_stack((_pnorm(x), _pnorm(-x), _dnorm(x), -x, x * x - 1.0))


def _betacf(a: float, b: float, x: float) -> float:
    max_iter = 200
    eps = 3e-14
    am = 1.0
    bm = 1.0
    az = 1.0
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    bz = 1.0 - qab * x / qap
    for index in range(1, max_iter + 1):
        em = float(index)
        tem = em + em
        d = em * (b - em) * x / ((qam + tem) * (a + tem))
        ap = az + d * am
        bp = bz + d * bm
        d = -(a + em) * (qab + em) * x / ((a + tem) * (qap + tem))
        app = ap + d * az
        bpp = bp + d * bz
        am = ap / bpp
        bm = bp / bpp
        az = app / bpp
        bz = 1.0
        if abs(bz) < eps:
            bz = eps
        if abs(az - app / bpp) < eps * abs(az):
            return az
    return az


def _betainc(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    ln_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(a * math.log(x) + b * math.log(1.0 - x) - ln_beta) / a
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x)
    tail = math.exp(b * math.log(1.0 - x) + a * math.log(x) - ln_beta) / b
    return 1.0 - tail * _betacf(b, a, 1.0 - x)


def _pt_lower(value: float, df: float) -> float:
    x = df / (df + value * value)
    prob = 0.5 * _betainc(df / 2.0, 0.5, x)
    if value < 0.0:
        return prob
    return 1.0 - prob


def _pt(x: np.ndarray, df: float) -> np.ndarray:
    flat = np.asarray(x, dtype=float).reshape(-1)
    out = np.array([_pt_lower(float(val), df) for val in flat], dtype=float)
    return out.reshape(np.shape(x))


def _dt(x: np.ndarray, df: float) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    lcoef = math.lgamma((df + 1.0) / 2.0) - math.lgamma(df / 2.0) - 0.5 * (math.log(df) + math.log(math.pi))
    return np.exp(lcoef - (df + 1.0) / 2.0 * np.log1p(x * x / df))


def _density_t(x: np.ndarray, parms: Any) -> np.ndarray:
    if parms is None:
        raise ValueError("missing value for 'parms'")
    df = float(np.asarray(parms, dtype=float).reshape(-1)[0])
    x = np.asarray(x, dtype=float)
    pdf = _dt(x, df)
    cdf = _pt(x, df)
    term1 = -(df + 1.0) * x / (df + x * x)
    term2 = (df + 1.0) * (x * x * (df + 3.0) / (df + x * x) - 1.0) / (df + x * x)
    return np.column_stack((cdf, _pt(-x, df), pdf, term1, term2))


_DENSITY: dict[str, Callable[[np.ndarray, Any], np.ndarray]] = {
    "extreme": _density_extreme,
    "logistic": _density_logistic,
    "gaussian": _density_gaussian,
    "t": _density_t,
}

_ALIASES: dict[str, dict[str, Any]] = {
    "weibull": {"dist": "extreme", "trans": _log_trans, "dtrans": _dlog_trans},
    "exponential": {"dist": "extreme", "trans": _log_trans, "dtrans": _dlog_trans},
    "rayleigh": {"dist": "extreme", "trans": _log_trans, "dtrans": _dlog_trans},
    "loggaussian": {"dist": "gaussian", "trans": _log_trans, "dtrans": _dlog_trans},
    "lognormal": {"dist": "gaussian", "trans": _log_trans, "dtrans": _dlog_trans},
    "loglogistic": {"dist": "logistic", "trans": _log_trans, "dtrans": _dlog_trans},
}


def _lookup_distribution(name: str) -> tuple[str, dict[str, Any] | None]:
    key = str(name).casefold()
    if key in _ALIASES:
        return key, _ALIASES[key]
    if key in _DENSITY:
        return key, None
    raise ValueError("Distribution not found")


def dsurvreg(
    x,
    mean,
    scale=1,
    distribution="weibull",
    parms=None,
):
    """Density for a survreg location-scale family at ``x``."""
    x_arr = np.asarray(x, dtype=float)
    orig_shape = x_arr.shape
    _, (x_vec, mean_vec, scale_vec) = _recycle(
        x_arr.reshape(-1),
        np.asarray(mean, dtype=float),
        np.asarray(scale, dtype=float),
    )
    key, alias = _lookup_distribution(distribution)

    if alias is not None:
        dx = alias["dtrans"](x_vec)
        x_work = alias["trans"](x_vec)
        x_work = (x_work - mean_vec) / scale_vec
        base = _DENSITY[alias["dist"]]
        y = base(x_work, parms)[:, 2]
        out = y * dx / scale_vec
    else:
        x_work = (x_vec - mean_vec) / scale_vec
        y = _DENSITY[key](x_work, parms)[:, 2]
        out = y / scale_vec

    if orig_shape == ():
        return float(out[0])
    return out.reshape(orig_shape)
