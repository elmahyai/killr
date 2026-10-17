"""General positive-definite matrix constructor (nlme ``pdSymm``)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping, Sequence

import numpy as np

from nlme.pdmat import PdMat, _pd_construct_pd_mat, pdMat


def pdSymm(
    value: Any = None,
    form: Any = None,
    nam: Sequence[str] | None = None,
    data: Mapping[str, Sequence[Any]] | None = None,
) -> PdMat:
    """Construct a ``pdSymm`` object (general symmetric matrix, log-SVD parameters).

    A square matrix is converted the way R's ``pdConstruct.pdSymm`` does it: the
    upper Cholesky factor ``U = chol(value)`` is decomposed as ``V diag(log d) V'``
    and the upper triangle is stored in column-major order.  A parameter vector
    is only length-checked and stored.
    """
    if isinstance(value, np.ndarray) and value.ndim == 2 and value.size > 0:
        base = _pd_construct_pd_mat(value, form, nam, data, "pdSymm")
        return _log_svd_parameters(base)
    return pdMat(value, form, nam, data, pdClass="pdSymm")


def _log_svd_parameters(base: PdMat) -> PdMat:
    # The shared constructor stores the lower Cholesky factor; R's chol() is upper.
    upper = np.asarray(base.values, dtype=np.float64).T
    _, singular, vt = np.linalg.svd(upper, full_matrices=False)
    log_matrix = vt.T @ (np.log(singular)[:, None] * vt)
    ncol = log_matrix.shape[0]
    values = np.array(
        [log_matrix[row, col] for col in range(ncol) for row in range(col + 1)],
        dtype=np.float64,
    )
    return replace(base, values=values, pd_class="pdSymm")
