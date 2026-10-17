"""``densityMclust``: Gaussian mixture density estimate (mclust 6.1.3, R/densityMclust.R).

Mirrors ``densityMclust`` in ``R/densityMclust.R`` (mclust 6.1.3). R takes the
complete rows of ``data``, fits ``Mclust`` with the same arguments, and adds
the fitted density at the observations from ``dens``.

``plot = TRUE`` makes R draw the density. Drawing is a plotting function and is
not translated, so ``plot`` is accepted and nothing is drawn. The return value
is the same either way.

The noise model (``Vinv``) is not translated; see ``Mclust``.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .density import dens
from .mclust_object import Mclust

__all__ = ["densityMclust"]


def _na_omit_matrix(data: Any) -> np.ndarray:
    """R's ``na.omit(data.matrix(data))``: a matrix with incomplete rows removed."""
    a = np.asarray(data, dtype=float)
    if a.ndim == 1:
        a = a.reshape(-1, 1)
    return a[~np.isnan(a).any(axis=1)]


def densityMclust(data: Any, plot: bool = True, **kwargs: Any) -> dict[str, Any] | None:
    """Fit ``Mclust`` and add the fitted density at each observation."""
    del plot  # Drawing is not translated; see the module docstring.
    values = _na_omit_matrix(data)
    obj = Mclust(values, **kwargs)
    if obj is None:
        return None
    obj = dict(obj)
    obj["density"] = dens(
        obj["data"], obj["modelName"], obj["parameters"], logarithm=False
    )
    obj["class"] = ["densityMclust", "Mclust"]
    return obj
