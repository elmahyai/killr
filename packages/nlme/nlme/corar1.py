"""AR(1) correlation structure constructor (nlme corAR1)."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any

import numpy as np


@dataclass(slots=True)
class CorAR1:
    """Unconstrained AR(1) parameter storage with formula and fixed flag."""

    value: float
    formula: str = "~ 1"
    fixed: bool = False
    dim: Any = None
    covariate: Any = None
    groups: Any = None
    factor: Any = None
    log_det: float | None = None


def corAR1(value: float = 0.0, form: str | None = "~ 1", fixed: bool = False) -> CorAR1:
    """Construct a corAR1 object from the lag-1 autocorrelation ``value``."""
    if abs(value) >= 1:
        raise ValueError("parameter in AR(1) structure must be between -1 and 1")
    unconstrained = math.log((1.0 + value) / (1.0 - value))
    if form is None:
        form = "~ 1"
    return CorAR1(unconstrained, str(form), fixed)


def initialize(object: CorAR1, data: Any, **_ignored) -> CorAR1:
    """Initialize a corAR1 object: groups, ``Dim`` and covariate (R ``Initialize.corAR1``).

    A covariate that is not consecutive within groups turns the object into a
    corARMA(1, 0) in R; that path needs the ARMA kernel and is not translated.
    """
    from nlme.corstruct import initialize_cor_struct

    from nlme.corarma import CorARMA, initialize as initialize_arma

    object = initialize_cor_struct(object, data)
    by_group = object.covariate if isinstance(object.covariate, dict) else {0: object.covariate}
    consecutive = True
    for group_cov in by_group.values():
        group_vals = np.asarray(group_cov, dtype=np.int64).reshape(-1)
        if np.unique(group_vals).size != group_vals.size:
            raise ValueError('covariate must have unique values within groups for "corAR1" objects')
        if group_vals.size > 1 and np.any(np.diff(group_vals) != 1):
            consecutive = False
    if not consecutive:
        # R: attr p = 1, q = 0, class corARMA, then Initialize(object, data).
        arma = CorARMA(
            value=np.array([object.value], dtype=np.float64),
            formula=object.formula,
            p=1,
            q=0,
            fixed=object.fixed,
        )
        return initialize_arma(arma, data)
    # R: attr(object, "factor") <- corFactor(object); attr(object, "logDet") <- -logDet(factor).
    try:
        import nlmerecalc
    except ImportError as exc:  # pragma: no cover - the extension is installed for proofs
        raise ImportError("nlmerecalc extension is required for corAR1 factors") from exc
    values, factor_log_det = nlmerecalc.ar1_fact_list(
        float(object.value), object.dim.as_pdims().tolist()
    )
    return replace(object, factor=np.asarray(values, dtype=np.float64), log_det=-float(factor_log_det))


def coef(object, unconstrained: bool = True, **_ignored):
    """Extract constrained or unconstrained coefficients from a corAR1 object."""
    if not isinstance(object, CorAR1):
        raise TypeError(f"do not know how to get coefficients for object of type {type(object)!r}")
    return _coef_cor_ar1(object, unconstrained=unconstrained)


@dataclass(frozen=True, slots=True)
class _CoefVector:
    values: np.ndarray
    names: tuple[str | None, ...]


def _coef_cor_ar1(object: CorAR1, unconstrained: bool) -> _CoefVector:
    if unconstrained:
        if object.fixed:
            return _CoefVector(np.array([], dtype=np.float64), ())
        return _CoefVector(np.array([object.value], dtype=np.float64), (None,))
    aux = math.exp(object.value)
    phi = (aux - 1.0) / (aux + 1.0)
    return _CoefVector(np.array([phi], dtype=np.float64), ("Phi",))
