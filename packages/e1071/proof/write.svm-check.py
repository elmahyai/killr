import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_json(script: Path) -> dict:
    if script.suffix == ".R":
        proc = subprocess.run(
            ["R", "--slave", "-f", str(script)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(proc.stdout)
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def numeric_fields(text: str) -> list[float]:
    return [float(match) for match in re.findall(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", text)]


r_out = load_json(ROOT / "write.svm-r.R")
py_out = load_json(ROOT / "write.svm-py.py")

matches = r_out["text"] == py_out["text"]
max_abs_diff = 0.0
if not matches:
    r_nums = numeric_fields(r_out["text"])
    py_nums = numeric_fields(py_out["text"])
    if len(r_nums) == len(py_nums):
        max_abs_diff = max(abs(a - b) for a, b in zip(r_nums, py_nums, strict=True))

print(
    json.dumps(
        {
            "matches": matches,
            "max_abs_diff": max_abs_diff,
            "r_median_ms": r_out["median_ms"],
            "py_median_ms": py_out["median_ms"],
        }
    )
)
if not matches and max_abs_diff > 1e-8:
    sys.exit(1)
