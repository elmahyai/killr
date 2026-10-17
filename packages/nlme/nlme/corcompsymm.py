"""Compound-symmetry correlation structure (nlme corCompSymm)."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from nlme.corstruct import _NlmeFrame, initialize_cor_struct


@dataclass(slots=True)
class CorCompSymm:
    """Unconstrained compound-symmetry parameter with formula metadata."""

    value: float
    formula: str = "~ 1"
    fixed: bool = False
    inf: float | None = None
    dim: Any = None
    groups: np.ndarray | None = None
    covariate: Any = None
    factor: np.ndarray | None = None
    log_det: float | None = None

    @property
    def classes(self) -> tuple[str, ...]:
        return ("corCompSymm", "corStruct")


def corCompSymm(
    value: float = 0.0,
    form: str | None = "~ 1",
    fixed: bool = False,
) -> CorCompSymm:
    """Construct a corCompSymm object from the intra-group correlation ``value``."""
    if abs(value) >= 1:
        raise ValueError('parameter in "corCompSymm" structure must be < 1 in absolute value')
    if form is None:
        form = "~ 1"
    return CorCompSymm(float(value), str(form), fixed)


def initialize(object: CorCompSymm, data: _NlmeFrame | Mapping[str, Any], **_ignored) -> CorCompSymm:
    """Initialize a corCompSymm object on grouped data."""
    if object.inf is not None:
        return object
    object = initialize_cor_struct(object, data)
    assert object.dim is not None
    inf = -1.0 / (object.dim.max_len - 1)
    nat_par = float(object.value)
    if nat_par <= inf:
        raise ValueError(
            f'initial value in "corCompSymm" must be greater than {inf}'
        )
    unc = math.log((nat_par - inf) / (1.0 - nat_par))
    from nlme.corfactor import _comp_symm_factor_list

    updated = replace(object, inf=inf, value=unc)
    factor, log_det = _comp_symm_factor_list(updated.value, updated.inf, updated.dim)
    return replace(
        updated,
        factor=factor,
        log_det=-log_det,
    )


def coef(object, unconstrained: bool = True, **_ignored):
    """Extract constrained or unconstrained coefficients from a corCompSymm object."""
    if not isinstance(object, CorCompSymm):
        raise TypeError(f"do not know how to get coefficients for object of type {type(object)!r}")
    return _coef_cor_comp_symm(object, unconstrained=unconstrained)


@dataclass(frozen=True, slots=True)
class _CoefVector:
    values: np.ndarray
    names: tuple[str | None, ...]


def _coef_cor_comp_symm(object: CorCompSymm, unconstrained: bool) -> _CoefVector:
    if unconstrained:
        if object.fixed:
            return _CoefVector(np.array([], dtype=np.float64), ())
        return _CoefVector(np.array([object.value], dtype=np.float64), (None,))
    if object.inf is None:
        raise ValueError("invalid length argument")
    aux = math.exp(object.value)
    rho = (aux + object.inf) / (aux + 1.0)
    return _CoefVector(np.array([rho], dtype=np.float64), ("Rho",))
