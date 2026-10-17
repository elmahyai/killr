#!/usr/bin/env python3
"""Compare R and Python proof outputs for write.matrix.csr."""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF = Path(__file__).resolve().parent
TOL = 1e-8
ENV = {**os.environ, "PYTHONPATH": str(ROOT)}


def run(cmd: list[str], *, cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True, env=ENV).strip()


def _numeric_diffs(r_text: str, py_text: str) -> float:
    pattern = re.compile(r":(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)")
    r_nums = [float(m.group(1)) for m in pattern.finditer(r_text)]
    py_nums = [float(m.group(1)) for m in pattern.finditer(py_text)]
    max_abs_diff = 0.0
    if len(r_nums) != len(py_nums):
        return math.inf
    for r_v, py_v in zip(r_nums, py_nums, strict=True):
        max_abs_diff = max(max_abs_diff, abs(r_v - py_v))
    return max_abs_diff


def main() -> None:
    py_out = json.loads(
        run([sys.executable, str(PROOF / "write.matrix.csr-py.py")], cwd=ROOT)
    )
    r_out = json.loads(
        run(["R", "--slave", "-f", str(PROOF / "write.matrix.csr-r.R")], cwd=ROOT)
    )

    r_text = r_out["text"]
    py_text = py_out["text"]
    text_matches = r_text == py_text
    max_abs_diff = 0.0 if text_matches else _numeric_diffs(r_text, py_text)
    matches = text_matches and max_abs_diff <= TOL
    print(
        json.dumps(
            {
                "r_ms": r_out["median_ms"],
                "translated_ms": py_out["median_ms"],
                "max_abs_diff": max_abs_diff,
                "matches": matches,
                "r_text": r_text,
                "py_text": py_text,
            }
        )
    )
    sys.exit(0 if matches else 1)


if __name__ == "__main__":
    main()
