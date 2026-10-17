import statistics
import time

import numpy as np
from matrixstats.sum2 import sum2

sample = np.fromfile("/tmp/matrixstats-seed1.bin", dtype="<f8")


def one():
    sum2(sample, na_rm=False)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(statistics.median(elapsed))
