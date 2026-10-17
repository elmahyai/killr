#!/usr/bin/env python3
"""Run one R and one Python proof, then compare their outputs.

Usage: python3 check_e1071.py NAME

NAME is the function name, for example best.tune. The scripts are
NAME-r.R and NAME-py.py. Each writes its timing and values to
NAME-r-out.json and NAME-py-out.json. The printed example is saved to
docs/output/NAME-r.txt and docs/output/NAME-python.txt.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROOF = Path(__file__).resolve().parent
OUTPUT = ROOT / "packages/e1071/docs/output"
TOL = 1e-8


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, env=dict(os.environ))


def main() -> None:
    name = sys.argv[1]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    r_run = run(["Rscript", str(PROOF / f"{name}-r.R")])
    py_run = run([sys.executable, str(PROOF / f"{name}-py.py")])
    if r_run.returncode != 0 or py_run.returncode != 0:
        print(json.dumps({"matches": False, "error": (r_run.stderr + py_run.stderr)[-2000:]}))
        sys.exit(1)
    (OUTPUT / f"{name}-r.txt").write_text(r_run.stdout)
    (OUTPUT / f"{name}-python.txt").write_text(py_run.stdout)

    r_out = json.loads((PROOF / f"{name}-r-out.json").read_text())
    py_out = json.loads((PROOF / f"{name}-py-out.json").read_text())
    r_vals = r_out["value"]
    py_vals = py_out["value"]
    if len(r_vals) != len(py_vals):
        max_abs_diff = math.inf
    else:
        max_abs_diff = 0.0
        for r_v, py_v in zip(r_vals, py_vals, strict=True):
            r_f, py_f = float(r_v), float(py_v)
            if math.isnan(r_f) and math.isnan(py_f):
                continue
            max_abs_diff = max(max_abs_diff, abs(r_f - py_f))
    matches = max_abs_diff <= TOL
    r_ms = r_out["median_ms"]
    py_ms = py_out["median_ms"]
    print(
        json.dumps(
            {
                "function": name,
                "matches": matches,
                "max_abs_diff": max_abs_diff,
                "r_ms": r_ms,
                "translated_ms": py_ms,
                "speedup": r_ms / py_ms,
            }
        )
    )
    sys.exit(0 if matches else 1)


if __name__ == "__main__":
    main()
