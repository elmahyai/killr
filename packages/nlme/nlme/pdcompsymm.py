"""Compound-symmetry structure (nlme ``pdCompSymm`` and ``pdConstruct.pdCompSymm``)."""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

from nlme.pdconstruct import pdConstruct, resolve_value
from nlme.pdmat import PdMat


def pdCompSymm(value: Any = (), form: Any = None, nam: Any = None, data: Any = None) -> PdMat:
    """Construct a ``pdCompSymm`` object: equal variances and one common correlation.

    Parameters are ``c(log(sd), z)`` with ``z = log((rho + 1/(n-1)) / (1 - rho))``.
    """
    obj = PdMat(values=np.empty(0), formula=None, names=(), pd_class="pdCompSymm")
    return pdConstruct(obj, value, form, nam, data)


def construct_pd_comp_symm(object: PdMat, value: Any, form: Any, nam: Any, data: Any) -> PdMat:
    """``pdConstruct.pdCompSymm``: a matrix gives the mean variance and mean correlation."""
    res = resolve_value(value, form, nam, data)
    if res.kind == "empty":
        ncol = len(res.names) if res.names else None
        return PdMat(
            values=np.empty(0),
            formula=res.formula,
            names=res.names,
            pd_class="pdCompSymm",
            ncol=ncol,
        )
    if res.kind == "matrix":
        cross = res.chol.T @ res.chol
        nc = cross.shape[0]
        diag = np.diag(cross)
        corr = cross / np.sqrt(np.outer(diag, diag))
        off = corr[~np.eye(nc, dtype=bool)]
        aux = float(np.mean(off))
        if aux <= -1.0 / (nc - 1):
            aux = -1.0 / nc
            warnings.warn(
                'initializing "pdCompSymm" object is not positive definite', stacklevel=2
            )
        values = np.array(
            [np.log(np.mean(diag)) / 2.0, np.log((aux + 1.0 / (nc - 1)) / (1.0 - aux))],
            dtype=np.float64,
        )
        ncol = nc
    else:
        values = res.values
        if values.size != 2:
            raise ValueError(
                f"an object of length {values.size} does not match the required parameter size"
            )
        if not res.names and res.formula is None:
            raise ValueError(
                'must give names when initializing "pdCompSymm" from parameter without a formula'
            )
        ncol = len(res.names)
    return PdMat(
        values=np.asarray(values, dtype=np.float64),
        formula=res.formula,
        names=res.names,
        pd_class="pdCompSymm",
        ncol=ncol,
    )
