"""Structural change tests for an ``efp`` process, a formula, or a Chow split."""

import warnings

import numpy as np
from scipy.stats import chi2, f as f_dist

from strucchange.efp import Efp, efp
from strucchange.model import design_from_formula, lm_fit, match_arg
from strucchange.pvalue import pvalue_efp

FORMULA_TYPES = (
    "Rec-CUSUM",
    "OLS-CUSUM",
    "Rec-MOSUM",
    "OLS-MOSUM",
    "RE",
    "ME",
    "fluctuation",
    "Score-CUSUM",
    "Nyblom-Hansen",
    "Chow",
    "supF",
    "aveF",
    "expF",
)
FUNCTIONALS = ("max", "range", "maxL2", "meanL2")
_STAT_NAMES = {
    "Rec-CUSUM": "S",
    "OLS-CUSUM": "S0",
    "Rec-MOSUM": "M",
    "OLS-MOSUM": "M0",
    "RE": "RE",
    "ME": "ME",
}


class Htest:
    def __init__(self, statistic, p_value, method, data_name, statistic_name=None):
        self.statistic = float(statistic)
        self.p_value = float(p_value)
        self.method = method
        self.data_name = data_name
        self.statistic_name = statistic_name

    def __repr__(self):
        name = self.statistic_name or "statistic"
        return f"Htest({name}={self.statistic}, p_value={self.p_value}, method={self.method!r})"


def _as_matrix(process):
    values = np.asarray(process, dtype=float)
    if values.ndim == 1:
        return values.reshape(-1, 1)
    return values


def sctest_efp(x, alt_boundary=False, functional="max", **_ignored):
    """Test an empirical fluctuation process. Functionals are ``max``, ``range``, ``maxL2``, ``meanL2``."""
    if not isinstance(x, Efp):
        raise TypeError("sctest_efp expects an efp result")
    h = x.par
    process_type = x.type
    lim_process = x.lim_process
    functional = match_arg(functional, FUNCTIONALS)
    method = x.type_name
    values = _as_matrix(x.process)
    if lim_process in ("Brownian motion", "Brownian bridge"):
        values = values[1:, :]
    n, k = values.shape

    if alt_boundary:
        if functional == "max" and lim_process in ("Brownian motion", "Brownian bridge"):
            trim = max(int(np.round(n * 0.001)), 1)
            j = np.arange(1, n + 1, dtype=float) / n
            if lim_process == "Brownian bridge":
                keep = slice(trim, n - trim)
                values = values[keep, :] / np.sqrt(j[keep] * (1.0 - j[keep]))[:, None]
            else:
                keep = slice(trim - 1, n)
                values = values[keep, :] / np.sqrt(j[keep])[:, None]
            method = f"{method} with alternative boundaries"
        else:
            if lim_process == "Brownian motion":
                j = np.arange(1, n + 1, dtype=float) / n
                values = values / (1.0 + 2.0 * j)[:, None]
            warnings.warn(
                f"no alternative boundaries for {lim_process} with {functional} functional"
            )
    elif lim_process == "Brownian motion":
        j = np.arange(1, n + 1, dtype=float) / n
        values = values / (1.0 + 2.0 * j)[:, None]

    if functional == "max":
        stat = float(np.max(np.abs(values)))
    elif functional == "range":
        stat = float(np.max(np.max(values, axis=0) - np.min(values, axis=0)))
        method = f"{method} with range norm"
    elif functional == "maxL2":
        stat = float(np.max(np.sum(values ** 2, axis=1)))
        method = f"{method} with max L2 norm"
    else:
        stat = float(np.mean(np.sum(values ** 2, axis=1)))
        method = f"{method} with mean L2 norm"

    p_value = pvalue_efp(
        stat, lim_process, alt_boundary, functional=functional, h=h, k=k
    )
    return Htest(
        statistic=stat,
        p_value=p_value,
        method=method,
        data_name=x.formula if isinstance(x.formula, str) else "x",
        statistic_name=_STAT_NAMES.get(process_type, "f(efp)"),
    )


def _chow(formula, data, point, asymptotic):
    y, x, _names = design_from_formula(formula, data)
    k = int(x.shape[1])
    n = int(y.shape[0])
    point = np.asarray(point, dtype=float).ravel()
    if point.size > 1:
        raise ValueError("'point' does not specify a valid potential change point")
    point = float(point[0])
    if point < 1:
        point = float(np.floor(point * n))
    if not (point > k and point < (n - k)):
        raise ValueError("inadmissable change point")
    split = int(np.floor(point))
    e = lm_fit(x, y).residuals
    u = np.concatenate([
        lm_fit(x[:split, :], y[:split]).residuals,
        lm_fit(x[split:, :], y[split:]).residuals,
    ])
    stat = ((np.sum(e ** 2) - np.sum(u ** 2)) / k) / (np.sum(u ** 2) / (n - 2 * k))
    if asymptotic:
        stat = stat * k
        p_value = float(1.0 - chi2.cdf(stat, k))
    else:
        p_value = float(1.0 - f_dist.cdf(stat, k, n - 2 * k))
    return Htest(stat, p_value, "Chow test", formula, statistic_name="F")


def sctest_formula(formula, type="Rec-CUSUM", h=0.15, alt_boundary=False, functional="max",
                   from_=0.15, to=None, point=0.5, asymptotic=False, data=None, **kwargs):
    """Formula interface. ``supF``, ``aveF``, and ``expF`` need ``Fstats``, which is not ported."""
    type = match_arg(type, FORMULA_TYPES)
    if type == "fluctuation":
        type = "RE"
    functional = match_arg(functional, FUNCTIONALS)
    if type == "Nyblom-Hansen":
        type = "Score-CUSUM"
        functional = "meanL2"
    if type == "Chow":
        result = _chow(formula, data, point, asymptotic)
    elif type in ("Rec-CUSUM", "OLS-CUSUM", "Rec-MOSUM", "OLS-MOSUM", "RE", "ME", "Score-CUSUM"):
        process = efp(formula, data=data, type=type, h=h, **kwargs)
        result = sctest_efp(process, alt_boundary=alt_boundary, functional=functional)
    elif type in ("supF", "aveF", "expF"):
        raise NotImplementedError("Fstats")
    else:
        raise ValueError(f"unknown sctest type {type!r}")
    result.data_name = formula if isinstance(formula, str) else result.data_name
    return result


def sctest(x, *args, **kwargs):
    """Dispatch on an ``efp`` result or a formula string."""
    if isinstance(x, Efp):
        return sctest_efp(x, *args, **kwargs)
    if isinstance(x, str):
        return sctest_formula(x, *args, **kwargs)
    raise TypeError("sctest expects an efp result or a formula string")
