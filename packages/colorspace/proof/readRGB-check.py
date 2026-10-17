#!/usr/bin/env python3
"""Compare R and Python proof outputs for readRGB."""

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


def compare_color(r_obj, py_obj) -> float:
    if r_obj["space"] != py_obj["space"]:
        return math.inf
    if r_obj["names"] != py_obj["names"]:
        return math.inf
    if r_obj["columns"] != py_obj["columns"]:
        return math.inf
    worst = 0.0
    for r_row, py_row in zip(r_obj["coords"], py_obj["coords"], strict=True):
        for r_v, py_v in zip(r_row, py_row, strict=True):
            worst = max(worst, abs(float(r_v) - float(py_v)))
    return worst


def main() -> None:
    py_out = json.loads(run([sys.executable, str(PROOF / "readRGB-py.py")], cwd=ROOT))
    r_out = json.loads(run(["R", "--slave", "-f", str(PROOF / "readRGB-r.R")], cwd=ROOT))

    keys = [k for k in r_out if k != "median_ms"]
    max_abs_diff = 0.0
    worst_case = keys[0]
    for key in keys:
        diff = compare_color(r_out[key], py_out[key])
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
