from __future__ import annotations

import numpy as np

from ._quantile_common import parameters, probabilities


def quawei(f, para=(0.0, 1.0, 1.0)):
    f = probabilities(f)
    para = parameters(para, 3)
    if para[1] <= 0 or para[2] <= 0:
        raise ValueError("distribution parameters invalid")
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        return para[0] + para[1] * (-np.log1p(-f)) ** (1.0 / para[2])
