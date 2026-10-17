"""Port of R ``mclust::mclustLoglik`` (mclust 6.1.3, R/mclust.R).

Converts a mclustBIC matrix to log-likelihoods:
``loglik[i, j] = 0.5 * (BIC[i, j] + nMclustParams(model_j, d, G_i, noise) * log(n))``.
The result keeps the BIC attributes (``mostattributes``), with
``criterion = "loglik"`` and ``class = "mclustLoglik"``.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ._bic_objects import has_class, matrix_parts
from .model_metadata import nMclustParams

__all__ = ["mclustLoglik"]


def mclustLoglik(object: Any, **_: Any) -> dict[str, Any]:
    if not has_class(object, ("mclustBIC",)):
        raise ValueError("object must inherit from class mclustBIC")
    parts = matrix_parts(object)
    if parts is None:
        raise ValueError("object must be a matrix")
    values, rows, cols, attrs = parts
    G = [float(g) for g in rows]
    n = attrs.get("n")
    d = attrs.get("d")
    noise = attrs.get("noise") is not None

    loglik = np.full(values.shape, np.nan)
    for i, g in enumerate(G):
        for j, model in enumerate(cols):
            npar = nMclustParams(model, d=d, G=int(g), noise=noise)
            loglik[i, j] = 0.5 * (values[i, j] + npar * np.log(n))

    result = {k: v for k, v in attrs.items()
              if k not in ("values", "dim", "dimnames", "class", "criterion")}
    result["values"] = loglik
    result["G"] = G
    result["modelNames"] = list(cols)
    result["criterion"] = "loglik"
    result["class"] = "mclustLoglik"
    return result
