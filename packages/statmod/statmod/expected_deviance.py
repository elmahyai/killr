"""Expected value of scaled unit deviance for GLM families.

Translated from statmod 1.5.2 ``expectedDeviance`` in ``R/expectedDeviance.R``.
"""

from __future__ import annotations

import numpy as np

from statmod._expected_deviance_core import (
    _mbinomdev_scalar,
    _mnbinomdev_scalar,
    _mpoisdev_scalar,
)
from statmod.canonic_digamma import _meanval_digamma
from statmod.d2cumulant_digamma import d2cumulant_digamma

_FAMILIES = (
    "binomial",
    "gaussian",
    "Gamma",
    "inverse.gaussian",
    "poisson",
    "negative.binomial",
)


def _match_arg(value: str, choices: tuple[str, ...]) -> str:
    matches = [c for c in choices if c.startswith(value)]
    if len(matches) != 1:
        raise ValueError(f"'{value}' is not a valid choice")
    return matches[0]


def _broadcast_param(param, length: int, name: str):
    arr = np.asarray(param)
    if arr.size == 1:
        flat = np.full(length, float(arr.reshape(-1)[0]), dtype=float)
    elif arr.size == length:
        flat = np.asarray(arr, dtype=float).reshape(-1)
    else:
        raise ValueError(f"{name} must have length 1 or length must agree with mu")
    return flat


def expected_deviance(
    mu,
    family: str = "binomial",
    binom_size=None,
    nbinom_size=None,
    gamma_shape=None,
):
    """Return expected mean and variance of the unit deviance for ``family`` at ``mu``."""
    mu_arr = np.asarray(mu, dtype=float)
    out_mean = mu_arr.copy()
    out_var = mu_arr.copy()
    flat = mu_arr.reshape(-1)
    length = flat.size
    if length == 0:
        return {"mean": out_mean, "variance": out_var}

    if family == "Poisson":
        family = "poisson"
    if family == "gamma":
        family = "Gamma"
    family = _match_arg(family, _FAMILIES)

    mean_flat = np.empty(length, dtype=float)
    var_flat = np.empty(length, dtype=float)

    if family == "binomial":
        if binom_size is None:
            raise TypeError("expected_deviance() missing required argument: 'binom_size'")
        sizes = np.asarray(binom_size, dtype=int).reshape(-1)
        if sizes.size not in (1, length):
            raise ValueError("binom.size must have length 1 or length must agree with mu")
        min_n = int(np.min(sizes))
        if np.any(np.isnan(sizes)):
            raise ValueError("NAs not allowed in binom.size")
        if min_n < 1:
            raise ValueError("binom.size must be >= 1")
        min_m = float(np.min(flat))
        max_m = float(np.max(flat))
        if np.isnan(min_m):
            raise ValueError("NAs not allowed in mu")
        if min_m < 0 or max_m > 1:
            raise ValueError("binomial mu must be between 0 and 1")
        for i in range(length):
            sz = int(sizes[i % sizes.size])
            mean_flat[i], var_flat[i] = _mbinomdev_scalar(float(flat[i]), sz)

    elif family == "gaussian":
        mean_flat[:] = 1.0
        var_flat[:] = 2.0

    elif family == "Gamma":
        if gamma_shape is None:
            raise TypeError("expected_deviance() missing required argument: 'gamma_shape'")
        shapes = _broadcast_param(gamma_shape, length, "gamma.shape")
        min_s = float(np.min(shapes))
        if np.isnan(min_s):
            raise ValueError("NAs not allowed in gamma.shape")
        if min_s <= 0:
            raise ValueError("gamma.shape should be positive")
        theta = -shapes
        mv = _meanval_digamma(theta)
        d2 = d2cumulant_digamma(theta)
        mean_flat[:] = np.asarray(mv * shapes, dtype=float)
        var_flat[:] = np.asarray(2.0 * d2 * shapes * shapes, dtype=float)

    elif family == "inverse.gaussian":
        min_m = float(np.min(flat))
        if np.isnan(min_m):
            raise ValueError("NAs not allowed in mu")
        if min_m < 0:
            raise ValueError("inverse.gaussian mu must be non-negative")
        mean_flat[:] = 1.0
        var_flat[:] = 2.0

    elif family == "poisson":
        min_m = float(np.min(flat))
        if np.isnan(min_m):
            raise ValueError("NAs not allowed in mu")
        if min_m < 0:
            raise ValueError("Poisson mu must be non-negative")
        capped = np.minimum(flat, 1e7)
        for i in range(length):
            mean_flat[i], var_flat[i] = _mpoisdev_scalar(float(capped[i]))

    elif family == "negative.binomial":
        if nbinom_size is None:
            raise TypeError("expected_deviance() missing required argument: 'nbinom_size'")
        sizes = _broadcast_param(nbinom_size, length, "nbinom.size")
        min_s = float(np.min(sizes))
        if np.isnan(min_s):
            raise ValueError("NAs not allowed in nbinom.size")
        if min_s <= 0:
            raise ValueError("nbinom.size must be positive")
        if min_s > 1e7:
            return expected_deviance(mu, family="poisson")
        sizes = np.minimum(sizes, 1e7)
        if min_s <= 0.25:
            limit = np.minimum(flat * flat / (1e5 - 10.0), 0.25) + 1e-10
            sizes = np.maximum(sizes, limit)
        min_m = float(np.min(flat))
        if np.isnan(min_m):
            raise ValueError("NAs not allowed in mu")
        if min_m < 0:
            raise ValueError("Negative binomial mu must be non-negative")
        capped = np.minimum(flat, 1e7)
        for i in range(length):
            mean_flat[i], var_flat[i] = _mnbinomdev_scalar(
                float(capped[i]), float(sizes[i % sizes.size])
            )

    out_mean = mean_flat.reshape(mu_arr.shape)
    out_var = var_flat.reshape(mu_arr.shape)
    return {"mean": out_mean, "variance": out_var}
