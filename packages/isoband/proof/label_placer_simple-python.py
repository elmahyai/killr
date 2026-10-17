"""Proof: isoband.label_placer_simple against R isoband 0.3.0 label_placer_simple().

Run after label_placer_simple-r.R has written docs/output/label_placer_simple-r.txt.
Prints this run's output on stdout (same format as the R output). Prints the comparison
on stderr.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from _proof_io import emit_fields, run_proof

from isoband.label_placer_simple import LABEL_COLUMNS, label_placer_simple


def make_lines():
    n = 2000
    t = np.arange(n) / (n - 1) * 2 * math.pi
    xs, ys, ids = [], [], []
    for k in (1, 2, 3):
        xs.append(0.5 + 0.45 * np.cos(t + k))
        ys.append(0.5 + 0.45 * np.sin(1.3 * t + k))
        ids.append(np.full(n, k))
    m = 3000
    t2 = np.arange(m) / (m - 1) * 2 * math.pi
    xc = 0.5 + 0.4 * np.cos(t2)
    yc = 0.5 + 0.4 * np.sin(t2)
    xc[m - 1] = xc[0]
    yc[m - 1] = yc[0]
    zz = 2000
    i = np.arange(zz)
    xz = i / (zz - 1)
    yz = ((i * 37) % 101) / 100
    idz = i // 25 + 1
    return [
        {"x": np.concatenate(xs), "y": np.concatenate(ys), "id": np.concatenate(ids)},
        {"x": xc, "y": yc, "id": np.ones(m, dtype=np.int64)},
        {"x": xz, "y": yz, "id": idz},
    ]


def make_labels():
    return {
        "index": np.array([1, 1, 2, 3, 3, 2, 1, 3]),
        "break_index": np.array([1, 1, 1, 2, 2, 2, 1, 2]),
        "break_id": np.array(["0.5", "0.5", "0.5", "0.25", "0.75", "0.5", "0.25", "0.75"], dtype=object),
        "label": np.array(["a", "b", "c", "d", "e", "f", None, "h"], dtype=object),
    }


def my_placer(line_data, break_id):
    x = line_data["x"]
    y = line_data["y"]
    nch = len(str(break_id))
    return {
        "x": np.array([x.mean(), x.max()]),
        "y": np.array([y.mean(), y.max()]),
        "theta": np.array([nch * 0.1, -nch * 0.2]),
    }


def make_cases():
    lines = make_lines()
    labels = make_labels()
    all_na = dict(labels)
    all_na["label"] = np.array([None] * 8, dtype=object)
    return [
        {"name": "two_rows", "lines": lines, "labels": labels},
        {"name": "all_missing_labels", "lines": lines, "labels": all_na},
    ]


def run_all(cases):
    return [label_placer_simple(cs["lines"], cs["labels"], my_placer) for cs in cases]


def emit(res, cases):
    lines: list[str] = []
    for k, cs in enumerate(cases):
        emit_fields(lines, cs["name"], {c: res[k][c] for c in LABEL_COLUMNS})
    return lines


if __name__ == "__main__":
    cases = make_cases()
    run_proof("label_placer_simple", cases, cases * 20, run_all, emit)
