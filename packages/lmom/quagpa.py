from __future__ import annotations

import numpy as np

from ._quantile_common import parameters, probabilities


def quagpa(f, para=(0.0, 1.0, 0.0)):
    f = probabilities(f)
    para = parameters(para, 3)
    if para[1] <= 0:
        raise ValueError("distribution parameters invalid")
    if para[2] == 0:
        return para[0] + para[1] * (-np.log1p(-f))
    with np.errstate(divide="ignore", invalid="ignore"):
        return para[0] + para[1] / para[2] * (1.0 - (1.0 - f) ** para[2])
