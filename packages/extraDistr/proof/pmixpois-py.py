import statistics
import time

import numpy as np
from extradistr.multivariate import pmixpois

def flatten(value):
    return np.ravel(np.asarray(value, dtype=float), order="C")

answer = pmixpois([0, 2, 5, 10], [1, 5], [0.3, 0.7])
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    pmixpois([0, 2, 5, 10], [1, 5], [0.3, 0.7])
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join(format(float(v), ".17g") for v in flatten(answer)))
print(format(statistics.median(elapsed), ".17g"))
