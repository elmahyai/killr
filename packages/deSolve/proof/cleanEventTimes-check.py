import json
import subprocess
import sys

TOL = 1e-8

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/deSolve")
from deSolve.cleanEventTimes import cleanEventTimes

import numpy as np

events = np.sort(
    np.array(
        [
            0,
            2,
            3,
            4 + 1e-10,
            5,
            7 - 1e-10,
            7 + 6e-15,
            7.5,
            9,
            24.9999,
            25,
            80,
            1001,
            1e300,
        ],
        dtype=float,
    )
)
times = np.sort(
    np.array(
        [
            0,
            *range(1, 8),
            4.5,
            6.75,
            7.5,
            9.2,
            9.0001,
            25,
            879,
            1e3,
            1e300 + 5,
        ],
        dtype=float,
    )
)

r_proc = subprocess.run(
    ["R", "--slave", "-f", "/home/ahmed/killr_projects/killr/packages/deSolve/proof/cleanEventTimes-r.R"],
    check=True,
    capture_output=True,
    text=True,
)
r_out = json.loads(r_proc.stdout)
py_proc = subprocess.run(
    [sys.executable, "/home/ahmed/killr_projects/killr/packages/deSolve/proof/cleanEventTimes-py.py"],
    check=True,
    capture_output=True,
    text=True,
)
py_timed = json.loads(py_proc.stdout)
py_out = [float(x) for x in cleanEventTimes(times, events)]

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
            "r_value": r_out["value"],
            "py_value": py_out,
        }
    )
)
