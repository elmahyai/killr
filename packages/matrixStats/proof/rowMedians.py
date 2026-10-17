"""Timing case for rowMedians: the 400 by 250 sample written by rowMedians.R.

One untimed call, then the median of 20. Prints milliseconds.
"""

import statistics
import time
from pathlib import Path

import numpy as np
from matrixstats.rowmedians import rowMedians

flat = np.fromfile(Path(__file__).with_name("rowMedians-x.bin"), dtype="<f8")
x = np.reshape(flat, (400, 250), order="F")


def one():
    rowMedians(x)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(statistics.median(elapsed))
