from __future__ import annotations

import numpy as np
from scipy.stats import lognorm

from ._quantile_common import parameters, probabilities


def qualn3(f, para=(0.0, 0.0, 1.0)):
    f = probabilities(f)
    para = parameters(para, 3)
    if para[2] <= 0:
        raise ValueError("distribution parameters invalid")
    return para[0] + lognorm.ppf(f, s=para[2], scale=np.exp(para[1]))
