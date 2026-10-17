"""MclustDA classifiers and their deprecated training helpers.

The public ``MclustDA`` and ``cv.MclustDA`` names are retained here as
compatibility entry points; the main EDDA implementations live in their
dedicated modules.  ``cv1EMtrain`` and ``bicEMtrain`` are the older internal
helpers used by mclust releases before ``cvMclustDA``.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from mclust._mclust_mutils import as_factor, mclust_bic, unmap
from mclust.cv_mclust_da import cv_mclust_da
from mclust.estep_e import estepE
from mclust.estep_eev import estepEEV
from mclust.estep_eii import estepEII
from mclust.estep_eei import estepEEI
from mclust.estep_eee import estepEEE
from mclust.estep_evi import estepEVI
from mclust.estep_evv import estepEVV
from mclust.estep_vee_eve_vve import estep_eve, estep_vee, estep_vve
from mclust.estep_v_vei_vev_vii_vvi_vvv import (
    estepV, estepVII, estepVEI, estepVEV, estepVVI, estepVVV
)
from mclust.mclust_da import mclust_da
from mclust.mstep_models import mstepE, mstepEII, mstepEEI, mstepEVI, mstepV
from mclust.mstep_evv import mstepEVV
from mclust.mstep_eee_ev_vv import mstepEEE, mstepEEV, mstepVEV, mstepVVV
from mclust.mstep_vee_eve_vve import mstepEVE, mstepVEE, mstepVVE
from mclust.mstep_vei_vii_vvi import mstep_vei, mstep_vii, mstep_vvi

__all__ = [
    "MclustDA",
    "mclust_da_fit",
    "cv_MclustDA",
    "cvMclustDA",
    "cv1EMtrain",
    "bicEMtrain",
]

_MSTEP = {
    "E": mstepE,
    "V": mstepV,
    "EII": mstepEII,
    "EEI": mstepEEI,
    "EVI": mstepEVI,
    "VII": mstep_vii,
    "VEI": mstep_vei,
    "VVI": mstep_vvi,
    "EEE": mstepEEE,
    "EVE": mstepEVE,
    "VEE": mstepVEE,
    "VVE": mstepVVE,
    "EEV": mstepEEV,
    "VEV": mstepVEV,
    "EVV": mstepEVV,
    "VVV": mstepVVV,
}
_ESTEP = {
    "E": estepE,
    "V": estepV,
    "EII": estepEII,
    "VII": estepVII,
    "EEI": estepEEI,
    "VEI": estepVEI,
    "EVI": estepEVI,
    "VVI": estepVVI,
    "EEE": estepEEE,
    "EVE": estep_eve,
    "VEE": estep_vee,
    "VVE": estep_vve,
    "EEV": estepEEV,
    "VEV": estepVEV,
    "EVV": estepEVV,
    "VVV": estepVVV,
}


def MclustDA(data, class_, **kwargs):
    """Fit an EDDA/MclustDA classifier."""
    return mclust_da(data, class_, **kwargs)


def mclust_da_fit(data, class_, **kwargs):
    """Python-style alias for :func:`MclustDA`."""
    return MclustDA(data, class_, **kwargs)


def cv_MclustDA(*args, **kwargs):
    """Deprecated ``cv.MclustDA`` forwarding alias."""
    return cv_mclust_da(*args, **kwargs)


def cvMclustDA(*args, **kwargs):
    """Alias matching the exported R spelling."""
    return cv_MclustDA(*args, **kwargs)


def _model_names(data: Any, model_names: Sequence[str] | str | None) -> list[str]:
    x = np.asarray(data)
    one_d = x.ndim == 1 or (x.ndim == 2 and x.shape[1] == 1)
    if model_names is None:
        return ["E", "V"] if one_d else [
            "EII", "VII", "EEI", "VEI", "EVI", "VVI",
            "EEE", "EVE", "VEE", "VVE", "EEV", "VEV", "EVV", "VVV",
        ]
    return [model_names] if isinstance(model_names, str) else list(model_names)


def _fit_step(model: str, data: Any, z: np.ndarray) -> tuple[dict, dict]:
    if model not in _MSTEP or model not in _ESTEP:
        raise NotImplementedError(f"Waiting on mstep helper for model {model}")
    mstep = _MSTEP[model](data, z, warn=False)
    estep = _ESTEP[model](data, mstep["parameters"], warn=False)
    return mstep, estep


def _one_d_posterior(value: float, parameters: Mapping[str, Any]) -> np.ndarray:
    pro = np.asarray(parameters["pro"], dtype=float).ravel()
    mean = np.asarray(parameters["mean"], dtype=float).ravel()
    variance = np.asarray(parameters["variance"]["sigmasq"], dtype=float).ravel()
    if variance.size == 1:
        variance = np.repeat(variance, mean.size)
    logp = np.log(pro) - 0.5 * (np.log(2.0 * np.pi * variance) +
                                (float(value) - mean) ** 2 / variance)
    logp -= np.max(logp)
    return np.exp(logp) / np.sum(np.exp(logp))


def cv1EMtrain(data, labels, modelNames=None):
    """Leave-one-out classification error rates for each candidate model."""
    x = np.asarray(data, dtype=float)
    if x.ndim == 2 and x.shape[1] == 1:
        x = x[:, 0]
    names = _model_names(x, modelNames)
    codes, _ = as_factor(labels)
    z = unmap(codes + 1)
    n, groups = len(codes), z.shape[1]
    errors = np.ones((n, len(names)), dtype=float)
    for j, model in enumerate(names):
        for i in range(n):
            try:
                fitted, _ = _fit_step(
                    model, np.delete(x, i, axis=0), np.delete(z, i, axis=0)
                )
                posterior = _one_d_posterior(
                    x[i], fitted["parameters"]
                )[None, :]
                if np.isfinite(posterior).all():
                    predicted = np.flatnonzero(posterior[0] == np.max(posterior[0]))
                    observed = np.flatnonzero(z[i] == np.max(z[i]))
                    errors[i, j] = float(not np.intersect1d(predicted, observed).size)
            except (ValueError, FloatingPointError, np.linalg.LinAlgError):
                pass
    return dict(zip(names, np.mean(errors, axis=0)))


def bicEMtrain(data, labels, modelNames=None):
    """BIC values for each candidate model fit to labelled observations."""
    x = np.asarray(data, dtype=float)
    names = _model_names(x, modelNames)
    codes, _ = as_factor(labels)
    z = unmap(codes + 1)
    out = {name: float("nan") for name in names}
    for name in names:
        try:
            _, step = _fit_step(name, x, z)
            loglik = float(step.get("loglik", np.nan))
            if np.isfinite(loglik):
                out[name] = mclust_bic(
                    name, loglik, len(x), 1 if x.ndim == 1 else x.shape[1],
                    z.shape[1], equal_pro=False,
                )
        except (ValueError, FloatingPointError, np.linalg.LinAlgError):
            pass
    return out
