"""Negative binomial GLM family (MASS ``neg.bin``)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from mass.errors import MassError
from mass.glm_nb import _Link, _nb_deviance

_DBL_EPS = float(np.finfo(np.float64).eps)


def _lgamma(values: np.ndarray) -> np.ndarray:
    flat = np.asarray(values, dtype=float).reshape(-1)
    out = np.array([math.lgamma(float(v)) for v in flat], dtype=float)
    return out.reshape(np.asarray(values).shape)


@dataclass
class NegBinFamily:
    """R ``family`` object returned by ``neg.bin``."""

    theta: float
    family: str = "Negative Binomial"
    link: str = "log"
    _link: _Link = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._link = _Link("log")

    def linkfun(self, mu: np.ndarray) -> np.ndarray:
        return self._link.linkfun(mu)

    def linkinv(self, eta: np.ndarray) -> np.ndarray:
        return self._link.linkinv(eta)

    def mu_eta(self, eta: np.ndarray) -> np.ndarray:
        return self._link.mu_eta(eta)

    def valideta(self, eta: np.ndarray) -> bool:
        return self._link.valideta(eta)

    def variance(self, mu: np.ndarray) -> np.ndarray:
        mu = np.asarray(mu, dtype=float)
        return mu + mu**2 / self.theta

    def dev_resids(self, y: np.ndarray, mu: np.ndarray, wt: np.ndarray) -> np.ndarray:
        return _nb_deviance(y, mu, wt, self.theta)

    def aic(
        self,
        y: np.ndarray,
        n: np.ndarray,
        mu: np.ndarray,
        wt: np.ndarray,
        dev: float,
    ) -> float:
        del n, dev
        y = np.asarray(y, dtype=float)
        mu = np.clip(np.asarray(mu, dtype=float), _DBL_EPS, None)
        wt = np.asarray(wt, dtype=float)
        th = self.theta
        y_log_mu = np.where(y > 0, y * np.log(mu), 0.0)
        term = (y + th) * np.log(mu + th) - y_log_mu + _lgamma(y + 1.0)
        term = term - th * math.log(th) + _lgamma(np.full_like(y, th)) - _lgamma(th + y)
        return float(2.0 * np.sum(term * wt))

    def validmu(self, mu: np.ndarray) -> bool:
        return bool(np.all(np.asarray(mu, dtype=float) > 0))

    def simulate(self, object: Any, nsim: int) -> np.ndarray:
        raise MassError("simulate requires rnegbin, which is not translated")


def neg_bin(*, theta: float | None = None) -> NegBinFamily:
    """Construct the negative binomial family with fixed ``theta``."""
    if theta is None:
        raise MassError("'theta' must be given")
    return NegBinFamily(theta=float(theta))
