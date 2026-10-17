"""Quantiles for one-dimensional mclust density fits."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np
from scipy.optimize import brentq
from scipy.special import ndtri

from .cdf_mclust import cdfMclust


def _field(object: Any, name: str) -> Any:
    return object[name] if isinstance(object, Mapping) else getattr(object, name)


def quantileMclust(object: Any, p: Any, **_: Any) -> np.ndarray:
    """Return quantiles of a fitted one-dimensional Gaussian mixture."""
    if int(_field(object, "d")) != 1:
        raise ValueError("quantile function only available for 1-dimensional data")

    probabilities = np.asarray(p, dtype=float).reshape(-1)
    parameters = _field(object, "parameters")
    means = np.asarray(parameters["mean"], dtype=float).reshape(-1)
    scales = np.sqrt(
        np.asarray(parameters["variance"]["sigmasq"], dtype=float).reshape(-1)
    )
    groups = int(_field(object, "G"))
    if str(_field(object, "modelName")) == "E":
        scales = np.repeat(scales, groups)

    component_quantiles = ndtri(probabilities[:, None])
    component_quantiles = component_quantiles * scales[:groups] + means[:groups]
    if groups == 1:
        return component_quantiles[:, 0]

    result = np.full(probabilities.size, np.nan, dtype=float)
    mixture = lambda x: float(cdfMclust(object, np.asarray([x]))["y"][0])
    tolerance = float(np.sqrt(np.finfo(float).eps))
    for index, probability in enumerate(probabilities):
        if 0.0 < probability < 1.0:
            bounds = component_quantiles[index]
            result[index] = brentq(
                lambda x: mixture(x) - probability,
                float(np.min(bounds)),
                float(np.max(bounds)),
                xtol=tolerance,
                rtol=4.0 * np.finfo(float).eps,
            )
    result[probabilities < 0.0] = np.nan
    result[probabilities > 1.0] = np.nan
    result[probabilities == 0.0] = -np.inf
    result[probabilities == 1.0] = np.inf
    return result


__all__ = ["quantileMclust"]
