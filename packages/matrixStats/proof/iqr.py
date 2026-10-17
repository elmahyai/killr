import statistics
import time
from pathlib import Path

import numpy as np
from matrixstats.iqr import iqr

root = Path("/tmp/ms-rowquantiles-check")
flat = np.fromfile(root / "x.bin", dtype="<f8")
x = np.reshape(flat, (200, 80), order="F")
expected_false = float(np.fromfile(root / "iqr-false.bin", dtype="<f8")[0])
expected_true = float(np.fromfile(root / "iqr-true.bin", dtype="<f8")[0])


def one():
    return iqr(x, na_rm=False), iqr(x, na_rm=True)


def max_abs_diff(got, expected):
    if np.isnan(got) and np.isnan(expected):
        return 0.0
    if np.isnan(got) or np.isnan(expected):
        return float("inf")
    return abs(float(got) - float(expected))


warmup = one()
gap = max(max_abs_diff(warmup[0], expected_false), max_abs_diff(warmup[1], expected_true))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(statistics.median(elapsed))
print(gap)
print(gap <= 1e-8)
