import statistics
import sys
import time
import warnings

import numpy as np

warnings.filterwarnings("ignore", category=RuntimeWarning)

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.logmdigamma import logmdigamma


def one():
    x = np.concatenate(
        [
            np.array([np.nan, 0.0, -1.0], dtype=float),
            np.exp(np.linspace(np.log(1e-3), np.log(4.999), 40)),
            np.array([5.0, 5.001, 10.0, 100.0, 1e6, 1e15], dtype=float),
        ]
    )
    return logmdigamma(x)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join("%.17g" % float(v) for v in np.asarray(value, dtype=float)))
print("MS")
print("%.17g" % statistics.median(elapsed))
