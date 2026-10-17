"""Timing case for colVarDiffs: the 200 by 80 matrix written by colVarDiffs.R.

Axis 0 is rows. One untimed call, then the median of 20.
Prints the values, then milliseconds.
"""

import statistics
import time

import numpy as np
from matrixstats.vardiff import colVarDiffs

raw = np.fromfile("/tmp/matrixstats-colVarDiffs.bin", dtype="<f8")
x = raw.reshape((200, 80), order="F")


def one():
    return colVarDiffs(x)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    value = one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(" ".join(f"{item:.17g}" for item in value))
print(f"{statistics.median(elapsed):.17g}")
