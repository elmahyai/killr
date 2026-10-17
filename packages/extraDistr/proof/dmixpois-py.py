import statistics
import time

import numpy as np
from extradistr.multivariate import dmixpois

def flatten(value):
    return np.ravel(np.asarray(value, dtype=float), order="C")

answer = dmixpois([0, 1, 3, 8], [1, 5], [0.3, 0.7])
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    dmixpois([0, 1, 3, 8], [1, 5], [0.3, 0.7])
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join(format(float(v), ".17g") for v in flatten(answer)))
print(format(statistics.median(elapsed), ".17g"))
