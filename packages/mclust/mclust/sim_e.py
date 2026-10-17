"""Translation of mclust ``simE``: simulate from the univariate equal-variance model.

R checks for missing parameters before ``set.seed``, so the seed is set after that check.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from mclust._sim_core import (
    SimMatrix,
    mixing_proportions,
    parameters_missing,
    r_rnorm,
    r_sample_prob,
    seed_if,
    tabulate,
    missing_result,
)


def simE(parameters: dict[str, Any], n: int, seed: Any = None, **_: Any) -> SimMatrix:
    if parameters_missing(parameters):
        return missing_result("E", n, 2)
    seed_if(seed)
    mu = np.asarray(parameters["mean"], dtype=float).ravel()
    G = mu.size
    pro = mixing_proportions(parameters, G)
    clabels = r_sample_prob(G, int(n), pro)
    ctabel = tabulate(clabels, G)
    x = np.zeros(int(n))
    sd = np.sqrt(np.asarray(parameters["variance"]["sigmasq"], dtype=float)).ravel()
    for k in range(1, G + 1):
        x[clabels == k] = mu[k - 1] + r_rnorm(int(ctabel[k - 1]), 0.0, sd)
    return SimMatrix(np.column_stack([clabels.astype(float), x]), "E", ["group", "1"])
