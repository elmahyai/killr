"""Confidence limits for survival curves (survival::survfit_confint)."""

from __future__ import annotations

from statistics import NormalDist

import numpy as np


def survfit_confint(
    p,
    se,
    logse=True,
    conf_type=None,
    conf_int=0.95,
    selow=None,
    ulimit=True,
):
    """Return a dict with ``lower`` and ``upper`` confidence limits.

    ``conf_type`` is one of 'plain', 'log', 'log-log', 'logit', 'arcsin'.
    'none' is not accepted, matching the R function.
    """
    if conf_type is None:
        raise ValueError("argument conf_type is missing, with no default")
    if conf_int <= 0 or conf_int >= 1:
        raise ValueError("confidence intervals must be between 0 and 1")
    zval = NormalDist().inv_cdf(1 - (1 - conf_int) / 2)

    p = np.asarray(p, dtype=float)
    se = np.asarray(se, dtype=float)
    with np.errstate(all="ignore"):
        if selow is None:
            scale = 1.0
        else:
            selow = np.asarray(selow, dtype=float)
            scale = np.where(selow == 0, 1.0, selow / se)  # avoid 0/0 at the origin
        if not logse:
            se = np.where(se == 0, 0.0, se / p)  # se of log(survival) = log(p)

        if conf_type == "plain":
            se2 = se * p * zval
            lower = np.maximum(p - se2 * scale, 0.0)
            if ulimit:
                upper = np.minimum(p + se2, 1.0)
            else:
                upper = p + se2
            return {"lower": lower, "upper": upper}

        if conf_type == "log":
            xx = np.where(p == 0, np.nan, p)
            se2 = zval * se
            temp1 = np.where(se == 0, p, np.exp(np.log(xx) - se2 * scale))
            temp2 = np.where(se == 0, p, np.exp(np.log(xx) + se2))
            if ulimit:
                return {"lower": temp1, "upper": np.minimum(temp2, 1.0)}
            return {"lower": temp1, "upper": temp2}

        if conf_type == "log-log":
            xx = np.where((p == 0) | (p == 1), np.nan, p)
            se2 = zval * se / np.log(xx)
            temp1 = np.where(se == 0, p, np.exp(-np.exp(np.log(-np.log(xx)) - se2 * scale)))
            temp2 = np.where(se == 0, p, np.exp(-np.exp(np.log(-np.log(xx)) + se2)))
            return {"lower": temp1, "upper": temp2}

        if conf_type == "logit":
            xx = np.where(p == 0, np.nan, p)
            se2 = zval * se * (1 + xx / (1 - xx))
            temp1 = np.where(
                se == 0,
                p,
                1 - 1 / (1 + np.exp(np.log(p / (1 - p)) - se2 * scale)),
            )
            temp2 = np.where(
                se == 0,
                p,
                1 - 1 / (1 + np.exp(np.log(p / (1 - p)) + se2)),
            )
            return {"lower": temp1, "upper": temp2}

        if conf_type == "arcsin":
            xx = np.where(p == 0, np.nan, p)
            se2 = 0.5 * zval * se * np.sqrt(xx / (1 - xx))
            lower = np.sin(np.maximum(0.0, np.arcsin(np.sqrt(xx)) - se2 * scale)) ** 2
            upper = np.sin(np.minimum(np.pi / 2, np.arcsin(np.sqrt(xx)) + se2)) ** 2
            return {"lower": lower, "upper": upper}

    raise ValueError("invalid conf.int type")
