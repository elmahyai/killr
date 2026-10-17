import statistics
import time
from pathlib import Path

import numpy as np
from matrixstats.rowranks import rowRanks

here = Path(__file__).resolve().parent
flat = np.fromfile(here / "rowRanks-x.bin", dtype="<f8")
x = np.reshape(flat, (200, 80), order="F")
expected = np.fromfile(here / "rowRanks-y.bin", dtype="<i4").reshape((200, 80), order="F")

def one():
    return rowRanks(x)

got = one()
if not np.array_equal(got, expected):
    diff = np.max(np.abs(got.astype(np.float64) - expected.astype(np.float64)))
    raise SystemExit(f"rowRanks mismatch max_abs_diff={diff}")
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(statistics.median(elapsed))
