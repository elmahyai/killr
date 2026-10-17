#!/usr/bin/env python3
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


def run(cmd):
    return subprocess.check_output(cmd, cwd=ROOT, text=True, env=ENV).strip()


def main():
    py = json.loads(run([sys.executable, str(PROOF / "print.xtable-py.py")]))
    r = json.loads(run(["R", "--slave", "-f", str(PROOF / "print.xtable-r.R")]))
    diff = 0.0 if py["value"] == r["value"] else math.inf
    matches = diff <= TOL
    print(
        json.dumps(
            {
                "matches": matches,
                "r_ms": r["median_ms"],
                "translated_ms": py["median_ms"],
                "speedup": r["median_ms"] / py["median_ms"],
                "max_abs_diff": diff,
                "tolerance": TOL,
            }
        )
    )
    sys.exit(0 if matches else 1)


if __name__ == "__main__":
    main()
