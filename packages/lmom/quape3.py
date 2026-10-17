from __future__ import annotations

import numpy as np
from scipy.stats import gamma, norm

from ._quantile_common import parameters, probabilities


def quape3(f, para=(0.0, 1.0, 0.0)):
    f = probabilities(f)
    para = parameters(para, 3)
    if para[1] <= 0:
        raise ValueError("distribution parameters invalid")
    if abs(para[2]) <= 1e-8:
        return norm.ppf(f, loc=para[0], scale=para[1])
    alpha = 4.0 / para[2] ** 2
    beta = abs(0.5 * para[1] * para[2])
    if para[2] > 0:
        return para[0] - alpha * beta + beta * np.maximum(0.0, gamma.ppf(f, alpha))
    return para[0] + alpha * beta - beta * np.maximum(0.0, gamma.ppf(1.0 - f, alpha))
