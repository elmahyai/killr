"""Diagonal positive-definite structure (nlme ``pdDiag`` and ``pdConstruct.pdDiag``)."""

from __future__ import annotations

from typing import Any

import numpy as np

from nlme.pdconstruct import pdConstruct, resolve_value
from nlme.pdmat import PdMat


def pdDiag(value: Any = (), form: Any = None, nam: Any = None, data: Any = None) -> PdMat:
    """Construct a ``pdDiag`` object: diagonal, parameterized by ``log(sd)``."""
    obj = PdMat(values=np.empty(0), formula=None, names=(), pd_class="pdDiag")
    return pdConstruct(obj, value, form, nam, data)


def construct_pd_diag(object: PdMat, value: Any, form: Any, nam: Any, data: Any) -> PdMat:
    """``pdConstruct.pdDiag``: a matrix gives ``log(diag(crossprod(chol)))/2``."""
    res = resolve_value(value, form, nam, data)
    if res.kind == "empty":
        return PdMat(values=np.empty(0), formula=res.formula, names=res.names, pd_class="pdDiag")
    if res.kind == "matrix":
        cross = res.chol.T @ res.chol
        values = np.log(np.diag(cross)) / 2.0
    else:
        values = res.values
        if res.names and len(res.names) != values.size:
            raise ValueError(
                f"an object of length {values.size} does not match the required parameter size"
            )
    return PdMat(
        values=np.asarray(values, dtype=np.float64),
        formula=res.formula,
        names=res.names,
        pd_class="pdDiag",
    )
