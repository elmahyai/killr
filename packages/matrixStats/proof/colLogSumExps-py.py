import statistics
import time
from pathlib import Path

import numpy as np
from matrixstats.rowlogsumexps import colLogSumExps

path = Path("/tmp/rowlogsumexps-seed1.bin")
rng = np.random.default_rng(1)
lx = np.log(np.abs(rng.standard_normal((400, 250))) + 1e-12)
np.asfortranarray(lx).ravel(order="F").tofile(path)


def one():
    return colLogSumExps(lx, na_rm=False)


result = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(statistics.median(elapsed))
np.asarray(result, dtype=np.float64).tofile("/tmp/colLogSumExps-py.bin")
