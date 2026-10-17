import json
import subprocess
import sys

TOL = 1e-8

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/deSolve")
from deSolve.rk4 import rk4
from deSolve.timestep import timestep

import numpy as np


def mod(t, x, parms):
    r = float(parms["r"])
    k = float(parms["K"])
    dx = r * x[0] * (1.0 - x[0] / k)
    return {"": np.array([dx], dtype=float), "prev": timestep(True), "curr": timestep(False)}


r_proc = subprocess.run(
    ["R", "--slave", "-f", "/home/ahmed/killr_projects/killr/packages/deSolve/proof/timestep-r.R"],
    check=True,
    capture_output=True,
    text=True,
)
r_out = json.loads(r_proc.stdout)
py_proc = subprocess.run(
    [sys.executable, "/home/ahmed/killr_projects/killr/packages/deSolve/proof/timestep-py.py"],
    check=True,
    capture_output=True,
    text=True,
)
py_timed = json.loads(py_proc.stdout)

r_int = subprocess.run(
    ["R", "--slave", "-f", "/home/ahmed/killr_projects/killr/packages/deSolve/proof/timestep-compare-r.R"],
    check=True,
    capture_output=True,
    text=True,
)
r_globals = json.loads(r_int.stdout)

out = rk4({"N": 0.1}, np.arange(0.0, 22.0, 2.0), mod, {"r": 0.5, "K": 100.0})
py_prev = out.data[:, out.colnames.index("prev")]
py_curr = out.data[:, out.colnames.index("curr")]

max_abs_diff = 0.0
for r_v, py_v in zip(r_out["value"], py_timed["value"], strict=True):
    max_abs_diff = max(max_abs_diff, abs(r_v - py_v))
for r_v, py_v in zip(r_globals["prev"], py_prev, strict=True):
    max_abs_diff = max(max_abs_diff, abs(r_v - py_v))
for r_v, py_v in zip(r_globals["curr"], py_curr, strict=True):
    max_abs_diff = max(max_abs_diff, abs(r_v - py_v))

matches = max_abs_diff <= TOL
print(
    json.dumps(
        {
            "r_ms": r_out["median_ms"],
            "translated_ms": py_timed["median_ms"],
            "max_abs_diff": max_abs_diff,
            "matches": matches,
            "r_value": r_out["value"],
            "py_value": py_timed["value"],
        }
    )
)
