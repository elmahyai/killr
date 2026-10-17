import statistics
import time

import numpy as np
from matrixstats.rowweightedmedians import colWeightedMedians

x = np.fromfile("/tmp/colWeightedMedians-x.bin", dtype=np.float64).reshape((100, 40), order="F")
w = np.fromfile("/tmp/colWeightedMedians-w.bin", dtype=np.float64)


def one():
    return colWeightedMedians(x, w=w, na_rm=False)


result = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(statistics.median(elapsed))
np.asarray(result, dtype=np.float64).tofile("/tmp/colWeightedMedians-py.bin")
