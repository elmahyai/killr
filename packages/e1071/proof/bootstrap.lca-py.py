import json
import statistics
import sys
import time

import numpy as np

sys.path[:0] = [
    "/home/ahmed/killr_projects/killr/packages/e1071",
    "/home/ahmed/killr_projects/killr/packages/boot",
    "/home/ahmed/killr_projects/killr/packages/zoo",
]
from boot.rng import set_seed
from e1071.bootstrap_lca import bootstrap_lca
from e1071.lca import lca


def one():
    set_seed(4242)
    x = np.array(
        [
            [0, 1, 0, 1],
            [1, 0, 1, 0],
            [0, 0, 1, 1],
            [1, 1, 0, 0],
            [0, 1, 1, 0],
            [1, 0, 0, 1],
            [0, 1, 0, 0],
            [1, 0, 1, 1],
        ],
        dtype=float,
    )
    fit = lca(x, 2, niter=15, matchdata=False)
    boot = bootstrap_lca(fit, nsamples=4, lcaiter=12, verbose=False)
    logl = np.asarray(boot["logl"], dtype=float).reshape(-1, order="F")
    loglsat = np.asarray(boot["loglsat"], dtype=float).reshape(-1, order="F")
    lratio = np.asarray(boot["lratio"], dtype=float).reshape(-1, order="F")
    chisq = np.asarray(boot["chisq"], dtype=float).reshape(-1, order="F")
    return (
        list(logl)
        + list(loglsat)
        + list(lratio)
        + [
            boot["lratiomean"],
            boot["lratiosd"],
            boot["lratioorg"],
            boot["zratio"],
            boot["pvalzratio"],
            boot["pvalratio"],
        ]
        + list(chisq)
        + [
            boot["chisqmean"],
            boot["chisqsd"],
            boot["chisqorg"],
            boot["zchisq"],
            boot["pvalzchisq"],
            boot["pvalchisq"],
            boot["nsamples"],
            boot["lcaiter"],
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
