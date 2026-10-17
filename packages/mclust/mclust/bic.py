"""Port of R ``mclust::bic`` (mclust 6.1.3, R/mclust.R).

``bic = 2 * loglik - nparams * log(n)``, where ``nparams`` is
``nMclustParams(modelName, d, G, noise, equalPro)``.
"""

from __future__ import annotations

import math

from .model_metadata import nMclustParams

__all__ = ["bic"]


def bic(modelName: str, loglik: float, n: int, d: int, G: int,
        noise: bool = False, equalPro: bool = False, **_: object) -> float:
    nparams = nMclustParams(modelName, d=d, G=G, noise=noise, equalPro=equalPro)
    return 2.0 * float(loglik) - nparams * math.log(n)
