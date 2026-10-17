#!/usr/bin/env python3
"""Compare R and Python proof outputs for specplot."""

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


def compare_num(r_vals, py_vals) -> float:
    if len(r_vals) != len(py_vals):
        return math.inf
    worst = 0.0
    for r_v, py_v in zip(r_vals, py_vals, strict=True):
        if r_v is None and py_v is None:
            continue
        if r_v is None or py_v is None:
            return math.inf
        worst = max(worst, abs(float(r_v) - float(py_v)))
    return worst


def compare_chr(r_vals, py_vals) -> float:
    if r_vals != py_vals:
        return math.inf
    return 0.0


def compare_matrix(r_mat, py_mat) -> float:
    if len(r_mat) != len(py_mat):
        return math.inf
    worst = 0.0
    for r_row, py_row in zip(r_mat, py_mat, strict=True):
        worst = max(worst, compare_num(r_row, py_row))
    return worst


def compare_result(r_res, py_res) -> float:
    worst = compare_matrix(r_res["HCL"], py_res["HCL"])
    worst = max(worst, compare_matrix(r_res["RGB"], py_res["RGB"]))
    worst = max(worst, compare_chr(r_res["hex"], py_res["hex"]))
    return worst


def main() -> None:
    py_out = json.loads(run([sys.executable, str(PROOF / "specplot-py.py")], cwd=ROOT))
    r_out = json.loads(run(["R", "--slave", "-f", str(PROOF / "specplot-r.R")], cwd=ROOT))

    keys = [k for k in r_out if k != "median_ms"]
    max_abs_diff = 0.0
    worst_case = keys[0]
    for key in keys:
        diff = compare_result(r_out[key], py_out[key])
        if diff > max_abs_diff:
            max_abs_diff = diff
            worst_case = key

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
                "case": worst_case,
            }
        )
    )
    sys.exit(0 if matches else 1)


if __name__ == "__main__":
    main()
