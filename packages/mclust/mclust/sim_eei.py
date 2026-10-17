"""Translation of mclust ``simEEI``: simulate from the diagonal equal-volume and shape model."""

from __future__ import annotations

from typing import Any

import numpy as np

from mclust._sim_core import (
    SimMatrix,
    mean_matrix,
    mixing_proportions,
    missing_result,
    multivariate_sim,
    parameters_missing,
    r_diag,
    r_rmul,
    r_sample_prob,
    seed_if,
)


def simEEI(parameters: dict[str, Any], n: int, seed: Any = None, **_: Any) -> SimMatrix:
    seed_if(seed)
    mu, d, G = mean_matrix(parameters)
    if parameters_missing(parameters):
        return missing_result("EEI", n, d + 1)
    pro = mixing_proportions(parameters, G)
    clabels = r_sample_prob(G, int(n), pro)

    variance = parameters["variance"]
    shape = np.asarray(variance["shape"], dtype=float).ravel()
    if shape.size != d:
        raise ValueError("shape incompatible with mean")
    chol = r_diag(np.sqrt(r_rmul(variance["scale"], shape)))

    return multivariate_sim("EEI", n, clabels, G, d, mu, lambda k: chol)
