"""Time matrixstats.diff2. One untimed call, then the median of 20.

Python times with time.perf_counter(), in milliseconds. The sample is the
vector written by diff2-r.R (100000 standard normal values, seed 1).
"""

import statistics
import sys
import time
from pathlib import Path

import numpy as np
from matrixstats.diff2 import diff2

sample_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("diff2-x.txt")
x = np.loadtxt(sample_path)


def one():
    return diff2(x, lag=1, differences=1)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000.0)
print(statistics.median(elapsed))
