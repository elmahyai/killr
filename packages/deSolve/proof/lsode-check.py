import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/ahmed/killr_projects/killr")
proof = ROOT / "packages" / "deSolve" / "proof"

r_out = subprocess.check_output(["R", "--slave", "-f", str(proof / "lsode-r.R")], text=True)
py_out = subprocess.check_output([sys.executable, str(proof / "lsode-py.py")], text=True)
r_json = json.loads(r_out.strip().split("\n")[-1])
py_json = json.loads(py_out.strip())

r_val = r_json["value"]
py_val = py_json["value"]
diffs = [abs(a - b) for a, b in zip(r_val, py_val)]
max_diff = max(diffs)
tol = 1e-8
print(
    json.dumps(
        {
            "matches": max_diff <= tol,
            "max_abs_diff": max_diff,
            "r_ms": r_json["median_ms"],
            "translated_ms": py_json["median_ms"],
        }
    )
)
sys.exit(0 if max_diff <= tol else 1)
