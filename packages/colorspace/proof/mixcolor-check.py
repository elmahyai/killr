#!/usr/bin/env python3
"""Compare R and Python proof outputs for mixcolor."""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF = Path(__file__).resolve().parent
TOL = 1e-8
ENV = {**os.environ, "PYTHONPATH": str(ROOT)}


def run(cmd: list[str], *, cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True, env=ENV).strip()


def compare_color(r_block, py_block) -> float:
    if r_block["space"] != py_block["space"]:
        return math.inf
    r_coords = r_block["coords"]
    py_coords = py_block["coords"]
    if len(r_coords) != len(py_coords):
        return math.inf
    worst = 0.0
    for r_row, py_row in zip(r_coords, py_coords, strict=True):
        if len(r_row) != len(py_row):
            return math.inf
        for r_v, py_v in zip(r_row, py_row, strict=True):
            worst = max(worst, abs(float(r_v) - float(py_v)))
    return worst


def main() -> None:
    py_out = json.loads(run([sys.executable, str(PROOF / "mixcolor-py.py")], cwd=ROOT))
    r_out = json.loads(run(["Rscript", str(PROOF / "mixcolor-r.R")], cwd=ROOT))

    keys = [k for k in r_out if k != "median_ms"]
    max_abs_diff = 0.0
    for key in keys:
        max_abs_diff = max(max_abs_diff, compare_color(r_out[key], py_out[key]))

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
