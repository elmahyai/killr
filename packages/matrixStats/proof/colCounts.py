import statistics
import time
from pathlib import Path

import numpy as np
from matrixstats.rowcounts import colCounts

flat = np.fromfile("/tmp/ms-proof-colCounts-x.bin", dtype="<f8")
x = np.reshape(flat, (400, 250), order="F")

def tokens(value):
    if np.isscalar(value) or value is None or isinstance(value, (bool, np.bool_, int, float)):
        seq = [value]
    else:
        seq = list(np.asarray(value, dtype=object).reshape(-1))
    out = []
    for item in seq:
        if item is None:
            out.append("NA")
            continue
        if isinstance(item, (bool, np.bool_)):
            out.append("T" if bool(item) else "F")
            continue
        if isinstance(item, (float, np.floating)) and np.isnan(item):
            out.append("NA")
            continue
        if isinstance(item, (int, np.integer)):
            if int(item) == -2147483648:
                out.append("NA")
            else:
                out.append(str(int(item)))
            continue
        out.append(format(float(item), ".17g"))
    return out

def max_diff(got, exp):
    if len(got) != len(exp):
        return float("inf")
    worst = 0.0
    for left, right in zip(got, exp):
        if left == "NA" and right == "NA":
            continue
        if left == "NA" or right == "NA":
            return float("inf")
        if left in ("T", "F") or right in ("T", "F"):
            worst = max(worst, 0.0 if left == right else 1.0)
        else:
            worst = max(worst, abs(float(left) - float(right)))
    return worst

expected = Path("/tmp/ms-proof-colCounts-ans.txt").read_text().split()
got = tokens(colCounts(x))
worst = max_diff(got, expected)


def one():
    colCounts(x)

one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000.0)
print(statistics.median(elapsed))
print(worst)
