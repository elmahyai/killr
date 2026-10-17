import json
import statistics
import sys
import time

import numpy as np

ROOT = "/home/ahmed/killr_projects/killr"
sys.path.insert(0, f"{ROOT}/packages/deSolve")

from deSolve.zvode import zvode


def spin(t, y, parms):
    w = parms["w"]
    return [1j * w * y[0]]


def one():
    out = zvode({"z": 1 + 0j}, list(range(0, 7, 2)), spin, {"w": 1.0})
    flat = np.ravel(out.data, order="F")
    return np.concatenate([flat.real, flat.imag])


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
