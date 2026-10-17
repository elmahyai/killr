"""Timing case for colWeightedVars. One untimed call, then the median of 20."""

import pathlib
import statistics
import time

import numpy as np
from matrixstats.weightedvar import colWeightedVars

raw = np.fromfile(pathlib.Path(__file__).with_name("colWeightedVars-data.bin"), dtype="<f8")
x = np.reshape(raw, (400, 250), order="F")


def one():
    return colWeightedVars(x)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    value = one()
    elapsed.append((time.perf_counter() - started) * 1000)

np.asarray(value, dtype="<f8").tofile("/tmp/colWeightedVars-py-value.bin")
print(f"{statistics.median(elapsed):.17g}")
