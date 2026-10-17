"""Fit-family methods for mclust objects.

The fitting entry points are kept here even while the package's ``mclustBIC``
engine is being translated.  Prediction is independent of that engine and
operates on the ordinary dictionary representation used by this port.
"""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from .density import dens
from .loglik_mclust import _cdens

__all__ = [
    "Mclust",
    "predict_Mclust",
    "densityMclust",
    "predict_densityMclust",
    "densityMclust_diagnostic",
]


def Mclust(data: Any, G: Any = None, modelNames: Any = None, **kwargs: Any) -> dict[str, Any]:
    """Fit a Gaussian mixture model.

    The BIC search is delegated to ``mclustBIC`` in R.  That same-package
    routine is not translated yet, so this entry point deliberately reports
    the dependency instead of silently producing a partial fit.
    """
    del data, G, modelNames, kwargs
    raise NotImplementedError("Mclust is waiting on mclustBIC")


def predict_Mclust(
    object: Mapping[str, Any],
    newdata: Any = None,
    **kwargs: Any,
) -> dict[str, np.ndarray]:
    """Predict component membership for an ``Mclust`` object."""
    del kwargs
    if newdata is None:
        if "classification" in object and "z" in object:
            return {
                "classification": np.asarray(object["classification"]),
                "z": np.asarray(object["z"], dtype=float),
            }
        newdata = object.get("data")
    if newdata is None:
        raise ValueError("newdata is required when the fitted data are absent")

    x = np.asarray(newdata, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    model_name = str(object["modelName"])
    parameters = object["parameters"]
    log_component = np.asarray(
        _cdens(x, model_name, parameters, logarithm=True), dtype=float
    )
    if log_component.ndim == 1:
        log_component = log_component.reshape(-1, 1)
    pro = np.asarray(parameters["pro"], dtype=float).reshape(-1)
    if parameters.get("Vinv") is not None:
        pro = pro[:-1]
    if log_component.shape[1] != pro.size:
        raise ValueError("component density and mixing proportion dimensions differ")
    active = pro > 0
    log_component = log_component[:, active]
    pro = pro[active]
    shifted = log_component + np.log(pro)[None, :]
    maximum = np.max(shifted, axis=1)
    z_active = np.exp(shifted - maximum[:, None])
    z_active /= np.sum(z_active, axis=1, keepdims=True)
    z = np.zeros((x.shape[0], active.size), dtype=float)
    z[:, active] = z_active
    classification = np.argmax(z, axis=1) + 1
    return {"classification": classification, "z": z}


def densityMclust(data: Any, **kwargs: Any) -> dict[str, Any]:
    """Estimate a density using ``Mclust`` (currently blocked by mclustBIC)."""
    del data, kwargs
    raise NotImplementedError("densityMclust is waiting on mclustBIC")


def predict_densityMclust(
    object: Mapping[str, Any],
    newdata: Any = None,
    **kwargs: Any,
) -> np.ndarray:
    """Evaluate the fitted density at new observations."""
    del kwargs
    if newdata is None:
        newdata = object.get("data")
    if newdata is None:
        raise ValueError("newdata is required when the fitted data are absent")
    newdata = np.asarray(newdata, dtype=float)
    if newdata.ndim == 1:
        newdata = newdata.reshape(-1, 1)
    return np.asarray(
        dens(newdata, str(object["modelName"]), object["parameters"]),
        dtype=float,
    )


def densityMclust_diagnostic(object: Mapping[str, Any], **kwargs: Any) -> Any:
    """Return density diagnostics once the density fitting path is available."""
    del object, kwargs
    raise NotImplementedError("densityMclust.diagnostic is waiting on densityMclust")
