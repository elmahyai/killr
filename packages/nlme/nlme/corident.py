"""Independent (identity) correlation structure constructor (nlme corIdent)."""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np

_DEPRECATION_MSG = (
    'The "corIdent" class is deprecated.\n'
    "Use argument 'correlation = NULL' for uncorrelated errors in model functions."
)


@dataclass(slots=True)
class CorIdent:
    """Empty parameter storage with formula and fixed flag for uncorrelated errors."""

    value: np.ndarray
    formula: str | None = None
    fixed: bool = True


def corIdent(form: str | None = None) -> CorIdent:
    """Construct a deprecated corIdent object (uncorrelated errors; use correlation=None)."""
    warnings.warn(_DEPRECATION_MSG, DeprecationWarning, stacklevel=2)
    return CorIdent(np.array([], dtype=np.float64), form, True)


def coef(object, unconstrained: bool = True, **_ignored):
    """Extract coefficients from a corIdent object (always empty)."""
    if not isinstance(object, CorIdent):
        raise TypeError(f"do not know how to get coefficients for object of type {type(object)!r}")
    return _coef_cor_ident(object, unconstrained=unconstrained)


@dataclass(frozen=True, slots=True)
class _CoefVector:
    values: np.ndarray
    names: tuple[str | None, ...]


def _coef_cor_ident(object: CorIdent, unconstrained: bool) -> _CoefVector:
    del unconstrained
    return _CoefVector(np.array([], dtype=np.float64), ())
