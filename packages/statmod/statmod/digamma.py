"""Digamma GLM family object.

Translated from statmod 1.5.2 ``Digamma`` in ``R/digammaf.R``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from statmod.canonic_digamma import canonic_digamma
from statmod.cumulant_digamma import cumulant_digamma
from statmod.d2cumulant_digamma import d2cumulant_digamma

_DBL_EPS = float(np.finfo(np.float64).eps)
_SQRT2 = math.sqrt(2.0)
_INV_SQRT_2PI = 1.0 / math.sqrt(2.0 * math.pi)


def _as_float(values) -> np.ndarray:
    return np.asarray(values, dtype=np.float64)


def _pnorm(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / _SQRT2))


def _qnorm_rational(p: float) -> float:
    q = p - 0.5
    if abs(q) <= 0.425:
        r = 0.180625 - q * q
        return q * (
            (
                (
                    (
                        (((r * 2509.0809287301226727 + 33430.575583588128105) * r + 67265.770927008700853) * r + 45921.953931549871457)
                        * r
                        + 13731.536185768826317
                    )
                    * r
                    + 1971.5909503065514427
                )
                * r
                + 133.14166789178437745
            )
            * r
            + 3.387132872796366608
        ) / (
            (
                (
                    (
                        (((r * 5226.495278852854561 + 28729.085735721942674) * r + 39307.89580009271061) * r + 21213.794301586595867)
                        * r
                        + 5394.1960214247511077
                    )
                    * r
                    + 687.1870074920579083
                )
                * r
                + 42.313330701600911252
            )
            * r
            + 1.0
        )
    tail = (1.0 - p) if q > 0.0 else p
    r = math.sqrt(-math.log(tail))
    if r <= 5.0:
        r = r - 1.6
        val = (
            (
                (
                    (((r * 7.7454501427834140764e-4 + 0.0227238449892691845833) * r + 0.24178072517745061177) * r + 1.27045825245236838258)
                    * r
                    + 3.64784832476320460504
                )
                * r
                + 5.7694972214606914055
            )
            * r
            + 4.6303378461565452959
        ) * r + 1.42343711074968357734
        val /= (
            (
                (
                    (
                        (((r * 1.05075007164441684324e-9 + 5.475938084995344946e-4) * r + 0.0151986665636164571966) * r + 0.14810397642748007459)
                        * r
                        + 0.68976733498510000455
                    )
                    * r
                    + 1.6763848301838038494
                )
                * r
                + 2.05319162663775882187
            )
            * r
            + 1.0
        )
    else:
        r = r - 5.0
        val = (
            (
                (
                    (((r * 2.01033439929228813265e-7 + 2.71155556874348757815e-5) * r + 0.0012426609473880784386) * r + 0.026532189526576123093)
                    * r
                    + 0.29656057182850489123
                )
                * r
                + 1.7848265399172913358
            )
            * r
            + 5.4637849111641143699
        ) * r + 6.6579046435011037772
        val /= (
            (
                (
                    (
                        (((r * 2.04426310338993978564e-15 + 1.4215117583164458887e-7) * r + 1.8463183175100546818e-5) * r + 7.868691311456132591e-4)
                        * r
                        + 0.0148753612908506148525
                    )
                    * r
                    + 0.13692988092273580531
                )
                * r
                + 0.59983220655588793769
            )
            * r
            + 1.0
        )
    if q < 0.0:
        val = -val
    return val


def _qnorm_scalar(p: float) -> float:
    if math.isnan(p):
        return math.nan
    if p == 0.0:
        return -math.inf
    if p == 1.0:
        return math.inf
    if p < 0.0 or p > 1.0:
        return math.nan
    if p == 0.5:
        return 0.0
    z = _qnorm_rational(p)
    if abs(p - 0.5) > 0.425:
        return z
    for _ in range(3):
        err = _pnorm(z) - p
        if err == 0.0:
            return z
        pdf = math.exp(-0.5 * z * z) * _INV_SQRT_2PI
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


def _qnorm(p) -> np.ndarray:
    flat = np.asarray(p, dtype=np.float64).ravel()
    out = np.array([_qnorm_scalar(float(x)) for x in flat], dtype=np.float64)
    return out.reshape(np.asarray(p).shape)


def _dnorm(z) -> np.ndarray:
    z = _as_float(z)
    return np.exp(-0.5 * z * z) * _INV_SQRT_2PI


def _make_link(link: Any) -> tuple[str, dict[str, Callable[..., Any]]]:
    """R ``stats::make.link``, including numeric switch indexing."""
    if isinstance(link, (int, np.integer)) or (
        isinstance(link, float) and float(link).is_integer()
    ):
        index = int(link)
        ordered = (
            "logit",
            "probit",
            "cauchit",
            "cloglog",
            "identity",
            "log",
            "sqrt",
            "1/mu^2",
        )
        if index < 1 or index > len(ordered):
            raise ValueError(f"'{index}' link not recognised")
        link_name = ordered[index - 1]
        internal_name = str(index)
    elif isinstance(link, str):
        link_name = link
        internal_name = link
    else:
        raise TypeError("link must be a character string or a number")

    if link_name == "logit":

        def linkfun(mu):
            mu = _as_float(mu)
            return np.log(mu / (1.0 - mu))

        def linkinv(eta):
            eta = _as_float(eta)
            return 1.0 / (1.0 + np.exp(-eta))

        def mu_eta(eta):
            eta = _as_float(eta)
            exp_eta = np.exp(eta)
            return exp_eta / ((1.0 + exp_eta) ** 2)

    elif link_name == "log":

        def linkfun(mu):
            return np.log(_as_float(mu))

        def linkinv(eta):
            return np.maximum(np.exp(_as_float(eta)), _DBL_EPS)

        def mu_eta(eta):
            return np.maximum(np.exp(_as_float(eta)), _DBL_EPS)

    elif link_name == "probit":

        def linkfun(mu):
            return _qnorm(_as_float(mu))

        def linkinv(eta):
            flat = np.asarray(eta, dtype=np.float64).ravel()
            out = np.array([_pnorm(float(x)) for x in flat], dtype=np.float64)
            return out.reshape(np.asarray(eta).shape)

        def mu_eta(eta):
            return _dnorm(eta)

    elif link_name == "cauchit":

        def linkfun(mu):
            mu = _as_float(mu)
            return np.tan(np.pi * (mu - 0.5))

        def linkinv(eta):
            eta = _as_float(eta)
            return 0.5 + np.arctan(eta) / np.pi

        def mu_eta(eta):
            eta = _as_float(eta)
            return 1.0 / (np.pi * (1.0 + eta * eta))

    elif link_name == "cloglog":

        def linkfun(mu):
            mu = _as_float(mu)
            return np.log(-np.log1p(-mu))

        def linkinv(eta):
            eta = _as_float(eta)
            return -np.expm1(-np.exp(eta))

        def mu_eta(eta):
            eta = _as_float(eta)
            exp_eta = np.exp(eta)
            return exp_eta * np.exp(-exp_eta)

    elif link_name == "identity":

        def linkfun(mu):
            return _as_float(mu)

        def linkinv(eta):
            return _as_float(eta)

        def mu_eta(eta):
            return np.ones(np.asarray(eta).shape, dtype=np.float64)

    elif link_name == "inverse":

        def linkfun(mu):
            return 1.0 / _as_float(mu)

        def linkinv(eta):
            return 1.0 / _as_float(eta)

        def mu_eta(eta):
            eta = _as_float(eta)
            return -1.0 / (eta * eta)

    elif link_name == "1/mu^2":

        def linkfun(mu):
            mu = _as_float(mu)
            return 1.0 / (mu * mu)

        def linkinv(eta):
            eta = _as_float(eta)
            return 1.0 / np.sqrt(eta)

        def mu_eta(eta):
            eta = _as_float(eta)
            return -0.5 / (eta ** 1.5)

    elif link_name == "sqrt":

        def linkfun(mu):
            return np.sqrt(_as_float(mu))

        def linkinv(eta):
            return _as_float(eta) ** 2

        def mu_eta(eta):
            eta = _as_float(eta)
            return 2.0 * eta

    else:
        raise ValueError(f"'{link_name}' link not recognised")

    def valideta(eta):
        return True

    bundle = {
        "linkfun": linkfun,
        "linkinv": linkinv,
        "mu.eta": mu_eta,
        "valideta": valideta,
        "name": internal_name,
    }
    return link_name, bundle


def _unitdeviance_digamma(y, mu):
    y = _as_float(y)
    mu = _as_float(mu)
    thetay = canonic_digamma(y)
    theta = canonic_digamma(mu)
    return 2.0 * (
        y * (thetay - theta) - (cumulant_digamma(thetay) - cumulant_digamma(theta))
    )


def _varfun_digamma(mu):
    mu = _as_float(mu)
    theta = canonic_digamma(mu)
    return d2cumulant_digamma(theta)


@dataclass
class DigammaFamily:
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

    @property
    def mu(self):
        return self.mu_eta


def Digamma(link: str | float | int = "log") -> DigammaFamily:
    """Return the Digamma GLM family, matching R ``Digamma(link=)``."""
    if isinstance(link, str):
        linkname = link
        _, link_obj = _make_link(link)
    elif isinstance(link, (int, np.integer)) or (
        isinstance(link, float) and float(link).is_integer()
    ):
        linkname = f"power({int(link)})"
        _, link_obj = _make_link(int(link))
    else:
        linkname = str(link)
        _, link_obj = _make_link(linkname)

    def validmu(mu):
        mu = _as_float(mu)
        return bool(np.all(mu > 0))

    def dev_resids(y, mu, wt):
        y = _as_float(y)
        mu = _as_float(mu)
        wt = _as_float(wt)
        return wt * _unitdeviance_digamma(y, mu)

    def aic(y, n, mu, wt, dev):
        return math.nan

    initialize = {
        "check": "Non-positive values not allowed for the Digamma family",
    }

    return DigammaFamily(
        family="Digamma",
        link=linkname,
        linkfun=link_obj["linkfun"],
        linkinv=link_obj["linkinv"],
        mu_eta=link_obj["mu.eta"],
        valideta=link_obj["valideta"],
        validmu=validmu,
        variance=_varfun_digamma,
        dev_resids=dev_resids,
        aic=aic,
        initialize=initialize,
    )
