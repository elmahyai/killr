import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from mclust.crimcoords import summary_crimcoords

obj = {
    "basis": np.arange(1, 13).reshape(6, 2, order="F"),
    "evalues": np.array([4.0, 2.0]),
    "projection": np.arange(1, 13).reshape(6, 2, order="F"),
}


def one():
    return summary_crimcoords(obj)


value = one()
expected = {
    "basis": obj["basis"],
    "evalues": np.array([4.0, 2.0]),
    "evalues.cumperc": np.array([400 / 6, 100.0]),
}
diffs = [
    np.max(np.abs(np.asarray(value[key]) - expected[key]))
    for key in expected
]
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - t0) * 1000)
print("matches", "true" if max(diffs) <= 1e-8 else "false")
print(f"max_abs_diff {max(diffs):.17g}")
print(f"translated_ms {statistics.median(elapsed):.17g}")
