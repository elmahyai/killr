import json
import math
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.hilbert_schmidt_norm import hilbert_schmidt_norm


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def one():
    a = np.array([[3, 5, 7], [2, 6, 4], [0, 2, 8]], dtype=float)
    b = np.arange(1, 17, dtype=float).reshape(4, 4, order="C")
    v = np.arange(1, 13, dtype=float)
    return [
        hilbert_schmidt_norm(a),
        hilbert_schmidt_norm(b),
        hilbert_schmidt_norm(v),
        hilbert_schmidt_norm(np.array([[3.5]])),
        hilbert_schmidt_norm(np.zeros((0, 0))),
        hilbert_schmidt_norm(
            np.array(
                [[0.1, -1.5, 2.25], [4, 0.5, -0.25], [8, 3, 1.125]],
                dtype=float,
            )
        ),
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
