#!/usr/bin/env python3
"""Compare R and Python proof outputs for choose_color."""

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


def main() -> None:
    py_out = json.loads(
        run([sys.executable, str(PROOF / "choose_color-py.py")], cwd=ROOT)
    )
    r_out = json.loads(
        run(["R", "--slave", "-f", str(PROOF / "choose_color-r.R")], cwd=ROOT)
    )

    matches = (
        py_out["default_color"] == r_out["default_color"]
        and py_out["traced_color"] == r_out["traced_color"]
        and py_out["default_trace"] == r_out["default_trace"]
        and py_out["traced_trace"] == r_out["traced_trace"]
    )
    max_abs_diff = 0.0 if matches else math.inf

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
