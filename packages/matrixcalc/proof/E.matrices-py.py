import json
import math
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.e_matrices import e_matrices


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def flatten_e(blocks):
    parts = []
    for row in blocks:
        for matrix in row:
            parts.append(np.asarray(matrix, dtype=float).reshape(-1, order="F"))
    return np.concatenate(parts)


def one():
    return np.concatenate([flatten_e(e_matrices(3)), flatten_e(e_matrices(4))])


value = clean(one().tolist())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
