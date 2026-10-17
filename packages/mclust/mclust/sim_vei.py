"""Translation of mclust ``simVEI``: simulate from the diagonal equal-shape, varying-volume model."""

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
    r_sample_prob,
    seed_if,
)


def simVEI(parameters: dict[str, Any], n: int, seed: Any = None, **_: Any) -> SimMatrix:
    seed_if(seed)
    mu, d, G = mean_matrix(parameters)
    if parameters_missing(parameters):
        return missing_result("VEI", n, d + 1)
    pro = mixing_proportions(parameters, G)
    clabels = r_sample_prob(G, int(n), pro)

    variance = parameters["variance"]
    rtshape = np.sqrt(np.asarray(variance["shape"], dtype=float).ravel())
    if rtshape.size != d:
        raise ValueError("shape incompatible with mean")
    rtscale = np.sqrt(np.asarray(variance["scale"], dtype=float).ravel())
    if rtscale.size != G:
        raise ValueError("scale incompatible with mean")

    return multivariate_sim(
        "VEI", n, clabels, G, d, mu, lambda k: r_diag(rtscale[k - 1] * rtshape)
    )
