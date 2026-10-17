"""General natural-parameter correlation structure (nlme corNatural)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from nlme.corfactor import _symm_fact
from nlme.corstruct import CorDim, _NlmeFrame, initialize_cor_struct


@dataclass(slots=True)
class CorNatural:
    """Natural correlation parameters with formula and fixed flag.

    Before ``initialize`` ``value`` holds the constrained correlations. After it,
    ``value`` holds the unconstrained storage ``log((r + 1) / (1 - r))``, as R does.
    """

    value: np.ndarray
    formula: str = "~ 1"
    fixed: bool = False
    max_cov: int | None = None
    covariate: Any = None
    dim: Any = None
    max_cov: int | None = None
    covariate: Any = None
    dim: Any = None
    groups: np.ndarray | None = None
    factor: np.ndarray | None = None
    log_det: float | None = None

    @property
    def classes(self) -> tuple[str, ...]:
        return ("corNatural", "corStruct")


def corNatural(
    value: float | Sequence[float] | np.ndarray = (),
    form: str = "~ 1",
    fixed: bool = False,
) -> CorNatural:
    """Construct a corNatural object with optional natural parameter values."""
    arr = np.asarray(value, dtype=np.float64).reshape(-1)
    return CorNatural(arr, str(form), fixed)


def coef(object, unconstrained: bool = True, **_ignored):
    """Extract constrained or unconstrained coefficients from a corNatural object."""
    if not isinstance(object, CorNatural):
        raise TypeError(f"do not know how to get coefficients for object of type {type(object)!r}")
    return _coef_cor_natural(object, unconstrained=unconstrained)


@dataclass(frozen=True, slots=True)
class _CoefVector:
    values: np.ndarray
    names: tuple[str | None, ...]


def _coef_cor_natural(object: CorNatural, unconstrained: bool) -> _CoefVector:
    if unconstrained:
        if object.fixed:
            return _CoefVector(np.array([], dtype=np.float64), ())
        if object.value.size == 0:
            return _CoefVector(np.array([], dtype=np.float64), ())
        return _CoefVector(object.value.copy(), (None,) * object.value.size)
    # R: coef.corNatural(unconstrained = FALSE) calls nat_fullCorr on the stored values.
    if object.max_cov is None:
        raise ValueError("corNatural object must be initialized before constrained coef")
    corr = nat_full_corr(np.asarray(object.value, dtype=np.float64))
    names = tuple(
        f"cor({c},{r})"
        for c in range(1, object.max_cov + 1)
        for r in range(c + 1, object.max_cov + 1)
    )
    return _CoefVector(corr, names)


def nat_full_corr(pars: np.ndarray) -> np.ndarray:
    """Map unconstrained natural parameters to correlations, ``(e^u - 1) / (e^u + 1)``."""
    aux = np.exp(np.asarray(pars, dtype=np.float64))
    return (aux - 1.0) / (aux + 1.0)


def _nat_factor(corr: np.ndarray, covariate: list[int], max_cov: int, dim: CorDim) -> tuple[np.ndarray, float]:
    """Factor and log determinant of the block correlations, as ``nat_factList`` does."""
    out = np.zeros(dim.sum_len_sq, dtype=np.float64)
    log_det = 0.0
    offset = 0
    tpos = 0
    for length in dim.len:
        block, block_ld = _symm_fact(corr, covariate[tpos : tpos + length], length, max_cov)
        # nat_factList stores the transpose of the block that _symm_fact returns (verified against R).
        out[offset : offset + length * length] = block.T.reshape(-1, order="F")
        log_det += block_ld
        offset += length * length
        tpos += length
    return out, log_det


def initialize(object: CorNatural, data: _NlmeFrame | Mapping[str, Any], **_ignored) -> CorNatural:
    """Initialize a corNatural object: covariate, ``maxCov``, storage, factor and logDet (R ``Initialize.corNatural``)."""
    if object.max_cov is not None:
        return object
    object = initialize_cor_struct(object, data)
    covar = object.covariate
    by_group = covar if isinstance(covar, dict) else {0: covar}
    for group_cov in by_group.values():
        group_vals = np.asarray(group_cov, dtype=np.int64).reshape(-1)
        if np.unique(group_vals).size != group_vals.size:
            raise ValueError('covariate must have unique values within groups for "corNatural" objects')
    flat = np.concatenate([np.asarray(v, dtype=np.int64).reshape(-1) for v in by_group.values()])
    cov0 = flat - 1
    max_cov = int(np.max(cov0)) + 1
    unique_cov = np.unique(cov0)
    if unique_cov.size != max_cov or not np.array_equal(unique_cov, np.arange(max_cov)):
        raise ValueError(
            'unique values of the covariate for "corNatural" objects must be a sequence of consecutive integers'
        )
    assert object.dim is not None
    if object.dim.M > 1:
        cov_store: Any = {key: np.asarray(val, dtype=np.int64).reshape(-1) - 1 for key, val in by_group.items()}
    else:
        cov_store = cov0

    nat_par = np.asarray(object.value, dtype=np.float64).reshape(-1)
    n_par = max_cov * (max_cov - 1) // 2
    if nat_par.size > 0:
        if nat_par.size != n_par:
            raise ValueError('initial value for "corNatural" parameters of wrong dimension')
        if np.max(np.abs(nat_par)) >= 1:
            raise ValueError('initial values for "corNatural" must be between -1 and 1')
        nat_mat = np.eye(max_cov, dtype=np.float64) / 2.0
        # R fills the lower triangle column by column (column-major).
        idx = 0
        for j in range(max_cov):
            for r in range(j + 1, max_cov):
                nat_mat[r, j] = nat_par[idx]
                idx += 1
        nat_mat = nat_mat.T + nat_mat
        if np.min(np.linalg.eigvalsh(nat_mat)) <= 0:
            raise ValueError(
                'initial values for "corNatural" do not define a positive-definite correlation structure'
            )
        unc = np.log((nat_par + 1.0) / (1.0 - nat_par))
    else:
        unc = np.zeros(n_par, dtype=np.float64)

    updated = replace(object, max_cov=max_cov, covariate=cov_store, value=unc)
    values, log_det = _nat_factor(
        nat_full_corr(unc),
        _covariate_vector(updated),
        max_cov,
        object.dim,
    )
    return replace(updated, factor=values, log_det=-log_det)


def _covariate_vector(object: CorNatural) -> list[int]:
    cov = object.covariate
    if isinstance(cov, dict):
        parts = [np.asarray(v, dtype=np.int64).reshape(-1) for v in cov.values()]
        return np.concatenate(parts).astype(np.int32).tolist()
    return np.asarray(cov, dtype=np.int64).reshape(-1).astype(np.int32).tolist()
