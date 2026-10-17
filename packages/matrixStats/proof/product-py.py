import statistics
import time

import numpy as np
from matrixstats.product import product

sample = np.fromfile("/tmp/killr-product-sample.bin", dtype="<f8")


def one():
    return product(sample)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(statistics.median(elapsed))
print(f"{one():.17g}")
