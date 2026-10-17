#!/usr/bin/env python3
"""Compare R and Python proof outputs for darken."""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF = Path(__file__).resolve().parent
NAME = "darken"
TOL = 1e-8
ENV = {**os.environ, "PYTHONPATH": str(ROOT)}


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, cwd=ROOT, text=True, env=ENV).strip()


def _is_hex(text: str) -> bool:
    return (
        text.startswith("#")
        and len(text) in (7, 9)
        and all(ch in "0123456789abcdefABCDEF" for ch in text[1:])
    )


def _channels(text: str) -> list[float]:
    body = text[1:]
    return [int(body[i : i + 2], 16) / 255.0 for i in range(0, len(body), 2)]


def compare(r_val, py_val) -> float:
    if r_val is None or py_val is None:
        return 0.0 if r_val is None and py_val is None else math.inf
    if isinstance(r_val, list) or isinstance(py_val, list):
        if not (isinstance(r_val, list) and isinstance(py_val, list)):
            return math.inf
        if len(r_val) != len(py_val):
            return math.inf
        return max((compare(a, b) for a, b in zip(r_val, py_val, strict=True)), default=0.0)
    if isinstance(r_val, str) or isinstance(py_val, str):
        if not (isinstance(r_val, str) and isinstance(py_val, str)):
            return math.inf
        if r_val == py_val:
            return 0.0
        if _is_hex(r_val) and _is_hex(py_val) and len(r_val) == len(py_val):
            return max(abs(a - b) for a, b in zip(_channels(r_val), _channels(py_val), strict=True))
        return math.inf
    return abs(float(r_val) - float(py_val))


def main() -> None:
    py_out = json.loads(run([sys.executable, str(PROOF / f"{NAME}-py.py")]))
    r_out = json.loads(run(["R", "--slave", "-f", str(PROOF / f"{NAME}-r.R")]))

    keys = [k for k in r_out if k != "median_ms"]
    if set(keys) != {k for k in py_out if k != "median_ms"}:
        max_abs_diff = math.inf
    else:
        max_abs_diff = max((compare(r_out[k], py_out[k]) for k in keys), default=0.0)

    matches = max_abs_diff <= TOL
    r_ms = r_out["median_ms"]
    py_ms = py_out["median_ms"]
    print(
        json.dumps(
            {
                "matches": matches,
                "max_abs_diff": max_abs_diff,
                "tolerance": TOL,
                "r_ms": r_ms,
                "translated_ms": py_ms,
                "speedup": r_ms / py_ms,
            }
        )
    )
    sys.exit(0 if matches else 1)


if __name__ == "__main__":
    main()
