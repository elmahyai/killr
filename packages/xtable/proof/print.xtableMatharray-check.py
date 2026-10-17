#!/usr/bin/env python3
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


def run(cmd):
    return subprocess.check_output(cmd, cwd=ROOT, text=True, env=ENV).strip()


def array_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in text.splitlines():
        if "&" not in line:
            continue
        body = line.split("\\\\")[0]
        rows.append([cell.strip() for cell in body.split("&")])
    return rows


def main():
    py = json.loads(run([sys.executable, str(PROOF / "print.xtableMatharray-py.py")]))
    r = json.loads(run(["R", "--slave", "-f", str(PROOF / "print.xtableMatharray-r.R")]))
    py_rows = array_rows(py["value"])
    r_rows = array_rows(r["value"])
    diff = 0.0 if py_rows == r_rows else math.inf
    if diff == 0.0:
        if "array" not in py["value"] or "array" not in r["value"]:
            diff = math.inf
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
