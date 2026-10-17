"""Multiple of the identity (nlme ``pdIdent`` and ``pdConstruct.pdIdent``)."""

from __future__ import annotations

from typing import Any

import numpy as np

from nlme.pdconstruct import pdConstruct, resolve_value
from nlme.pdmat import PdMat


def pdIdent(value: Any = (), form: Any = None, nam: Any = None, data: Any = None) -> PdMat:
    """Construct a ``pdIdent`` object: ``sigma^2 * I``, parameterized by ``log(sigma)``."""
    obj = PdMat(values=np.empty(0), formula=None, names=(), pd_class="pdIdent")
    return pdConstruct(obj, value, form, nam, data)


def construct_pd_ident(object: PdMat, value: Any, form: Any, nam: Any, data: Any) -> PdMat:
    """``pdConstruct.pdIdent``: a matrix gives ``log(mean(diag(crossprod(chol))))/2``."""
    res = resolve_value(value, form, nam, data)
    if res.kind == "empty":
        ncol = len(res.names) if res.names else None
        return PdMat(
            values=np.empty(0), formula=res.formula, names=res.names, pd_class="pdIdent", ncol=ncol
        )
    if res.kind == "matrix":
        cross = res.chol.T @ res.chol
        values = np.array([np.log(np.mean(np.diag(cross))) / 2.0], dtype=np.float64)
        ncol = res.chol.shape[1]
    else:
        values = res.values
        if values.size > 1:
            raise ValueError(
                f"an object of length {values.size} does not match the required parameter size"
            )
        if not res.names and res.formula is None:
            raise ValueError(
                'must give names when initializing "pdIdent" from parameter without a formula'
            )
        ncol = len(res.names)
    return PdMat(
        values=np.asarray(values, dtype=np.float64),
        formula=res.formula,
        names=res.names,
        pd_class="pdIdent",
        ncol=ncol,
    )
