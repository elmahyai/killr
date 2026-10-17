"""Maximum-likelihood estimate of the negative-binomial theta (MASS ``theta.ml``)."""

from __future__ import annotations

import math
import warnings
from typing import Any

import numpy as np
from scipy.special import digamma, polygamma

_DBL_EPS = float(np.finfo(np.float64).eps)
_DEFAULT_EPS = _DBL_EPS**0.25


class ThetaMlResult:
    """Scalar theta estimate with R ``attr(., \"SE\")`` on ``SE``."""

    __slots__ = ("value", "SE", "warn")

    def __init__(self, value: float, se: float, warn: str | None = None) -> None:
        self.value = float(value)
        self.SE = float(se)
        self.warn = warn

    def __float__(self) -> float:
        return self.value

    def __index__(self) -> int:
        return int(self.value)

    def __repr__(self) -> str:
        return repr(self.value)


def _is_lm_like(obj: Any) -> bool:
    classes = getattr(obj, "__class__", type(obj))
    name = classes.__name__
    if name in {"Lm", "lm", "glm", "GlmNbFit"}:
        return True
    r_class = getattr(obj, "class_", None)
    if r_class is not None and "lm" in r_class:
        return True
    return hasattr(obj, "fitted_values") and hasattr(obj, "residuals")


def _resolve_y_mu(
    y: Any,
    mu: np.ndarray | None,
) -> tuple[np.ndarray, np.ndarray | None]:
    if _is_lm_like(y):
        fitted = np.asarray(y.fitted_values, dtype=float)
        y_stored = getattr(y, "y", None)
        if y_stored is None:
            resid = np.asarray(y.residuals, dtype=float)
            y_arr = fitted + resid
        else:
            y_arr = np.asarray(y_stored, dtype=float)
        return y_arr, fitted
    return np.asarray(y, dtype=float), None if mu is None else np.asarray(mu, dtype=float)


def theta_ml(
    y,
    mu=None,
    *,
    n: float | None = None,
    weights=None,
    limit: int = 10,
    eps: float = _DEFAULT_EPS,
    trace: bool = False,
) -> ThetaMlResult:
    """Estimate the negative-binomial dispersion parameter ``theta`` by ML."""
    y_arr, mu_from_lm = _resolve_y_mu(y, mu)
    if mu_from_lm is not None:
        mu_arr = mu_from_lm
    elif mu is not None:
        mu_arr = np.asarray(mu, dtype=float)
    else:
        raise TypeError("argument \"mu\" is missing, with no default")

    if weights is None:
        weights_arr = np.ones(y_arr.shape[0], dtype=float)
    else:
        weights_arr = np.asarray(weights, dtype=float)

    if n is None:
        n_val = float(np.sum(weights_arr))
    else:
        n_val = float(n)

    mu_arr = np.asarray(mu_arr, dtype=float)
    t0 = n_val / float(np.sum(weights_arr * (y_arr / mu_arr - 1.0) ** 2))
    it = 0
    del_val = 1.0
    info_val = 0.0
    warn_msg: str | None = None

    if trace:
        print(f"theta.ml: iter {it} 'theta = {t0:.6g}'")

    while it + 1 < limit and abs(del_val) > eps:
        it += 1
        t0 = abs(t0)
        th = t0
        score = float(
            np.sum(
                weights_arr
                * (
                    digamma(th + y_arr)
                    - digamma(th)
                    + math.log(th)
                    + 1.0
                    - np.log(th + mu_arr)
                    - (y_arr + th) / (mu_arr + th)
                )
            )
        )
        info_val = float(
            np.sum(
                weights_arr
                * (
                    -polygamma(1, th + y_arr)
                    + polygamma(1, th)
                    - 1.0 / th
                    + 2.0 / (mu_arr + th)
                    - (y_arr + th) / (mu_arr + th) ** 2
                )
            )
        )
        del_val = score / info_val
        t0 = t0 + del_val
        if trace:
            print(f"theta.ml: iter{it} theta ={t0:.6g}")

    if t0 < 0:
        t0 = 0.0
        warn_msg = "estimate truncated at zero"
        warnings.warn(warn_msg, stacklevel=2)
    if it == limit:
        warn_msg = "iteration limit reached"
        warnings.warn(warn_msg, stacklevel=2)

    se = math.sqrt(1.0 / info_val) if info_val != 0.0 else math.nan
    return ThetaMlResult(t0, se, warn_msg)
