"""Timing case for weightedMedian: the sample written by weightedMedian-r.R.

One untimed call, then the median of 20. Prints the value, then milliseconds.
"""

import pathlib
import statistics
import time

import numpy as np
from matrixstats.weightedmedian import weightedMedian

raw = np.fromfile(pathlib.Path(__file__).with_name("weightedMedian-data.bin"), dtype="<f8")
x = raw[:100_000]
w = raw[100_000:]


def one():
    return weightedMedian(x, w, na_rm=False)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(f"{one():.17g}")
print(f"{statistics.median(elapsed):.17g}")
