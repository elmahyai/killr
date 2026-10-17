"""Continuous AR(1) correlation structure constructor (nlme corCAR1)."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from nlme.asoneformula import _all_vars
from nlme.corspatial_init import _column, _columns_of, _nrow
from nlme.corstruct import Dim, _as_frame, _get_groups, _normalize_formula
from nlme.getcovariateformula import getCovariateFormula
from nlme.varconstpower import _get_groups_formula


@dataclass(slots=True)
class CorCAR1:
    """Unconstrained CAR(1) parameter storage with formula and fixed flag."""

    value: float
    formula: str = "~ 1"
    fixed: bool = False
    covariate: Any = None
    dim: Any = None
    groups: Any = None
    log_det: float | None = None


def corCAR1(value: float = 0.2, form: str | None = "~ 1", fixed: bool = False) -> CorCAR1:
    """Construct a corCAR1 object from the lag-1 autocorrelation ``value``."""
    if value <= 0 or value >= 1:
        raise ValueError("parameter in CAR(1) structure must be between 0 and 1")
    unconstrained = math.log(value / (1.0 - value))
    if form is None:
        form = "~ 1"
    return CorCAR1(unconstrained, str(form), fixed)


def coef(object, unconstrained: bool = True, **_ignored):
    """Extract constrained or unconstrained coefficients from a corCAR1 object."""
    if not isinstance(object, CorCAR1):
        raise TypeError(f"do not know how to get coefficients for object of type {type(object)!r}")
    return _coef_cor_car1(object, unconstrained=unconstrained)


@dataclass(frozen=True, slots=True)
class _CoefVector:
    values: np.ndarray
    names: tuple[str | None, ...]


def _coef_cor_car1(object: CorCAR1, unconstrained: bool) -> _CoefVector:
    if unconstrained:
        if object.fixed:
            return _CoefVector(np.array([], dtype=np.float64), ())
        return _CoefVector(np.array([object.value], dtype=np.float64), (None,))
    aux = math.exp(object.value)
    phi = aux / (aux + 1.0)
    return _CoefVector(np.array([phi], dtype=np.float64), ("Phi",))


def initialize(object: CorCAR1, data: Any, **_ignored) -> CorCAR1:
    """Initialize a corCAR1 object (R ``Initialize.corCAR1``): groups, times, and the log determinant."""
    form = _normalize_formula(object.formula)
    cov_vars = _all_vars(getCovariateFormula(form).text)
    n = _nrow(data)
    if cov_vars:
        if len(cov_vars) != 1:
            raise ValueError("corCAR1 needs a single covariate")
        time = _column(data, cov_vars[0])
    else:
        time = np.arange(1, n + 1, dtype=np.float64)
    if _get_groups_formula(form) is None:
        codes = np.ones(n, dtype=np.int64)
        times = [time]
        grouped = None
    else:
        codes = _get_groups(_as_frame(_columns_of(data)), form)
        times = [time[codes == g] for g in range(int(codes.max()) + 1)]
        grouped = codes
    for group_time in times:
        if np.unique(group_time).size != group_time.size:
            raise ValueError('covariate must have unique values within groups for "corCAR1" objects')
    phi = math.exp(object.value) / (math.exp(object.value) + 1.0)
    log_det = 0.0
    for group_time in times:
        mat = phi ** np.abs(group_time[:, None] - group_time[None, :])
        sign, value = np.linalg.slogdet(mat)
        if sign <= 0:
            raise ValueError("correlation matrix is not positive definite")
        log_det += float(value) / 2.0
    covariate = times if grouped is not None else times[0]
    return replace(
        object,
        covariate=covariate,
        dim=Dim(object, codes),
        groups=grouped,
        log_det=log_det,
    )
