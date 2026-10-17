"""Fixed-effects estimates (nlme ``fixef`` and its alias ``fixed.effects``)."""

from __future__ import annotations

from typing import Any

import numpy as np

from nlme.lmlistformula import LmList, coef


def fixef(object: Any) -> np.ndarray | None:
    """Fixed-effects coefficients of an ``lme`` or ``lmList`` fit (R ``fixef``)."""
    if isinstance(object, LmList):
        return _fixef_lm_list(object)
    coefficients = getattr(object, "coefficients", None)
    if coefficients is not None and hasattr(coefficients, "fixed"):
        return np.asarray(coefficients.fixed, dtype=np.float64)
    raise TypeError(f"no applicable method for 'fixef' applied to {type(object)!r}")


def fixed_effects(object: Any) -> np.ndarray | None:
    """Alias of :func:`fixef` (R ``fixed.effects``, a generic that dispatches to ``fixef``)."""
    return fixef(object)


def _fixef_lm_list(object: LmList) -> np.ndarray | None:
    """``fixef.lmList``: column means of the per-group coefficient matrix, ignoring NA."""
    table = coef(object)
    if table is None:
        return None
    return np.nanmean(np.asarray(table.values, dtype=np.float64), axis=0)
