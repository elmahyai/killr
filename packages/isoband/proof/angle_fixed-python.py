"""Proof: isoband.angle_fixed.angle_fixed against R isoband 0.3.0 angle_fixed().

Run after angle_fixed-r.R has written docs/output/angle_fixed-r.txt. Prints this run's
output on stdout (same format as the R output). Prints the comparison on stderr.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from _proof_io import emit_fields, run_proof

from isoband.angle_fixed import angle_fixed


def make_cases():
    n = 2000
    x = -1 + 2 * np.arange(n) / (n - 1)
    return [
        {"name": "scalar", "theta": 0.7, "x": x},
        {"name": "recycled", "theta": [0.1, 0.2, 0.3], "x": x[:1001]},
        {"name": "empty", "theta": -1.5, "x": np.zeros(0)},
    ]


def run_all(cases):
    return [angle_fixed(cs["theta"])(cs["x"]) for cs in cases]


def emit(res, cases):
    lines: list[str] = []
    for k, cs in enumerate(cases):
        emit_fields(lines, cs["name"], {"out": res[k]})
    return lines


if __name__ == "__main__":
    cases = make_cases()
    run_proof("angle_fixed", cases, cases * 200, run_all, emit)
