"""Timing case for rowWeightedMeans: the sample written by rowWeightedMeans-r.R.

One untimed call, then the median of 20. Prints milliseconds.
"""

import pathlib
import statistics
import time

import numpy as np
from matrixstats.rowweightedmeans import rowWeightedMeans

root = pathlib.Path(__file__).resolve().parent
raw = np.fromfile(root / "rowWeightedMeans-data.bin", dtype="<f8")
x = np.reshape(raw[: 400 * 250], (400, 250), order="F")
w = raw[400 * 250 :]


def one():
    return rowWeightedMeans(x, w=w, na_rm=False)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(f"{statistics.median(elapsed):.17g}")
