import json
import math
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.u_vectors import u_vectors


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def flatten_u(result):
    return np.concatenate(
        [
            np.asarray(result["k"], dtype=float).reshape(-1, order="F"),
            np.asarray(result["I"], dtype=float).reshape(-1, order="F"),
        ]
    )


def one():
    return np.concatenate([flatten_u(u_vectors(3)), flatten_u(u_vectors(4))])


value = clean(one().tolist())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
