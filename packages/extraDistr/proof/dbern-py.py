import math
import statistics
import time

import numpy as np
from extradistr.discrete import dbern

def show(value):
    arr = np.ravel(np.asarray(value, dtype=float), order="C")
    return ",".join("%.17g" % float(v) for v in arr)

value = dbern([0, 1, 2], 0.3)
print(show(value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    dbern([0, 1, 2], 0.3)
    elapsed.append((time.perf_counter() - started) * 1000.0)
print("%.17g" % statistics.median(elapsed))
