"""Semivariogram of a vector or of a spatial correlation structure (nlme Variogram)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np

from nlme import corexp, corgaus, corlin, corratio, corspher
from nlme.corexp import CorExp
from nlme.corgaus import CorGaus
from nlme.corlin import CorLin
from nlme.corratio import CorRatio
from nlme.corspher import CorSpher


@dataclass(slots=True)
class VariogramFrame:
    """Result of ``Variogram``: semivariances ``variog`` at distances ``dist``."""

    variog: np.ndarray
    dist: np.ndarray

    @property
    def classes(self) -> tuple[str, ...]:
        return ("Variogram", "data.frame")

    def __len__(self) -> int:
        return int(self.dist.size)


def _ratio_fun(x: np.ndarray, y: float) -> np.ndarray:
    x = (x / y) ** 2
    return x / (1.0 + x)


def _spher_fun(x: np.ndarray, y: float) -> np.ndarray:
    x = np.minimum(x / y, 1.0)
    return 1.5 * x - 0.5 * x**3


# (class, correlation function FUN, coef function) for each spatial method.
_SPATIAL_METHODS: tuple[tuple[type, Callable[[np.ndarray, float], np.ndarray], Callable[..., Any]], ...] = (
    (CorExp, lambda x, y: 1.0 - np.exp(-x / y), corexp.coef),
    (CorGaus, lambda x, y: 1.0 - np.exp(-((x / y) ** 2)), corgaus.coef),
    (CorLin, lambda x, y: np.minimum(x / y, 1.0), corlin.coef),
    (CorRatio, _ratio_fun, corratio.coef),
    (CorSpher, _spher_fun, corspher.coef),
)


def Variogram(
    object: Any,
    distance: Any = None,
    sig2: float = 1.0,
    length_out: int = 50,
) -> VariogramFrame:
    """Semivariogram of a numeric vector or of a spatial correlation object.

    A numeric vector uses the default method and needs ``distance`` with one
    entry per pair of observations. A spatial correlation object (corExp,
    corGaus, corLin, corRatio, corSpher) evaluates its correlation function on
    ``distance``. With no ``distance`` it uses ``length_out`` points spread over
    the stored covariate range. ``Variogram.lme`` and ``Variogram.gls`` need the
    lme and gls fits, which are not translated yet, so they raise here.
    """
    for cls, fun, coef_fn in _SPATIAL_METHODS:
        if isinstance(object, cls):
            return _variogram_cor_spatial(object, distance, sig2, length_out, fun, coef_fn)
    if isinstance(object, (np.ndarray, list, tuple, float, int)):
        return _variogram_default(object, distance)
    raise TypeError(
        f"no applicable method for 'Variogram' applied to an object of class "
        f"{type(object).__name__!r} (Variogram.lme and Variogram.gls are not translated yet)"
    )


def _variogram_default(object: Any, distance: Any) -> VariogramFrame:
    if distance is None:
        raise TypeError('argument "distance" is missing, with no default')
    obj = np.asarray(object, dtype=np.float64).reshape(-1)
    dist = np.asarray(distance, dtype=np.float64).reshape(-1)
    n = obj.size
    if dist.size != n * (n - 1) // 2:
        raise ValueError("'distance' and 'object' have incompatible lengths")
    # R takes the lower triangle of outer(object, object) in column-major order.
    values = np.array(
        [((obj[i] - obj[j]) ** 2) / 2.0 for j in range(n) for i in range(j + 1, n)],
        dtype=np.float64,
    )
    return VariogramFrame(values, dist)


def _variogram_cor_spatial(
    object: Any,
    distance: Any,
    sig2: float,
    length_out: int,
    fun: Callable[[np.ndarray, float], np.ndarray],
    coef_fn: Callable[..., Any],
) -> VariogramFrame:
    if distance is None:
        covariate = getattr(object, "covariate", None)
        if covariate is None:
            raise ValueError("'distance' must be supplied when the object has no covariate")
        if isinstance(covariate, list):
            flat = np.concatenate([np.asarray(part, dtype=np.float64).reshape(-1) for part in covariate])
        else:
            flat = np.asarray(covariate, dtype=np.float64).reshape(-1)
        distance = np.linspace(flat.min(), flat.max(), length_out)
    dist = np.asarray(distance, dtype=np.float64).reshape(-1)

    params = np.asarray(coef_fn(object, unconstrained=False).values, dtype=np.float64).reshape(-1)
    if params.size == 1:
        rang, nugg = params[0], 0.0
    elif params.size >= 2:
        rang, nugg = params[0], params[1]
    else:
        raise ValueError("no correlation parameters to build the variogram")
    variog = sig2 * (nugg + (1.0 - nugg) * fun(dist, rang))
    return VariogramFrame(np.asarray(variog, dtype=np.float64), dist)
