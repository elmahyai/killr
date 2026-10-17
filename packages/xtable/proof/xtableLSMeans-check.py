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


def normalize(value):
    if isinstance(value, str) and value == "xtableList":
        return value
    if isinstance(value, list) and value == ["xtableList"]:
        return "xtableList"
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


def max_diff(a, b):
    a, b = normalize(a), normalize(b)
    if a == b:
        return 0.0
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return math.inf
        return max(max_diff(x, y) for x, y in zip(a, b, strict=True))
    return math.inf if a != b else 0.0


def main():
    py = json.loads(run([sys.executable, str(PROOF / "xtableLSMeans-py.py")]))
    r = json.loads(run(["R", "--slave", "-f", str(PROOF / "xtableLSMeans-r.R")]))
    diff = max_diff(r["value"], py["value"])
    matches = diff <= TOL
    print(json.dumps({"matches": matches, "r_ms": r["median_ms"], "translated_ms": py["median_ms"], "speedup": r["median_ms"] / py["median_ms"], "max_abs_diff": diff, "tolerance": TOL}))
    sys.exit(0 if matches else 1)


if __name__ == "__main__":
    main()
