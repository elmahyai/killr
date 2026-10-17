"""logLik method for ``MclustDA`` objects."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from .density import dens
from .model_metadata import nVarParams

__all__ = ["logLik_MclustDA", "MclustDALogLik"]


class MclustDALogLik:
    """Numeric log-likelihood carrying R-compatible ``df`` and ``nobs``."""

    __slots__ = ("value", "df", "nobs")

    def __init__(self, value: float, df: int, nobs: int) -> None:
        self.value = float(value)
        self.df = int(df)
        self.nobs = int(nobs)

    def __float__(self) -> float:
        return self.value

    def __array__(self, dtype=None):
        return np.asarray(self.value, dtype=dtype)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    return obj.get(key, default) if isinstance(obj, Mapping) else getattr(obj, key, default)


def logLik_MclustDA(object: Mapping[str, Any], data: Any = None, **_: Any) -> MclustDALogLik:
    """Return the class-mixture log-likelihood for an ``MclustDA`` fit."""
    x = np.asarray(_get(object, "data") if data is None else data, dtype=float)
    models = _get(object, "models")
    model_list = list(models.values()) if isinstance(models, Mapping) else list(models)
    prop = _get(object, "prop")
    if isinstance(prop, Mapping):
        prop_arr = np.asarray(list(prop.values()), dtype=float)
    else:
        prop_arr = np.asarray(prop, dtype=float)
    log_densities = np.column_stack(
        [
            dens(
                x,
                _get(model, "modelName"),
                _get(model, "parameters"),
                logarithm=True,
            )
            for model in model_list
        ]
    )
    weighted = log_densities + np.log(prop_arr)[None, :]
    row_max = np.max(weighted, axis=1)
    ll = float(np.sum(row_max + np.log(np.sum(np.exp(weighted - row_max[:, None]), axis=1))))

    nclass = len(model_list)
    n = int(_get(object, "n", x.shape[0]))
    d = int(_get(object, "d", x.shape[1] if x.ndim > 1 else 1))
    if str(_get(object, "type", "")) == "EDDA":
        first = model_list[0]
        df = d * nclass + nVarParams(
            _get(first, "modelName"), d=d, G=nclass
        )
    else:
        df = sum(
            (int(_get(model, "G")) - 1)
            + int(_get(model, "G")) * d
            + nVarParams(_get(model, "modelName"), d=d, G=int(_get(model, "G")))
            for model in model_list
        )
    df += nclass - 1
    return MclustDALogLik(ll, df, n)
