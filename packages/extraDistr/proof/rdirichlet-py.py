import statistics
import time

import numpy as np
from boot.rng import set_seed
from extradistr.multivariate import rdirichlet

def flatten(value):
    return np.ravel(np.asarray(value, dtype=float), order="C")

set_seed(1)
alpha = np.array([[1.0, 1.0, 1.0], [2.0, 3.0, 4.0]])
answer = rdirichlet(4, alpha)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    rdirichlet(4, alpha)
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join(format(float(v), ".17g") for v in flatten(answer)))
print(format(statistics.median(elapsed), ".17g"))
