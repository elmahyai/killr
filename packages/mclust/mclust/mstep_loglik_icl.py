"""Dispatch and criterion helpers for mclust.

This module gathers the small public wrappers ``mstep``, ``me.weighted``,
and ``icl``. ``mclustICL`` is in ``mclust_icl``. Numerical model work remains
in the translated model-specific modules.
"""

from __future__ import annotations

import warnings
from collections.abc import Mapping
from typing import Any

import numpy as np

from .density import dens
from .em_control import em_control
from .estep import estep
from .estep_e import estepE
from .mclust_options import mclust_options
from .model_metadata import nMclustParams
from .mstep_eee_ev_vv import mstepEEE, mstepEEV, mstepVEV, mstepVVV
from .mstep_evv import mstepEVV
from .mstep_models import mstepE, mstepEII, mstepEEI, mstepEVI, mstepV
from .mstep_vee_eve_vve import mstepEVE, mstepVEE, mstepVVE

__all__ = ["mstep", "print_mclust_loglik", "me_weighted", "icl"]

_MSTEP = {
    "E": mstepE, "V": mstepV, "EII": mstepEII, "VII": None,
    "EEI": mstepEEI, "VEI": None, "EVI": mstepEVI, "VVI": None,
    "EEE": mstepEEE, "EEV": mstepEEV, "VEV": mstepVEV,
    "VEE": mstepVEE, "EVE": mstepEVE, "VVE": mstepVVE,
    "EVV": mstepEVV, "VVV": mstepVVV,
}


def mstep(data: Any, modelName: str, z: Any, prior: Any = None,
          warn: bool | None = None, **kwargs: Any) -> dict[str, Any]:
    """Call the translated model-specific M-step."""
    name = str(modelName)
    fn = _MSTEP.get(name)
    if fn is None:
        if name == "VII":
            from .mstep_vei_vii_vvi import mstep_vii as fn
        elif name == "VEI":
            from .mstep_vei_vii_vvi import mstep_vei as fn
        elif name == "VVI":
            from .mstep_vei_vii_vvi import mstep_vvi as fn
        else:
            raise ValueError(f"invalid model name: {name}")
    if name not in ("VEI", "VEE", "EVE", "VVE", "VEV"):
        # R mstep passes control only to the models whose mstepXXX takes it
        # (VEI, VEE, EVE, VVE, VEV); the other models do not accept it.
        kwargs.pop("control", None)
    return fn(data, z, prior=prior, warn=warn, **kwargs)


def print_mclust_loglik(x: Any, **kwargs: Any) -> str:
    """Render the R ``print.mclustLoglik`` output for a scalar-like object."""
    del kwargs
    value = x.get("value", x.get("loglik", x)) if isinstance(x, Mapping) else getattr(x, "value", x)
    df = x.get("df") if isinstance(x, Mapping) else getattr(x, "df", None)
    nobs = x.get("nobs") if isinstance(x, Mapping) else getattr(x, "nobs", None)
    lines = ["Log-likelihood:", f"[1] {float(value):.6g}"]
    if df is not None:
        lines += ['attr(,"df")', f"[1] {int(df)}"]
    if nobs is not None:
        lines += ['attr(,"nobs")', f"[1] {int(nobs)}"]
    return "\n".join(lines)


def me_weighted(data: Any, modelName: str, z: Any, weights: Any = None,
                prior: Any = None, control: Any = None, Vinv: Any = None,
                warn: bool | None = None, **kwargs: Any) -> dict[str, Any]:
    """Weighted EM, the R ``me.weighted`` loop.

    Each outer iteration takes one M-step (``mstep``) on the weighted
    responsibilities, then one E-step (``estep``), then the weighted
    log-likelihood from ``dens``. The loop stops on the relative
    log-likelihood tolerance or the iteration limit, as in R. Only the
    one-dimensional E model has been proven against R.
    """
    del kwargs
    x = np.asarray(data, dtype=float)
    if x.ndim == 1:
        x = x[:, None]
    nobs = x.shape[0]
    name = {"X": "E", "XII": "EII", "XXI": "EEI", "XXX": "EEE"}.get(str(modelName), str(modelName))
    if warn is None:
        warn = bool(mclust_options("warn"))
    control = em_control() if control is None else control
    w = np.ones(nobs) if weights is None else np.asarray(weights, dtype=float).reshape(-1)
    if w.size != nobs or np.any(w < 0) or np.any(~np.isfinite(w)):
        raise ValueError("Weights must be positive and finite")
    if np.max(w, initial=0) > 1:
        if warn:
            warnings.warn("Weights rescaled to have maximum equal to 1")
        w = w / np.max(w)
    zw = np.asarray(z, dtype=float) * w[:, None]
    itmax = float(np.asarray(control["itmax"]).ravel()[0])
    tol = float(np.asarray(control["tol"]).ravel()[0])
    eps = np.finfo(float).eps
    llold, ll = -np.inf, -np.inf
    criterion = True
    iteration = 0
    fit_m = None
    fit_e = None
    while criterion:
        iteration += 1
        fit_m = mstep(x, name, zw, prior=prior, warn=warn)
        fit_m["parameters"]["pro"] = np.asarray(fit_m["parameters"]["pro"]) / np.mean(w)
        fit_e = estep(x, name, fit_m["parameters"], warn=warn)
        if np.isnan(fit_e["loglik"]):
            criterion = False
            continue
        zw = np.maximum(np.asarray(fit_e["z"]) * w[:, None], eps)
        ldens = dens(x, name, fit_m["parameters"], logarithm=True, warn=warn)
        ll = float(np.sum(w * np.asarray(ldens, dtype=float)))
        criterion = criterion and (iteration < itmax)
        criterion = criterion and ((ll - llold) / (1.0 + abs(ll)) > tol)
        llold = ll
    fit = dict(fit_m)
    fit["z"] = fit_e["z"]
    fit["weights"] = w
    fit["loglik"] = ll / np.mean(w)
    npar = nMclustParams(modelName=fit["modelName"], d=fit["d"], G=fit["G"])
    fit["bic"] = 2 * fit["loglik"] - npar * np.log(fit["n"])
    return fit


def icl(object: Any, **kwargs: Any) -> float:
    """Compute ICL from an Mclust-like fit."""
    del kwargs
    get = object.get if isinstance(object, Mapping) else lambda k, d=None: getattr(object, k, d)
    n = int(get("n", len(np.asarray(get("z")))))
    z = np.asarray(get("z", np.ones((n, 1))), dtype=float)
    if z.ndim == 1:
        z = z[:, None]
    bic = float(get("bic", get("BIC")))
    hard = np.zeros_like(z)
    hard[np.arange(n), np.argmax(z, axis=1)] = 1
    return bic + 2 * float(np.sum(hard * np.where(z > 0, np.log(z), 0.0)))
