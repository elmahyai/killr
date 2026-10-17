import statistics
import time
from pathlib import Path

import numpy as np
from matrixstats.rowquantiles import colQuantiles

root = Path("/tmp/ms-rowquantiles-check")
flat = np.fromfile(root / "x.bin", dtype="<f8")
x = np.reshape(flat, (200, 80), order="F")
probs = np.array([0.25, 0.75])
nrow, ncol = (int(part) for part in (root / "colQuantiles-shape.txt").read_text().split())
expected_false = np.reshape(np.fromfile(root / "colQuantiles-false.bin", dtype="<f8"), (nrow, ncol), order="F")
expected_true = np.reshape(np.fromfile(root / "colQuantiles-true.bin", dtype="<f8"), (nrow, ncol), order="F")


def one():
    return (
        colQuantiles(x, probs=probs, na_rm=False),
        colQuantiles(x, probs=probs, na_rm=True),
    )


def max_abs_diff(got, expected):
    got = np.asarray(got, dtype=np.float64)
    expected = np.asarray(expected, dtype=np.float64)
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
