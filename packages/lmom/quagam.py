from __future__ import annotations

import numpy as np
from scipy.stats import gamma

from ._quantile_common import parameters, probabilities


def quagam(f, para=(1.0, 1.0)):
    f = probabilities(f)
    para = parameters(para, 2)
    if np.any(para <= 0):
        raise ValueError("distribution parameters invalid")
    return para[1] * np.maximum(0.0, gamma.ppf(f, para[0]))
