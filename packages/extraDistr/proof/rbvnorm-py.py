import statistics
import time

import numpy as np
from boot.rng import set_seed
from extradistr.multivariate import rbvnorm

def flatten(value):
    return np.ravel(np.asarray(value, dtype=float), order="C")

set_seed(1)
answer = rbvnorm(4, mean1=[0, 1], mean2=[0, -1], sd1=[1, 2], sd2=1, cor=[0, 0.5])
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    rbvnorm(4, mean1=[0, 1], mean2=[0, -1], sd1=[1, 2], sd2=1, cor=[0, 0.5])
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join(format(float(v), ".17g") for v in flatten(answer)))
print(format(statistics.median(elapsed), ".17g"))
