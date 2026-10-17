from __future__ import annotations

import numpy as np

from ._quantile_common import parameters, probabilities


def quaglo(f, para=(0.0, 1.0, 0.0)):
    f = probabilities(f)
    para = parameters(para, 3)
    if para[1] <= 0:
        raise ValueError("distribution parameters invalid")
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        if para[2] == 0:
            return para[0] + para[1] * np.log(f / (1.0 - f))
        return para[0] + para[1] / para[2] * (1.0 - ((1.0 - f) / f) ** para[2])
