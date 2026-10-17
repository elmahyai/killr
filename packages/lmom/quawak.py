from __future__ import annotations

import numpy as np

from ._quantile_common import parameters, probabilities


def quawak(f, para=(0.0, 1.0, 0.0, 0.0, 0.0)):
    f = probabilities(f)
    para = parameters(para, 5)
    alpha, beta, gamma, delta = para[1:]
    valid = (
        (gamma > 0 and alpha + gamma > 0 and beta + delta > 0)
        or (
            gamma >= 0
            and alpha + gamma >= 0
            and (beta + delta > 0 or (beta == gamma == delta == 0))
            and not (alpha == 0 and beta != 0)
            and not (gamma == 0 and delta != 0)
        )
    )
    if not valid:
        raise ValueError("distribution parameters invalid")
    flog = -np.log1p(-f)
    first = 0.0 if alpha == 0 else alpha * (
        flog if beta == 0 else -np.expm1(-beta * flog) / beta
    )
    second = 0.0 if gamma == 0 else gamma * (
        flog if delta == 0 else -(-np.expm1(delta * flog)) / delta
    )
    return para[0] + first + second
