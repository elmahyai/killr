"""Proof for cdfkap, cdfln3, cdfpe3, and cdfwak: R lmom 3.3 against the Python modules.

Run from anywhere with the repository venv:
    .venv/bin/python packages/lmom/proof/cdf4_proof.py
The R side runs cdf4_proof.R, which writes R values and R timings. This script
writes the Python values and timings, then compares them. Tolerance is 1e-8.
"""
from __future__ import annotations

import importlib
import statistics
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
OUT = PKG / "docs" / "output"
sys.path.insert(0, str(PKG.parent))  # so that `lmom` is packages/lmom

FUNCS = ["cdfkap", "cdfln3", "cdfpe3", "cdfwak"]
CASES = {
    "cdfkap": [(0, 1, 0.2, 0.1), (1.2, 2.3, -0.25, 0.15), (0, 1, 0, 0), (0, 1, 0.3, -0.2)],
    "cdfln3": [(0.5, 1, 0.2), (-1, 0, 1), (0, 0.3, 0.8), (-0.5, -0.2, 0.6)],
    "cdfpe3": [(0, 1, 0.5), (1.2, 2.3, -0.8), (0, 1, 0), (0, 1, 1e-7), (-1, 2, -0.3)],
    "cdfwak": [(0, 1, 0.5, 0.2, 0.1), (1.2, 2.3, 0.25, 0.8, -0.15), (0, 1, 0, 0, 0),
               (0, 1, 0.5, 0, 0), (0, 0, 0, 0.5, 0.2), (0, 1, 0, 0.3, 0.2), (0, 1, -0.3, 0.2, 0.5)],
}
XS = np.array([-2, -0.5, 0, 0.5, 1, 2, 5, 10], dtype=float)
TOL = 1e-8


def read_r():
    values = {}
    for line in (OUT / "cdf4_r_values.txt").read_text().splitlines():
        parts = line.split()
        values[(parts[0], int(parts[1]))] = np.array([float(v) for v in parts[2:]])
    timings = {}
    for line in (OUT / "cdf4_r_timings.txt").read_text().splitlines():
        name, value = line.split()
        timings[name] = float(value)
    return values, timings


def main() -> int:
    subprocess.run(["Rscript", str(HERE / "cdf4_proof.R")], check=True)
    r_values, r_times = read_r()

    py_lines, py_times = [], {}
    maxdiff = {}
    matches = {}
    for name in FUNCS:
        fn = getattr(importlib.import_module(f"lmom.{name}"), name)
        cases = CASES[name]
        worst = 0.0
        ok = True
        for i, para in enumerate(cases, start=1):
            value = np.asarray(fn(XS, para), dtype=float)
            py_lines.append(f"{name} {i} " + " ".join(f"{v:.17g}" for v in value))
            ref = r_values[(name, i)]
            if ref.shape != value.shape or np.any(np.isnan(ref) != np.isnan(value)):
                ok = False
                worst = float("inf")
                continue
            diff = float(np.nanmax(np.abs(ref - value))) if ref.size else 0.0
            worst = max(worst, diff)
        maxdiff[name] = worst
        matches[name] = ok and worst <= TOL

        para = np.asarray(cases[0], dtype=float)
        call = lambda: fn(XS, para)
        call()
        times = []
        for _ in range(20):
            t = time.perf_counter()
            call()
            times.append(time.perf_counter() - t)
        py_times[name] = statistics.median(times)

    (OUT / "cdf4_python_values.txt").write_text("\n".join(py_lines) + "\n")
    (OUT / "cdf4_python_timings.txt").write_text(
        "\n".join(f"{n} {py_times[n]:.12g}" for n in FUNCS) + "\n")

    summary = []
    for name in FUNCS:
        r_ms = r_times[name] * 1000
        py_ms = py_times[name] * 1000
        summary.append(
            f"{name} {'yes' if matches[name] else 'no'} {maxdiff[name]:.17g} "
            f"{r_ms:.9g} {py_ms:.9g} {r_times[name] / py_times[name]:.9g} "
            f"cases={len(CASES[name])}")
    (OUT / "cdf4_proof.txt").write_text("\n".join(summary) + "\n")
    print("\n".join(summary))
    return 0 if all(matches.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
