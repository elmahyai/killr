import statistics
import time

import numpy as np
from boot.rng import set_seed
from extradistr.multivariate import rmixnorm

def flatten(value):
    return np.ravel(np.asarray(value, dtype=float), order="C")

set_seed(1)
answer = rmixnorm(4, [0, 4], [1, 1], [0.25, 0.75])
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    rmixnorm(4, [0, 4], [1, 1], [0.25, 0.75])
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join(format(float(v), ".17g") for v in flatten(answer)))
print(format(statistics.median(elapsed), ".17g"))
