#!/usr/bin/env python3
"""Compare R and Python proof outputs for coords."""

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


def compare_mat(r_mat, py_mat) -> float:
    if len(r_mat) != len(py_mat):
        return math.inf
    worst = 0.0
    for r_row, py_row in zip(r_mat, py_mat, strict=True):
        if len(r_row) != len(py_row):
            return math.inf
        for r_cell, py_cell in zip(r_row, py_row, strict=True):
            worst = max(worst, abs(float(r_cell) - float(py_cell)))
    return worst


def main() -> None:
    py_out = json.loads(run([sys.executable, str(PROOF / "coords-py.py")], cwd=ROOT))
    r_out = json.loads(run(["R", "--slave", "-f", str(PROOF / "coords-r.R")], cwd=ROOT))

    keys = [k for k in r_out if k != "median_ms"]
    max_abs_diff = max(compare_mat(r_out[k], py_out[k]) for k in keys)
    matches = max_abs_diff <= TOL
    print(
        json.dumps(
            {
                "matches": matches,
                "r_ms": r_out["median_ms"],
                "translated_ms": py_out["median_ms"],
                "speedup": r_out["median_ms"] / py_out["median_ms"],
                "max_abs_diff": max_abs_diff,
                "tolerance": TOL,
            }
        )
    )
    sys.exit(0 if matches else 1)


if __name__ == "__main__":
    main()
