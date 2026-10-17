#!/usr/bin/env python3
"""Compare R and Python proof outputs for cvd_emulator."""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF = Path(__file__).resolve().parent
PNG_ROOT = ROOT.parent / "png"
TOL = 1e-8
ENV = {
    **os.environ,
    "PYTHONPATH": os.pathsep.join([str(ROOT), str(PNG_ROOT)]),
}


def run(cmd: list[str], *, cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True, env=ENV).strip()


def main() -> None:
    py_out = json.loads(
        run([sys.executable, str(PROOF / "cvd_emulator-py.py")], cwd=ROOT)
    )
    r_out = json.loads(
        run(["R", "--slave", "-f", str(PROOF / "cvd_emulator-r.R")], cwd=ROOT)
    )

    max_abs_diff = 0.0
    for a, b in zip(r_out["summaries"], py_out["summaries"], strict=True):
        max_abs_diff = max(max_abs_diff, abs(float(a) - float(b)))

    matches = (
        max_abs_diff <= TOL
        and py_out["shiny_trace"] == r_out["shiny_trace"]
    )

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
