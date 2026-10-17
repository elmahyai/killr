import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")

from boot.rng import set_seed
from statmod.compare_two_growth_curves import compareTwoGrowthCurves


def proof_data():
    group = np.array([2, 2, 2, 1, 1, 1, 2, 1], dtype=float)
    y = np.array(
        [
            [1.0, 1.2, 1.1, 0.9],
            [1.1, 1.3, 1.0, 1.0],
            [0.9, 1.0, 1.2, 1.1],
            [2.0, 2.1, 1.9, 2.2],
            [2.2, 2.0, 2.3, 2.1],
            [2.1, 2.4, 2.0, 2.0],
            [1.0, np.nan, 1.1, 1.0],
            [2.1, 2.0, np.nan, 2.2],
        ],
        dtype=float,
    )
    return group, y


def one():
    group, y = proof_data()
    set_seed(424242)
    out = compareTwoGrowthCurves(group, y, nsim=80)
    return np.array([out["stat"], out["p.value"]], dtype=float)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join(f"{float(x):.17g}" for x in value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
