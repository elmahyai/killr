import json
import math
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.matrix_rank import matrix_rank


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def one():
    a = np.diag(np.arange(1, 5, dtype=float))
    b = np.arange(1, 17, dtype=float).reshape(4, 4)
    singular = np.array([[1, 2], [2, 4]], dtype=float)
    return [
        matrix_rank(a),
        matrix_rank(b),
        matrix_rank(a, method="chol"),
        matrix_rank(b, method="chol"),
        matrix_rank(singular),
        matrix_rank(singular, method="chol"),
        matrix_rank(np.array([[3.5]], dtype=float)),
        matrix_rank(np.zeros((0, 0))),
        matrix_rank(np.array([[1, 3], [2, 4]], dtype=int)),
        matrix_rank(np.array([[True, True], [False, True]])),
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
