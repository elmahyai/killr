"""Method-of-deviance estimate of negative-binomial theta (MASS ``theta.md``)."""

from __future__ import annotations

import warnings

import numpy as np

from mass.theta_ml import _DEFAULT_EPS, _is_lm_like, _resolve_y_mu


def theta_md(
    y,
    mu,
    dfr: float,
    weights=None,
    *,
    limit: int = 20,
    eps: float = _DEFAULT_EPS,
) -> float:
    """Estimate ``theta`` by equating the deviance to its residual degrees of freedom."""
    y_arr, mu_from_lm = _resolve_y_mu(y, mu)
    if _is_lm_like(y):
        mu_arr = mu_from_lm
        assert mu_arr is not None
        dfr_val = float(getattr(y, "df_residual", dfr))
    else:
        if mu is None:
            raise TypeError("argument \"mu\" is missing, with no default")
        mu_arr = np.asarray(mu, dtype=float)
        dfr_val = float(dfr)

    if weights is None:
        weights_arr = np.ones(y_arr.shape[0], dtype=float)
    else:
        weights_arr = np.asarray(weights, dtype=float)

    n = float(np.sum(weights_arr))
    t0 = n / float(np.sum(weights_arr * (y_arr / mu_arr - 1.0) ** 2))
    a = 2.0 * float(np.sum(weights_arr * y_arr * np.log(np.maximum(1.0, y_arr) / mu_arr))) - dfr_val
    it = 0
    del_val = 1.0

    while it + 1 < limit and abs(del_val) > eps:
        it += 1
        t0 = abs(t0)
        tmp = np.log((y_arr + t0) / (mu_arr + t0))
        top = a - 2.0 * float(np.sum(weights_arr * (y_arr + t0) * tmp))
        bot = 2.0 * float(np.sum(weights_arr * ((y_arr - mu_arr) / (mu_arr + t0) - tmp)))
        del_val = top / bot
        t0 = t0 - del_val

    if t0 < 0:
        t0 = 0.0
        warnings.warn("estimate truncated at zero", stacklevel=2)
    return float(t0)
