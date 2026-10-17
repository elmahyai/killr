"""Timing case for rowWeightedMads: the matrix written by rowWeightedMads-r.R.

One untimed call, then the median of 20. Prints the 40 values, then milliseconds.
"""

import pathlib
import statistics
import time

import numpy as np
from matrixstats.weightedmad import rowWeightedMads

raw = np.fromfile(pathlib.Path(__file__).with_name("rowWeightedMads-data.bin"), dtype="<f8")
x = np.reshape(raw[: 40 * 200], (40, 200), order="F")
w = raw[40 * 200 :]


def one():
    return rowWeightedMads(x, w, na_rm=False)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

values = one()
for value in values:
    print(f"{value:.17g}")
print(f"{statistics.median(elapsed):.17g}")
