"""Proof for the pbivnorm Rust crate: Python side.

Run after grid_proof_r.R from the repository root:
    .venv/bin/python packages/pbivnorm/proof/grid_proof_py.py

Reads the grid and R values that grid_proof_r.R wrote, calls the Rust kernel
through pyo3, and compares within 1e-8. One untimed call, then the median of
20 timed calls with time.perf_counter(). Does not call R.
"""

import csv
import statistics
import time
from pathlib import Path

import numpy as np

from pbivnorm import pbivnorm

OUT = Path("packages/pbivnorm/docs/output")
TOLERANCE = 1e-8


def read_column(path, name):
    with open(path, newline="") as handle:
        return np.array([float(row[name]) for row in csv.DictReader(handle)], dtype=np.float64)


def read_r_timings(path):
    with open(path, newline="") as handle:
        return [float(row["seconds"]) for row in csv.DictReader(handle)]


def main():
    x = read_column(OUT / "grid.csv", "x")
    y = read_column(OUT / "grid.csv", "y")
    rho = read_column(OUT / "grid.csv", "rho")
    r_values = read_column(OUT / "r_values.csv", "r_value")
    r_times = read_r_timings(OUT / "r_timings.csv")

    py_values = pbivnorm(x, y, rho)  # untimed warm-up call

    times = []
    for _ in range(20):
        t0 = time.perf_counter()
        py_values = pbivnorm(x, y, rho)
        times.append(time.perf_counter() - t0)

    max_abs_diff = float(np.max(np.abs(py_values - r_values)))
    py_median = statistics.median(times)
    r_median = statistics.median(r_times)
    speedup = r_median / py_median
    matches = max_abs_diff < TOLERANCE

    summary = "\n".join([
        "pbivnorm Rust crate vs R pbivnorm 0.6.0 (Fortran PBIVNORM)",
        f"grid points: {x.size}",
        f"max abs diff: {max_abs_diff:.3e} (tolerance {TOLERANCE:g}, matches: {matches})",
        f"R median time (20 calls, Sys.time): {r_median:.6f} s",
        f"Rust median time (20 calls, time.perf_counter): {py_median:.6f} s",
        f"speedup (R / Rust): {speedup:.2f}",
        "",
    ])
    (OUT / "proof_summary.txt").write_text(summary)
    print(summary)

    if not matches:
        raise SystemExit("proof failed: max abs diff exceeds tolerance")


if __name__ == "__main__":
    main()
