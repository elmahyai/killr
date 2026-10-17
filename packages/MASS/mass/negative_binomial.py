"""Negative binomial GLM family with selectable link (MASS ``negative.binomial``)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from mass.errors import MassError
from mass.glm_nb import _Link, _as_link_name, _nb_deviance


def _lgamma(values: np.ndarray) -> np.ndarray:
    flat = np.asarray(values, dtype=float).reshape(-1)
    out = np.array([math.lgamma(float(v)) for v in flat], dtype=float)
    return out.reshape(np.asarray(values).shape)


def _family_label(theta: float) -> str:
    """Match R ``paste(\"Negative Binomial(\", format(round(theta, 4)), \")\", sep=\"\")``."""
    rounded = round(float(theta), 4)
    text = format(rounded, "g")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return f"Negative Binomial({text})"


@dataclass
class NegativeBinomialFamily:
    """R ``family`` object returned by ``negative.binomial``."""

    theta: float
    link: str
    family: str = field(init=False)
    _link: _Link = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.theta = float(self.theta)
        self.link = str(self.link)
        self.family = _family_label(self.theta)
        self._link = _Link(self.link)

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
        mu = np.asarray(mu, dtype=float)
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


def negative_binomial(
    *,
    theta: float | None = None,
    link: Any = "log",
) -> NegativeBinomialFamily:
    """Construct the negative binomial family with fixed ``theta`` and ``link``."""
    if theta is None:
        raise MassError("'theta' must be specified")
    link_name = _as_link_name(link)
    return NegativeBinomialFamily(theta=float(theta), link=link_name)
