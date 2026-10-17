import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/abind")
from abind.asub import asub


def one():
    x = np.arange(1, 25, dtype=float).reshape((2, 3, 4), order="F")
    y = np.arange(1, int(np.prod(np.arange(1, 9))) + 1, dtype=float).reshape(
        tuple(range(1, 9)), order="F"
    )
    parts = [
        asub(x, 1, 1, drop=False),
        asub(x, [np.array([1, 2]), np.array([3, 4])], dims=[1, 3]),
        asub(
            x,
            [np.array([1, 2]), np.array([2]), np.array([1, 2])],
            dims=[1, 2, 3],
        ),
        asub(y, 1, 1),
        asub(y, 1, 2),
        asub(y, 1, 3),
        asub(y, 1, 3, drop=False),
        asub(y, [np.array([1]), np.array([1])], dims=[3, 5], drop=False),
        asub(y, [np.array([1]), np.array([1])], dims=[3, 5]),
    ]
    out = []
    for part in parts:
        data = np.asarray(part.data if hasattr(part, "data") else part, dtype=float)
        if data.ndim == 0:
            dims = [1]
        else:
            dims = list(data.shape)
        out.extend(float(size) for size in dims)
        out.extend(float(value) for value in np.ravel(data, order="F"))
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
