#!/usr/bin/env python3
"""Compare R and Python proof outputs for interpolate_cvd_transform."""

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
KEYS = (
    "example",
    "zero",
    "full",
    "above",
    "below",
    "mid",
    "quarter",
    "three_tenths",
    "third",
    "frac",
    "bulk_tritan",
    "bulk_protan",
    "bulk_deutan",
)


def run(cmd: list[str], *, cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True, env=ENV).strip()


def compare_matrices(r_mats, py_mats) -> float:
    if isinstance(r_mats[0][0], list):
        if len(r_mats) != len(py_mats):
            return math.inf
        worst = 0.0
        for r_mat, py_mat in zip(r_mats, py_mats, strict=True):
            worst = max(worst, compare_matrices(r_mat, py_mat))
        return worst
    worst = 0.0
    for r_row, py_row in zip(r_mats, py_mats, strict=True):
        for r_v, py_v in zip(r_row, py_row, strict=True):
            worst = max(worst, abs(float(r_v) - float(py_v)))
    return worst


def main() -> None:
    py_out = json.loads(run([sys.executable, str(PROOF / "interpolate_cvd_transform-py.py")], cwd=ROOT))
    r_out = json.loads(run(["Rscript", str(PROOF / "interpolate_cvd_transform-r.R")], cwd=ROOT))
    max_abs_diff = 0.0
    for key in KEYS:
        max_abs_diff = max(max_abs_diff, compare_matrices(r_out[key], py_out[key]))
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
