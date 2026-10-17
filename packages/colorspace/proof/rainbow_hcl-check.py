#!/usr/bin/env python3
"""Compare R and Python proof outputs for rainbow_hcl."""

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


def _hex_to_rgb(value: str) -> tuple[float, float, float]:
    body = value[1:7]
    return (
        int(body[0:2], 16) / 255.0,
        int(body[2:4], 16) / 255.0,
        int(body[4:6], 16) / 255.0,
    )


def compare_vec(r_vals, py_vals) -> float:
    if len(r_vals) != len(py_vals):
        return math.inf
    worst = 0.0
    for r_v, py_v in zip(r_vals, py_vals, strict=True):
        if r_v is None and py_v is None:
            continue
        if r_v is None or py_v is None:
            return math.inf
        r_s, py_s = str(r_v), str(py_v)
        if r_s == py_s:
            continue
        r_rgb = _hex_to_rgb(r_s[:7])
        py_rgb = _hex_to_rgb(py_s[:7])
        for a, b in zip(r_rgb, py_rgb, strict=True):
            worst = max(worst, abs(a - b))
    return worst


def main() -> None:
    py_out = json.loads(run([sys.executable, str(PROOF / "rainbow_hcl-py.py")], cwd=ROOT))
    r_out = json.loads(
        run(["R", "--slave", "-f", str(PROOF / "rainbow_hcl-r.R")], cwd=ROOT)
    )

    keys = [k for k in r_out if k != "median_ms"]
    max_abs_diff = 0.0
    for key in keys:
        max_abs_diff = max(max_abs_diff, compare_vec(r_out[key], py_out[key]))

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
