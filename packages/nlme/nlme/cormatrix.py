"""Generic correlation-matrix extractor (nlme corMatrix)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from nlme.corlin import CorLin, corMatrix as corMatrix_corLin
from nlme.corratio import CorRatio, corMatrix as corMatrix_corRatio
from nlme.corspher import CorSpher, corMatrix as corMatrix_corSpher


def corMatrix(
    object: Any,
    covariate: Sequence[float] | np.ndarray | None = None,
    corr: bool = True,
    **_ignored,
) -> np.ndarray:
    """Dispatch ``corMatrix`` to the spatial correlation implementation."""
    if isinstance(object, CorLin):
        return corMatrix_corLin(object, covariate=covariate, corr=corr, **_ignored)
    if isinstance(object, CorSpher):
        return corMatrix_corSpher(object, covariate=covariate, corr=corr, **_ignored)
    if isinstance(object, CorRatio):
        return corMatrix_corRatio(object, covariate=covariate, corr=corr, **_ignored)
    label = type(object).__name__
    if corr:
        raise ValueError(f'do not know how to calculate correlation matrix of "{label}" object')
    raise ValueError(f'do not know how to calculate correlation matrix of "{label}" object')
