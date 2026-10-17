"""Port of R ``mclust::pickBIC`` (mclust 6.1.3, R/mclust.R).

Returns the ``k`` largest BIC entries as ``{"values": ndarray, "names": [...]}``.
Ties on the value are ordered by G label, then by model name, as in R. NA
entries sort last and get the name ``" "``. A non-matrix input returns
``None``.
"""

from __future__ import annotations

import sys
import warnings
from typing import Any

import numpy as np

from ._bic_objects import matrix_parts
from .mclust_options import mclust_options

__all__ = ["pickBIC"]

_XMAX = sys.float_info.max  # .Machine$double.xmax


def pickBIC(x: Any, k: int = 3, **_: Any) -> dict[str, Any] | None:
    parts = matrix_parts(x)
    if parts is None:
        warnings.warn("sorry, the pickBIC function cannot be applied to the provided argument!")
        return None
    values, glabels, model_names, _attrs = parts
    flat = values.ravel(order="F")  # R indexes matrices column-major
    mis = np.isnan(flat)
    if mis.all() and mclust_options("warn"):
        warnings.warn("none of the selected models could be fitted")
        return {"values": np.full(k, np.nan), "names": None}

    nrow = values.shape[0]
    total = flat.size
    xv = np.where(mis, -_XMAX, flat)
    # order(-x[,1], x[,2], x[,3]): value descending, then G label, then model name
    order = sorted(
        range(total),
        key=lambda t: (-xv[t], glabels[t % nrow], model_names[t // nrow]),
    )
    k = min(int(k), total)
    top = order[:k]
    vals = xv[top].astype(float)
    names: list[str] = []
    for t in top:
        names.append(f"{model_names[t // nrow]},{glabels[t % nrow]}")
    vals = np.where(vals == -_XMAX, np.nan, vals)
    for i in range(k):
        if np.isnan(vals[i]):
            names[i] = " "
    return {"values": vals, "names": names}
