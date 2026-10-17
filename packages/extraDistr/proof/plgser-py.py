import math
import statistics
import time

import numpy as np
from extradistr.discrete import plgser

def show(value):
    arr = np.ravel(np.asarray(value, dtype=float), order="C")
    return ",".join("%.17g" % float(v) for v in arr)

value = plgser([0, 1, 2.4, 5], 0.5)
print(show(value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    plgser([0, 1, 2.4, 5], 0.5)
    elapsed.append((time.perf_counter() - started) * 1000.0)
print("%.17g" % statistics.median(elapsed))
