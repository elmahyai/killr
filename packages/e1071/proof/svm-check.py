import json
import subprocess
import sys

TOL = 1e-8


def run(cmd):
    return subprocess.check_output(cmd, text=True).strip()


r_out = json.loads(run(["R", "--slave", "-f", "/home/ahmed/killr_projects/killr/packages/e1071/proof/svm-r.R"]))
py_out = json.loads(
    run(["/home/ahmed/killr_projects/killr/.venv/bin/python", "/home/ahmed/killr_projects/killr/packages/e1071/proof/svm-py.py"])
)
rv = r_out["value"]
pv = py_out["value"]
if len(rv) != len(pv):
    raise SystemExit(f"length mismatch {len(rv)} vs {len(pv)}")
diffs = [abs(a - b) for a, b in zip(rv, pv, strict=True)]
max_diff = max(diffs)
matches = max_diff <= TOL
print(
    json.dumps(
        {
            "matches": matches,
            "max_abs_diff": max_diff,
            "r_median_ms": r_out["median_ms"],
            "python_median_ms": py_out["median_ms"],
        }
    )
)
sys.exit(0 if matches else 1)
