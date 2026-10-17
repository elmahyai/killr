import math
import statistics
import time

import numpy as np
from boot.rng import set_seed
from extradistr.discrete import rbnbinom

def show(value):
    arr = np.ravel(np.asarray(value, dtype=float), order="C")
    return ",".join("%.17g" % float(v) for v in arr)

set_seed(1)
value = rbnbinom(4, 3, 2, 4)
print(show(value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    rbnbinom(4, 3, 2, 4)
    elapsed.append((time.perf_counter() - started) * 1000.0)
print("%.17g" % statistics.median(elapsed))
