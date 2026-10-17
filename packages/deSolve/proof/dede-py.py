import json
import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path("/home/ahmed/killr_projects/killr")
sys.path[:0] = [
    str(ROOT / "packages" / "deSolve"),
    str(ROOT / "crates" / "dede"),
    str(ROOT / "crates" / "lagvalue"),
]

from deSolve.dede import dede  # noqa: E402
from deSolve.lagvalue import lagvalue  # noqa: E402


def derivs(t, y, parms):
    del parms
    if t < 1:
        lag1 = math.cos(t - 1)
    else:
        lag1 = float(lagvalue(t - 1)[0])
    if t < 2:
        lag2 = math.sin(t - 2)
    else:
        lag2 = float(lagvalue(t - 2, 2))
    return [[lag1 * lag2, -y[0] * lag2]]


def one():
    times = np.linspace(0, 20, 2001, dtype=float)
    yout = dede({"y1": 0.0, "y2": 0.0}, times, derivs, None, atol=1e-9)
    return np.ravel(yout.data, order="F")


value = one()
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
        }
    )
)
