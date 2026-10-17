import json
import subprocess
import sys

TOL = 1e-8
ROOT = "/home/ahmed/killr_projects/killr/packages/deSolve/proof"

r_proc = subprocess.run(
    ["R", "--slave", "-f", f"{ROOT}/DLLfunc-r.R"],
    check=True,
    capture_output=True,
    text=True,
)
r_out = json.loads(r_proc.stdout)
py_proc = subprocess.run(
    [sys.executable, f"{ROOT}/DLLfunc-py.py"],
    check=True,
    capture_output=True,
    text=True,
)
py_out = json.loads(py_proc.stdout)
max_abs_diff = max(abs(a - b) for a, b in zip(r_out["value"], py_out["value"], strict=True))
matches = max_abs_diff <= TOL
print(
    json.dumps(
        {
            "r_ms": r_out["median_ms"],
            "translated_ms": py_out["median_ms"],
            "max_abs_diff": max_abs_diff,
            "matches": matches,
        }
    )
)
