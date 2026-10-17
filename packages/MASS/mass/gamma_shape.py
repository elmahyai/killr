"""Estimate the Gamma shape parameter from a GLM fit (MASS ``gamma.shape``)."""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from decimal import Decimal, getcontext

import numpy as np

getcontext().prec = 42


def _digamma_decimal(x: Decimal) -> Decimal:
    if x <= 0:
        return Decimal("NaN")
    result = Decimal(0)
    while x < Decimal(8):
        result -= Decimal(1) / x
        x += Decimal(1)
    inv = Decimal(1) / x
    inv2 = inv * inv
    inv4 = inv2 * inv2
    result += x.ln() - inv / Decimal(2)
    result -= inv2 * (
        Decimal(1) / Decimal(12)
        - inv2 * (Decimal(1) / Decimal(120) - inv2 * (Decimal(1) / Decimal(252)))
    )
    return result


def _trigamma_decimal(x: Decimal) -> Decimal:
    if x <= 0:
        return Decimal("NaN")
    step = Decimal("1e-12") * x
    return (_digamma_decimal(x + step) - _digamma_decimal(x - step)) / (Decimal(2) * step)


def _gamma_shape_glm(
    object,
    *,
    it_lim: int = 10,
    eps_max: float | None = None,
    verbose: bool = False,
) -> tuple[float, float]:
    if eps_max is None:
        eps_max = float(np.finfo(float).eps**0.25)
    y = np.asarray(object.y, dtype=float)
    fitted = np.asarray(object.fitted_values, dtype=float)
    prior = object.prior_weights
    if prior is None:
        a = np.ones(y.shape[0], dtype=float)
    else:
        a = np.asarray(prior, dtype=float)
    u = fitted
    dbar = Decimal(str(float(object.deviance))) / Decimal(int(object.df_residual))
    alpha = (Decimal(6) + Decimal(2) * dbar) / (dbar * (Decimal(6) + dbar))
    if verbose:
        print(f"Initial estimate: {float(alpha)}")
    fixed = [
        Decimal(str(v))
        for v in (-y / u - np.log(u) + np.log(a) + 1.0 + np.log(y + (y == 0.0)))
    ]
    weights = [Decimal(str(v)) for v in a]
    eps = Decimal(1)
    itr = 0
    inf = Decimal(0)
    eps_max_d = Decimal(str(eps_max))
    while abs(eps) > eps_max_d and (itr := itr + 1) <= it_lim:
        sc = Decimal(0)
        inf = Decimal(0)
        log_alpha = alpha.ln()
        inv_alpha = Decimal(1) / alpha
        for w, fx in zip(weights, fixed):
            aa = w * alpha
            sc += w * (fx + log_alpha - _digamma_decimal(aa))
            inf += w * (w * _trigamma_decimal(aa) - inv_alpha)
        alpha = alpha + (eps := sc / inf)
        if verbose:
            print(f"Iter. {itr} Alpha: {float(alpha)}")
    if itr > it_lim:
        warnings.warn("iteration limit reached", stacklevel=2)
    se = float((Decimal(1) / inf).sqrt())
    return float(alpha), se


@dataclass
class GammaShape:
    """MLE shape estimate and approximate standard error (class ``gamma.shape``)."""

    alpha: float
    SE: float


def gamma_shape(object, /, **kwargs) -> GammaShape:
    """Maximum-likelihood Gamma shape after a ``Gamma`` glm fit."""
    alpha, se = _gamma_shape_glm(object, **kwargs)
    return GammaShape(alpha=alpha, SE=se)
