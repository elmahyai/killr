"""Proof: isoband.isobands.isobands against R isoband 0.3.0 isobands().

Run after isobands-r.R has written docs/output/isobands-r.txt. Prints this run's
output on stdout (same format as the R output). Prints the comparison on stderr.
"""

from __future__ import annotations

import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

from isoband.isobands import isobands

OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "output"
R_FILE = OUT_DIR / "isobands-r.txt"
TOL = 1e-8


def make_cases():
    sizes = [(5, 7), (20, 30), (60, 80), (150, 120)]
    cases = []
    for nr, nc in sizes:
        x = np.array([k / (nc - 1) for k in range(nc)])
        y = np.array([r / (nr - 1) * 1.5 for r in range(nr)])
        z_smooth = np.zeros((nr, nc))
        z_int = np.zeros((nr, nc))
        for r in range(nr):
            for k in range(nc):
                z_smooth[r, k] = math.sin(3 * x[k]) * math.cos(2 * y[r]) + 0.5 * x[k] * y[r]
                v = ((7 * r + 13 * k + 3 * r * k) % 11) / 10
                if (r + 2 * k) % 9 == 0:
                    v = math.nan
                z_int[r, k] = v
        cases.append(
            {
                "name": f"smooth_{nr}x{nc}",
                "x": x,
                "y": y,
                "z": z_smooth,
                "low": [-0.4, 0.0, 0.8, 0.5],
                "high": [0.0, 0.3, 0.3, 1.2],
            }
        )
        cases.append(
            {
                "name": f"int_{nr}x{nc}",
                "x": x,
                "y": y,
                "z": z_int,
                "low": [0.0, 0.25, 0.5],
                "high": [0.25, 0.5, 1.0],
            }
        )
    return cases


def run_all(cases):
    return [isobands(cs["x"], cs["y"], cs["z"], cs["low"], cs["high"]) for cs in cases]


def emit(res, cases):
    lines = []
    for k, cs in enumerate(cases):
        for g, el in enumerate(res[k], start=1):
            lines.append(f"G\t{cs['name']}\t{g}")
            for xv, yv, iv in zip(el["x"], el["y"], el["id"]):
                lines.append(f"P\t{cs['name']}\t{g}\t{xv:.17g}\t{yv:.17g}\t{int(iv)}")
    return lines


def read_r(path):
    groups = {}
    r_ms = None
    for line in path.read_text().splitlines():
        parts = line.split("\t")
        if line.startswith("r_ms"):
            r_ms = float(line.split()[1])
        elif parts[0] == "G":
            groups.setdefault((parts[1], int(parts[2])), [])
        elif parts[0] == "P":
            groups.setdefault((parts[1], int(parts[2])), []).append(
                (float(parts[3]), float(parts[4]), int(parts[5]))
            )
    return groups, r_ms


def compare(res, cases, r_groups):
    max_diff = 0.0
    matched = True
    py_groups = {}
    for k, cs in enumerate(cases):
        for g, el in enumerate(res[k], start=1):
            rows = list(zip(el["x"].tolist(), el["y"].tolist(), el["id"].tolist()))
            py_groups[(cs["name"], g)] = rows
    if set(py_groups) != set(r_groups):
        matched = False
    for key, rows in py_groups.items():
        ref = r_groups.get(key, [])
        if len(rows) != len(ref):
            matched = False
            continue
        for (px, py_, pid), (rx, ry, rid) in zip(rows, ref):
            if pid != rid:
                matched = False
            max_diff = max(max_diff, abs(px - rx), abs(py_ - ry))
    if max_diff > TOL:
        matched = False
    return matched, max_diff


def main():
    cases = make_cases()
    run_all(cases)  # untimed call
    elapsed = []
    res = None
    for _ in range(20):
        t0 = time.perf_counter()
        res = run_all(cases)
        elapsed.append(time.perf_counter() - t0)
    py_ms = statistics.median(elapsed) * 1000
    print(f"py_ms {py_ms:.17g}")
    print("\n".join(emit(res, cases)))

    r_groups, r_ms = read_r(R_FILE)
    matched, max_diff = compare(res, cases, r_groups)
    speedup = r_ms / py_ms if r_ms and py_ms else float("nan")
    print(
        f"isoband.isobands.isobands matched={'yes' if matched else 'no'} "
        f"max_abs_diff={max_diff:.3g} r_ms={r_ms:.6g} py_ms={py_ms:.6g} speedup={speedup:.4g}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
