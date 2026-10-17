import json
import subprocess
import sys

import numpy as np

TOL = 1e-8
ROOT = "/home/ahmed/killr_projects/killr"

r_out = subprocess.check_output(
    ["R", "--slave"],
    input=open(f"{ROOT}/packages/deSolve/proof/euler1D-r.R").read(),
    text=True,
)
py_out = subprocess.check_output(
    [sys.executable, f"{ROOT}/packages/deSolve/proof/euler1D-py.py"],
    text=True,
)
r_data = json.loads(r_out)
py_data = json.loads(py_out)
r_val = np.array(r_data["value"], dtype=np.float64)
py_val = np.array(py_data["value"], dtype=np.float64)
max_diff = float(np.max(np.abs(r_val - py_val)))
matches = max_diff <= TOL
speedup = r_data["median_ms"] / py_data["median_ms"]
print(
    json.dumps(
        {
            "matches": matches,
            "max_abs_diff": max_diff,
            "r_ms": r_data["median_ms"],
            "translated_ms": py_data["median_ms"],
            "speedup": speedup,
            "tolerance": TOL,
        }
    )
)
