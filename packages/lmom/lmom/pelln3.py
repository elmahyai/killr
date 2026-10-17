"""Lognormal type III parameters from L-moments."""

import numpy as np

from .pelgno import pelgno


def pelln3(xmom, bound=None):
    """Return lognormal III parameters, optionally with a lower bound."""
    values = np.asarray(xmom, dtype=float).ravel()
    if bound is not None:
        if values.size < 2:
            raise ValueError("with bound specified, need at least 2 L-moments")
        lam1 = values[0] - bound
        if lam1 <= 0 or values[1] <= 0 or values[1] >= lam1:
            raise ValueError("invalid L-moments")
        sigma = np.sqrt(2.0) * _qnorm((1.0 + values[1] / lam1) / 2.0)
        return np.array([bound, np.log(lam1) - 0.5 * sigma * sigma, sigma])
    if values.size < 3:
        raise ValueError("need at least 3 L-moments")
    gno = pelgno(values[:3])
    sigma = -gno[2]
    expmu = gno[1] / sigma
    return np.array([gno[0] - expmu, np.log(expmu), sigma])


def _qnorm(p):
    import statistics

    return statistics.NormalDist().inv_cdf(float(p))
