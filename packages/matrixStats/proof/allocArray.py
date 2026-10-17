import statistics
import time

import numpy as np
from matrixstats.alloc import allocArray


def one():
    return allocArray([2000, 500], 1.5)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
y = one()
y.astype("<f8", copy=False).ravel().tofile("/tmp/ms-allocArray-py.bin")
with open("/tmp/ms-allocArray-py.meta", "w", encoding="utf-8") as handle:
    handle.write(f"{y.dtype}\n")
    handle.write(" ".join(str(extent) for extent in y.shape) + "\n")
    handle.write(f"{float(y.ravel()[0]):.17g}\n")
    handle.write(f"{int(np.sum(y != 1.5))}\n")
print(statistics.median(elapsed))
