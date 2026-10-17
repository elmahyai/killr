import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PROOF = Path(__file__).resolve().parent
TOL = 1e-8


def run(cmd):
    return subprocess.check_output(cmd, text=True).strip()


r_out = json.loads(run(["R", "--slave", "-f", str(PROOF / "lsodes-r.R")]))
py_out = json.loads(run([sys.executable, str(PROOF / "lsodes-py.py")]))

r_val = np.array(r_out["value"])
py_val = np.array(py_out["value"])
max_diff = float(np.max(np.abs(r_val - py_val)))
matches = max_diff <= TOL

print(
    json.dumps(
        {
            "matches": matches,
            "max_abs_diff": max_diff,
            "r_ms": r_out["median_ms"],
            "translated_ms": py_out["median_ms"],
            "tolerance": TOL,
        }
    )
)

if not matches:
    sys.exit(1)
