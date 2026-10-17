import statistics
import time

import numpy as np
from extradistr.multivariate import dbvnorm

def flatten(value):
    return np.ravel(np.asarray(value, dtype=float), order="C")

answer = dbvnorm([-1, 0, 1.5], [0.2, -0.3, 0.7], mean1=[0, 1], mean2=0, sd1=1, sd2=[1, 1.5], cor=[0.2, -0.4])
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    dbvnorm([-1, 0, 1.5], [0.2, -0.3, 0.7], mean1=[0, 1], mean2=0, sd1=1, sd2=[1, 1.5], cor=[0.2, -0.4])
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join(format(float(v), ".17g") for v in flatten(answer)))
print(format(statistics.median(elapsed), ".17g"))
