"""Densities and random draws for the multivariate normal and t."""

from __future__ import annotations

import math
import warnings

import numpy as np

from extradistr._rgen import rchisq
from extradistr._rng import norm_rand

_EPS = float(np.finfo(float).eps)
_SQRT_EPS = math.sqrt(_EPS)


def _as_1d(x):
    a = np.asarray(x, dtype=float)
    return np.ravel(a)


def match_arg(arg, choices):
    if arg is None:
        return choices[0]
    name = str(arg)
    hits = [c for c in choices if c.startswith(name)]
    if len(hits) != 1:
        raise ValueError(f"'{name}' should be one of {', '.join(repr(c) for c in choices)}")
    return hits[0]


def is_symmetric(sigma, tol=_SQRT_EPS) -> bool:
    a = np.asarray(sigma, dtype=float)
    if a.ndim != 2 or a.shape[0] != a.shape[1]:
        return False
    scale = np.mean(np.abs(a)) if a.size else 1.0
    return np.max(np.abs(a - a.T)) <= tol * max(scale, 1.0)


def _factor(sigma, method):
    sigma = np.asarray(sigma, dtype=float)
    if method == "eigen":
        values, vectors = np.linalg.eigh(sigma)
        order = np.argsort(values)[::-1]
        values = values[order]
        vectors = vectors[:, order]
        if not np.all(values >= -_SQRT_EPS * abs(values[0])):
            warnings.warn("sigma is numerically not positive semidefinite", stacklevel=3)
        scale = np.sqrt(np.maximum(values, 0.0))
        return (vectors @ (vectors.T * scale[:, None])).T
    if method == "svd":
        u, d, vt = np.linalg.svd(sigma, full_matrices=True)
        if not np.all(d >= -_SQRT_EPS * abs(d[0])):
            warnings.warn("sigma is numerically not positive semidefinite", stacklevel=3)
        return (vt.T @ (u.T * np.sqrt(np.maximum(d, 0.0))[:, None])).T
    pivot = np.linalg.cholesky(sigma).T
    return pivot


def rmvnorm(n, mean=None, sigma=None, method="eigen", pre0_9_9994=False, checkSymmetry=True, rnorm=None):
    """R rmvnorm. The default factor is the symmetric eigen decomposition."""
    if sigma is None and mean is None:
        mean = np.zeros(1)
        sigma = np.ones((1, 1))
    elif sigma is None:
        mean = _as_1d(mean)
        sigma = np.eye(len(mean))
    else:
        sigma = np.asarray(sigma, dtype=float)
        if mean is None:
            mean = np.zeros(sigma.shape[0])
        else:
            mean = _as_1d(mean)
    if checkSymmetry and not is_symmetric(sigma):
        raise ValueError("sigma must be a symmetric matrix")
    if len(mean) != sigma.shape[0]:
        raise ValueError("mean and sigma have non-conforming size")
    method = match_arg(method, ("eigen", "svd", "chol"))
    factor = _factor(sigma, method)
    draw = rnorm if rnorm is not None else norm_rand
    raw = np.array([float(draw()) for _ in range(int(n) * sigma.shape[1])], dtype=float)
    if pre0_9_9994:
        raw = raw.reshape((int(n), sigma.shape[1]), order="F")
    else:
        raw = raw.reshape((int(n), sigma.shape[1]))
    out = raw @ factor
    out = out + mean
    return out


