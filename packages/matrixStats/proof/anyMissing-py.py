import json
import statistics
import time

import numpy as np
from matrixstats.anymissing import anyMissing

rng = np.random.default_rng(1)
x = rng.standard_normal(100_000)
x[99::100] = np.nan

no_na = anyMissing(np.array([1.0, 2.0, 3.0, 4.0]))
has_na = anyMissing(np.array([1.0, np.nan, 3.0]))
idxs = anyMissing(np.array([1.0, np.nan, 3.0, 4.0]), idxs=[1, 3, 4])
listed = anyMissing([np.array([1.0, 2.0]), np.array([4.0, np.nan])])


def one():
    return anyMissing(x)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({
    "no_na": no_na,
    "has_na": has_na,
    "idxs": idxs,
    "listed": listed,
    "timed": one(),
    "median_ms": statistics.median(elapsed),
}))
