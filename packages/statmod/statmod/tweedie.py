"""Tweedie GLM family object.

Translated from statmod 1.5.2 ``tweedie`` in ``R/tweedie.R``.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

_DBL_EPS = float(np.finfo(np.float64).eps)


def _as_float(values) -> np.ndarray:
    return np.asarray(values, dtype=np.float64)


def _match_link_power(link_power: Any) -> float:
    if isinstance(link_power, str):
        names = ("identity", "log", "inverse")
        try:
            index = names.index(link_power)
        except ValueError as exc:
            raise ValueError("link.power should be a number") from exc
        lambda_val = (1.0, 0.0, -1.0)[index]
        warnings.warn(f"Setting link.power = {lambda_val}", stacklevel=3)
        return lambda_val
    return float(link_power)


def _match_var_power(var_power: Any) -> float:
    if isinstance(var_power, str):
        names = ("gaussian", "poisson", "Gamma", "gamma", "inverse.gaussian")
        try:
            index = names.index(var_power)
        except ValueError as exc:
            raise ValueError("var.power should be a number") from exc
        p = (0.0, 1.0, 2.0, 2.0, 3.0)[index]
        warnings.warn(f"Setting var.power = {p}", stacklevel=3)
        return p
    return float(var_power)


@dataclass
class TweedieFamily:
    family: str
    link: str
    linkfun: Callable[..., Any]
    linkinv: Callable[..., Any]
    mu_eta: Callable[..., Any]
    valideta: Callable[..., Any]
    validmu: Callable[..., Any]
    variance: Callable[..., Any]
    dev_resids: Callable[..., Any]
    aic: Callable[..., Any]
    initialize: dict[str, Any]
    var_power: float
    link_power: float

    @property
    def mu(self):
        return self.mu_eta


def tweedie(var_power: float | str = 0, link_power: float | str | None = None) -> TweedieFamily:
    """Return the Tweedie GLM family, matching R ``tweedie(var.power=, link.power=)``."""
    p = _match_var_power(var_power)
    if link_power is None:
        lambda_val = 1.0 - p
    else:
        lambda_val = _match_link_power(link_power)

    if lambda_val == 0.0:

        def linkfun(mu):
            return np.log(_as_float(mu))

        def linkinv(eta):
            return np.maximum(np.exp(_as_float(eta)), _DBL_EPS)

        def mu_eta(eta):
            return np.maximum(np.exp(_as_float(eta)), _DBL_EPS)

    else:

        def linkfun(mu):
            return _as_float(mu) ** lambda_val

        def linkinv(eta):
            return _as_float(eta) ** (1.0 / lambda_val)

        def mu_eta(eta):
            eta = _as_float(eta)
            return (1.0 / lambda_val) * eta ** (1.0 / lambda_val - 1.0)

    def valideta(eta):
        return True

    def variance(mu):
        return _as_float(mu) ** p

    if p == 0.0:

        def validmu(mu):
            return True

    elif p > 0.0:

        def validmu(mu):
            return bool(np.all(_as_float(mu) >= 0))

    else:

        def validmu(mu):
            return bool(np.all(_as_float(mu) > 0))

    def dev_resids(y, mu, wt):
        y = _as_float(y)
        mu = _as_float(mu)
        wt = _as_float(wt)
        y1 = y + 0.1 * (y == 0)
        if p == 1.0:
            theta = np.log(y1 / mu)
        else:
            theta = (y1 ** (1.0 - p) - mu ** (1.0 - p)) / (1.0 - p)
        if p == 2.0:
            kappa = np.log(y1 / mu)
        else:
            kappa = (y ** (2.0 - p) - mu ** (2.0 - p)) / (2.0 - p)
        return 2.0 * wt * (y * theta - kappa)

    def aic(y, n, mu, wt, dev):
        return math.nan

    initialize = {
        "n": "rep(1, nobs)",
        "mustart": "y + 0.1 * (y == 0)",
    }

    if lambda_val == int(lambda_val):
        link_label = f"mu^{int(lambda_val)}"
    else:
        link_label = f"mu^{lambda_val}"

    return TweedieFamily(
        family="Tweedie",
        link=link_label,
        linkfun=linkfun,
        linkinv=linkinv,
        mu_eta=mu_eta,
        valideta=valideta,
        validmu=validmu,
        variance=variance,
        dev_resids=dev_resids,
        aic=aic,
        initialize=initialize,
        var_power=p,
        link_power=lambda_val,
    )
