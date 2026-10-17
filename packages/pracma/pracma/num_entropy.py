"""Approximate entropy and sample entropy."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.arrays import zeros
from pracma.num_helpers import is_r_numeric, repmat, sample_sd


def approx_entropy(ts, edim=2, r=None, elag=1):
    series = np.asarray(ts, dtype=float).reshape(-1)
    if r is None:
        r = 0.2 * sample_sd(series)
    radius = float(r)
    count = series.size
    result = np.zeros(2)
    for j in range(1, 3):
        m = int(edim) + j - 1
        width = count - m + 1
        data = np.asarray(zeros(m, width), dtype=float)
        for i in range(1, m + 1):
            data[i - 1, :] = series[i - 1:count - m + i]
        phi = np.zeros(width)
        for i in range(width):
            column = data[:, i:i + 1]
            distance = np.abs(data - repmat(column, 1, width))
            too_far = np.max(distance > radius, axis=0)
            phi[i] = np.sum(~too_far) / width
        result[j - 1] = np.sum(np.log(phi)) / width
    return float(result[0] - result[1])


def sample_entropy(ts, edim=2, r=None, tau=1):
    if not is_r_numeric(ts):
        raise PracmaError("is.numeric(ts) is not TRUE")
    if not is_r_numeric(edim):
        raise PracmaError("is.numeric(edim) is not TRUE")
    series = np.asarray(ts, dtype=float).reshape(-1)
    if r is None:
        r = 0.2 * sample_sd(series)
    radius = float(r)
    if tau > 1:
        series = series[::int(tau)]
    count = series.size
    dimension = int(edim)
    data = np.asarray(zeros(dimension + 1, count - dimension), dtype=float)
    for i in range(1, dimension + 2):
        data[i - 1, :] = series[i - 1:count - dimension + i - 1]
    correl = np.zeros(2)
    for m in range(dimension, dimension + 2):
        counts = np.zeros(count - dimension)
        temp = data[:m, :]
        for i in range(1, count - m):
            block = temp[:, i:count - dimension]
            column = temp[:, i - 1:i]
            distance = np.abs(block - repmat(column, 1, count - dimension - i))
            nearest = np.max(distance, axis=0)
            counts[i - 1] = np.sum(nearest < radius) / (count - dimension)
        correl[m - dimension] = np.sum(counts) / (count - dimension)
    return float(np.log(correl[0] / correl[1]))
