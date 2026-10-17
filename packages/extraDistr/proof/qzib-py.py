import math
import statistics
import time

import numpy as np
from extradistr.discrete import qzib

def show(value):
    arr = np.ravel(np.asarray(value, dtype=float), order="C")
    return ",".join("%.17g" % float(v) for v in arr)

value = qzib([0.1, 0.3, 0.8], 5, 0.4, 0.2)
print(show(value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    qzib([0.1, 0.3, 0.8], 5, 0.4, 0.2)
    elapsed.append((time.perf_counter() - started) * 1000.0)
print("%.17g" % statistics.median(elapsed))
