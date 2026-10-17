"""Translation of mclust ``simEVI``: simulate from the diagonal equal-volume, varying-shape model."""

from __future__ import annotations

from typing import Any

import numpy as np

from mclust._sim_core import (
    SimMatrix,
    as_matrix,
    mean_matrix,
    mixing_proportions,
    missing_result,
    multivariate_sim,
    parameters_missing,
    r_diag,
    r_rmul_like,
    r_sample_prob,
    seed_if,
)


def simEVI(parameters: dict[str, Any], n: int, seed: Any = None, **_: Any) -> SimMatrix:
    seed_if(seed)
    mu, d, G = mean_matrix(parameters)
    if parameters_missing(parameters):
        return missing_result("EVI", n, d + 1)
    pro = mixing_proportions(parameters, G)
    clabels = r_sample_prob(G, int(n), pro)

    variance = parameters["variance"]
    # R's check is `!all(dim(shape) == dim(mean))`, and dim(mean) is NULL because mean is the
    # base function there. That makes the test always pass, so there is no check to translate.
    shape = as_matrix(variance["shape"])
    # R: scale * shape recycles the scale vector along the column-major order of the d-by-G matrix.
    sss = np.sqrt(r_rmul_like(variance["scale"], shape))

    return multivariate_sim("EVI", n, clabels, G, d, mu, lambda k: r_diag(sss[:, k - 1]))
