"""Timing case for x_OP_y: the sample written by x_OP_y-r.R.

One untimed call, then the median of 20. Prints the max absolute difference,
then milliseconds.
"""

import pathlib
import statistics
import time

import numpy as np
from matrixstats.x_op_y import x_OP_y

here = pathlib.Path(__file__).resolve().parent
raw = np.fromfile(here / "x_OP_y-data.bin", dtype="<f8")
x = np.reshape(raw[: 400 * 250], (400, 250), order="F")
y = raw[400 * 250 :]
reference = np.fromfile(here / "x_OP_y-ans.bin", dtype="<f8")


def one():
    return x_OP_y(x, y, "+")


got = np.ravel(one(), order="F")
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

diff = np.max(np.abs(got - reference))
print(f"{diff:.17g}")
print(f"{statistics.median(elapsed):.17g}")
