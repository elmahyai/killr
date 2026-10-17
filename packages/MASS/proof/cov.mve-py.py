import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/MASS")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/Formula")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")

from mass._r_rng import set_seed
from mass.cov_mve import cov_mve

x = np.array(
    [
        [2.4, 1.5, 0.3],
        [2.8, 1.3, 0.5],
        [0.5, 1.8, 0.4],
        [2.4, 2.0, 0.6],
        [0.3, 1.6, 0.2],
        [2.7, 1.4, 0.7],
        [0.7, 1.9, 0.1],
        [2.9, 2.2, 0.8],
        [0.8, 1.7, 0.3],
        [1.7, 1.1, 0.4],
    ],
    dtype=float,
)


def one():
    set_seed(123)
    fit = cov_mve(x)
    return np.concatenate(
        [
            np.asarray(fit.center, dtype=float).reshape(-1),
            np.asarray(fit.cov, dtype=float).reshape(-1, order="F"),
            np.array([fit.crit, fit.n_obs], dtype=float),
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
flat = np.asarray(value, dtype=float).reshape(-1)
print("\n".join("%.17g" % item for item in flat))
print("%.17g" % statistics.median(elapsed))
