"""Variance weights of a variance function (nlme varWeights generic)."""

from __future__ import annotations

from typing import Any

import numpy as np

from nlme.varcomb import VarComb, VarFunc


def varWeights(object: Any) -> np.ndarray | None:
    """Return the variance weights of a variance function.

    ``varComb`` objects return the product of their components' weights, as
    ``varWeights.varComb`` does. Any other ``varFunc`` returns the stored
    ``weights`` attribute, or ``None`` when it is not initialized.
    ``lmeStruct`` and ``glsStruct`` methods need the lme and gls fits, which
    are not translated yet, so they raise here.
    """
    if isinstance(object, VarComb):
        return _var_comb_weights(object)
    if isinstance(object, VarFunc):
        return _var_func_weights(object)
    raise TypeError(
        f"no applicable method for 'varWeights' applied to an object of class "
        f"{type(object).__name__!r}"
    )


def _var_func_weights(object: VarFunc) -> np.ndarray | None:
    return getattr(object, "weights", None)


def _var_comb_weights(object: VarComb) -> np.ndarray:
    parts = [varWeights(component) for component in object.components]
    if any(part is None for part in parts):
        raise ValueError("cannot compute weights of an uninitialized varComb")
    if not parts:
        return np.array([], dtype=np.float64)
    stacked = np.column_stack([np.asarray(part, dtype=np.float64).reshape(-1) for part in parts])
    return np.prod(stacked, axis=1)
