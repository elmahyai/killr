"""Timing case for weightedSd. One untimed call, then the median of 20."""

import pathlib
import statistics
import time

import numpy as np
from matrixstats.weightedvar import weightedSd

raw = np.fromfile(pathlib.Path(__file__).with_name("weightedSd-data.bin"), dtype="<f8")
x = raw[:100_000]
w = raw[100_000:]


def one():
    return weightedSd(x, w)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    value = one()
    elapsed.append((time.perf_counter() - started) * 1000)

np.asarray([value], dtype="<f8").tofile("/tmp/weightedSd-py-value.bin")
print(f"{float(value):.17g}")
print(f"{statistics.median(elapsed):.17g}")
