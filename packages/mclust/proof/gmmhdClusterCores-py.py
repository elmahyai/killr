import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.gmmhd_family import gmmhdClusterCores

obj = {
    "x": np.zeros((5, 1)),
    "nc": np.array([1, 2, 2, 1]),
    "con": [[np.array([1, 2, 3, 4, 5])], [np.array([1, 2]), np.array([3, 4, 5])],
            [np.array([1, 2]), np.array([3, 4]), np.array([5])], [np.array([1, 2, 3, 4, 5])]],
}
value = gmmhdClusterCores(obj)
times = []
for _ in range(20):
    started = time.perf_counter()
    gmmhdClusterCores(obj)
    times.append((time.perf_counter() - started) * 1000)
for item in value:
    print("NA" if np.isnan(item) else "%.17g" % item)
print("%.17g" % statistics.median(times))
