import json
import subprocess
import sys

TOL = 1e-8
ROOT = "/home/ahmed/killr_projects/killr/packages/deSolve/proof"

subprocess.run(
    ["R", "--slave", "-f", f"{ROOT}/lagderiv-r.R"],
    check=True,
    capture_output=True,
    text=True,
)
r_out = json.loads(open(f"{ROOT}/lagderiv-r-out.json").read())
py_proc = subprocess.run(
    [sys.executable, f"{ROOT}/lagderiv-py.py"],
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
