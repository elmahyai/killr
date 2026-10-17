"""Translation of mclust ``simEII``: simulate from the spherical equal-volume model.

The missing-parameter result has d columns and no group column, as in R.
"""

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


def simEII(parameters: dict[str, Any], n: int, seed: Any = None, **_: Any) -> SimMatrix:
    seed_if(seed)
    mu, d, G = mean_matrix(parameters)
    if parameters_missing(parameters):
        return missing_result("EII", n, d)
    pro = mixing_proportions(parameters, G)
    clabels = r_sample_prob(G, int(n), pro)

    sigmasq = parameters["variance"]["sigmasq"]
    # R: diag(rep(sqrt(sigmasq), d))
    chol = r_diag(np.tile(np.sqrt(np.asarray(sigmasq, dtype=float).ravel()), d))

    return multivariate_sim("EII", n, clabels, G, d, mu, lambda k: chol)
