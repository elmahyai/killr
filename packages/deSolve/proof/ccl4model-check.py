import json
import subprocess
import sys

TOL = 1e-8

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/deSolve")
from deSolve.ccl4model import ccl4model

import numpy as np

Pm = {
    "BW": 0.182,
    "QP": 4.0,
    "QC": 4.0,
    "VFC": 0.08,
    "VLC": 0.04,
    "VMC": 0.74,
    "QFC": 0.05,
    "QLC": 0.15,
    "QMC": 0.32,
    "PLA": 16.17,
    "PFA": 281.48,
    "PMA": 13.3,
    "PTA": 16.17,
    "PB": 5.487,
    "MW": 153.8,
    "VMAX": 0.04321671,
    "KM": 0.4027255,
    "CONC": 1000.0,
    "KL": 0.02,
    "RATS": 1.0,
    "VCHC": 3.8,
}
y = {"AI": 21.0, "AAM": 0.0, "AT": 0.0, "AF": 0.0, "AL": 0.0, "CLT": 0.0, "AM": 0.0}
times = [0.0, 0.1, 0.2, 0.3]

r_proc = subprocess.run(
    ["R", "--slave", "-f", "/home/ahmed/killr_projects/killr/packages/deSolve/proof/ccl4model-r.R"],
    check=True,
    capture_output=True,
    text=True,
)
r_out = json.loads(r_proc.stdout)
py_proc = subprocess.run(
    [sys.executable, "/home/ahmed/killr_projects/killr/packages/deSolve/proof/ccl4model-py.py"],
    check=True,
    capture_output=True,
    text=True,
)
py_timed = json.loads(py_proc.stdout)
py_out = np.ravel(ccl4model(times, y, Pm, method="rk4").data, order="F").tolist()

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
