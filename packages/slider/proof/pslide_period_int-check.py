#!/usr/bin/env python3
"""Compare R and Python proof outputs for pslide_period_int."""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF = Path(__file__).resolve().parent
TOL = 1e-8


def run(cmd: list[str], *, cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True).strip()


def main() -> None:
    py_out = json.loads(run([sys.executable, str(PROOF / "pslide_period_int-py.py")], cwd=ROOT))
    r_out = json.loads(run(["Rscript", str(PROOF / "pslide_period_int-r.R")], cwd=ROOT))

    r_vals = r_out["value"]
    py_vals = py_out["value"]
    if len(r_vals) != len(py_vals):
        print(json.dumps({"matches": False, "error": "length mismatch"}))
        sys.exit(1)

    max_abs_diff = 0.0
    for r_v, py_v in zip(r_vals, py_vals):
        if r_v is None and py_v is None:
            continue
        if r_v is None or py_v is None:
            max_abs_diff = math.inf
            continue
        max_abs_diff = max(max_abs_diff, abs(float(r_v) - float(py_v)))

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
    sys.exit(0 if matches else 1)


if __name__ == "__main__":
    main()
