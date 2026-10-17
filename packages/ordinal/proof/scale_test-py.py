import json
import statistics
import time
from pathlib import Path

import numpy as np

from ordinal.scale_test import clm_like_for_scale_test, scale_test, scale_test_values

_RHO = Path(__file__).resolve().parent / "slice_wine_rho.npz"


def one():
    obj = clm_like_for_scale_test(str(_RHO))
    return scale_test_values(scale_test(obj))


value = np.ravel(np.asarray(one(), dtype=float), order="F")
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    json.dumps(
        {
            "value": [float(x) for x in value],
            "median_ms": statistics.median(elapsed),
        },
        allow_nan=True,
    )
)
