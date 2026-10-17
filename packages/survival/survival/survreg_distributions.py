"""Distribution table for survreg (survival::survreg.distributions).

Each entry keeps the fields of the R list. Fields that R does not define are
absent from the dict. Functions take the same arguments, in the same order, as
the R closures.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import numpy as np
from scipy.stats import norm
from scipy.stats import t as student_t

from survival.dsurvreg import (
    _density_extreme,
    _density_gaussian,
    _density_logistic,
    _dlog_trans,
    _log_trans,
)


def _df(parms: Any) -> float:
    """Return the first numeric value of a parms object (R's named vector)."""
    if parms is None:
        raise ValueError("missing value for 'parms'")
    if isinstance(parms, Mapping):
        parms = list(parms.values())
    return float(np.asarray(parms, dtype=float).reshape(-1)[0])


def _weighted_mean_var(x: Any, weights: Any) -> tuple[float, float]:
    x_arr = np.asarray(x, dtype=float)
    w_arr = np.asarray(weights, dtype=float)
    mean = float(np.sum(x_arr * w_arr) / np.sum(w_arr))
    var = float(np.sum(w_arr * (x_arr - mean) ** 2) / np.sum(w_arr))
    return mean, var


def _status(y: Any) -> np.ndarray:
    return np.asarray(y, dtype=float)[:, -1]


# ---------------------------------------------------------------- extreme


def _init_extreme(x: Any, weights: Any, *_args: Any, **_kwargs: Any) -> np.ndarray:
    mean, var = _weighted_mean_var(x, weights)
    return np.array([mean + 0.572, var / 1.64])


def _deviance_extreme(y: Any, scale: Any, parms: Any = None) -> dict[str, np.ndarray]:
    y_arr = np.asarray(y, dtype=float)
    status = _status(y_arr)
    scale = float(scale)
    with np.errstate(all="ignore"):
        width = np.where(status == 3, (y_arr[:, 1] - y_arr[:, 0]) / scale, 1.0)
        temp = width / (np.exp(width) - 1.0)
        center = np.where(status == 3, y_arr[:, 0] - np.log(temp), y_arr[:, 0])
        temp3 = (-temp) + np.log(1.0 - np.exp(-np.exp(width)))
        loglik = np.where(
            status == 1,
            -(1.0 + np.log(scale)),
            np.where(status == 3, temp3, 0.0),
        )
    return {"center": center, "loglik": loglik}


def _quantile_extreme(p: Any, parms: Any = None) -> np.ndarray:
    p_arr = np.asarray(p, dtype=float)
    with np.errstate(all="ignore"):
        return np.log(-np.log(1.0 - p_arr))


# --------------------------------------------------------------- logistic


def _init_logistic(x: Any, weights: Any, *_args: Any, **_kwargs: Any) -> np.ndarray:
    mean, var = _weighted_mean_var(x, weights)
    return np.array([mean, var / 3.2])


def _deviance_logistic(y: Any, scale: Any, parms: Any = None) -> dict[str, np.ndarray]:
    y_arr = np.asarray(y, dtype=float)
    status = _status(y_arr)
    scale = float(scale)
    with np.errstate(all="ignore"):
        width = np.where(status == 3, (y_arr[:, 1] - y_arr[:, 0]) / scale, 0.0)
        center = np.where(status == 3, (y_arr[:, 0] + y_arr[:, 1]) / 2.0, y_arr[:, 0])
        temp2 = np.where(status == 3, np.exp(width / 2.0), 2.0)
        temp3 = np.log((temp2 - 1.0) / (temp2 + 1.0))
        loglik = np.where(
            status == 1,
            -np.log(4.0 * scale),
            np.where(status == 3, temp3, 0.0),
        )
    return {"center": center, "loglik": loglik}


def _quantile_logistic(p: Any, parms: Any = None) -> np.ndarray:
    p_arr = np.asarray(p, dtype=float)
    with np.errstate(all="ignore"):
        return np.log(p_arr / (1.0 - p_arr))


# --------------------------------------------------------------- gaussian


def _init_gaussian(x: Any, weights: Any, *_args: Any, **_kwargs: Any) -> np.ndarray:
    mean, var = _weighted_mean_var(x, weights)
    return np.array([mean, var])


def _deviance_gaussian(y: Any, scale: Any, parms: Any = None) -> dict[str, np.ndarray]:
    y_arr = np.asarray(y, dtype=float)
    status = _status(y_arr)
    scale = float(scale)
    with np.errstate(all="ignore"):
        width = np.where(status == 3, (y_arr[:, 1] - y_arr[:, 0]) / scale, 0.0)
        center = np.where(status == 3, (y_arr[:, 0] + y_arr[:, 1]) / 2.0, y_arr[:, 0])
        temp2 = np.log(2.0 * norm.cdf(width / 2.0) - 1.0)
        loglik = np.where(
            status == 1,
            -np.log(math.sqrt(2.0 * math.pi) * scale),
            np.where(status == 3, temp2, 0.0),
        )
    return {"center": center, "loglik": loglik}


def _quantile_gaussian(p: Any, parms: Any = None) -> np.ndarray:
    return norm.ppf(np.asarray(p, dtype=float))


# ---------------------------------------------------------------- Student-t


def _init_t(x: Any, weights: Any, df: Any = None) -> np.ndarray:
    df_value = _df(df)
    if df_value <= 2:
        raise ValueError("Degrees of freedom must be >=3")
    mean, var = _weighted_mean_var(x, weights)
    return np.array([mean, var * (df_value - 2.0) / df_value])


def _deviance_t(y: Any, scale: Any, parms: Any) -> dict[str, np.ndarray]:
    y_arr = np.asarray(y, dtype=float)
    status = _status(y_arr)
    scale = float(scale)
    df_value = _df(parms)
    with np.errstate(all="ignore"):
        width = np.where(status == 3, (y_arr[:, 1] - y_arr[:, 0]) / scale, 0.0)
        # R uses rowMeans(y), which includes the status column.
        center = np.where(status == 3, y_arr.mean(axis=1), y_arr[:, 0])
        temp2 = np.log(1.0 - 2.0 * student_t.cdf(width / 2.0, df_value))
        pdf0 = float(student_t.pdf(0.0, df_value))
        loglik = np.where(
            status == 1,
            -np.log(pdf0 * scale),
            np.where(status == 3, temp2, 0.0),
        )
    return {"center": center, "loglik": loglik}


def _density_t_wrapper(x: Any, parms: Any = None) -> np.ndarray:
    # Same five columns as R's density for "t". The CDF is SciPy's t.cdf,
    # which agrees with R's pt() to 1e-8; dsurvreg's helper does not.
    df_value = _df(parms)
    x_arr = np.asarray(x, dtype=float)
    with np.errstate(all="ignore"):
        return np.column_stack(
            (
                student_t.cdf(x_arr, df_value),
                student_t.cdf(-x_arr, df_value),
                student_t.pdf(x_arr, df_value),
                -(df_value + 1.0) * x_arr / (df_value + x_arr * x_arr),
                (df_value + 1.0)
                * (x_arr * x_arr * (df_value + 3.0) / (df_value + x_arr * x_arr) - 1.0)
                / (df_value + x_arr * x_arr),
            )
        )


def _quantile_t(p: Any, df: Any = None) -> np.ndarray:
    return student_t.ppf(np.asarray(p, dtype=float), _df(df))


# ------------------------------------------------------------ transforms


def _itrans_exp(x: Any) -> np.ndarray:
    return np.exp(np.asarray(x, dtype=float))


def _alias(name: str, dist: str, scale: float | None = None) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "name": name,
        "dist": dist,
        "trans": _log_trans,
        "dtrans": _dlog_trans,
    }
    if scale is not None:
        entry["scale"] = scale
    entry["itrans"] = _itrans_exp
    return entry


