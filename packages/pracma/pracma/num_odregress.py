"""Orthogonal distance regression for a hyperplane."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric, r_svd, repmat


def odregress(x, y):
    if not is_r_numeric(x):
        raise PracmaError("is.numeric(x) is not TRUE")
    if not is_r_numeric(y):
        raise PracmaError("is.numeric(y) is not TRUE")
    predictors = np.asarray(x, dtype=float)
    response = np.asarray(y, dtype=float).reshape(-1, 1)
    if predictors.ndim == 1:
        predictors = predictors.reshape(-1, 1)
    data = np.column_stack([predictors, response])
    rows = data.shape[0]
    independent = data.shape[1] - 1
    means = np.mean(data, axis=0)
    centered = data - repmat(means, rows, 1)
    _, _, vectors = r_svd(centered)
    normal = vectors[:, independent]
    slope = -vectors[:independent, independent] / vectors[independent, independent]
    intercept = float(np.mean(data @ vectors[:, independent]) / vectors[independent, independent])
    fitted = np.column_stack([predictors, np.ones(rows)]) @ np.concatenate([np.atleast_1d(slope), [intercept]])
    fitted = np.asarray(fitted, dtype=float).reshape(-1, 1)
    residual = response.reshape(-1, 1) - fitted
    error = np.abs((centered @ normal).reshape(-1, 1))
    return {
        "coeff": np.concatenate([np.atleast_1d(slope), [intercept]]),
        "ssq": float(np.sum(error ** 2)),
        "err": error,
        "fitted": fitted,
        "resid": residual,
        "normal": normal,
    }
