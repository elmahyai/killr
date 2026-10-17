from __future__ import annotations

import numpy as np

from ._quantile_common import parameters, probabilities


def quagev(f, para=(0.0, 1.0, 0.0)):
    f = probabilities(f)
    para = parameters(para, 3)
    if para[1] <= 0:
        raise ValueError("distribution parameters invalid")
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        y = -np.log(f)
        if para[2] == 0:
            return para[0] - para[1] * np.log(y)
        return para[0] + para[1] / para[2] * (1.0 - y**para[2])
