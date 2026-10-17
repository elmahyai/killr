import statistics
import time
from pathlib import Path

import numpy as np
from matrixstats.rowcumsums import rowCumsums

path = Path("/tmp/rowcumsums-seed1.bin")
rng = np.random.default_rng(1)
x = rng.standard_normal((400, 250))
np.asfortranarray(x).ravel(order="F").tofile(path)


def one():
    rowCumsums(x)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(statistics.median(elapsed))