def dmvnorm(x, mean=None, sigma=None, log=False, checkSymmetry=True):
    """R dmvnorm. A failed Cholesky follows dnorm: Inf at the mean, 0 elsewhere."""
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(1, -1)
    p = x.shape[1]
    if mean is None:
        mean = np.zeros(p)
    else:
        mean = _as_1d(mean)
        if len(mean) != p:
            raise ValueError("x and mean have non-conforming size")
    if sigma is None:
        sigma = np.eye(p)
    else:
        sigma = np.asarray(sigma, dtype=float)
        if p != sigma.shape[1]:
            raise ValueError("x and sigma have non-conforming size")
        if checkSymmetry and not is_symmetric(sigma):
            raise ValueError("sigma must be a symmetric matrix")
    try:
        dec = np.linalg.cholesky(sigma).T
        solved = np.linalg.solve(dec.T, (x - mean).T)
        rss = np.sum(solved ** 2, axis=0)
        logretval = -np.sum(np.log(np.diag(dec))) - 0.5 * p * math.log(2 * math.pi) - 0.5 * rss
    except np.linalg.LinAlgError:
        same = np.sum((x - mean) != 0, axis=1) == 0
        logretval = np.full(x.shape[0], -math.inf)
        logretval[same] = math.inf
    return logretval if log else np.exp(logretval)


def _is_pos_inf(x):
    return np.isinf(x) & (np.asarray(x) > 0)


def dmvt(x, delta=None, sigma=None, df=1, log=True, type="shifted", checkSymmetry=True):
    """R dmvt. df 0 or Inf is the normal density."""
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(1, -1)
    p = x.shape[1]
    if df == 0 or (isinstance(df, float) and math.isinf(df)) or (np.ndim(df) == 0 and np.isinf(df)):
        return dmvnorm(x, mean=np.zeros(p) if delta is None else delta, sigma=sigma, log=log, checkSymmetry=checkSymmetry)
    if delta is None:
        delta = np.zeros(p)
    else:
        delta = _as_1d(delta)
        if len(delta) != p:
            raise ValueError("delta and sigma have non-conforming size")
    if sigma is None:
        sigma = np.eye(p)
    else:
        sigma = np.asarray(sigma, dtype=float)
        if p != sigma.shape[1]:
            raise ValueError("x and sigma have non-conforming size")
        if checkSymmetry and not is_symmetric(sigma):
            raise ValueError("sigma must be a symmetric matrix")
    type = match_arg(type, ("shifted", "Kshirsagar"))
    try:
        dec = np.linalg.cholesky(sigma).T
        solved = np.linalg.solve(dec.T, (x - delta).T)
        rss = np.sum(solved ** 2, axis=0)
        logretval = (
            math.lgamma((p + df) / 2)
            - (math.lgamma(df / 2) + np.sum(np.log(np.diag(dec))) + p / 2 * math.log(math.pi * df))
            - 0.5 * (df + p) * np.log1p(rss / df)
        )
    except np.linalg.LinAlgError:
        same = np.sum((x - delta) != 0, axis=1) == 0
        logretval = np.full(x.shape[0], -math.inf)
        logretval[same] = math.inf
    return logretval if log else np.exp(logretval)


def rmvt(n, sigma=None, df=1, delta=None, type="shifted", **kwargs):
    """R rmvt. A mean argument is refused, matching the R message."""
    if "mean" in kwargs:
        raise ValueError("Providing 'mean' does *not* sample from a multivariate t distribution!")
    if sigma is None:
        sigma = np.eye(2)
    else:
        sigma = np.asarray(sigma, dtype=float)
    if delta is None:
        delta = np.zeros(sigma.shape[0])
    else:
        delta = _as_1d(delta)
    if len(delta) != sigma.shape[0]:
        raise ValueError("delta and sigma have non-conforming size")
    if df == 0 or (np.ndim(df) == 0 and np.isinf(df)):
        return rmvnorm(n, mean=delta, sigma=sigma, **kwargs)
    kind = match_arg(type, ("shifted", "Kshirsagar"))
    if kind == "Kshirsagar":
        draws = rmvnorm(n, mean=delta, sigma=sigma, **kwargs)
    else:
        draws = rmvnorm(n, sigma=sigma, **kwargs)
    scale = np.sqrt(np.array([rchisq(df) for _ in range(int(n))], dtype=float) / df)
    draws = draws / scale[:, None]
    if kind == "shifted":
        draws = draws + delta
    return draws
