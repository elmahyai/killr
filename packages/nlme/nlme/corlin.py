"""Linear spatial correlation structure (nlme corLin)."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from nlme.asoneformula import _all_vars
from nlme.getcovariateformula import getCovariateFormula
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
class CorLin:
    """Unconstrained parameters and metadata for corLin."""

    value: np.ndarray
    formula: str = "~ 1"
    nugget: bool = False
    metric: str = "euclidean"
    fixed: bool = False
    min_d: float | None = None
    covariate: np.ndarray | list[np.ndarray] | None = None
    dim: Any = None
    groups: Any = None
    log_det: float | None = None


def corLin(
    value: float | Sequence[float] | np.ndarray = (),
    form: str = "~ 1",
    nugget: bool = False,
    metric: str = "euclidean",
    fixed: bool = False,
) -> CorLin:
    """Construct a corLin object with optional range and nugget parameters."""
    arr = np.asarray(value, dtype=np.float64).reshape(-1)
    return CorLin(arr, str(form), nugget, _match_metric(metric), fixed)


def coef(object, unconstrained: bool = True, **_ignored):
    """Extract constrained or unconstrained coefficients from a corLin object."""
    if not isinstance(object, CorLin):
        raise TypeError(f"do not know how to get coefficients for object of type {type(object)!r}")
    return _coef_cor_lin(object, unconstrained=unconstrained)


@dataclass(frozen=True, slots=True)
class _CoefVector:
    values: np.ndarray
    names: tuple[str | None, ...]


def _coef_cor_lin(object: CorLin, unconstrained: bool) -> _CoefVector:
    if object.fixed and unconstrained:
        return _CoefVector(np.array([], dtype=np.float64), ())
    if object.value.size == 0:
        return _CoefVector(np.array([], dtype=np.float64), ())
    if unconstrained:
        return _CoefVector(object.value.copy(), (None,) * object.value.size)
    val = np.exp(object.value.copy())
    if object.nugget and val.size >= 2:
        val[1] = val[1] / (1.0 + val[1])
    if object.min_d is not None and val.size >= 1:
        val[0] = val[0] + object.min_d
    if object.nugget:
        names: tuple[str | None, ...] = ("range", "nugget")[: val.size]
    elif val.size:
        names = ("range",)
    else:
        names = ()
    return _CoefVector(val, names)


def _nrow(data: Any) -> int:
    if isinstance(data, Mapping):
        lengths = {len(np.asarray(col).reshape(-1)) for col in data.values()}
        if len(lengths) != 1:
            raise ValueError("data columns must have equal length")
        return next(iter(lengths)) if lengths else 0
    columns = getattr(data, "columns", None)
    if isinstance(columns, Mapping):
        return _nrow(columns)
    raise TypeError("data must be a mapping of column vectors")


def _column(data: Any, name: str) -> np.ndarray:
    if isinstance(data, Mapping):
        if name not in data:
            raise KeyError(name)
        return np.asarray(data[name], dtype=np.float64).reshape(-1)
    columns = getattr(data, "columns", None)
    if isinstance(columns, Mapping):
        return _column(columns, name)
    raise TypeError("data must be a mapping of column vectors")


def _pairwise_dist(coords: np.ndarray, metric: str) -> np.ndarray:
    n = coords.shape[0]
    out: list[float] = []
    for i in range(n):
        for j in range(i + 1, n):
            diff = coords[j] - coords[i]
            if metric == "euclidean":
                out.append(float(np.sqrt(np.sum(diff * diff))))
            elif metric == "manhattan":
                out.append(float(np.sum(np.abs(diff))))
            else:
                out.append(float(np.max(np.abs(diff))))
    return np.asarray(out, dtype=np.float64)


def _covariate_distances(data: Any, form: str, metric: str) -> np.ndarray:
    cov_text = getCovariateFormula(form).text
    vars_ = _all_vars(cov_text)
    if not vars_:
        n = _nrow(data)
        coords = np.arange(1, n + 1, dtype=np.float64).reshape(-1, 1)
    else:
        coords = np.column_stack([_column(data, name) for name in vars_])
    dist = _pairwise_dist(coords, metric)
    if dist.size and np.any(dist == 0):
        raise ValueError('cannot have zero distances in "corSpatial"')
    return dist


def initialize(object: CorLin, data: Any, **_ignored) -> CorLin:
    """Initialize a corLin object (R ``Initialize.corLin``)."""
    return initialize_spatial(
        object,
        data,
        name="corLin",
        shift_by_min_d=True,
        default_scale=1.1,
        corr=spatial_corr.lin_corr,
    )


def _lin_corr(val: float) -> float:
    return 1.0 - val if val < 1.0 else 0.0


def _spatial_matrix(
    par: np.ndarray,
    dist: np.ndarray,
    n: int,
    nugget: bool,
    min_d: float,
    corr,
) -> np.ndarray:
    work = par.astype(np.float64, copy=True)
    work[0] = math.exp(work[0]) + min_d
    ratio = 1.0
    if nugget:
        aux = math.exp(work[1])
        ratio = 1.0 / (1.0 + aux)
    mat = np.eye(n, dtype=np.float64)
    k = 0
    for i in range(n):
        for j in range(i + 1, n):
            aux = dist[k] / work[0]
            k += 1
            cval = ratio * corr(aux)
            mat[i, j] = cval
            mat[j, i] = cval
    return mat


def corMatrix(
    object: CorLin,
    covariate: Sequence[float] | np.ndarray | None = None,
    corr: bool = True,
    **_ignored,
) -> np.ndarray:
    """Correlation matrix from initialized corLin parameters and distances."""
    del corr
    if object.min_d is None:
        raise ValueError("corLin object must be initialized before corMatrix")
    if covariate is None and isinstance(object.covariate, list):
        return spatial_matrices(object, spatial_corr.lin_corr, object.min_d)
    dist = np.asarray(object.covariate if covariate is None else covariate, dtype=np.float64).reshape(-1)
    n = int(round((1 + math.sqrt(1 + 8 * dist.size)) / 2))
    if n * (n - 1) // 2 != dist.size:
        raise ValueError("length of covariate distances is not valid for one group")
    return _spatial_matrix(object.value, dist, n, object.nugget, object.min_d, _lin_corr)
