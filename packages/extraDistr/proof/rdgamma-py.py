import math
import statistics
import time

import numpy as np
from boot.rng import set_seed
from extradistr.discrete import rdgamma

def show(value):
    arr = np.ravel(np.asarray(value, dtype=float), order="C")
    return ",".join("%.17g" % float(v) for v in arr)

set_seed(1)
value = rdgamma(4, 2, 1)
print(show(value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    rdgamma(4, 2, 1)
    elapsed.append((time.perf_counter() - started) * 1000.0)
print("%.17g" % statistics.median(elapsed))
