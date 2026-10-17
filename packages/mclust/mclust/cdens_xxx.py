"""Translation of mclust ``cdensXXX``.

The XXX model is an alias for EEE in mclust, so R delegates this export to
``cdensEEE``.  Keep the delegated result unchanged, including its attributes.
"""

from __future__ import annotations

from typing import Any

from mclust.cdens_eee import cdensEEE

__all__ = ["cdensXXX"]


def cdensXXX(
    data: Any,
    parameters: dict[str, Any],
    logarithm: bool = False,
    warn: bool | None = None,
) -> dict[str, Any]:
    """Return component densities for the XXX (EEE) model."""
    return cdensEEE(data, parameters, logarithm=logarithm, warn=warn)
