"""Gaussian mixture density helper from mclust's ``dens`` routine."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from .loglik_mclust import _dens


def dens(
    data: Any,
    modelName: str,
    parameters: Mapping[str, Any],
    logarithm: bool = False,
    warn: bool | None = None,
    **kwargs: Any,
) -> np.ndarray:
    """Evaluate a model-based mixture density.

    ``warn`` and additional arguments are accepted for API compatibility;
    kernel warnings are handled by the translated density implementations.
    """
    del warn, kwargs
    return _dens(
        np.asarray(data, dtype=float),
        str(modelName),
        parameters,
        logarithm=bool(logarithm),
    )


__all__ = ["dens"]
