#!/usr/bin/env python3
"""Compare R and Python proof outputs for hcl_palettes."""

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
    return 0.0 if r_vals == py_vals else math.inf


def compare_frame(r_frame, py_frame) -> float:
    worst = compare_chr(r_frame["names"], py_frame["names"])
    worst = max(worst, compare_chr(r_frame["type"], py_frame["type"]))
    for key in ("h1", "h2", "c1", "c2", "l1", "l2", "p1", "p2", "cmax"):
        worst = max(worst, compare_num(r_frame[key], py_frame[key]))
    if r_frame["fixup"] != py_frame["fixup"]:
        return math.inf
    return worst


def main() -> None:
    py_out = json.loads(run([sys.executable, str(PROOF / "hcl_palettes-py.py")], cwd=ROOT))
    r_out = json.loads(run(["Rscript", str(PROOF / "hcl_palettes-r.R")], cwd=ROOT))

    keys = [k for k in r_out if k not in ("median_ms", "print_set2")]
    max_abs_diff = 0.0
    for key in keys:
        max_abs_diff = max(max_abs_diff, compare_frame(r_out[key], py_out[key]))
    norm = lambda lines: [" ".join(line.split()) for line in lines]
    if norm(r_out["print_set2"]) != norm(py_out["print_set2"]):
        max_abs_diff = math.inf

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
