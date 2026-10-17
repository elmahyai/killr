#!/usr/bin/env python3
"""Compare R and Python proof JSON outputs."""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

TOL = 1e-8
ROOT = Path(__file__).resolve().parent
PKG = ROOT.parent


def compare(a, b) -> float:
    if a is None and b is None:
        return 0.0
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if isinstance(a, bool) or isinstance(b, bool):
            return 0.0 if a == b else math.inf
        return abs(float(a) - float(b))
    if isinstance(a, str) and isinstance(b, str):
        return 0.0 if a == b else math.inf
    if type(a) is not type(b):
        return math.inf
    if isinstance(a, list):
        if len(a) != len(b):
            return math.inf
        return max(compare(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, dict):
        if set(a) != set(b):
            return math.inf
        return max(compare(a[k], b[k]) for k in a)
    return 0.0 if a == b else math.inf


def main(name: str) -> None:
    py_out = json.loads(
        subprocess.check_output(
            [sys.executable, str(ROOT / f"{name}-py.py")], cwd=PKG, text=True
        )
    )
    r_out = json.loads(
        subprocess.check_output(
            ["R", "--slave", "-f", str(ROOT / f"{name}-r.R")], cwd=PKG, text=True
        )
    )
    diff = compare(r_out["value"], py_out["value"])
    matches = diff <= TOL
    print(
        json.dumps(
            {
                "name": name,
                "matches": matches,
                "max_abs_diff": diff,
                "tolerance": TOL,
                "r_ms": r_out["median_ms"],
                "translated_ms": py_out["median_ms"],
                "speedup": r_out["median_ms"] / py_out["median_ms"],
            }
        )
    )
    if not matches:
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1])
