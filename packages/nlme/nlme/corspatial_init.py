"""Shared ``Initialize`` for the spatial correlation structures (nlme ``Initialize.corSpatial``).

R's ``Initialize.corLin`` and ``Initialize.corSpher`` shift the range by the
minimum distance (``minD``); ``Initialize.corSpatial`` (used by ``corExp``,
``corGaus`` and ``corRatio``) does not. Both start from ``Initialize.corStruct``:
the groups, ``Dim``, and one distance vector per group (``getCovariate.corSpatial``),
where the covariate is a plain vector when the formula has no groups.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Callable

import numpy as np

from nlme.asoneformula import _all_vars
from nlme.corstruct import Dim, _as_frame, _get_groups, _normalize_formula
from nlme.getcovariateformula import getCovariateFormula
from nlme.varconstpower import _get_groups_formula


def _nrow(data: Any) -> int:
    columns = _columns_of(data)
    lengths = {len(np.asarray(col).reshape(-1)) for col in columns.values()}
    if len(lengths) != 1:
        raise ValueError("data columns must have equal length")
    return next(iter(lengths)) if lengths else 0


def _columns_of(data: Any) -> Mapping[str, Any]:
    if isinstance(data, Mapping):
        return data
    columns = getattr(data, "columns", None)
    if isinstance(columns, Mapping):
        return columns
    raise TypeError("data must be a mapping of column vectors")


def _column(data: Any, name: str) -> np.ndarray:
    columns = _columns_of(data)
    if name not in columns:
        raise KeyError(name)
    return np.asarray(columns[name], dtype=np.float64).reshape(-1)


def _pairwise_dist(coords: np.ndarray, metric: str) -> np.ndarray:
    """Upper-triangle distances in row-major order, matching ``_spatial_matrix``."""
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


def _group_distances(object: Any, data: Any) -> tuple[list[np.ndarray], Any, np.ndarray | None]:
    """Per-group distance vectors, ``Dim``, and group codes (``None`` when ungrouped)."""
    form = _normalize_formula(object.formula)
    cov_vars = _all_vars(getCovariateFormula(form).text)
    n = _nrow(data)
    if cov_vars:
        coords = np.column_stack([_column(data, name) for name in cov_vars])
    else:
        coords = np.arange(1, n + 1, dtype=np.float64).reshape(-1, 1)
    if _get_groups_formula(form) is None:
        dists = [_pairwise_dist(coords, object.metric)]
        codes = np.ones(n, dtype=np.int64)
        grouped = None
    else:
        codes = _get_groups(_as_frame(_columns_of(data)), form)
        dists = [_pairwise_dist(coords[codes == g], object.metric) for g in range(int(codes.max()) + 1)]
        grouped = codes
    for dist in dists:
        if dist.size and np.any(dist == 0):
            raise ValueError('cannot have zero distances in "corSpatial"')
    return dists, Dim(object, codes), grouped


def _dist_n(size: int) -> int:
    n = int(round((1 + math.sqrt(1 + 8 * size)) / 2))
    if n * (n - 1) // 2 != size:
        raise ValueError("length of covariate distances is not valid for one group")
    return n


def _group_matrix(par: np.ndarray, dist: np.ndarray, nugget: bool, shift: float, corr: Callable[[float], float]) -> np.ndarray:
    """Correlation matrix of one group; ``par`` is the stored (log-scale) vector."""
    rng = math.exp(par[0]) + shift
    ratio = 1.0 / (1.0 + math.exp(par[1])) if nugget else 1.0
    n = _dist_n(dist.size)
    mat = np.eye(n, dtype=np.float64)
    k = 0
    for i in range(n):
        for j in range(i + 1, n):
            cval = ratio * corr(dist[k] / rng)
            k += 1
            mat[i, j] = cval
            mat[j, i] = cval
    return mat


def spatial_matrices(object: Any, corr: Callable[[float], float], shift: float, covariate: Any = None) -> list[np.ndarray]:
    """Correlation matrix of every group of an initialized spatial object."""
    dists = object.covariate if covariate is None else covariate
    if not isinstance(dists, list):
        dists = [dists]
    par = np.asarray(object.value, dtype=np.float64).reshape(-1)
    return [_group_matrix(par, np.asarray(d, dtype=np.float64).reshape(-1), object.nugget, shift, corr) for d in dists]


def _half_logdet(par: np.ndarray, dists: list[np.ndarray], nugget: bool, shift: float, corr: Callable[[float], float]) -> float:
    total = 0.0
    for dist in dists:
        mat = _group_matrix(par, dist, nugget, shift, corr)
        sign, value = np.linalg.slogdet(mat)
        if sign <= 0:
            raise ValueError("correlation matrix is not positive definite")
        total += float(value) / 2.0
    return total


def initialize_spatial(
    object: Any,
    data: Any,
    *,
    name: str,
    shift_by_min_d: bool,
    default_scale: float,
    corr: Callable[[float], float],
) -> Any:
    """Initialize a spatial correlation object (R ``Initialize.corLin``/``corSpher``/``corSpatial``)."""
    if object.min_d is not None:
        return object
    dists, dim, groups = _group_distances(object, data)
    min_d = min(float(np.min(d)) for d in dists if d.size)
    val = np.asarray(object.value, dtype=np.float64).copy()
    nug = object.nugget
    if val.size > 0:
        if val[0] <= 0:
            raise ValueError(f"'range' must be > 0 in \"{name}\" initial value")
        if shift_by_min_d and val[0] <= min_d:
            val[0] = 1.1 * min_d
        if nug:
            if val.size == 1:
                val = np.array([val[0], 0.1], dtype=np.float64)
            elif val.size != 2:
                raise ValueError(f'initial value for "{name}" parameters of wrong dimension')
            if val[1] <= 0 or val[1] >= 1:
                raise ValueError("initial value of nugget ratio must be between 0 and 1")
        elif val.size != 1:
            raise ValueError(f'initial value for "{name}" parameters of wrong dimension')
    else:
        val = np.array([min_d * (1.1 if shift_by_min_d else default_scale)], dtype=np.float64)
        if nug:
            val = np.array([val[0], 0.1], dtype=np.float64)
    shift = min_d if shift_by_min_d else 0.0
    val = val.copy()
    val[0] = math.log(val[0] - shift)
    if nug:
        val[1] = math.log(val[1] / (1.0 - val[1]))
    log_det = _half_logdet(val, dists, nug, shift, corr)
    covariate = dists if groups is not None else dists[0]
    return replace(
        object,
        value=val,
        min_d=min_d,
        covariate=covariate,
        dim=dim,
        groups=groups,
        log_det=log_det,
    )


def lin_corr(val: float) -> float:
    return 1.0 - val if val < 1.0 else 0.0


def spher_corr(val: float) -> float:
    if val < 1.0:
        return 1.0 - 1.5 * val + 0.5 * val**3
    return 0.0


def ratio_corr(val: float) -> float:
    return 1.0 / (1.0 + val * val)


def exp_corr(val: float) -> float:
    return math.exp(-val)


def gauss_corr(val: float) -> float:
    return math.exp(-val * val)