# ----------------------------------------------------------------- table

survreg_distributions: dict[str, dict[str, Any]] = {
    "extreme": {
        "name": "Extreme value",
        "variance": lambda parm=None: math.pi**2 / 6.0,
        "init": _init_extreme,
        "deviance": _deviance_extreme,
        "density": lambda x, parms=None: _density_extreme(x, parms),
        "quantile": _quantile_extreme,
    },
    "logistic": {
        "name": "Logistic",
        "variance": lambda parm=None: math.pi**2 / 3.0,
        "init": _init_logistic,
        "deviance": _deviance_logistic,
        "density": lambda x, parms=None: _density_logistic(x, parms),
        "quantile": _quantile_logistic,
    },
    "gaussian": {
        "name": "Gaussian",
        "variance": lambda parm=None: 1.0,
        "init": _init_gaussian,
        "deviance": _deviance_gaussian,
        "density": lambda x, parms=None: _density_gaussian(x, parms),
        "quantile": _quantile_gaussian,
    },
    "weibull": _alias("Weibull", "extreme"),
    "exponential": _alias("Exponential", "extreme", scale=1.0),
    "rayleigh": _alias("Rayleigh", "extreme", scale=0.5),
    "loggaussian": _alias("Log Normal", "gaussian"),
    "lognormal": _alias("Log Normal", "gaussian"),
    "loglogistic": _alias("Log logistic", "logistic"),
    "t": {
        "name": "Student-t",
        "variance": lambda df: _df(df) / (_df(df) - 2.0),
        "parms": {"df": 4.0},
        "init": _init_t,
        "deviance": _deviance_t,
        "density": _density_t_wrapper,
        "quantile": _quantile_t,
    },
}
