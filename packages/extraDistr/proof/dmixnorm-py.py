import statistics
import time

import numpy as np
from extradistr.multivariate import dmixnorm

def flatten(value):
    return np.ravel(np.asarray(value, dtype=float), order="C")

answer = dmixnorm([-1, 0, 2, 5], [0, 3], [1, 1.5], [0.4, 0.6])
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    dmixnorm([-1, 0, 2, 5], [0, 3], [1, 1.5], [0.4, 0.6])
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join(format(float(v), ".17g") for v in flatten(answer)))
print(format(statistics.median(elapsed), ".17g"))
