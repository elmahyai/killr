import json
import statistics
import sys
import time

import numpy as np

sys.path[:0] = [
    "/home/ahmed/killr_projects/killr/packages/e1071",
    "/home/ahmed/killr_projects/killr/packages/boot",
    "/home/ahmed/killr_projects/killr/packages/MASS",
]
from boot.rng import set_seed, unif
from e1071.lca import lca


def one():
    set_seed(4242)
    type1 = np.array([0.8, 0.8, 0.2, 0.2])
    type2 = np.array([0.2, 0.2, 0.8, 0.8])
    draws = [unif() for _ in range(400)]
    x = np.array(draws, dtype=float).reshape(100, 4, order="F")
    x[:50, :] = (x[:50, :] < type1).astype(float)
    x[50:, :] = (x[50:, :] < type2).astype(float)
    fit = lca(x, 2, niter=25, matchdata=True)
    classprob = np.asarray(fit["classprob"], dtype=float).reshape(-1, order="F")
    p = np.asarray(fit["p"], dtype=float).reshape(-1, order="F")
    matching = np.asarray(fit["matching"], dtype=float).reshape(-1, order="F")
    return list(classprob) + list(p) + list(matching) + [
        fit["logl"],
        fit["loglsat"],
        fit["chisq"],
        fit["lhquot"],
        fit["bic"],
        fit["bicsat"],
        fit["n"],
        fit["np"],
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
