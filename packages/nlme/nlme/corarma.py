"""ARMA(p,q) correlation structure constructor (nlme corARMA)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import numpy as np

try:
    import nlcorarma
except ImportError:  # pragma: no cover - proof installs the crate
    nlcorarma = None


@dataclass(slots=True)
class CorARMA:
    """ARMA storage: unconstrained parameters, orders, fixed flag, and the
    attributes that ``Initialize.corARMA`` adds (covariate, ``Dim``, ``maxLag``,
    factor, and ``logDet``)."""

    value: np.ndarray
    formula: str = "~ 1"
    p: int = 0
    q: int = 0
    fixed: bool = False
    groups: Any = None
    dim: Any = None
    covariate: Any = None
    max_lag: int | None = None
    factor: np.ndarray | None = None
    log_det: float | None = None

    @property
    def classes(self) -> tuple[str, ...]:
        return ("corARMA", "corStruct")


def corARMA(
    value: np.ndarray | list[float] | None = None,
    form: str | None = "~ 1",
    p: int = 0,
    q: int = 0,
    fixed: bool = False,
) -> CorARMA:
    """Construct a corARMA object from AR and MA constrained parameters."""
    if not (p >= 0 and p == round(p)):
        raise ValueError("autoregressive order must be a non-negative integer")
    if not (q >= 0 and q == round(q)):
        raise ValueError("moving average order must be a non-negative integer")
    if p + q == 0:
        raise ValueError("at least one of 'p' and 'q' must be > 0")
    p = int(p)
    q = int(q)
    if value is None:
        pars = np.zeros(p + q, dtype=np.float64)
    else:
        pars = np.asarray(value, dtype=np.float64).reshape(-1)
    if pars.size != p + q:
        raise ValueError("initial value for parameter of wrong length")
    if np.max(np.abs(pars)) >= 1:
        raise ValueError("parameters in ARMA structure must be < 1 in absolute value")
    unconstrained = _require_nlcorarma().arma_unconst_coef_py(p, q, pars.tolist())
    if form is None:
        form = "~ 1"
    return CorARMA(
        np.asarray(unconstrained, dtype=np.float64),
        str(form),
        p,
        q,
        fixed,
    )


def initialize(object: CorARMA, data: Any, **_ignored) -> Any:
    """Initialize a corARMA object (R ``Initialize.corARMA``).

    ARMA(1, 0) on consecutive covariate values is handed to the corAR1 methods,
    which return a ``CorAR1`` object as R does. Otherwise the object gets
    ``maxLag``, the factor list, and ``logDet = -logDet(factor)``.
    """
    from nlme.corstruct import initialize_cor_struct

    object = initialize_cor_struct(object, data)
    by_group = object.covariate if isinstance(object.covariate, dict) else {0: object.covariate}
    covar = {key: np.asarray(val, dtype=np.int64).reshape(-1) for key, val in by_group.items()}
    for group_vals in covar.values():
        if np.unique(group_vals).size != group_vals.size:
            raise ValueError('covariate must have unique integer values within groups for "corARMA" objects')
    if object.p == 1 and object.q == 0 and all(np.all(np.diff(v) == 1) for v in covar.values()):
        from nlme.corar1 import CorAR1, initialize as initialize_ar1

        ar1 = CorAR1(
            value=float(np.asarray(object.value, dtype=np.float64).reshape(-1)[0]),
            formula=object.formula,
            fixed=object.fixed,
        )
        return initialize_ar1(ar1, data)

    max_lag = max(int(np.max(v) - np.min(v)) for v in covar.values())
    if object.p > max_lag or object.q > max_lag:
        raise ValueError(
            f'"corARMA" order ({object.p}, {object.q}) exceeds maximum lag in data ({max_lag})'
        )
    factor, logdet = _arma_factor(object, max_lag)
    return replace(object, max_lag=max_lag, factor=factor, log_det=-logdet)


def recalc_arma(object: CorARMA, conLin: Any) -> Any:
    """Apply ``recalc.corARMA``: multiply each group block of ``Xy`` by its ARMA factor."""
    if object.max_lag is None:
        raise ValueError("'object' has not been Initialize()d")
    dim = object.dim
    xy = np.asarray(conLin.Xy, dtype=np.float64)
    if xy.ndim == 1:
        xy = xy.reshape(dim.N, xy.size // dim.N, order="F")
    n, zxcol = xy.shape
    if n != dim.N:
        raise ValueError("ConLin.Xy row count does not match corARMA dimensions")
    flat, logdet = _require_nlcorarma().arma_recalc_py(
        np.asarray(xy, dtype=np.float64).reshape(-1, order="F").tolist(),
        dim.as_pdims().tolist(),
        int(zxcol),
        np.asarray(object.value, dtype=np.float64).reshape(-1).tolist(),
        int(object.p),
        int(object.q),
        _time_vector(object).tolist(),
        int(object.max_lag),
        0.0,
    )
    return replace(
        conLin,
        Xy=np.asarray(flat, dtype=np.float64).reshape((n, zxcol), order="F"),
        logLik=float(conLin.logLik) + float(logdet),
    )


def _time_vector(object: CorARMA) -> np.ndarray:
    cov = object.covariate
    if isinstance(cov, dict):
        parts = [np.asarray(v, dtype=np.int64).reshape(-1) for v in cov.values()]
        return np.concatenate(parts).astype(np.int32)
    return np.asarray(cov, dtype=np.int64).reshape(-1).astype(np.int32)


def _arma_factor(object: CorARMA, max_lag: int) -> tuple[np.ndarray, float]:
    """Factor list and log-determinant term from ``ARMA_factList``."""
    values, logdet = _require_nlcorarma().arma_fact_list_py(
        np.asarray(object.value, dtype=np.float64).reshape(-1).tolist(),
        int(object.p),
        int(object.q),
        _time_vector(object).tolist(),
        int(max_lag),
        object.dim.as_pdims().tolist(),
    )
    return np.asarray(values, dtype=np.float64), float(logdet)


def coef(object, unconstrained: bool = True, **_ignored):
    """Extract constrained or unconstrained coefficients from a corARMA object."""
    if not isinstance(object, CorARMA):
        raise TypeError(f"do not know how to get coefficients for object of type {type(object)!r}")
    return _coef_cor_arma(object, unconstrained=unconstrained)


@dataclass(frozen=True, slots=True)
class _CoefVector:
    values: np.ndarray
    names: tuple[str | None, ...]


def _coef_cor_arma(object: CorARMA, unconstrained: bool) -> _CoefVector:
    if object.fixed and unconstrained:
        return _CoefVector(np.array([], dtype=np.float64), ())
    val = np.asarray(object.value, dtype=np.float64).copy()
    if not unconstrained:
        constrained = _require_nlcorarma().arma_const_coef_py(object.p, object.q, val.tolist())
        val = np.asarray(constrained, dtype=np.float64)
        names: list[str | None] = []
        if object.p > 0:
            names.extend(f"Phi{i}" for i in range(1, object.p + 1))
        if object.q > 0:
            names.extend(f"Theta{i}" for i in range(1, object.q + 1))
        return _CoefVector(val, tuple(names))
    return _CoefVector(val, (None,) * val.size)


def _require_nlcorarma():
    if nlcorarma is None:
        raise ImportError("nlcorarma extension is required for corARMA")
    return nlcorarma
