import statistics
import time

import numpy as np
from extradistr.multivariate import dbvpois

def flatten(value):
    return np.ravel(np.asarray(value, dtype=float), order="C")

answer = dbvpois([0, 1, 2, 3], [1, 1, 0, 2], [1, 1.5], 0.8, [0.2, 0.5])
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    dbvpois([0, 1, 2, 3], [1, 1, 0, 2], [1, 1.5], 0.8, [0.2, 0.5])
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join(format(float(v), ".17g") for v in flatten(answer)))
print(format(statistics.median(elapsed), ".17g"))
