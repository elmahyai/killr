import statistics
import time

import numpy as np
from extradistr.multivariate import ddirichlet

def flatten(value):
    return np.ravel(np.asarray(value, dtype=float), order="C")

x = np.array([[0.2, 0.3, 0.5], [0.1, 0.2, 0.7]])
alpha = np.array([[1.0, 2.0, 3.0], [0.5, 0.5, 0.5]])
answer = ddirichlet(x, alpha)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    ddirichlet(x, alpha)
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join(format(float(v), ".17g") for v in flatten(answer)))
print(format(statistics.median(elapsed), ".17g"))
