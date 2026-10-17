import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.power_fisher_test import power_fisher_test, set_seed


def one():
    set_seed(42)
    return np.array(
        [
            power_fisher_test(0.5, 0.9, 20, 20, nsim=100),
            power_fisher_test(0.3, 0.5, 10, 10, nsim=50),
            power_fisher_test(0.2, 0.8, 15, 25, nsim=80, alternative="greater"),
            power_fisher_test(0.2, 0.8, 15, 25, nsim=80, alternative="less", alpha=0.1),
        ],
        dtype=float,
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join("%.17g" % float(v) for v in np.asarray(value, dtype=float)))
print("MS")
print("%.17g" % statistics.median(elapsed))
