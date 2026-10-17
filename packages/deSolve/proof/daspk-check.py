import json
import subprocess
import sys

import numpy as np

TOL = 1e-8
ROOT = "/home/ahmed/killr_projects/killr/packages/deSolve/proof"

r_out = subprocess.check_output(
    ["R", "--slave"],
    input=open(f"{ROOT}/daspk-r.R").read(),
    text=True,
)
py_out = subprocess.check_output([sys.executable, f"{ROOT}/daspk-py.py"], text=True)
r_data = json.loads(r_out)
py_data = json.loads(py_out)
r_val = np.array(r_data["value"], dtype=np.float64)
py_val = np.array(py_data["value"], dtype=np.float64)
max_diff = float(np.max(np.abs(r_val - py_val)))
matches = max_diff <= TOL
print(
    json.dumps(
        {
            "matches": matches,
            "max_abs_diff": max_diff,
            "r_ms": r_data["median_ms"],
            "translated_ms": py_data["median_ms"],
            "tolerance": TOL,
        }
    )
)
