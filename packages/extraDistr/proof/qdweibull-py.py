import math
import statistics
import time

import numpy as np
from extradistr.discrete import qdweibull

def show(value):
    arr = np.ravel(np.asarray(value, dtype=float), order="C")
    return ",".join("%.17g" % float(v) for v in arr)

value = qdweibull([0, 0.2, 0.5, 0.9], 0.4, 1.3)
print(show(value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    qdweibull([0, 0.2, 0.5, 0.9], 0.4, 1.3)
    elapsed.append((time.perf_counter() - started) * 1000.0)
print("%.17g" % statistics.median(elapsed))
