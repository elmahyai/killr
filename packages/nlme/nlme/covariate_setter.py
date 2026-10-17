"""Assign the primary covariate of a variance function (nlme ``covariate<-``)."""

from __future__ import annotations

import copy
from typing import Any

import numpy as np

from nlme.varcomb import _is_var_func


def covariate_assign(object: Any, value) -> Any:
    """Return ``object`` with its covariate replaced by ``value`` (R ``covariate<-.varFunc``)."""
    if not _is_var_func(object):
        raise TypeError(f"no applicable method for 'covariate<-' applied to {type(object)!r}")
    new_value = np.asarray(value, dtype=np.float64).reshape(-1)
    aux = getattr(object, "covariate", None)
    if aux is not None and np.asarray(aux).reshape(-1).size != new_value.size:
        raise ValueError('cannot change the length of covariate in "varFunc" object')
    result = copy.copy(object)
    result.covariate = new_value
    return result
