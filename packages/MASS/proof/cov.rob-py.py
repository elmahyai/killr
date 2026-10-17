import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/MASS")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")

from mass._r_rng import set_seed
from mass.cov_rob import cov_rob

stackloss = np.array(
    [
        [80, 27, 89, 42],
        [80, 27, 88, 37],
        [75, 25, 90, 37],
        [62, 24, 87, 28],
        [62, 22, 87, 18],
        [62, 23, 87, 18],
        [62, 24, 93, 19],
        [62, 24, 93, 20],
        [58, 23, 87, 15],
        [58, 18, 80, 14],
        [58, 18, 89, 14],
        [58, 17, 88, 13],
        [58, 18, 82, 11],
        [58, 19, 93, 12],
        [50, 18, 89, 8],
        [50, 18, 86, 7],
        [50, 19, 72, 8],
        [50, 19, 79, 8],
        [50, 20, 80, 9],
        [56, 20, 82, 15],
        [70, 20, 91, 15],
    ],
    dtype=float,
)


def one():
    set_seed(123)
    fit = cov_rob(stackloss)
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
