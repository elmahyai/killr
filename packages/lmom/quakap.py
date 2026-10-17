from __future__ import annotations

import numpy as np

from ._quantile_common import parameters, probabilities


def quakap(f, para=(0.0, 1.0, 0.0, 0.0)):
    f = probabilities(f)
    para = parameters(para, 4)
    if para[1] <= 0:
        raise ValueError("distribution parameters invalid")
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        first = -np.log(f) if para[3] == 0 else (1.0 - f**para[3]) / para[3]
        second = -np.log(first) if para[2] == 0 else (1.0 - first**para[2]) / para[2]
        result = para[0] + para[1] * second
        if para[3] <= 0 and para[2] <= 0:
            result = np.where(second == 1, np.inf, result)
        return result
