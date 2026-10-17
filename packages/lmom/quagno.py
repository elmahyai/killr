from __future__ import annotations

import numpy as np
from scipy.special import ndtri

from ._quantile_common import parameters, probabilities


def quagno(f, para=(0.0, 1.0, 0.0)):
    f = probabilities(f)
    para = parameters(para, 3)
    if para[1] <= 0:
        raise ValueError("distribution parameters invalid")
    z = ndtri(f)
    if para[2] == 0:
        return para[0] + para[1] * z
    return para[0] + para[1] / para[2] * (1.0 - np.exp(-z * para[2]))
