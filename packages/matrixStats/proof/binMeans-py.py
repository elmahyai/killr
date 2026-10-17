"""Timing proof for binMeans. One untimed call, then the median of 20.

Python time is time.perf_counter(), in milliseconds. x and y are R's
runif(100000, 0, 10) after set.seed(1). The timed call uses both bin
closures and a point that lands on a break.
"""

import statistics
import subprocess
import time

import numpy as np

from matrixstats.binmeans import binMeans

subprocess.check_call(
    [
        "Rscript",
        "-e",
        "set.seed(1); x <- runif(100000, 0, 10); y <- runif(100000, 0, 10); "
        'writeBin(x, "/tmp/killr-binmeans-x.bin"); writeBin(y, "/tmp/killr-binmeans-y.bin")',
    ]
)
x = np.fromfile("/tmp/killr-binmeans-x.bin", dtype=np.float64)
y = np.fromfile("/tmp/killr-binmeans-y.bin", dtype=np.float64)
bx = np.arange(11, dtype=np.float64)
boundary_x = np.array([0.0, 1.0, 2.0, 5.0, 10.0])
boundary_y = np.array([10.0, 20.0, 30.0, 40.0, 50.0])


def one():
    return (
        binMeans(y, x, bx, right=True),
        binMeans(y, x, bx, right=False),
        binMeans(boundary_y, boundary_x, bx, right=True),
        binMeans(boundary_y, boundary_x, bx, right=False),
    )


def emit(values):
    text = []
    for value in np.asarray(values, dtype=float):
        text.append("NA" if np.isnan(value) else f"{value:.17g}")
    return " ".join(text)


warm = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(f"{statistics.median(elapsed):.17g}")
for result in warm:
    print(emit(result))
    print(" ".join(str(int(value)) for value in result.count))
