import json
import math
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.matrix_trace import matrix_trace


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
    return [
        matrix_trace(a),
        matrix_trace(b),
        matrix_trace(np.array([[3.5]])),
        matrix_trace(np.zeros((0, 0))),
        matrix_trace(d),
        matrix_trace(np.array([[1, 3], [2, 4]])),
        matrix_trace(np.array([[True, True], [False, True]])),
    ]


value = clean(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
