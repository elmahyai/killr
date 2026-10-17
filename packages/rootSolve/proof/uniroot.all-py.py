import statistics
import time

import numpy as np

from rootSolve import uniroot_all


def fun(x):
    return np.cos(2 * np.asarray(x, dtype=float)) ** 3


def one():
    return uniroot_all(fun, [0, 10])


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
