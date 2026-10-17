import json
import statistics
import time

import numpy as np
from matrixstats.signtabulate import signTabulate

NA_INTEGER = -2147483648

rng = np.random.default_rng(1)
x = rng.standard_normal(100_000)
x[[0, 9, 99, 999, 9999]] = 0
x[[1, 19, 199]] = np.nan
x[2] = np.inf
x[3] = -np.inf
x[4] = np.nan

double_small = signTabulate(np.array([-2.0, -np.inf, 0.0, 1.0, np.inf, np.nan, np.nan]))
integer_small = signTabulate(
    np.array([-2, -1, 0, 1, NA_INTEGER, 5], dtype=np.int32)
)


def one():
    return signTabulate(x)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({
    "double_small": double_small.tolist(),
    "integer_small": integer_small.tolist(),
    "timed": one().tolist(),
    "median_ms": statistics.median(elapsed),
}))
