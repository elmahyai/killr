import statistics
import time
from pathlib import Path

import numpy as np
from matrixstats.rowcumprods import rowCumprods

path = Path("/tmp/rowcumprods-seed1.bin")
rng = np.random.default_rng(1)
x = rng.uniform(0.5, 1.5, size=(200, 80))
np.asfortranarray(x).ravel(order="F").tofile(path)


def one():
    rowCumprods(x)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(statistics.median(elapsed))
