"""Translation of mclust ``simEEV``: simulate from the ellipsoidal equal-volume and shape model."""

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
    r_rmul,
    r_sample_prob,
    seed_if,
)


def simEEV(parameters: dict[str, Any], n: int, seed: Any = None, **_: Any) -> SimMatrix:
    seed_if(seed)
    mu, d, G = mean_matrix(parameters)
    if parameters_missing(parameters):
        return missing_result("EEV", n, d + 1)
    pro = mixing_proportions(parameters, G)
    clabels = r_sample_prob(G, int(n), pro)

    variance = parameters["variance"]
    shape = np.asarray(variance["shape"], dtype=float).ravel()
    if shape.size != d:
        raise ValueError("shape incompatible with mean")
    sss = np.sqrt(r_rmul(variance["scale"], shape))
    orientation = np.asarray(variance["orientation"], dtype=float)

    def chol_for(k: int) -> np.ndarray:
        # R: t(orientation[, , k]) * sss recycles sss down the columns, so row i is scaled by sss[i].
        return orientation[:, :, k - 1].T * sss[:, np.newaxis]

    return multivariate_sim("EEV", n, clabels, G, d, mu, chol_for)
