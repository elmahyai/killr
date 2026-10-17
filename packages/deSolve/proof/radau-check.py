import json
import subprocess
import sys

TOL = 1e-8

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/deSolve")
from deSolve.radau import radau

import numpy as np


def robertson(t, y, parms):
    dy1 = -0.04 * y[0] + 1e4 * y[1] * y[2]
    dy2 = 0.04 * y[0] - 1e4 * y[1] * y[2] - 3e7 * y[1] ** 2
    dy3 = 3e7 * y[1] ** 2
    return [[dy1, dy2, dy3]]


r_proc = subprocess.run(
    ["R", "--slave", "-f", "/home/ahmed/killr_projects/killr/packages/deSolve/proof/radau-r.R"],
    check=True,
    capture_output=True,
    text=True,
)
r_out = json.loads(r_proc.stdout)
py_proc = subprocess.run(
    [sys.executable, "/home/ahmed/killr_projects/killr/packages/deSolve/proof/radau-py.py"],
    check=True,
    capture_output=True,
    text=True,
)
py_timed = json.loads(py_proc.stdout)
py_out = np.ravel(
    radau([1.0, 0.0, 0.0], [0.0, 10.0, 20.0, 30.0, 40.0], robertson, None).data,
    order="F",
).tolist()

max_abs_diff = 0.0
if len(r_out["value"]) != len(py_out):
    max_abs_diff = float("inf")
else:
    for r_v, py_v in zip(r_out["value"], py_out, strict=True):
        max_abs_diff = max(max_abs_diff, abs(r_v - py_v))

matches = max_abs_diff <= TOL
print(
    json.dumps(
        {
            "r_ms": r_out["median_ms"],
            "translated_ms": py_timed["median_ms"],
            "max_abs_diff": max_abs_diff,
            "matches": matches,
        }
    )
)
