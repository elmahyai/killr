"""CDF evaluation for one-dimensional mclust density fits."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np
from scipy.special import ndtr


def _field(object: Any, name: str) -> Any:
    return object[name] if isinstance(object, Mapping) else getattr(object, name)


def cdfMclust(
    object: Any,
    data: Any = None,
    ngrid: int = 100,
    **_: Any,
) -> dict[str, np.ndarray]:
    """Evaluate the fitted one-dimensional Gaussian mixture CDF on a grid.

    With no ``data``, the grid spans the fitted observations extended by ten
    percent, matching R's ``extendrange`` and ``seq`` behaviour.
    """
    if data is None:
        observed = np.asarray(_field(object, "data"), dtype=float)
        lo = float(np.min(observed))
        hi = float(np.max(observed))
        extension = 0.1 * (hi - lo)
        eval_points = np.linspace(lo - extension, hi + extension, int(ngrid))
    else:
        eval_points = np.sort(np.asarray(data, dtype=float).reshape(-1))

    parameters = _field(object, "parameters")
    pro = np.asarray(parameters["pro"], dtype=float).reshape(-1)
    means = np.asarray(parameters["mean"], dtype=float).reshape(-1)
    variance = np.asarray(parameters["variance"]["sigmasq"], dtype=float).reshape(-1)
    groups = int(_field(object, "G"))
    if variance.size < groups:
        variance = np.repeat(variance, groups)

    cdf = np.zeros(eval_points.size, dtype=float)
    for group in range(groups):
        cdf += pro[group] * ndtr(
            (eval_points - means[group]) / np.sqrt(variance[group])
        )
    if parameters.get("Vinv") is not None:
        cdf /= np.sum(pro[:groups])
    return {"x": eval_points, "y": cdf}


__all__ = ["cdfMclust"]
