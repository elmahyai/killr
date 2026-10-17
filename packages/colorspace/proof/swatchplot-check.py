#!/usr/bin/env python3
"""Compare R and Python proof outputs for swatchplot."""

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


def compare_matrix(r_mat, py_mat) -> float:
    if r_mat["rownames"] != py_mat["rownames"]:
        return math.inf
    if r_mat["colnames"] != py_mat["colnames"]:
        return math.inf
    if len(r_mat["rows"]) != len(py_mat["rows"]):
        return math.inf
    worst = 0.0
    for r_row, py_row in zip(r_mat["rows"], py_mat["rows"], strict=True):
        if len(r_row) != len(py_row):
            return math.inf
        for r_cell, py_cell in zip(r_row, py_row, strict=True):
            if r_cell is None and py_cell is None:
                continue
            if r_cell is None or py_cell is None:
                return math.inf
            if r_cell != py_cell:
                return math.inf
    return worst


def main() -> None:
    py_out = json.loads(run([sys.executable, str(PROOF / "swatchplot-py.py")], cwd=ROOT))
    r_out = json.loads(run(["R", "--slave", "-f", str(PROOF / "swatchplot-r.R")], cwd=ROOT))

    max_abs_diff = compare_matrix(r_out["matrix"], py_out["matrix"])
    matches = max_abs_diff <= TOL
    speedup = r_out["median_ms"] / py_out["median_ms"]
    print(
        json.dumps(
            {
                "matches": matches,
                "r_ms": r_out["median_ms"],
                "translated_ms": py_out["median_ms"],
                "speedup": speedup,
                "max_abs_diff": max_abs_diff,
                "tolerance": TOL,
            }
        )
    )
    sys.exit(0 if matches else 1)


if __name__ == "__main__":
    main()
