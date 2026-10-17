"""Timing case for rowWeightedSds. One untimed call, then the median of 20."""

import pathlib
import statistics
import time

import numpy as np
from matrixstats.weightedvar import rowWeightedSds

raw = np.fromfile(pathlib.Path(__file__).with_name("rowWeightedSds-data.bin"), dtype="<f8")
x = np.reshape(raw, (400, 250), order="F")


def one():
    return rowWeightedSds(x)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    value = one()
    elapsed.append((time.perf_counter() - started) * 1000)

np.asarray(value, dtype="<f8").tofile("/tmp/rowWeightedSds-py-value.bin")
print(f"{statistics.median(elapsed):.17g}")
