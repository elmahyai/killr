from __future__ import annotations

from scipy.special import ndtri

from ._quantile_common import parameters, probabilities


def quanor(f, para=(0.0, 1.0)):
    f = probabilities(f)
    para = parameters(para, 2)
    if para[1] <= 0:
        raise ValueError("distribution parameters invalid")
    return para[0] + para[1] * ndtri(f)
