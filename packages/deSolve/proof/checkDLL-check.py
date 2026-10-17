import json
import subprocess
import sys

TOL = 1e-8

ROOT = "/home/ahmed/killr_projects/killr"
r_proc = subprocess.run(
    ["R", "--slave", "-f", f"{ROOT}/packages/deSolve/proof/checkDLL-r.R"],
    check=True,
    capture_output=True,
    text=True,
)
py_proc = subprocess.run(
    [sys.executable, f"{ROOT}/packages/deSolve/proof/checkDLL-py.py"],
    check=True,
    capture_output=True,
    text=True,
)
r_out = json.loads(r_proc.stdout)
py_out = json.loads(py_proc.stdout)

max_abs_diff = 0.0
if len(r_out["value"]) != len(py_out["value"]):
    max_abs_diff = float("inf")
else:
    for r_value, py_value in zip(r_out["value"], py_out["value"], strict=True):
        max_abs_diff = max(max_abs_diff, abs(r_value - py_value))

matches = max_abs_diff <= TOL
print(
    json.dumps(
        {
            "r_ms": r_out["median_ms"],
            "translated_ms": py_out["median_ms"],
            "max_abs_diff": max_abs_diff,
            "matches": matches,
            "n": len(r_out["value"]),
        }
    )
)
if not matches:
    sys.stderr.write(r_proc.stdout + "\n" + py_proc.stdout + "\n")
    if r_proc.stderr:
        sys.stderr.write(r_proc.stderr + "\n")
    if py_proc.stderr:
        sys.stderr.write(py_proc.stderr + "\n")
    raise SystemExit(1)
