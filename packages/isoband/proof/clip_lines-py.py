"""Proof: isoband.clip_lines.clip_lines against R isoband 0.3.0 clip_lines().

Run after clip_lines-r.R has written docs/output/clip_lines-r.txt. Prints this run's
output on stdout (same format as the R output). Prints the comparison on stderr.
"""

from __future__ import annotations

import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

from isoband.clip_lines import clip_lines

OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "output"
R_FILE = OUT_DIR / "clip_lines-r.txt"
TOL = 1e-8

BOXES = {
    "x": [0.5, 0.2, 0.8, 0.5, 0.35],
    "y": [0.5, 0.7, 0.3, 0.9, 0.2],
    "width": [0.3, 0.25, 0.4, 0.5, 0.2],
    "height": [0.2, 0.15, 0.1, 0.2, 0.3],
    "theta": [0.3, -0.8, 1.2, 0.0, 0.7],
}


def make_cases():
    n = 200
    t = [i / (n - 1) * 2 * math.pi for i in range(n)]
    xa, ya, ida = [], [], []
    for k in (1, 2, 3):
        xa += [0.5 + 0.45 * math.cos(tv + k) for tv in t]
        ya += [0.5 + 0.45 * math.sin(1.3 * tv + k) for tv in t]
        ida += [k] * n

    m = 300
    t2 = [i / (m - 1) * 2 * math.pi for i in range(m)]
    xc = [0.5 + 0.4 * math.cos(tv) for tv in t2]
    yc = [0.5 + 0.4 * math.sin(tv) for tv in t2]
    idc = [1] * m

    zz = 200
    xz = [i / (zz - 1) for i in range(zz)]
    yz = [((i * 37) % 101) / 100 for i in range(zz)]
    idz = [i // 25 + 1 for i in range(zz)]

    return [
        {"name": "curves", "x": xa, "y": ya, "id": ida, "asp": 1.25},
        {"name": "circle", "x": xc, "y": yc, "id": idc, "asp": 1.25},
        {"name": "zigzag", "x": xz, "y": yz, "id": idz, "asp": 0.8},
    ]


def run_all(cases):
    return [
        clip_lines(
            np.asarray(cs["x"]), np.asarray(cs["y"]), np.asarray(cs["id"]), BOXES, asp=cs["asp"]
        )
        for cs in cases
    ]


def emit(res, cases):
    lines = []
    for k, cs in enumerate(cases):
        lines.append(f"G\t{cs['name']}\t1")
        el = res[k]
        for xv, yv, iv in zip(el["x"], el["y"], el["id"]):
            lines.append(f"P\t{cs['name']}\t1\t{xv:.17g}\t{yv:.17g}\t{int(iv)}")
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
        el = res[k]
        py_groups[(cs["name"], 1)] = list(
            zip(el["x"].tolist(), el["y"].tolist(), el["id"].tolist())
        )
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
        f"isoband.clip_lines.clip_lines matched={'yes' if matched else 'no'} "
        f"max_abs_diff={max_diff:.3g} r_ms={r_ms:.6g} py_ms={py_ms:.6g} speedup={speedup:.4g}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
