import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.sage_test import sage_test


def one():
    parts = [
        sage_test([0, 5, 10], [0, 30, 50], n1=10000, n2=15000),
        sage_test([1, 5, 10], [2, 4, 10], n1=100, n2=100),
        sage_test(5000, 6000, n1=10000, n2=15000),
        sage_test([3, 7], [4, 3], n1=20, n2=20),
        sage_test([0.4, 2.6], [1.4, 3.6]),
        sage_test([2, 8, 15], [1, 12, 5], n1=50, n2=60),
    ]
    return np.concatenate([np.asarray(part, dtype=float).reshape(-1) for part in parts])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join("%.17g" % float(v) for v in np.asarray(value, dtype=float)))
print("MS")
print("%.17g" % statistics.median(elapsed))
