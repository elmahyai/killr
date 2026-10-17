"""Baseline hazard alias for survfit on a coxph model."""

from __future__ import annotations

import numpy as np

from survival._coxsurv import _component, _inherits, survfit_coxph


def basehaz(fit, newdata=None, centered=True):
    """Return cumulative baseline hazard from a fitted Cox model."""
    if _inherits(fit, "coxphms"):
        raise ValueError("the basehaz function is not implemented for multi-state models")
    if not _inherits(fit, "coxph"):
        raise ValueError("must be a coxph object")
    if newdata is not None:
        sfit = survfit_coxph(fit, newdata=newdata, se_fit=False)
        chaz = sfit["cumhaz"]
    else:
        sfit = survfit_coxph(fit, se_fit=False)
        if not centered:
            coefficients = _component(fit, "coefficients", optional=True)
            means = _component(fit, "means", optional=True)
            if coefficients is None:
                zcoef = np.array([], dtype=float)
            else:
                zcoef = np.where(np.isnan(np.asarray(coefficients, dtype=float)), 0.0, coefficients)
            if means is None or len(means) == 0:
                offset = 0.0
            else:
                offset = float(np.sum(np.asarray(means, dtype=float) * zcoef))
            chaz = sfit["cumhaz"] * np.exp(-offset)
        else:
            chaz = sfit["cumhaz"]
    out = {"hazard": np.asarray(chaz, dtype=float), "time": np.asarray(sfit["time"], dtype=float)}
    strata = sfit.get("strata")
    if strata is not None:
        names = list(strata.keys()) if isinstance(strata, dict) else list(strata)
        counts = np.asarray(list(strata.values()) if isinstance(strata, dict) else strata, dtype=int)
        levels = names
        repeated = np.repeat(levels, counts)
        out["strata"] = repeated
    return out
