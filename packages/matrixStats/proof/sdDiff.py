"""Timing case for sdDiff: the 100000 standard normals written by sdDiff.R.

One untimed call, then the median of 20. Prints the value, then milliseconds.
"""

import statistics
import time

import numpy as np
from matrixstats.vardiff import sdDiff

x = np.fromfile("/tmp/matrixstats-sdDiff.bin", dtype="<f8")


def one():
    return sdDiff(x)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(f"{one():.17g}")
print(f"{statistics.median(elapsed):.17g}")
