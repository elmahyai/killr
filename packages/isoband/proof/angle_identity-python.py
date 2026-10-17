"""Proof: isoband.angle_identity against R isoband 0.3.0 angle_identity().

Run after angle_identity-r.R has written docs/output/angle_identity-r.txt. Prints this
run's output on stdout (same format as the R output). Prints the comparison on stderr.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from _proof_io import emit_fields, run_proof

from isoband.angle_identity import angle_identity


def make_cases():
    n = 2000
    grid = -3 * math.pi + 6 * math.pi * np.arange(n) / (n - 1)
    m = 1000
    wide = -10 + 20 * np.arange(m) / (m - 1)
    return [
        {"name": "grid", "theta": grid},
        {"name": "wide", "theta": wide},
    ]


def run_all(cases):
    return [angle_identity()(cs["theta"]) for cs in cases]


def emit(res, cases):
    lines: list[str] = []
    for k, cs in enumerate(cases):
        emit_fields(lines, cs["name"], {"out": res[k]})
    return lines


if __name__ == "__main__":
    cases = make_cases()
    run_proof("angle_identity", cases, cases * 200, run_all, emit)
