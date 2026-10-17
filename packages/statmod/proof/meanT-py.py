import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.mean_t import mean_t


def proof_matrices():
    rows = np.arange(1, 51, dtype=float).reshape(-1, 1)
    cols = np.arange(1, 31, dtype=float).reshape(1, -1)
    y1 = np.sin(rows * cols / 100)
    rows2 = np.arange(1, 41, dtype=float).reshape(-1, 1)
    y2 = np.cos(rows2 * cols / 100)
    for matrix in (y1, y2):
        flat = matrix.ravel(order="F")
        flat[np.arange(0, flat.size, 7)] = np.nan
        matrix[:] = flat.reshape(matrix.shape, order="F")
    return y1, y2


def one():
    y1, y2 = proof_matrices()
    return mean_t(y1, y2)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % float(value))
print("MS")
print("%.17g" % statistics.median(elapsed))
