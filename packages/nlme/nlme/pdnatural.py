"""Natural positive-definite parametrization constructor (nlme ``pdNatural``)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping, Sequence

import numpy as np

from nlme.pdmat import PdMat, _pd_construct_pd_mat, pdMat


def pdNatural(
    value: Any = None,
    form: Any = None,
    nam: Sequence[str] | None = None,
    data: Mapping[str, Sequence[Any]] | None = None,
) -> PdMat:
    """Construct a ``pdNatural`` object.

    Parameters are ``log`` standard deviations followed by the generalized logit
    of the correlations (column-major lower triangle), as in R's
    ``pdConstruct.pdNatural``.  A matrix is converted from its upper Cholesky
    factor; a parameter vector is only length-checked and stored.
    """
    if isinstance(value, np.ndarray) and value.ndim == 2 and value.size > 0:
        base = _pd_construct_pd_mat(value, form, nam, data, "pdNatural")
        return replace(base, values=_natural_parameters(base), pd_class="pdNatural")

    obj = pdMat(value, form, nam, data, pdClass="pdNatural")
    if obj.values.size > 0:
        ncol = _ncol_from_length(int(obj.values.size))
        if obj.values.size != ncol * (ncol + 1) // 2:
            raise ValueError(
                f"an object of length {obj.values.size} does not match the required parameter size"
            )
    return obj


def _natural_parameters(base: PdMat) -> np.ndarray:
    # The shared constructor stores the lower Cholesky factor; R's chol() is upper.
    upper = np.asarray(base.values, dtype=np.float64).T
    ncol = upper.shape[1]
    if ncol == 1:
        return np.log(upper.reshape(-1))
    crossprod = upper.T @ upper
    std_dev = np.sqrt(np.diag(crossprod))
    corr = (crossprod / std_dev[:, None]).T / std_dev[:, None]
    lower = [corr[row, col] for col in range(ncol) for row in range(col + 1, ncol)]
    logits = [np.log((r + 1.0) / (1.0 - r)) for r in lower]
    return np.concatenate([np.log(std_dev), np.asarray(logits, dtype=np.float64)])


def _ncol_from_length(length: int) -> int:
    return int(round((np.sqrt(8 * length + 1) - 1) / 2))
