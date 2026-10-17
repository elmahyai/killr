"""Time matrixstats.indexbyrow.indexByRow. One untimed call, then the median of 20.

Python time is time.perf_counter(), in milliseconds. The timed call is
dim = (500, 400), idxs None. A short idxs vector and a negative idxs vector
are checked outside the timer.
"""

import statistics
import time

from matrixstats.indexbyrow import indexByRow

dim = (500, 400)


def one():
    return indexByRow(dim)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000.0)

y = one()
try:
    indexByRow(dim, idxs=[-1, -2])
    negative = ""
except ValueError as err:
    negative = str(err)

short = indexByRow(dim, idxs=[1, 7, 400, 200_000])
print(f"{statistics.median(elapsed):.17g}")
print(" ".join(str(int(value)) for value in short))
print(negative)
print(y.size)
print(int(y[0]), int(y[-1]))
