"""Single-component full-covariance multivariate normal EM fit, ``emXXX`` (mclust 6.1.3).

R ``emXXX`` calls ``mvnXXX`` directly, and ``meXXX`` is an alias of ``emXXX``.
This module makes the same call, so it returns the ``mvnXXX`` result.
"""

from __future__ import annotations

from typing import Any

from mclust.mvn import mvnXXX

__all__ = ["emXXX"]


def emXXX(data, prior=None, warn=None, **kwargs: Any) -> dict[str, Any]:
    """Fit a one-component full-covariance multivariate normal model (`emXXX` calls `mvnXXX`)."""
    return mvnXXX(data, prior=prior, warn=warn, **kwargs)
