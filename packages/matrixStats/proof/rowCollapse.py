import statistics
import time

import numpy as np
from matrixstats.rowcollapse import rowCollapse

x = np.arange(1, 400 * 250 + 1, dtype=np.float64).reshape((400, 250), order="F")
idxs = np.resize(np.arange(1, 251), 400)


def one():
    rowCollapse(x, idxs)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(statistics.median(elapsed))
