"""Huber location, from MASS huber and hubers."""

from __future__ import annotations

import math

import numpy as np

from mass.errors import MassError


def _as_float(y) -> np.ndarray:
    values = np.asarray(y, dtype=float).reshape(-1)
    return values[~np.isnan(values)]


def _median(y: np.ndarray) -> float:
    return float(np.median(y))


def _mad(y: np.ndarray) -> float:
    center = _median(y)
    return float(np.median(np.abs(y - center)) * 1.4826)


def _pnorm(k: float) -> float:
    return 0.5 * (1.0 + math.erf(k / math.sqrt(2.0)))


def _dnorm(k: float) -> float:
    return math.exp(-0.5 * k * k) / math.sqrt(2.0 * math.pi)


def huber(y, k: float = 1.5, tol: float = 1.0e-6) -> dict[str, float]:
    """Huber location with the MAD scale held fixed."""
    values = _as_float(y)
    n = len(values)
    mu = _median(values)
    scale = _mad(values)
    if scale == 0:
        raise MassError("cannot estimate scale: MAD is zero for this sample")
    while True:
        clipped = np.minimum(np.maximum(mu - k * scale, values), mu + k * scale)
        mu1 = float(np.sum(clipped) / n)
        if abs(mu - mu1) < tol * scale:
            break
        mu = mu1
    return {"mu": mu, "s": scale}


def hubers(
    y,
    k: float = 1.5,
    mu=None,
    s=None,
    initmu=None,
    tol: float = 1.0e-6,
) -> dict[str, float]:
    """Huber location and scale estimated together."""
    values = _as_float(y)
    n = len(values)
    mmu = mu is None
    ms = s is None
    if mmu:
        mu0 = _median(values) if initmu is None else float(initmu)
        n1 = n - 1
    else:
        mu0 = float(mu)
        mu1 = float(mu)
        n1 = n
    if ms:
        s0 = _mad(values)
        if s0 == 0.0:
            return {"mu": mu0, "s": 0.0}
    else:
        s0 = float(s)
        s1 = float(s)
    th = 2 * _pnorm(k) - 1
    beta = th + k * k * (1 - th) - 2 * k * _dnorm(k)
    for _ in range(30):
        clipped = np.minimum(np.maximum(mu0 - k * s0, values), mu0 + k * s0)
        if mmu:
            mu1 = float(np.sum(clipped) / n)
        if ms:
            ss = float(np.sum((clipped - mu1) ** 2) / n1)
            s1 = math.sqrt(ss / beta)
        if abs(mu0 - mu1) < tol * s0 and abs(s0 - s1) < tol * s0:
            break
        mu0 = mu1
        s0 = s1
    return {"mu": mu0, "s": s0}
