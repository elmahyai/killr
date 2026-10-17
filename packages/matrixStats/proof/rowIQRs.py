import statistics
import time
from pathlib import Path

import numpy as np
from matrixstats.rowiqrs import rowIQRs

root = Path("/tmp/ms-rowquantiles-check")
flat = np.fromfile(root / "x.bin", dtype="<f8")
x = np.reshape(flat, (200, 80), order="F")
length = int((root / "rowIQRs-length.txt").read_text())
expected_false = np.fromfile(root / "rowIQRs-false.bin", dtype="<f8")
expected_true = np.fromfile(root / "rowIQRs-true.bin", dtype="<f8")
assert expected_false.size == length


def one():
    return rowIQRs(x, na_rm=False), rowIQRs(x, na_rm=True)


def max_abs_diff(got, expected):
    got = np.asarray(got, dtype=np.float64).ravel()
    expected = np.asarray(expected, dtype=np.float64).ravel()
    both_missing = np.isnan(got) & np.isnan(expected)
    one_missing = np.isnan(got) ^ np.isnan(expected)
    if one_missing.any():
        return float("inf")
    diff = np.zeros(got.shape, dtype=np.float64)
    finite = ~both_missing
    diff[finite] = np.abs(got[finite] - expected[finite])
    return float(diff.max()) if diff.size else 0.0


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
