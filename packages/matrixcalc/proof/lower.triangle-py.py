import json
import math
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.lower_triangle import lower_triangle


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def one():
    a = np.arange(1, 17, dtype=float).reshape(4, 4)
    b = np.array(
        [
            [0.1, -1.5, 2.25],
            [4, 0.5, -0.25],
            [8, 3, 1.125],
        ],
        dtype=float,
    )
    d = np.zeros((64, 64), dtype=float)
    np.fill_diagonal(d, np.arange(1, 65, dtype=float) / 7)
    e = np.arange(1, 10, dtype=int).reshape(3, 3, order="F")
    f = np.array(
        [
            [True, False, True],
            [False, True, False],
            [True, False, True],
        ],
        dtype=bool,
    )
    parts = [
        lower_triangle(a),
        lower_triangle(b),
        lower_triangle(np.array([[3.5]])),
        lower_triangle(np.zeros((0, 0))),
        lower_triangle(d),
        lower_triangle(e),
        lower_triangle(f),
    ]
    return np.concatenate([part.reshape(-1, order="F") for part in parts])


value = clean(one().tolist())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
