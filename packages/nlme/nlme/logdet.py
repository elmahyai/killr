"""Log of the determinant of nlme objects (nlme ``logDet``)."""

from __future__ import annotations

from typing import Any

import numpy as np

from nlme.isinitialized import isInitialized
from nlme.matrix_assign import pd_matrix_from_params
from nlme.pdmat import PdMat
from nlme.restruct import PdMatElement, ReStruct


def _is_cor_ident(object: Any) -> bool:
    """Detect ``corIdent`` objects by class name (avoids the deprecated constructor import)."""
    return type(object).__name__ == "CorIdent"


def _pd_dim(object: PdMat | PdMatElement) -> int:
    if object.names:
        return len(object.names)
    ncol = getattr(object, "ncol", None)
    if ncol is None:
        raise ValueError("cannot determine the dimension of the pdMat object")
    return int(ncol)


def logDet(object: Any, **_ignored: Any) -> Any:
    """Log determinant of a ``pdMat``, ``reStruct`` or ``corIdent`` object.

    For ``pdMat`` the value is ``sum(log(svd(factor)))`` where ``factor`` is a
    square root of the matrix, which equals half the log determinant.  The
    singular values do not depend on which square root is used.  ``reStruct``
    returns one value per element.  ``corIdent`` returns zero.

    Correlation structures return half the log determinant of their
    correlation matrix, matching nlme's factor convention.
    """
    if isinstance(object, ReStruct):
        return np.array([logDet(element) for _, element in object.blocks], dtype=np.float64)
    if isinstance(object, (PdMat, PdMatElement)):
        if not isInitialized(object):
            raise ValueError("cannot extract the log of the determinant from an uninitialized object")
        mat = pd_matrix_from_params(object.pd_class, object.values, _pd_dim(object))
        factor = np.linalg.cholesky(mat)
        singular = np.linalg.svd(factor, compute_uv=False)
        return float(np.sum(np.log(singular)))
    if _is_cor_ident(object):
        return 0.0
    correlation_types = {
        "CorSymm",
        "CorCompSymm",
        "CorAR1",
        "CorARMA",
        "CorLin",
        "CorRatio",
        "CorSpher",
        "CorExp",
        "CorGaus",
        "CorCAR1",
    }
    if (
        hasattr(object, "classes") and "corStruct" in object.classes
    ) or type(object).__name__ in correlation_types:
        stored = getattr(object, "log_det", None)
        if stored is not None:
            return float(stored)
        if type(object).__name__ in {"CorSymm", "CorCompSymm"}:
            from nlme.corfactor import corFactor

            return float(-corFactor(object).log_det)
        from nlme.cormatrix import corMatrix

        matrix = corMatrix(object)
        if isinstance(matrix, (list, tuple)):
            return float(
                sum(_half_logdet(np.asarray(block, dtype=np.float64)) for block in matrix)
            )
        return _half_logdet(np.asarray(matrix, dtype=np.float64))
    raise TypeError(f"no applicable method for 'logDet' applied to {type(object).__name__}")


def _half_logdet(matrix: np.ndarray) -> float:
    sign, value = np.linalg.slogdet(matrix)
    if sign <= 0:
        raise ValueError("correlation matrix is not positive definite")
    return float(value / 2.0)
