import json
import subprocess
import sys

TOL = 1e-8

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/deSolve")
from scoc import scocder_py

r_proc = subprocess.run(
    ["R", "--slave", "-f", "/home/ahmed/killr_projects/killr/packages/deSolve/proof/SCOC-r.R"],
    check=True,
    capture_output=True,
    text=True,
)
r_out = json.loads(r_proc.stdout)
py_proc = subprocess.run(
    [sys.executable, "/home/ahmed/killr_projects/killr/packages/deSolve/proof/SCOC-py.py"],
    check=True,
    capture_output=True,
    text=True,
)
py_timed = json.loads(py_proc.stdout)

py_out = []
pts = [
    (0.01, 63.00301, 0.654),
    (0.01, 34.3997631, 0.2205),
    (0.01, 72.98281, 1.135),
    (0.02, 10.0, 0.5),
    (0.005, 100.0, 0.0),
]
for k, y, depo in pts:
    ydot, mineralisation, depo_out = scocder_py(k, y, depo)
    py_out.extend([ydot, mineralisation, depo_out])

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
            "proof_case": "scocder at five (k,y,depo) points",
        }
    )
)
sys.exit(0 if matches else 1)
