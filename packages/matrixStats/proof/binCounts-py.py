"""Timing proof for binCounts. One untimed call, then the median of 20.

Python time is time.perf_counter(), in milliseconds. The sample is R's
runif(100000, 0, 10) after set.seed(1), including checks for both bin
closures and for a value that lands on a break.
"""

import statistics
import subprocess
import time

import numpy as np

from matrixstats.bincounts import binCounts

sample_path = "/tmp/killr-bincounts-x.bin"
subprocess.check_call(
    [
        "Rscript",
        "-e",
        'set.seed(1); x <- runif(100000, 0, 10); writeBin(x, "/tmp/killr-bincounts-x.bin")',
    ]
)
x = np.fromfile(sample_path, dtype=np.float64)
bx = np.arange(11, dtype=np.float64)
boundary = np.array([0.0, 1.0, 2.0, 5.0, 10.0])


def one():
    return (
        binCounts(x, bx, right=True),
        binCounts(x, bx, right=False),
        binCounts(boundary, bx, right=True),
        binCounts(boundary, bx, right=False),
    )


warm = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(f"{statistics.median(elapsed):.17g}")
for counts in warm:
    print(" ".join(str(int(value)) for value in counts))
