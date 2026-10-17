"""Log-Cholesky parameterized positive-definite structure (nlme ``pdLogChol``)."""

from __future__ import annotations

from typing import Any

import numpy as np

from nlme.pdconstruct import pdConstruct, resolve_value
from nlme.pdmat import PdMat


def pdLogChol(value: Any = (), form: Any = None, nam: Any = None, data: Any = None) -> PdMat:
    """Construct a ``pdLogChol`` object.

    Parameters are ``log(diag(R))`` followed by the upper-triangle elements of
    the Cholesky factor ``R`` in column-major order.
    """
    obj = PdMat(values=np.empty(0), formula=None, names=(), pd_class="pdLogChol")
    return pdConstruct(obj, value, form, nam, data)


def construct_pd_log_chol(object: PdMat, value: Any, form: Any, nam: Any, data: Any) -> PdMat:
    """``pdConstruct.pdLogChol``: a matrix gives its log-Cholesky parameters."""
    res = resolve_value(value, form, nam, data)
    if res.kind == "empty":
        return PdMat(values=np.empty(0), formula=res.formula, names=res.names, pd_class="pdLogChol")
    if res.kind == "matrix":
        chol = res.chol
        q = chol.shape[0]
        upper = np.array([chol[i, j] for j in range(q) for i in range(j)], dtype=np.float64)
        values = np.concatenate([np.log(np.diag(chol)), upper])
    else:
        values = res.values
        n = values.size
        q = int(round((np.sqrt(8 * n + 1) - 1) / 2))
        if n != int(round(q * (q + 1) / 2)):
            raise ValueError(f"an object of length {n} does not match a Cholesky factor")
    return PdMat(
        values=np.asarray(values, dtype=np.float64),
        formula=res.formula,
        names=res.names,
        pd_class="pdLogChol",
    )
