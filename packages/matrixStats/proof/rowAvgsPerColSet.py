import statistics
import time

import numpy as np
from matrixstats.rowavgs import rowAvgsPerColSet

x = np.fromfile("/tmp/rowavgs-seed1.bin", dtype="<f8").reshape((500, 200), order="F")
sets = np.column_stack(
    [np.arange(1, 31), np.arange(31, 61), np.arange(61, 91), np.arange(91, 121)]
)


def one():
    rowAvgsPerColSet(x, S=sets)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(statistics.median(elapsed))
