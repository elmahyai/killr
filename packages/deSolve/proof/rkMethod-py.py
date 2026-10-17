import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/deSolve")
from deSolve.rkMethod import flatten_rk_method, rkMethod


def one():
    return flatten_rk_method(rkMethod("ode45"))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    json.dumps(
        {
            "value": [float(item) for item in value],
            "median_ms": statistics.median(elapsed),
        }
    )
)
