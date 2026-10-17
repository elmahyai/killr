import statistics
import time

import numpy as np
from matrixstats.alloc import allocVector


def one():
    return allocVector(1_000_000, 1.5)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
y = one()
y.astype("<f8", copy=False).ravel().tofile("/tmp/ms-allocVector-py.bin")
with open("/tmp/ms-allocVector-py.meta", "w", encoding="utf-8") as handle:
    handle.write(f"{y.dtype}\n")
    handle.write(f"{y.size}\n")
    handle.write(f"{float(y.ravel()[0]):.17g}\n")
    handle.write(f"{int(np.sum(y != 1.5))}\n")
print(statistics.median(elapsed))
