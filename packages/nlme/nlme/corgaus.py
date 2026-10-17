"""Gaussian spatial correlation structure constructor (nlme corGaus)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from nlme import corspatial_init as spatial_corr
from nlme.corspatial_init import initialize_spatial, spatial_matrices

_METRICS = ("euclidean", "maximum", "manhattan")


def _match_metric(metric: str) -> str:
    if metric in _METRICS:
        return metric
    matches = [name for name in _METRICS if name.startswith(metric)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"'{metric}' is ambiguous")
    raise ValueError(f"'{metric}' is not a valid metric")


@dataclass(slots=True)
class CorGaus:
    """Range parameters and spatial correlation metadata for corGaus."""

    value: np.ndarray
    formula: str = "~ 1"
    nugget: bool = False
    metric: str = "euclidean"
    fixed: bool = False
    min_d: float | None = None
    covariate: Any = None
    dim: Any = None
    groups: Any = None
    log_det: float | None = None


def corGaus(
    value: float | Sequence[float] | np.ndarray = (),
    form: str = "~ 1",
    nugget: bool = False,
    metric: str = "euclidean",
    fixed: bool = False,
) -> CorGaus:
    """Construct a corGaus object with optional range and nugget parameters."""
    arr = np.asarray(value, dtype=np.float64).reshape(-1)
    return CorGaus(arr, str(form), nugget, _match_metric(metric), fixed)


def initialize(object: CorGaus, data: Any, **_ignored) -> CorGaus:
    """Initialize a corGaus object (R ``Initialize.corSpatial``)."""
    return initialize_spatial(
        object,
        data,
        name="corGaus",
        shift_by_min_d=False,
        default_scale=0.9,
        corr=spatial_corr.gauss_corr,
    )


def coef(object, unconstrained: bool = True, **_ignored):
    """Extract constrained or unconstrained coefficients from a corGaus object."""
    if not isinstance(object, CorGaus):
        raise TypeError(f"do not know how to get coefficients for object of type {type(object)!r}")
    return _coef_cor_gaus(object, unconstrained=unconstrained)


@dataclass(frozen=True, slots=True)
class _CoefVector:
    values: np.ndarray
    names: tuple[str | None, ...]


def _coef_cor_gaus(object: CorGaus, unconstrained: bool) -> _CoefVector:
    if object.fixed and unconstrained:
        return _CoefVector(np.array([], dtype=np.float64), ())
    if object.value.size == 0:
        return _CoefVector(np.array([], dtype=np.float64), ())
    if unconstrained:
        return _CoefVector(object.value.copy(), (None,) * object.value.size)
    val = np.exp(object.value.copy())
    if object.nugget and val.size >= 2:
        val[1] = val[1] / (1.0 + val[1])
    if object.nugget:
        names: tuple[str | None, ...] = ("range", "nugget")[: val.size]
    elif val.size:
        names = ("range",)
    else:
        names = ()
    return _CoefVector(val, names)
