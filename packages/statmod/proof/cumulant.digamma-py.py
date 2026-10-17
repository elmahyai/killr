import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.cumulant_digamma import cumulant_digamma


def one():
    theta = np.concatenate(
        [
            -np.exp(np.linspace(np.log(1e-3), np.log(500), 50)),
            np.array([-1e-6, -0.5, -1, -2, -10, -1000], dtype=float),
        ]
    )
    return cumulant_digamma(theta)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join("%.17g" % float(v) for v in np.asarray(value, dtype=float)))
print("MS")
print("%.17g" % statistics.median(elapsed))
