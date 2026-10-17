import statistics
import time

import numpy as np
from matrixstats.rowprods import rowProds

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


time_one(lambda: rowProds(x), "/tmp/rowProds-py.bin")
time_one(lambda: rowProds(x, method="expSumLog"), "/tmp/rowProds-exp-py.bin")
