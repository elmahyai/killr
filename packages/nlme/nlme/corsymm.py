"""General symmetric correlation structure (nlme corSymm)."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from nlme.corstruct import _NlmeFrame, initialize_cor_struct


@dataclass(slots=True)
class CorSymm:
    """Unconstrained symmetric-correlation parameters with formula metadata."""

    value: np.ndarray
    formula: str = "~ 1"
    fixed: bool = False
    max_cov: int | None = None
    covariate: Any = None
    dim: Any = None
    groups: np.ndarray | None = None
    factor: np.ndarray | None = None
    log_det: float | None = None

    @property
    def classes(self) -> tuple[str, ...]:
        return ("corSymm", "corStruct")


def corSymm(
    value: float | Sequence[float] | np.ndarray = (),
    form: str | None = "~ 1",
    fixed: bool = False,
) -> CorSymm:
    """Construct a corSymm object from optional initial correlations."""
    arr = np.asarray(value, dtype=np.float64).reshape(-1)
    if form is None:
        form = "~ 1"
    return CorSymm(arr, str(form), fixed)


def initialize(object: CorSymm, data: _NlmeFrame | Mapping[str, Any], **_ignored) -> CorSymm:
    """Initialize a corSymm object on grouped data with a covariate sequence."""
    if object.max_cov is not None:
        return object
    object = initialize_cor_struct(object, data)
    covar = object.covariate
    by_group = covar if isinstance(covar, dict) else {0: covar}
    for group_cov in by_group.values():
        group_vals = np.asarray(group_cov, dtype=np.int64).reshape(-1)
        if np.unique(group_vals).size != group_vals.size:
            raise ValueError('covariate must have unique values within groups for "corSymm" objects')
    flat = np.concatenate([np.asarray(v, dtype=np.int64).reshape(-1) for v in by_group.values()])
    cov0 = flat - 1
    max_cov = int(np.max(cov0)) + 1
    unique_cov = np.unique(cov0)
    if unique_cov.size != max_cov or not np.array_equal(unique_cov, np.arange(max_cov)):
        raise ValueError(
            'unique values of the covariate  for "corSymm" objects must be a sequence of consecutive integers'
        )
    assert object.dim is not None
    if object.dim.M > 1:
        split_cov = {key: np.asarray(val, dtype=np.int64).reshape(-1) - 1 for key, val in by_group.items()}
        cov_store: Any = split_cov
    else:
        cov_store = cov0

    nat_par = np.asarray(object.value, dtype=np.float64).reshape(-1)
    n_par = max_cov * (max_cov - 1) // 2
    if nat_par.size > 0:
        if nat_par.size != n_par:
            raise ValueError('initial value for "corSymm" parameters of wrong dimension')
        if np.max(np.abs(nat_par)) >= 1:
            raise ValueError('initial values for "corSymm" must be between -1 and 1')
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
                "initial values for corSymm do not define a positive-definite correlation structure"
            )
        # R's chol() is upper triangular; numpy's is lower, so transpose it.
        upper = np.linalg.cholesky(nat_mat).T
        unc_parts: list[float] = []
        for i in range(1, max_cov):
            col = upper[:i, i]
            denom = np.array([np.linalg.norm(upper[k : i + 1, i]) for k in range(i)])
            aux = np.arccos(col / denom)
            unc_parts.extend(np.log(aux / (math.pi - aux)).tolist())
        unc = np.asarray(unc_parts, dtype=np.float64)
        updated = replace(object, max_cov=max_cov, covariate=cov_store, value=unc)
    else:
        updated = replace(
            object,
            max_cov=max_cov,
            covariate=cov_store,
            value=np.zeros(n_par, dtype=np.float64),
        )
        from nlme.corfactor import _cor_factor_symm

        factor = _cor_factor_symm(updated)
        updated = replace(
            updated,
            factor=factor.values,
            log_det=-factor.log_det,
        )
    return updated


def coef(object, unconstrained: bool = True, **_ignored):
    """Extract constrained or unconstrained coefficients from a corSymm object."""
    if not isinstance(object, CorSymm):
        raise TypeError(f"do not know how to get coefficients for object of type {type(object)!r}")
    return _coef_cor_symm(object, unconstrained=unconstrained)


@dataclass(frozen=True, slots=True)
class _CoefVector:
    values: np.ndarray
    names: tuple[str | None, ...]


def _coef_cor_symm(object: CorSymm, unconstrained: bool) -> _CoefVector:
    if unconstrained:
        if object.fixed:
            return _CoefVector(np.array([], dtype=np.float64), ())
        return _CoefVector(np.asarray(object.value, dtype=np.float64).copy(), (None,) * object.value.size)
    if object.max_cov is None:
        raise ValueError("invalid length argument")
    from nlme.corfactor import symm_full_corr

    corr = symm_full_corr(
        np.asarray(object.value, dtype=np.float64),
        int(object.max_cov),
    )
    return _CoefVector(corr, (None,) * corr.size)
