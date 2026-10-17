import statistics
import time

import numpy as np
from matrixstats.rowprods import colProds

x = np.reshape(np.fromfile("/tmp/rowProds-seed1.bin", dtype="<f8"), (80, 40), order="F")


def time_one(fun, path):
    fun()
    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        fun()
        elapsed.append((time.perf_counter() - started) * 1000)
    np.asarray(fun(), dtype=np.float64).tofile(path)
    print(statistics.median(elapsed))


time_one(lambda: colProds(x), "/tmp/colProds-py.bin")
time_one(lambda: colProds(x, method="expSumLog"), "/tmp/colProds-exp-py.bin")
