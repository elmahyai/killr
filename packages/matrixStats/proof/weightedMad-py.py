"""Timing case for weightedMad: the sample written by weightedMad-r.R.

One untimed call, then the median of 20. Prints the weighted value, the
unweighted value, and milliseconds for the weighted call.
"""

import pathlib
import statistics
import time

import numpy as np
from matrixstats.weightedmad import weightedMad

raw = np.fromfile(pathlib.Path(__file__).with_name("weightedMad-data.bin"), dtype="<f8")
x = raw[:20_000]
w = raw[20_000:]


def one():
    return weightedMad(x, w, na_rm=False)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(f"{one():.17g}")
print(f"{weightedMad(x):.17g}")
print(f"{statistics.median(elapsed):.17g}")
