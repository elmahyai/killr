"""Translation of mclust ``simEEE``: simulate from the ellipsoidal equal-volume, shape and orientation model."""

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
    r_sample_prob,
    seed_if,
)


def simEEE(parameters: dict[str, Any], n: int, seed: Any = None, **_: Any) -> SimMatrix:
    seed_if(seed)
    mu, d, G = mean_matrix(parameters)
    if parameters_missing(parameters):
        return missing_result("EEE", n, d + 1)
    pro = mixing_proportions(parameters, G)
    clabels = r_sample_prob(G, int(n), pro)

    variance = parameters["variance"]
    chol_sigma = variance.get("cholSigma")
    if chol_sigma is None:
        sigma = variance.get("Sigma")
        if sigma is None:
            raise ValueError("variance parameters must inlcude either Sigma or cholSigma")
        # R's chol() returns the upper-triangular U with t(U) %*% U = Sigma.
        chol = np.linalg.cholesky(np.asarray(sigma, dtype=float)).T
    else:
        chol = np.asarray(chol_sigma, dtype=float)

    return multivariate_sim("EEE", n, clabels, G, d, mu, lambda k: chol)
