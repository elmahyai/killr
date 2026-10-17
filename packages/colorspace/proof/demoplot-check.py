#!/usr/bin/env python3
"""Compare R and Python proof outputs for demoplot palette use."""

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


def compare_block(r_block, py_block) -> float:
    if r_block.get("type") != py_block.get("type"):
        return math.inf
    r_colors = r_block["colors"]
    py_colors = py_block["colors"]
    if len(r_colors) != len(py_colors):
        return math.inf
    for r_c, py_c in zip(r_colors, py_colors, strict=True):
        if r_c != py_c:
            return math.inf
    if "matrix" in r_block and "matrix" in py_block:
        r_mat = r_block["matrix"]
        py_mat = py_block["matrix"]
        if len(r_mat) != len(py_mat):
            return math.inf
        for r_row, py_row in zip(r_mat, py_mat, strict=True):
            if len(r_row) != len(py_row):
                return math.inf
            for r_cell, py_cell in zip(r_row, py_row, strict=True):
                if abs(float(r_cell) - float(py_cell)) > TOL:
                    return math.inf
    if r_block.get("matrix_shape") != py_block.get("matrix_shape"):
        return math.inf
    if r_block.get("border_black") != py_block.get("border_black"):
        return math.inf
    return 0.0


def main() -> None:
    py_out = json.loads(run([sys.executable, str(PROOF / "demoplot-py.py")], cwd=ROOT))
    r_out = json.loads(run(["R", "--slave", "-f", str(PROOF / "demoplot-r.R")], cwd=ROOT))

    keys = [k for k in r_out if k != "median_ms"]
    max_abs_diff = max(compare_block(r_out[k], py_out[k]) for k in keys)
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
