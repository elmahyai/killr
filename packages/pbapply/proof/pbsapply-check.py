import json
import os
import subprocess
import sys

TOL = 1e-8
ROOT = "/home/ahmed/killr_projects/killr"
r_proc = subprocess.run(
    ["R", "--slave", "-f", f"{ROOT}/packages/pbapply/proof/pbsapply-r.R"],
    check=True,
    capture_output=True,
    text=True,
)
py_proc = subprocess.run(
    [sys.executable, f"{ROOT}/packages/pbapply/proof/pbsapply-py.py"],
    check=True,
    capture_output=True,
    text=True,
    env={**os.environ, "PYTHONPATH": f"{ROOT}/packages/pbapply"},
)
r_out = json.loads(r_proc.stdout)
py_out = json.loads(py_proc.stdout)
max_abs_diff = 0.0
if len(r_out["value"]) != len(py_out["value"]):
    max_abs_diff = float("inf")
else:
    for r_value, py_value in zip(r_out["value"], py_out["value"], strict=True):
        max_abs_diff = max(max_abs_diff, abs(float(r_value) - float(py_value)))
matches = max_abs_diff <= TOL
print(
    json.dumps(
        {
            "function": "pbsapply",
            "r_ms": r_out["median_ms"],
            "translated_ms": py_out["median_ms"],
            "speedup": r_out["median_ms"] / py_out["median_ms"],
            "max_abs_diff": max_abs_diff,
            "matches": matches,
        }
    )
)
if not matches:
    sys.stderr.write(r_proc.stdout + "\n" + py_proc.stdout + "\n")
    raise SystemExit(1)
